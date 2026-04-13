"""
This file takes the raw fingerprint comparison results and turns them into
something a person can actually read — a list of matching code blocks, each
showing the exact lines from both submissions that appear to be copied.

The core challenge here is that fingerprints work at the token level, not the
line level. So we need to convert token positions back to line numbers, then
merge nearby matches (ones that are only a few lines apart) into a single
block rather than showing dozens of tiny fragments. Each resulting block gets
rated high, medium, or low based on how much code it covers.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from engine.tokenize.lex import Token
from engine.preprocess.canonicalize import SourceMapEntry
from engine.preprocess.strip_comments import strip_comments


def _token_line(tokens: List[Token], idx: int) -> int:
    if not tokens:
        return 1
    idx = max(0, min(idx, len(tokens) - 1))
    return tokens[idx].line


def _canonical_line_to_source(canonical_line: int, source_map: List[SourceMapEntry]):
    """
    After canonicalization, all source files are stitched together into one long
    text. This function takes a line number in that combined text and figures out
    which original file it came from and what the original line number was.
    Returns (None, None) if the line falls outside any recorded range.
    """
    for entry in source_map:
        if entry.canonical_start <= canonical_line <= entry.canonical_end:
            offset = canonical_line - entry.canonical_start
            return entry.original_file, entry.original_start + offset
    return None, None


def _load_source_lines(work_dir: Optional[Path], filename: str) -> List[str]:
    """
    Read a source file from disk and return its lines as a list so we can
    extract specific line ranges for display. Searches the whole work directory
    recursively in case the file is nested inside subdirectories.
    """
    if work_dir is None:
        return []
    try:
        matches = list(work_dir.rglob(Path(filename).name))
        if not matches:
            return []
        best = matches[0]
        for m in matches:
            if str(m).replace("\\", "/").endswith(filename.replace("\\", "/")):
                best = m
                break
        return best.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []


def _slice_code(lines: List[str], start: int, end: int) -> str:
    """Pull out lines start through end (1-indexed, inclusive) from a list of lines."""
    if not lines:
        return ""
    s = max(1, start) - 1
    e = min(len(lines), end)
    return "\n".join(lines[s:e])


def _strip_and_collapse(code: str, lang: str) -> str:
    """
    Strip comments from a code snippet and then collapse any runs of blank lines
    down to a single blank line. This gives the instructor a cleaner view of
    the matched code without comment noise, and without large gaps where comment
    blocks used to be.
    """
    stripped = strip_comments(code, lang=lang)
    lines = stripped.splitlines()
    result = []
    prev_blank = False
    for line in lines:
        trimmed = line.rstrip()
        if not trimmed:
            if not prev_blank:
                result.append("")
            prev_blank = True
        else:
            result.append(trimmed)
            prev_blank = False
    return "\n".join(result).strip()


def _compute_line_highlights(lines: List[str], start: int, end: int, lang: str) -> List[int]:
    """
    Figure out which specific line numbers within the matched block contain real
    code — not just comments, blank lines, or lone braces. The frontend uses this
    list to highlight exactly the meaningful lines rather than lighting up entire
    blocks including boilerplate structure.
    """
    if not lines:
        return []
    s = max(1, start)
    e = min(len(lines), end)
    slice_text = "\n".join(lines[s - 1:e])
    stripped = strip_comments(slice_text, lang=lang)
    result = []
    _structural = {"{", "}", "};", "{;", "});", "})"}
    for i, line in enumerate(stripped.splitlines()):
        content = line.strip()
        if content and content not in _structural:
            result.append(s + i)
    return result


def _match_strength(token_count: int) -> str:
    """
    Rate the size of a matched block. A block covering at least 40 tokens is a
    strong match — that's roughly 5 or more lines of real code. Between 15 and 39
    tokens is a medium match. Anything smaller is flagged low because short
    snippets could coincidentally appear in two unrelated submissions.
    """
    if token_count >= 40:
        return "high"
    if token_count >= 15:
        return "medium"
    return "low"


def build_evidence(
    fp_a: Dict[int, List[int]],
    fp_b: Dict[int, List[int]],
    tok_a: List[Token],
    tok_b: List[Token],
    source_map_a: List[SourceMapEntry],
    source_map_b: List[SourceMapEntry],
    k: int = 5,
    merge_gap: int = 3,
    work_dir_a: Optional[Path] = None,
    work_dir_b: Optional[Path] = None,
    canonical_text_a: Optional[str] = None,
    canonical_text_b: Optional[str] = None,
    lang: str = "mixed",
) -> List[dict]:
    """
    The main function in this file. It finds all fingerprint hashes that appear
    in both submissions, converts those matches to line numbers in the original
    source files, merges nearby matches into single blocks, filters out blocks
    that are too small to be meaningful, and returns a ranked list of evidence
    blocks for the report.
    """
    shared = set(fp_a.keys()) & set(fp_b.keys())
    if not shared:
        return []

    raw: List[Tuple[int, int, int, int]] = []
    for h in shared:
        # Cap at 50 positions per hash to prevent O(n²) blowup on adversarial inputs
        # where the same k-gram repeats thousands of times (e.g. a file full of zeros).
        for ia in fp_a[h][:50]:
            for ib in fp_b[h][:50]:
                ia_end = min(ia + k - 1, len(tok_a) - 1)
                ib_end = min(ib + k - 1, len(tok_b) - 1)
                raw.append((ia, ia_end, ib, ib_end))

    if not raw:
        return []

    # Convert token positions to line numbers before merging, since the merge
    # logic works on line ranges and the frontend ultimately needs line numbers.
    line_pairs: List[Tuple[int, int, int, int]] = []
    for ia, ia_end, ib, ib_end in raw:
        a1 = _token_line(tok_a, ia)
        a2 = _token_line(tok_a, ia_end)
        b1 = _token_line(tok_b, ib)
        b2 = _token_line(tok_b, ib_end)
        line_pairs.append((a1, a2, b1, b2))

    line_pairs.sort(key=lambda x: (x[0], x[2]))

    # Merge pairs of blocks that are close together in BOTH submissions. We check
    # both sides because checking only submission A was causing unrelated matches
    # that happened to sit near each other in A (but were far apart in B) to be
    # fused into one large fake evidence block.
    merged: List[Tuple[int, int, int, int]] = [line_pairs[0]]
    for a1, a2, b1, b2 in line_pairs[1:]:
        pa1, pa2, pb1, pb2 = merged[-1]
        a_gap = a1 - pa2
        b_gap = b1 - pb2
        if a_gap <= merge_gap and b_gap <= merge_gap and b1 >= pb1:
            merged[-1] = (pa1, max(pa2, a2), pb1, max(pb2, b2))
        else:
            merged.append((a1, a2, b1, b2))

    canonical_lines_a = canonical_text_a.splitlines() if canonical_text_a else None
    canonical_lines_b = canonical_text_b.splitlines() if canonical_text_b else None

    # Cache file contents so we don't re-read the same file once per evidence block.
    _file_cache: Dict[str, List[str]] = {}

    def get_lines(work_dir, filename):
        key = f"{id(work_dir)}::{filename}"
        if key not in _file_cache:
            _file_cache[key] = _load_source_lines(work_dir, filename)
        return _file_cache[key]

    evidence_blocks = []
    for a1, a2, b1, b2 in merged:
        file_a, orig_a1 = _canonical_line_to_source(a1, source_map_a)
        _, orig_a2      = _canonical_line_to_source(a2, source_map_a)
        file_b, orig_b1 = _canonical_line_to_source(b1, source_map_b)
        _, orig_b2      = _canonical_line_to_source(b2, source_map_b)

        if file_a is None:  # fall back to canonical line numbers if source map lookup fails
            file_a, orig_a1, orig_a2 = "canonical", a1, a2
        if file_b is None:
            file_b, orig_b1, orig_b2 = "canonical", b1, b2

        # Skip matches between files of different languages. When submissions contain
        # mixed languages, a Java fingerprint could accidentally match a C fingerprint
        # because both were hashed from the same normalized token stream. These matches
        # are meaningless and would confuse the instructor.
        _lang_family = {
            ".java":  "java",
            ".py":    "python",
            ".c":     "c",
            ".h":     "c",
            ".cpp":   "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp",
            ".js":    "js",
            ".ts":    "ts",
        }
        ext_a = Path(file_a).suffix.lower()
        ext_b = Path(file_b).suffix.lower()
        if _lang_family.get(ext_a) != _lang_family.get(ext_b):
            continue

        la1 = orig_a1 or a1
        la2 = orig_a2 or a2
        lb1 = orig_b1 or b1
        lb2 = orig_b2 or b2

        src_lines_a = get_lines(work_dir_a, file_a) if work_dir_a else []
        if src_lines_a:
            code_a = _strip_and_collapse(_slice_code(src_lines_a, la1, la2), lang)
        elif canonical_lines_a is not None:
            code_a = "\n".join(canonical_lines_a[a1-1:a2]) if a1 <= len(canonical_lines_a) else ""
        else:
            code_a = ""

        src_lines_b = get_lines(work_dir_b, file_b) if work_dir_b else []
        if src_lines_b:
            code_b = _strip_and_collapse(_slice_code(src_lines_b, lb1, lb2), lang)
        elif canonical_lines_b is not None:
            code_b = "\n".join(canonical_lines_b[b1-1:b2]) if b1 <= len(canonical_lines_b) else ""
        else:
            code_b = ""

        def _meaningful_lines(code: str) -> int:
            count = 0
            for l in code.splitlines():
                s = l.strip()
                if s and s not in ("{", "}", "};", "{;", "};", "});", "})"):
                    count += 1
            return count

        a_code_lines = _meaningful_lines(code_a)
        b_code_lines = _meaningful_lines(code_b)

        # Require at least 4 meaningful lines on each side. This filters out blocks
        # that are nothing but closing braces and return statements — those are
        # structurally required by the language and don't indicate copying.
        if a_code_lines < 4 or b_code_lines < 4:
            continue

        token_count = max(a_code_lines, b_code_lines) * 8

        highlights_a = _compute_line_highlights(src_lines_a, la1, la2, lang)
        highlights_b = _compute_line_highlights(src_lines_b, lb1, lb2, lang)

        evidence_blocks.append({
            "file_a":            file_a,
            "lines_a":           [la1, la2],
            "code_a":            code_a,
            "line_highlights_a": highlights_a,
            "file_b":            file_b,
            "lines_b":           [lb1, lb2],
            "code_b":            code_b,
            "line_highlights_b": highlights_b,
            "match_strength":    _match_strength(token_count),
            "tokens_matched":    token_count,
        })

    # Sort so the strongest matches appear first in the report.
    strength_order = {"high": 0, "medium": 1, "low": 2}
    evidence_blocks.sort(key=lambda e: strength_order.get(e["match_strength"], 3))

    return evidence_blocks
