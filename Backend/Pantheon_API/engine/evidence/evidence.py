"""
engine/evidence/evidence.py

Builds the list of matching code blocks that the instructor sees in the report.

For every fingerprint hash shared between two submissions, we find the token
positions in each, convert those to original file line numbers via the source
map, and merge nearby matches into contiguous blocks. Each block gets a
match strength rating (high/medium/low) based on how many tokens it spans.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from engine.tokenize.lex import Token
from engine.preprocess.canonicalize import SourceMapEntry


def _token_line(tokens: List[Token], idx: int) -> int:
    if not tokens:
        return 1
    idx = max(0, min(idx, len(tokens) - 1))
    return tokens[idx].line


def _canonical_line_to_source(canonical_line: int, source_map: List[SourceMapEntry]):
    """
    Given a line number in the canonical text, find which original file it
    came from and what line number it corresponds to in that file.

    Returns (original_filename, original_line).
    If the line falls in a file separator or outside any mapped region,
    returns (None, None).
    """
    for entry in source_map:
        if entry.canonical_start <= canonical_line <= entry.canonical_end:
            # offset within this file's block
            offset = canonical_line - entry.canonical_start
            return entry.original_file, entry.original_start + offset
    return None, None


def _load_source_lines(work_dir: Optional[Path], filename: str) -> List[str]:
    """
    Loads the original source file and returns its lines (1-indexed friendly —
    index 0 = line 1). Returns empty list if file can't be found.
    Searches recursively under work_dir because the file could be nested
    inside src/ or any subfolder from the ZIP.
    """
    if work_dir is None:
        return []
    try:
        matches = list(work_dir.rglob(Path(filename).name))
        if not matches:
            return []
        # if multiple files with same name, pick the one whose path
        # ends with the relative filename we have
        best = matches[0]
        for m in matches:
            if str(m).replace("\\", "/").endswith(filename.replace("\\", "/")):
                best = m
                break
        return best.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []


def _slice_code(lines: List[str], start: int, end: int) -> str:
    """
    Extracts lines start..end (both 1-indexed, inclusive) from the line list.
    Returns them joined as a single string with newlines preserved.
    """
    if not lines:
        return ""
    # clamp to actual file bounds
    s = max(1, start) - 1       # convert to 0-indexed
    e = min(len(lines), end)    # end is inclusive, so no -1 needed
    return "\n".join(lines[s:e])


def _match_strength(token_count: int) -> str:
    """
    Classify a match block by how many tokens it spans.
    Rough heuristic: short matches are low confidence, long ones are high.
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
) -> List[dict]:
    """
    For every shared fingerprint between submission A and B, find where in
    each submission's token stream (and therefore original source files)
    those matching k-grams appear.

    Groups nearby matches into contiguous blocks so the instructor sees
    "lines 10-25 in Main.java" rather than 15 individual 8-token matches.

    canonical_text_a/b: if provided, uses canonical text for code extraction
    (which has comments stripped). Otherwise loads from original files.
    merge_gap: how many lines apart two match regions can be and still
    get merged into one block. Tuned to 3 because in typical student code
    a few blank lines between copied sections shouldn't split the evidence.
    """
    shared = set(fp_a.keys()) & set(fp_b.keys())
    if not shared:
        return []

    # collect raw match pairs: (a_start_token, a_end_token, b_start_token, b_end_token)
    raw: List[Tuple[int, int, int, int]] = []
    for h in shared:
        # use all occurrences, not just first - catches multiple copies
        for ia in fp_a[h]:
            for ib in fp_b[h]:
                ia_end = min(ia + k - 1, len(tok_a) - 1)
                ib_end = min(ib + k - 1, len(tok_b) - 1)
                raw.append((ia, ia_end, ib, ib_end))

    if not raw:
        return []

    # convert to line numbers for merging
    line_pairs: List[Tuple[int, int, int, int]] = []
    for ia, ia_end, ib, ib_end in raw:
        a1 = _token_line(tok_a, ia)
        a2 = _token_line(tok_a, ia_end)
        b1 = _token_line(tok_b, ib)
        b2 = _token_line(tok_b, ib_end)
        line_pairs.append((a1, a2, b1, b2))

    # sort by a_start then b_start
    line_pairs.sort(key=lambda x: (x[0], x[2]))

    # merge overlapping/nearby blocks
    merged: List[Tuple[int, int, int, int]] = [line_pairs[0]]
    for a1, a2, b1, b2 in line_pairs[1:]:
        pa1, pa2, pb1, pb2 = merged[-1]
        # merge only when BOTH sides are close/overlapping AND the B-side is
        # moving forward (b1 >= pb1).  Without the monotonicity check, two
        # unrelated matches can be fused: A-close + B-backwards still satisfies
        # "b1 <= pb2 + gap" and produces a nonsense wide evidence block.
        if a1 <= pa2 + merge_gap and b1 >= pb1 and b1 <= pb2 + merge_gap:
            merged[-1] = (pa1, max(pa2, a2), pb1, max(pb2, b2))
        else:
            merged.append((a1, a2, b1, b2))

    # Prepare canonical lines if provided (these have comments stripped)
    canonical_lines_a = canonical_text_a.splitlines() if canonical_text_a else None
    canonical_lines_b = canonical_text_b.splitlines() if canonical_text_b else None

    # cache loaded source files so we don't re-read the same file for every block
    _file_cache: Dict[str, List[str]] = {}

    def get_lines(work_dir, filename):
        key = f"{id(work_dir)}::{filename}"
        if key not in _file_cache:
            _file_cache[key] = _load_source_lines(work_dir, filename)
        return _file_cache[key]

    # translate canonical lines back to original file + line
    evidence_blocks = []
    for a1, a2, b1, b2 in merged:
        file_a, orig_a1 = _canonical_line_to_source(a1, source_map_a)
        _, orig_a2      = _canonical_line_to_source(a2, source_map_a)
        file_b, orig_b1 = _canonical_line_to_source(b1, source_map_b)
        _, orig_b2      = _canonical_line_to_source(b2, source_map_b)

        # fallback to canonical line if source map lookup fails
        if file_a is None:
            file_a, orig_a1, orig_a2 = "canonical", a1, a2
        if file_b is None:
            file_b, orig_b1, orig_b2 = "canonical", b1, b2

        la1 = orig_a1 or a1
        la2 = orig_a2 or a2
        lb1 = orig_b1 or b1
        lb2 = orig_b2 or b2

        # Always show ORIGINAL source code (before normalization) so professors
        # see the actual student code, not the canonicalized form.
        # Only fall back to canonical text if the original file cannot be loaded.
        src_lines_a = get_lines(work_dir_a, file_a) if work_dir_a else []
        if src_lines_a:
            code_a = _slice_code(src_lines_a, la1, la2)
        elif canonical_lines_a is not None:
            code_a = "\n".join(canonical_lines_a[a1-1:a2]) if a1 <= len(canonical_lines_a) else ""
        else:
            code_a = ""

        src_lines_b = get_lines(work_dir_b, file_b) if work_dir_b else []
        if src_lines_b:
            code_b = _slice_code(src_lines_b, lb1, lb2)
        elif canonical_lines_b is not None:
            code_b = "\n".join(canonical_lines_b[b1-1:b2]) if b1 <= len(canonical_lines_b) else ""
        else:
            code_b = ""

        # Skip trivial matches where either side spans fewer than 3 lines.
        # k-gram artifacts (isolated brackets, single-statement commonalities)
        # rarely span more than 2 lines. Requiring span >= 3 eliminates the
        # most common false positives without hiding real copied blocks.
        a_span = la2 - la1
        b_span = lb2 - lb1
        if a_span < 3 or b_span < 3:
            continue

        # rough token count for this block.
        # ~8 tokens per line is a realistic average for typed languages (Java/C/C++).
        # The old estimate of 3 was too low — it caused real algorithm blocks to
        # score as LOW even when they clearly contained non-trivial copied logic.
        token_count = (a2 - a1 + 1) * 8

        evidence_blocks.append({
            "file_a":         file_a,
            "lines_a":        [la1, la2],
            "code_a":         code_a,
            "file_b":         file_b,
            "lines_b":        [lb1, lb2],
            "code_b":         code_b,
            "match_strength": _match_strength(token_count),
            "tokens_matched": token_count,
        })

    # sort by strength descending so frontend shows worst offences first
    strength_order = {"high": 0, "medium": 1, "low": 2}
    evidence_blocks.sort(key=lambda e: strength_order.get(e["match_strength"], 3))

    return evidence_blocks
