"""
Canonicalize source files into a single normalized text for fingerprinting.

Steps per file:
  1. Normalize line endings and strip BOM
  2. Strip comments (language-aware)
  3. Filter stdlib imports/includes
  4. Normalize simple token-level patterns (i++ → i+=1, compound assignments, etc.)
  5. Normalize whitespace (strip trailing whitespace)
  6. Record source map entry for evidence tracing

Intentionally does NOT perform structural transformations (for→while,
switch→if-else) — those change line counts, break line-number tracking,
and silently corrupt the obfuscation detection in detect.py by hiding
the original structural differences before they can be compared.
Cosine similarity handles these obfuscation patterns at the scoring level.
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
    Maps a range of lines in the canonical file back to the original source.
    canonical_start and canonical_end are 1-indexed line numbers.
    Always 1:1 mapping — canonical line N corresponds to original line N
    within this entry's range (offset from original_start).
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
    Takes the list of source files from ingest, concatenates them into
    a single canonical representation for fingerprinting.
    """
    if not source_files:
        raise ValueError("No source files to canonicalize")

    source_files = sorted(source_files, key=lambda p: str(p).lower())

    parts: List[str] = []
    source_map: List[SourceMapEntry] = []
    current_canonical_line = 1

    # find common root for relative path display
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

        # normalize line endings
        raw = raw.replace("\r\n", "\n").replace("\r", "\n")

        # strip BOM
        if raw.startswith("\ufeff"):
            raw = raw[1:]

        # strip null bytes and control characters (except newline, tab)
        raw = _strip_control_chars(raw)

        # detect file-level language if overall is mixed
        file_lang = lang
        if lang == "mixed":
            file_lang = _detect_file_lang(src_file)

        # strip comments (language-aware)
        cleaned = strip_comments(raw, lang=file_lang)

        # filter boilerplate imports
        cleaned = filter_boilerplate(cleaned, file_lang)

        # normalize control flow patterns — returns (text, switch_line_map)
        # switch_line_map[canonical_offset] = original_offset (0-based)
        # None if no switch statements were present (1:1 mapping assumed)
        cleaned, switch_line_map = _normalize_control_flow(cleaned, file_lang)

        # normalize whitespace
        # NOTE: do NOT collapse blank lines here — comment stripping replaces
        # comment lines with blank lines to preserve line count, and collapsing
        # those blanks would shift line numbers, breaking the source map.
        cleaned = _strip_trailing_whitespace(cleaned)

        lines = cleaned.splitlines()
        if not lines:
            continue

        # relative display name
        try:
            rel = str(src_file.relative_to(common_root)).replace("\\", "/")
        except ValueError:
            rel = src_file.name

        # separator line — must be added BEFORE the source map entry so that
        # canonical_start correctly points to the first content line, not the
        # separator.  The off-by-one bug: separator was previously counted
        # inside canonical_start, causing every source map lookup to return an
        # original line number that was 1 too high.
        parts.append(f"# --- {rel} ---\n")
        current_canonical_line += 1

        # source map entry: canonical_start is now the first content line
        # line_map stores switch expansion offsets so _canonical_line_to_source
        # can correctly reverse-map even when line counts changed.
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


# ─── Normalization Helpers ──────────────────────────────────────────

def _strip_control_chars(text: str) -> str:
    """Remove null bytes and control characters except \\n and \\t."""
    return "".join(
        ch for ch in text
        if ch == "\n" or ch == "\t" or (ord(ch) >= 32)
    )


def _detect_file_lang(path: Path) -> str:
    """Map file extension to language string."""
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
    Apply simple, same-line token-level normalizations that do not change
    line counts and therefore do not require line map tracking.

    Structural transformations (for→while, switch→if-else) are intentionally
    excluded — they break line number tracking and hide patterns from
    obfuscation detection. Cosine similarity handles those at scoring time.

    Returns (text, None) — None because line count never changes here.
    """
    # --- normalize increment/decrement variants ---
    # i++ / ++i / i += 1 all mean the same thing
    text = re.sub(r'(\w+)\s*\+\+', r'\1 += 1', text)
    text = re.sub(r'\+\+\s*(\w+)', r'\1 += 1', text)
    text = re.sub(r'(\w+)\s*--',   r'\1 -= 1', text)
    text = re.sub(r'--\s*(\w+)',   r'\1 -= 1', text)

    # --- normalize compound assignments to simple form ---
    # x += y → x = x + y  (students swap these to disguise copying)
    text = re.sub(r'\b(\w+)\s*\*=\s*([^\n;]+);', r'\1 = \1 * \2;', text)
    text = re.sub(r'\b(\w+)\s*/=\s*([^\n;]+);',  r'\1 = \1 / \2;', text)
    text = re.sub(r'\b(\w+)\s*%=\s*([^\n;]+);',  r'\1 = \1 % \2;', text)
    text = re.sub(r'\b(\w+)\s*\+=\s*([^\n;]+);', r'\1 = \1 + \2;', text)
    text = re.sub(r'\b(\w+)\s*-=\s*([^\n;]+);',  r'\1 = \1 - \2;', text)

    # --- normalize redundant boolean returns (same-line patterns only) ---
    text = re.sub(
        r"if\s*\(([^)]+)\)\s*return\s+true\s*;\s*else\s+return\s+false\s*;",
        r"return \1;", text,
    )
    text = re.sub(
        r"if\s*\(([^)]+)\)\s*return\s+false\s*;\s*else\s+return\s+true\s*;",
        r"return !(\1);", text,
    )

    # --- normalize null comparison ordering ---
    # null != x → x != null
    text = re.sub(r"null\s*!=\s*(\w+)", r"\1 != null", text)
    text = re.sub(r"null\s*==\s*(\w+)", r"\1 == null", text)

    return text, None


def _strip_trailing_whitespace(text: str) -> str:
    """Strip trailing whitespace from every line."""
    return "\n".join(line.rstrip() for line in text.split("\n"))


def _common_parts(a: tuple, b: tuple) -> tuple:
    """Return the common leading path components of two path tuples."""
    common = []
    for x, y in zip(a, b):
        if x == y:
            common.append(x)
        else:
            break
    return tuple(common) if common else (a[0],)
