"""
engine/ingest/ingest.py

Handles everything needed to turn a raw student submission into a set of
source files the engine can process.

Takes a ZIP archive or a single source file, extracts it safely into a
working directory, filters out non-source files, and detects the primary
language. Safety checks include ZIP bomb detection, path traversal
prevention, nested ZIP depth limits, and per-file size limits.
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

# all file types the engine can process
ALLOWED_EXTS = {
    ".java",                    # Java
    ".c", ".h",                 # C source + headers
    ".cpp", ".cc", ".cxx",      # C++ source
    ".hpp", ".hxx",             # C++ headers
}

# hard limits
MAX_FILES = 5000
MAX_COMPRESSED_BYTES   = 100 * 1024 * 1024   # 100 MB compressed
MAX_UNCOMPRESSED_BYTES = 500 * 1024 * 1024   # 500 MB decompressed (zip bomb guard)
MAX_SINGLE_FILE_BYTES  = 10 * 1024 * 1024    # 10 MB per file
MAX_NESTED_ZIP_DEPTH   = 10
MAX_PATH_LENGTH        = 260


def detect_language(files: list) -> str:
    """
    Look at what source files are present and guess the primary language.
    If a mix, return 'mixed'. Called after extraction so we know what's inside.
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
    # c and cpp are close enough to treat as cpp
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
    Resolve the extraction path and ensure it stays within dest.
    Blocks path traversal attacks (../../etc/passwd) and overly long paths.
    Also normalizes Windows-style backslashes.
    """
    # normalize backslashes (Windows ZIPs)
    clean = entry_name.replace("\\", "/")

    # strip leading slashes and ../ components
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
    Safe zip extraction with:
    - Path traversal protection
    - ZIP bomb detection (tracks running decompressed size)
    - Symlink rejection
    - File count limits
    - Recursive nested ZIP extraction up to MAX_NESTED_ZIP_DEPTH
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

            # pre-check: sum of declared uncompressed sizes
            total_declared = sum(e.file_size for e in entries)
            if total_declared > MAX_UNCOMPRESSED_BYTES:
                raise ZipBombError(
                    f"ZIP declared uncompressed size {total_declared} bytes "
                    f"exceeds limit of {MAX_UNCOMPRESSED_BYTES}"
                )

            # check compression ratio — anything over 100:1 is suspicious
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
                # skip directories, macOS metadata, and hidden files
                if entry.is_dir():
                    continue
                name = entry.filename
                if name.startswith("__MACOSX") or "/.DS_Store" in name or name.endswith(".DS_Store"):
                    continue

                # reject symlinks (external_attr check)
                # Unix symlinks have the mode bits 0o120000 in the upper 16 bits
                unix_attrs = entry.external_attr >> 16
                if unix_attrs != 0 and stat.S_ISLNK(unix_attrs):
                    continue  # silently skip symlinks

                # sanitize the output path
                out_path = _sanitize_zip_entry(name, dest)

                # enforce per-file size limit
                if entry.file_size > MAX_SINGLE_FILE_BYTES:
                    continue  # skip oversized files

                # track running decompressed bytes (zip bomb check)
                running_bytes += entry.file_size
                if running_bytes > MAX_UNCOMPRESSED_BYTES:
                    raise ZipBombError(
                        f"Cumulative decompressed size {running_bytes} bytes "
                        f"exceeds limit during extraction"
                    )

                # extract the file
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(entry) as src, open(out_path, "wb") as dst:
                    # read in chunks to catch actual decompression bombs
                    # (declared size can lie)
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

                # check if this is a nested ZIP
                if out_path.suffix.lower() == ".zip":
                    nested_zips.append(out_path)

            # recursively extract nested ZIPs
            for nested in nested_zips:
                nested_dest = nested.parent / nested.stem
                try:
                    _extract_zip(nested, nested_dest, depth=depth + 1)
                except EngineError:
                    pass  # if nested zip fails, skip it — outer files are enough
                finally:
                    # remove the nested .zip file itself
                    nested.unlink(missing_ok=True)

    except zipfile.BadZipFile as e:
        raise CorruptZipError(f"Could not open ZIP file: {e}") from e


def _collect_source_files(root: Path) -> list:
    """Walk directory tree and return all supported source files."""
    found = []
    for p in root.rglob("*"):
        if p.is_file() and not p.is_symlink() and p.suffix.lower() in ALLOWED_EXTS:
            # skip files that are empty or suspiciously large
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
    For files with no recognized extension, try to detect language by content.
    Returns extension string like '.java' or None.
    """
    try:
        head = filepath.read_text(encoding="utf-8", errors="ignore")[:2000]
    except Exception:
        return None

    # quick heuristics
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
    Takes an uploaded file (zip or single source file) and sets up
    a working directory with the extracted contents.

    Returns (out_dir, detected_language, list_of_source_files).
    The source file list is what canonicalize needs.
    """
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    upload = upload.resolve()
    ext = upload.suffix.lower()

    if ext == ".zip":
        # check compressed size before even opening
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

        # drop any non-source files (build artifacts, .class, etc.)
        for p in extracted.rglob("*"):
            if p.is_file() and p.suffix.lower() not in ALLOWED_EXTS:
                # but first check if no-extension files might be source
                if p.suffix == "":
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

    # single file submission
    if ext not in ALLOWED_EXTS:
        raise UnsupportedFileTypeError(
            f"File type '{ext}' not supported. Supported: {', '.join(sorted(ALLOWED_EXTS))}"
        )

    dest = out_dir / upload.name
    shutil.copy2(upload, dest)
    lang = detect_language([dest])
    return out_dir, lang, [dest]
