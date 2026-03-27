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

    line_map: optional list where line_map[canonical_offset] = original_offset
    (both 0-indexed relative to this entry's start). Built when control flow
    normalization changes line counts (e.g. switch → if-else expansion).
    None means 1:1 mapping — canonical offset == original offset.
    """
    canonical_start: int
    canonical_end: int
    original_file: str
    original_start: int
    line_map: list = None  # None = 1:1 mapping


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


def _normalize_switch_to_ifelse(text: str) -> tuple:
    """
    Convert switch(EXPR) { case VAL: ...; break; ... default: ...; }
    to an equivalent if / else-if / else chain.

    Processes the text line-by-line with brace-depth tracking so it handles
    multi-line cases, nested blocks, and both brace styles:
        switch(x) {        ← brace on same line
        switch(x)          ← brace on next line
        {

    Assumptions (safe for typical student code):
      - Each case ends with a `break;` (no fall-through across cases)
      - Case values are simple literals or identifiers
      - No gotos or labelled breaks inside the switch body
    """
    lines = text.split('\n')
    result = []
    # line_map[result_index] = original_index (both 0-based)
    # tracks how canonical output lines map back to original source lines
    line_map = []
    i = 0

    while i < len(lines):
        line = lines[i]
        orig_i = i  # track where this block started in original

        m = re.match(r'^(\s*)switch\s*\(\s*(.*?)\s*\)\s*\{?\s*$', line)
        if not m:
            line_map.append(i)
            result.append(line)
            i += 1
            continue

        indent      = m.group(1)
        switch_expr = m.group(2)
        i += 1

        # Consume standalone opening brace if not on the switch line
        if '{' not in line:
            while i < len(lines):
                s = lines[i].strip()
                i += 1
                if s == '{':
                    break
                if s:          # unexpected non-blank before '{' — abort
                    line_map.append(orig_i)
                    result.append(line)
                    i -= 1     # re-process from here
                    break

        # ── Parse switch body ────────────────────────────────────────────────
        cases: list = []       # [(value_str | None, [stmt_str, ...])]
        cur_val   = '__NONE__' # sentinel: not yet inside a case clause
        cur_stmts: list = []
        depth = 1              # we already consumed the opening '{'

        while i < len(lines) and depth > 0:
            ln = lines[i]
            s  = ln.strip()
            i += 1

            opens  = s.count('{')
            closes = s.count('}')

            # Closing brace(s) — check whether this ends the switch
            if closes and depth - closes <= 0:
                if cur_val != '__NONE__':
                    cases.append((cur_val, cur_stmts[:]))
                depth = 0
                break

            depth += opens - closes

            # Only interpret case/default/break at switch's direct depth
            if depth != 1:
                if cur_val != '__NONE__':
                    cur_stmts.append(s)
                continue

            cm = re.match(r'^case\s+(.*?)\s*:(.*)', s)
            dm = re.match(r'^default\s*:(.*)',      s)

            if cm:
                if cur_val != '__NONE__':
                    cases.append((cur_val, cur_stmts[:]))
                cur_val   = cm.group(1).strip()
                cur_stmts = []
                rest = re.sub(r'\s*break\s*;?\s*$', '', cm.group(2)).strip()
                if rest:
                    cur_stmts.append(rest)

            elif dm:
                if cur_val != '__NONE__':
                    cases.append((cur_val, cur_stmts[:]))
                cur_val   = None   # None → default clause
                cur_stmts = []
                rest = re.sub(r'\s*break\s*;?\s*$', '', dm.group(1)).strip()
                if rest:
                    cur_stmts.append(rest)

            elif s in ('break;', 'break ;', 'break'):
                pass   # already stripped; skip the sentinel line

            elif s not in ('{', '}', ''):
                if cur_val != '__NONE__':
                    clean = re.sub(r'\s*break\s*;?\s*$', '', s).strip()
                    if clean:
                        cur_stmts.append(clean)

        orig_end = i  # original lines orig_i..orig_end-1 consumed

        # ── Emit if / else-if / else chain ───────────────────────────────────
        if not cases:          # parse failed — emit original switch line untouched
            line_map.append(orig_i)
            result.append(line)
            continue

        emit_start = len(result)
        for idx, (val, stmts) in enumerate(cases):
            if val is not None:
                kw = 'if' if idx == 0 else 'else if'
                result.append(f'{indent}{kw} ({switch_expr} == {val}) {{')
            else:
                result.append(f'{indent}else {{')
            for stmt in stmts:
                result.append(f'{indent}    {stmt}')
            result.append(f'{indent}}}')
        emit_end = len(result)

        # map each emitted output line back to a proportional original line
        orig_block_len = max(orig_end - orig_i, 1)
        emit_block_len = emit_end - emit_start
        for out_idx in range(emit_start, emit_end):
            ratio = (out_idx - emit_start) / emit_block_len
            orig_offset = int(ratio * orig_block_len)
            line_map.append(orig_i + orig_offset)

    return '\n'.join(result), line_map


def _normalize_control_flow(text: str, lang: str) -> tuple:
    """
    Normalize equivalent control flow patterns so they produce the same tokens.

    1. Switch → if-else chain  (handles switch↔if-else obfuscation at text level)
    2. Ternary → if/else
    3. Redundant boolean returns / assignments
    4. Null-comparison canonicalisation
    5. Increment/decrement normalisation (i++ → i += 1)
    """
    lang = (lang or "mixed").lower()

    # --- switch → if-else (C, C++, Java) ---
    # Returns (text, line_map) where line_map[canonical_offset] = original_offset
    switch_line_map = None
    if lang in ("c", "cpp", "c_or_cpp", "java", "csharp", "javascript",
                "typescript", "mixed"):
        text, switch_line_map = _normalize_switch_to_ifelse(text)

    # --- normalize increment/decrement variants ---
    # `i++` / `++i` / `i += 1` all mean the same thing — normalize to `i += 1`
    # so for-loop headers like `for(i=0; i<n; i++)` vs `for(i=0; i<n; i=i+1)`
    # produce the same token sequence. Only safe for the standalone ++;/--; form
    # and for-loop third clause (before ')' ).
    text = re.sub(r'(\w+)\s*\+\+', r'\1 += 1', text)
    text = re.sub(r'\+\+\s*(\w+)', r'\1 += 1', text)
    text = re.sub(r'(\w+)\s*--',   r'\1 -= 1', text)
    text = re.sub(r'--\s*(\w+)',   r'\1 -= 1', text)

    # --- normalize compound assignments to simple form ---
    # `x *= 2` → `x = x * 2`  (and likewise for /=, %=, +=, -=)
    # Students often swap between `x += y` and `x = x + y` to disguise copying.
    # Only matches simple variable names (not array subscripts) to avoid
    # corrupting complex expressions. [^\n;]+ stops at end-of-line or semicolon.
    text = re.sub(r'\b(\w+)\s*\*=\s*([^\n;]+);', r'\1 = \1 * \2;', text)
    text = re.sub(r'\b(\w+)\s*/=\s*([^\n;]+);',  r'\1 = \1 / \2;', text)
    text = re.sub(r'\b(\w+)\s*%=\s*([^\n;]+);',  r'\1 = \1 % \2;', text)
    text = re.sub(r'\b(\w+)\s*\+=\s*([^\n;]+);', r'\1 = \1 + \2;', text)
    text = re.sub(r'\b(\w+)\s*-=\s*([^\n;]+);',  r'\1 = \1 - \2;', text)

    # --- normalize ternary boolean: `(COND) ? true : false` → `(COND)` ---
    # so it matches `return COND;` produced by the if-else normalizer below
    text = re.sub(
        r"\(([^()]+)\)\s*\?\s*true\s*:\s*false",
        r"(\1)",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\(([^()]+)\)\s*\?\s*false\s*:\s*true",
        r"!(\1)",
        text,
        flags=re.IGNORECASE,
    )

    # --- normalize `return (COND) ? A : B;` → `if (COND) { return A; } else { return B; }` ---
    # handles the most common student copy pattern: ternary return rewritten as if-else
    text = re.sub(
        r"return\s+\(([^()]+)\)\s*\?\s*([^:;\n]+?)\s*:\s*([^;\n]+?)\s*;",
        r"if (\1) { return \2; } else { return \3; }",
        text,
    )
    # handle without parens around condition: `return SIMPLE_COND ? A : B;`
    text = re.sub(
        r"return\s+([\w\s.<>=!&|]+?)\s*\?\s*([^:;\n]+?)\s*:\s*([^;\n]+?)\s*;",
        r"if (\1) { return \2; } else { return \3; }",
        text,
    )

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
    # normalize if-else return blocks with braces (converted from ternary)
    text = re.sub(
        r"if\s*\(([^)]+)\)\s*\{\s*return\s+true\s*;\s*\}\s*else\s*\{\s*return\s+false\s*;\s*\}",
        r"return \1;",
        text,
    )
    text = re.sub(
        r"if\s*\(([^)]+)\)\s*\{\s*return\s+false\s*;\s*\}\s*else\s*\{\s*return\s+true\s*;\s*\}",
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

    return text, switch_line_map


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
