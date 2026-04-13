"""
This file takes the raw source files from a student's submission and prepares
them for fingerprinting. The output is a single combined text file where all
the source files are stitched together, with their comments stripped, boilerplate
imports removed, and common coding patterns normalized to a consistent form.

We also record a "source map" that remembers which lines in the combined output
came from which original file — this lets the evidence builder trace any match
back to the exact filename and line number in the original submission.

Intentionally does NOT do structural transformations like converting for-loops
to while-loops or switch statements to if-else chains. Those transformations
would change line counts, break the source map, and hide the structural
differences that the obfuscation detector is specifically looking for. Instead,
those patterns are handled at the scoring level by cosine similarity.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from engine.preprocess.strip_comments import strip_comments
from engine.preprocess.stdlib_filter import filter_boilerplate

ALLOWED_EXTS = {
    ".java", ".c", ".cpp"
}


@dataclass
class SourceMapEntry:
    """
    Records the relationship between a range of lines in the combined canonical
    output and the original source file those lines came from. The mapping is
    always 1-to-1: canonical line N corresponds to original line (original_start
    + N - canonical_start). This is guaranteed because we normalize in-place
    without adding or removing lines.
    """
    canonical_start: int
    canonical_end: int
    original_file: str
    original_start: int
    line_map: list = None  # always None — kept for interface compatibility


@dataclass
class CanonicalResult:
    canonical_text: str
    source_map: List[SourceMapEntry]
    canonical_path: Path


def canonicalize(source_files: List[Path], out_dir: Path, lang: str = "mixed") -> CanonicalResult:
    """
    Takes the list of source files from ingest, runs each one through comment
    stripping, boilerplate filtering, and token normalization, then concatenates
    them all into a single canonical text file ready for fingerprinting.
    """
    if not source_files:
        raise ValueError("No source files to canonicalize")

    source_files = sorted(source_files, key=lambda p: str(p).lower())

    parts: List[str] = []
    source_map: List[SourceMapEntry] = []
    current_canonical_line = 1

    # Find the common directory prefix so filenames in the report show relative paths
    # rather than long absolute paths that expose the server's directory structure.
    if len(source_files) == 1:
        common_root = source_files[0].parent
    else:
        common_root = Path(*[p.parts for p in source_files][0])
        for f in source_files:
            try:
                common_root = Path(*_common_parts(common_root.parts, f.parts))
            except Exception:
                common_root = source_files[0].parent

    for src_file in source_files:
        try:
            raw = src_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        raw = raw.replace("\r\n", "\n").replace("\r", "\n")
        if raw.startswith("\ufeff"):  # strip BOM (byte order mark) that some editors add
            raw = raw[1:]
        raw = _strip_control_chars(raw)

        file_lang = lang
        if lang == "mixed":
            file_lang = _detect_file_lang(src_file)

        cleaned = strip_comments(raw, lang=file_lang)
        cleaned = filter_boilerplate(cleaned, file_lang)
        cleaned, switch_line_map = _normalize_control_flow(cleaned, file_lang)

        # Do NOT collapse blank lines here. When we strip comments, those lines
        # become blank but they still count toward the line number. Collapsing
        # them would shift all subsequent line numbers and corrupt the source map.
        cleaned = _strip_trailing_whitespace(cleaned)

        lines = cleaned.splitlines()
        if not lines:
            continue

        try:
            rel = str(src_file.relative_to(common_root)).replace("\\", "/")
        except ValueError:
            rel = src_file.name

        # The separator line goes in BEFORE the source map entry so that
        # canonical_start points to the first actual code line, not the separator.
        parts.append(f"# --- {rel} ---\n")
        current_canonical_line += 1

        entry = SourceMapEntry(
            canonical_start=current_canonical_line,
            canonical_end=current_canonical_line + len(lines) - 1,
            original_file=rel,
            original_start=1,
            line_map=switch_line_map,
        )
        source_map.append(entry)

        parts.append(cleaned)
        if not cleaned.endswith("\n"):
            parts.append("\n")
        current_canonical_line += len(lines)

        parts.append("\n")
        current_canonical_line += 1

    canonical_text = "".join(parts)

    out_path = out_dir / "canonical.txt"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(canonical_text, encoding="utf-8")

    return CanonicalResult(
        canonical_text=canonical_text,
        source_map=source_map,
        canonical_path=out_path,
    )


def _strip_control_chars(text: str) -> str:
    """Remove null bytes and other invisible control characters from the text,
    keeping only normal characters, newlines, and tabs."""
    return "".join(
        ch for ch in text
        if ch == "\n" or ch == "\t" or (ord(ch) >= 32)
    )


def _detect_file_lang(path: Path) -> str:
    """Look at the file extension and return which programming language it is."""
    ext = path.suffix.lower()
    mapping = {
        ".java": "java", ".c": "c", ".cpp": "cpp", ".cc": "cpp",
        ".cxx": "cpp", ".h": "c_or_cpp", ".hpp": "cpp", ".hxx": "cpp",
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".cs": "csharp", ".go": "go", ".rs": "rust", ".rb": "ruby",
    }
    return mapping.get(ext, "mixed")


def _normalize_control_flow(text: str, lang: str) -> tuple:
    """
    Apply simple text-level normalizations that do not change the number of lines
    in the file. This is the key constraint: because we preserve line counts, the
    source map stays valid and line numbers in the report stay accurate.

    The normalizations here handle common ways students try to disguise copied
    code at the syntactic level: rewriting i++ as i += 1, swapping compound
    assignment operators for their expanded form (x += y → x = x + y), flipping
    comparison order around null, and simplifying trivial if-return-true patterns.

    Structural transformations like converting for-loops to while-loops are
    intentionally not done here — they would add or remove lines, break the
    source map, and also hide the very patterns the obfuscation detector looks for.
    """
    # i++ and ++i both become i += 1
    text = re.sub(r'(\w+)\s*\+\+', r'\1 += 1', text)
    text = re.sub(r'\+\+\s*(\w+)', r'\1 += 1', text)
    text = re.sub(r'(\w+)\s*--',   r'\1 -= 1', text)
    text = re.sub(r'--\s*(\w+)',   r'\1 -= 1', text)

    # x += y becomes x = x + y, and similarly for other compound operators.
    # Students sometimes swap these to make copied code look different.
    text = re.sub(r'\b(\w+)\s*\*=\s*([^\n;]+);', r'\1 = \1 * \2;', text)
    text = re.sub(r'\b(\w+)\s*/=\s*([^\n;]+);',  r'\1 = \1 / \2;', text)
    text = re.sub(r'\b(\w+)\s*%=\s*([^\n;]+);',  r'\1 = \1 % \2;', text)
    text = re.sub(r'\b(\w+)\s*\+=\s*([^\n;]+);', r'\1 = \1 + \2;', text)
    text = re.sub(r'\b(\w+)\s*-=\s*([^\n;]+);',  r'\1 = \1 - \2;', text)

    # if (x) return true; else return false; → return x;
    # These are logically identical and students sometimes expand them to add lines.
    text = re.sub(
        r"if\s*\(([^)]+)\)\s*return\s+true\s*;\s*else\s+return\s+false\s*;",
        r"return \1;", text,
    )
    text = re.sub(
        r"if\s*\(([^)]+)\)\s*return\s+false\s*;\s*else\s+return\s+true\s*;",
        r"return !(\1);", text,
    )

    # null != x → x != null. Both mean the same thing but look different.
    text = re.sub(r"null\s*!=\s*(\w+)", r"\1 != null", text)
    text = re.sub(r"null\s*==\s*(\w+)", r"\1 == null", text)

    return text, None


def _strip_trailing_whitespace(text: str) -> str:
    """Remove trailing spaces and tabs from the end of every line."""
    return "\n".join(line.rstrip() for line in text.split("\n"))


def _common_parts(a: tuple, b: tuple) -> tuple:
    """Find the shared leading path components between two paths."""
    common = []
    for x, y in zip(a, b):
        if x == y:
            common.append(x)
        else:
            break
    return tuple(common) if common else (a[0],)
