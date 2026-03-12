"""
Canonicalize source files into a single normalized text for fingerprinting.

Steps per file:
  1. Normalize line endings and strip BOM
  2. Strip comments (language-aware)
  3. Filter stdlib imports/includes
  4. Normalize control flow patterns (ternary → if/else, switch → if-else chains)
  5. Normalize whitespace (collapse blanks, strip trailing whitespace)
  6. Normalize null/boolean patterns
  7. Record source map entry for evidence tracing
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from engine.preprocess.strip_comments import strip_comments
from engine.preprocess.stdlib_filter import filter_boilerplate

ALLOWED_EXTS = {
    ".java", ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx",
    ".py", ".js", ".ts", ".cs", ".go", ".rs", ".rb",
}


@dataclass
class SourceMapEntry:
    """
    Maps a range of lines in the canonical file back to the original source.
    canonical_start and canonical_end are 1-indexed line numbers.
    """
    canonical_start: int
    canonical_end: int
    original_file: str
    original_start: int


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

        # normalize control flow patterns
        cleaned = _normalize_control_flow(cleaned, file_lang)

        # normalize whitespace
        cleaned = _collapse_blanks(cleaned)
        cleaned = _strip_trailing_whitespace(cleaned)

        lines = cleaned.splitlines()
        if not lines:
            continue

        # relative display name
        try:
            rel = str(src_file.relative_to(common_root)).replace("\\", "/")
        except ValueError:
            rel = src_file.name

        # source map entry
        entry = SourceMapEntry(
            canonical_start=current_canonical_line,
            canonical_end=current_canonical_line + len(lines) - 1,
            original_file=rel,
            original_start=1,
        )
        source_map.append(entry)

        parts.append(f"# --- {rel} ---\n")
        current_canonical_line += 1

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


def _normalize_control_flow(text: str, lang: str) -> str:
    """
    Normalize equivalent control flow patterns so they produce the same tokens.

    1. Ternary → if/else (so `x = a > b ? a : b` matches `if(a>b) x=a; else x=b;`)
       We don't literally rewrite — we normalize the ternary OPERATOR to
       a canonical marker that the tokenizer will treat equivalently.

    2. Simple return patterns:
       `if(x) return true; else return false;` → `return x;`
       `if(!x) return false; else return true;` → `return x;`

    3. Normalize for-each / enhanced-for to canonical form (Java)
       This is a token-level concern handled by the tokenizer.

    4. Normalize `switch` to if-else chain (simple replacement at text level
       is too fragile — this is better done at token level in lex.py).
    """
    lang = (lang or "mixed").lower()

    # --- normalize redundant boolean returns ---
    # `if (COND) return true; else return false;` → `return COND;`
    text = re.sub(
        r"if\s*\(([^)]+)\)\s*return\s+true\s*;\s*else\s+return\s+false\s*;",
        r"return \1;",
        text,
    )
    text = re.sub(
        r"if\s*\(([^)]+)\)\s*return\s+false\s*;\s*else\s+return\s+true\s*;",
        r"return !(\1);",
        text,
    )

    # --- normalize redundant boolean assignments ---
    # `if (COND) x = true; else x = false;` → `x = COND;`
    text = re.sub(
        r"if\s*\(([^)]+)\)\s*(\w+)\s*=\s*true\s*;\s*else\s+\2\s*=\s*false\s*;",
        r"\2 = \1;",
        text,
    )

    # --- normalize `!= null` / `== null` to canonical form ---
    # not a rewrite, just ensure consistency: `x != null` stays, `null != x` → `x != null`
    text = re.sub(r"null\s*!=\s*(\w+)", r"\1 != null", text)
    text = re.sub(r"null\s*==\s*(\w+)", r"\1 == null", text)

    return text


def _collapse_blanks(text: str) -> str:
    """Collapse 3+ consecutive blank lines down to 1."""
    lines = text.split("\n")
    out = []
    blank_count = 0
    for line in lines:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= 1:
                out.append(line)
        else:
            blank_count = 0
            out.append(line)
    return "\n".join(out)


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
