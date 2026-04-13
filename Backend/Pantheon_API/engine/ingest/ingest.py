"""
This file handles the very first step of processing a student submission: taking
whatever file the student uploaded and turning it into a set of source files that
the engine can work with.

A submission can arrive as either a ZIP archive (containing multiple source files)
or a single source file. For ZIP archives, we extract the contents safely into a
temporary working directory, filter out everything that isn't source code, and
detect what programming language the submission is written in.

Security is a major concern here because ZIP files can be crafted maliciously.
We guard against ZIP bombs (archives that decompress to gigabytes of data), path
traversal attacks (archive entries that try to write files outside the destination
directory), unreasonably deep nested ZIPs, and files that are too large to process.
"""

import os
import shutil
import stat
import zipfile
from pathlib import Path

from engine.exceptions import (
    EngineError, CorruptZipError, EmptySubmissionError,
    UnsupportedFileTypeError, ZipTooLargeError,
    ZipBombError, PathTraversalError, NestedZipDepthError,
)

ALLOWED_EXTS = {
    ".java",
    ".c", ".h",
    ".cpp", ".cc", ".cxx",
    ".hpp", ".hxx",
}

MAX_FILES = 5000
MAX_COMPRESSED_BYTES   = 100 * 1024 * 1024   # 100 MB compressed
MAX_UNCOMPRESSED_BYTES = 500 * 1024 * 1024   # 500 MB decompressed total (ZIP bomb guard)
MAX_SINGLE_FILE_BYTES  = 10 * 1024 * 1024    # 10 MB per individual file
MAX_NESTED_ZIP_DEPTH   = 10
MAX_PATH_LENGTH        = 260


def detect_language(files: list) -> str:
    """
    Look at which file extensions are present in the submission and figure out
    what programming language it uses. If the submission mixes multiple languages,
    return "mixed". C and C++ are treated as a single family since many submissions
    contain both .c and .cpp files.
    """
    ext_map = {
        "java": {".java"},
        "c":    {".c", ".h"},
        "cpp":  {".cpp", ".cc", ".cxx", ".hpp", ".hxx"},
        "python": {".py"},
        "javascript": {".js"},
        "typescript": {".ts"},
        "csharp": {".cs"},
        "go":   {".go"},
        "rust": {".rs"},
        "ruby": {".rb"},
    }
    found_langs = set()
    for f in files:
        ext = f.suffix.lower()
        for lang, exts in ext_map.items():
            if ext in exts:
                found_langs.add(lang)

    # C and C++ together just means C++ — treat the submission as cpp.
    if found_langs == {"c", "cpp"} or found_langs == {"c"} or found_langs == {"cpp"}:
        if "cpp" in found_langs:
            return "cpp"
        return "c"
    if len(found_langs) == 1:
        return found_langs.pop()
    if len(found_langs) > 1:
        return "mixed"
    return "mixed"


def _sanitize_zip_entry(entry_name: str, dest: Path) -> Path:
    """
    Compute the safe extraction path for a file inside a ZIP archive.
    ZIP files can contain entries with names like "../../etc/passwd" that,
    if extracted naively, would write files outside the intended destination.
    We strip all leading slashes, dots, and parent-directory references, then
    verify that the resolved path still starts with the destination directory.
    """
    clean = entry_name.replace("\\", "/")
    parts = []
    for part in clean.split("/"):
        if part in ("", ".", ".."):
            continue
        parts.append(part)
    clean = "/".join(parts)

    if len(clean) > MAX_PATH_LENGTH:
        raise PathTraversalError(f"Path too long in ZIP: {len(clean)} chars")

    out_path = (dest / clean).resolve()
    dest_resolved = dest.resolve()

    if not str(out_path).startswith(str(dest_resolved)):
        raise PathTraversalError(f"Path traversal attempt in ZIP: {entry_name}")

    return out_path


def _extract_zip(zip_path: Path, dest: Path, depth: int = 0) -> None:
    """
    Extract a ZIP archive to the destination directory with all safety checks
    in place. If any nested ZIP files are found inside, they are extracted
    recursively up to MAX_NESTED_ZIP_DEPTH levels deep. The nested ZIP files
    themselves are deleted after extraction to avoid leaving them around for
    the source file collector to process.
    """
    if depth > MAX_NESTED_ZIP_DEPTH:
        raise NestedZipDepthError(
            f"ZIP nesting depth {depth} exceeds limit of {MAX_NESTED_ZIP_DEPTH}"
        )

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            entries = zf.infolist()

            if len(entries) > MAX_FILES:
                raise ZipTooLargeError(
                    f"ZIP has {len(entries)} files, limit is {MAX_FILES}"
                )

            # Check the total declared uncompressed size before extracting anything.
            # This is a fast pre-check — the actual decompression check below is
            # the reliable one, since declared sizes can be faked.
            total_declared = sum(e.file_size for e in entries)
            if total_declared > MAX_UNCOMPRESSED_BYTES:
                raise ZipBombError(
                    f"ZIP declared uncompressed size {total_declared} bytes "
                    f"exceeds limit of {MAX_UNCOMPRESSED_BYTES}"
                )

            # A compression ratio over 100:1 is a classic ZIP bomb signature.
            compressed_size = zip_path.stat().st_size
            if compressed_size > 0 and total_declared / compressed_size > 100:
                raise ZipBombError(
                    f"ZIP compression ratio {total_declared / compressed_size:.0f}:1 "
                    f"exceeds safety threshold"
                )

            dest.mkdir(parents=True, exist_ok=True)
            running_bytes = 0
            nested_zips = []

            for entry in entries:
                if entry.is_dir():
                    continue
                name = entry.filename
                if name.startswith("__MACOSX") or "/.DS_Store" in name or name.endswith(".DS_Store"):
                    continue  # skip macOS metadata files

                # Reject symlinks — a symlink inside a ZIP could point anywhere
                # on the filesystem if followed after extraction.
                unix_attrs = entry.external_attr >> 16
                if unix_attrs != 0 and stat.S_ISLNK(unix_attrs):
                    continue

                out_path = _sanitize_zip_entry(name, dest)

                if entry.file_size > MAX_SINGLE_FILE_BYTES:
                    continue  # skip oversized individual files

                running_bytes += entry.file_size
                if running_bytes > MAX_UNCOMPRESSED_BYTES:
                    raise ZipBombError(
                        f"Cumulative decompressed size {running_bytes} bytes "
                        f"exceeds limit during extraction"
                    )

                out_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(entry) as src, open(out_path, "wb") as dst:
                    # Read in chunks rather than all at once. A ZIP can lie about its
                    # declared size, so we enforce the limit on actual bytes read.
                    actual_bytes = 0
                    while True:
                        chunk = src.read(65536)
                        if not chunk:
                            break
                        actual_bytes += len(chunk)
                        if actual_bytes > MAX_SINGLE_FILE_BYTES:
                            dst.close()
                            out_path.unlink(missing_ok=True)
                            break
                        dst.write(chunk)

                if out_path.suffix.lower() == ".zip":
                    nested_zips.append(out_path)

            for nested in nested_zips:
                nested_dest = nested.parent / nested.stem
                try:
                    _extract_zip(nested, nested_dest, depth=depth + 1)
                except EngineError:
                    pass  # if a nested ZIP fails, skip it — the outer files are enough
                finally:
                    nested.unlink(missing_ok=True)

    except zipfile.BadZipFile as e:
        raise CorruptZipError(f"Could not open ZIP file: {e}") from e


def _collect_source_files(root: Path) -> list:
    """Walk the extracted directory and collect every source file with a supported extension."""
    found = []
    for p in root.rglob("*"):
        if p.is_file() and not p.is_symlink() and p.suffix.lower() in ALLOWED_EXTS:
            try:
                sz = p.stat().st_size
                if sz == 0 or sz > MAX_SINGLE_FILE_BYTES:
                    continue
            except OSError:
                continue
            found.append(p)
    return found


def _try_detect_language_by_content(filepath: Path) -> str:
    """
    For files that have no extension (which happens in some submissions), try to
    figure out what language they are by looking at the first 2000 characters of
    the file. Returns a file extension string like ".java" if we recognize it,
    or None if we can't tell.
    """
    try:
        head = filepath.read_text(encoding="utf-8", errors="ignore")[:2000]
    except Exception:
        return None

    if "public class " in head or "import java." in head:
        return ".java"
    if "#include" in head and ("{" in head):
        if "class " in head or "namespace " in head or "template" in head:
            return ".cpp"
        return ".c"
    if "def " in head and "import " in head:
        return ".py"
    if "func " in head and "package " in head:
        return ".go"
    if "fn " in head and ("let mut" in head or "use std" in head):
        return ".rs"
    return None


def ingest_to_dir(upload: Path, out_dir: Path) -> tuple:
    """
    The main entry point for this file. Takes the path to whatever the student
    uploaded and sets up a clean working directory with just the source files.

    For ZIP archives: extracts safely, renames any extensionless files we can
    identify, deletes everything that isn't source code, then detects language.
    For single files: copies into the working directory and detects language.

    Returns a tuple of (working_directory, detected_language, list_of_source_files).
    """
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    upload = upload.resolve()
    ext = upload.suffix.lower()

    if ext == ".zip":
        try:
            compressed_size = upload.stat().st_size
            if compressed_size > MAX_COMPRESSED_BYTES:
                raise ZipTooLargeError(
                    f"ZIP file is {compressed_size} bytes, limit is {MAX_COMPRESSED_BYTES}"
                )
        except OSError as e:
            raise CorruptZipError(f"Cannot read ZIP file: {e}") from e

        extracted = out_dir / "src"
        extracted.mkdir(parents=True, exist_ok=True)
        _extract_zip(upload, extracted, depth=0)

        for p in extracted.rglob("*"):
            if p.is_file() and p.suffix.lower() not in ALLOWED_EXTS:
                if p.suffix == "":  # check if this extensionless file might be source code
                    detected_ext = _try_detect_language_by_content(p)
                    if detected_ext:
                        new_path = p.with_suffix(detected_ext)
                        p.rename(new_path)
                        continue
                try:
                    p.unlink()
                except Exception:
                    pass

        source_files = _collect_source_files(extracted)
        if not source_files:
            raise EmptySubmissionError(
                "ZIP contained no supported source files"
            )

        lang = detect_language(source_files)
        return out_dir, lang, source_files

    # Single-file submission path
    if ext not in ALLOWED_EXTS:
        raise UnsupportedFileTypeError(
            f"File type '{ext}' not supported. Supported: {', '.join(sorted(ALLOWED_EXTS))}"
        )

    dest = out_dir / upload.name
    shutil.copy2(upload, dest)
    lang = detect_language([dest])
    return out_dir, lang, [dest]
