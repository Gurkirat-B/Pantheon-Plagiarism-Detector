"""
Obfuscation detection.

Compares normalized vs raw token streams and fingerprints to detect
common cheating tactics like variable renaming, loop swaps, dead code
insertion, and structural refactoring.
"""

from typing import Dict, List
from engine.tokenize.lex import Token


def detect_obfuscation(
    tok_a_raw: List[Token],
    tok_b_raw: List[Token],
    tok_a_norm: List[Token],
    tok_b_norm: List[Token],
    fp_a_norm: Dict[int, List[int]],
    fp_b_norm: Dict[int, List[int]],
) -> List[str]:
    """
    Compare normalized vs raw fingerprint scores to detect cheating tricks.

    Two token streams per submission:
      - raw: identifiers kept as-is
      - normalized: identifiers → "ID", literals → "NUM"/"STR"/"CHR"

    If normalized score >> raw score, student renamed variables.
    """
    flags = []

    from engine.fingerprint.kgrams import build_fingerprints
    from engine.similarity.scores import jaccard

    fp_a_raw = build_fingerprints(tok_a_raw, k=8)
    fp_b_raw = build_fingerprints(tok_b_raw, k=8)

    raw_score  = jaccard(fp_a_raw, fp_b_raw)
    norm_score = jaccard(fp_a_norm, fp_b_norm)

    # ── Identifier Renaming ──────────────────────────────────────
    # normalized >> raw means identifiers were systematically changed
    if norm_score - raw_score > 0.12 and norm_score > 0.3:
        flags.append("identifier_renaming")

    # ── Loop Type Swap (for ↔ while ↔ do-while) ─────────────────
    a_loops = _count_loop_types(tok_a_raw)
    b_loops = _count_loop_types(tok_b_raw)

    if _loops_swapped(a_loops, b_loops) and norm_score > 0.3:
        flags.append("loop_type_swap")

    # ── Literal Substitution ─────────────────────────────────────
    a_lits = [t.text for t in tok_a_raw if t.text in ("STR", "NUM", "CHR") or
              t.text.startswith('"') or t.text.startswith("'") or
              t.text[:1].isdigit()]
    b_lits = [t.text for t in tok_b_raw if t.text in ("STR", "NUM", "CHR") or
              t.text.startswith('"') or t.text.startswith("'") or
              t.text[:1].isdigit()]

    if a_lits and b_lits:
        shared = set(a_lits) & set(b_lits)
        total  = set(a_lits) | set(b_lits)
        if total and (len(shared) / len(total)) < 0.3 and norm_score > 0.4:
            flags.append("literal_substitution")

    # ── Dead Code Insertion ──────────────────────────────────────
    len_a = len(tok_a_norm)
    len_b = len(tok_b_norm)
    min_len = max(min(len_a, len_b), 1)
    max_len = max(len_a, len_b)
    ratio = max_len / min_len

    if ratio > 1.4 and norm_score > 0.45:
        flags.append("dead_code_insertion")

    # ── Code Reordering ──────────────────────────────────────────
    # high normalized similarity but different sequential structure
    # check if the shared fingerprints appear in very different positions
    if norm_score > 0.5 and not flags:
        shared_hashes = set(fp_a_norm.keys()) & set(fp_b_norm.keys())
        if shared_hashes:
            position_deltas = []
            for h in list(shared_hashes)[:50]:  # sample up to 50
                pos_a = fp_a_norm[h][0] / max(len(tok_a_norm), 1)
                pos_b = fp_b_norm[h][0] / max(len(tok_b_norm), 1)
                position_deltas.append(abs(pos_a - pos_b))
            avg_delta = sum(position_deltas) / len(position_deltas) if position_deltas else 0
            if avg_delta > 0.25:
                flags.append("code_reordering")

    # ── Comment Stuffing (detected via length discrepancy) ───────
    # if raw text lengths differ dramatically but token counts are similar
    # this suggests one added lots of non-code content
    # (comments were already stripped, so this is a secondary check)

    # ── Switch ↔ If-Else Conversion ──────────────────────────────
    a_has_switch = any(t.text == "switch" for t in tok_a_raw)
    b_has_switch = any(t.text == "switch" for t in tok_b_raw)
    a_if_count = sum(1 for t in tok_a_raw if t.text == "if")
    b_if_count = sum(1 for t in tok_b_raw if t.text == "if")

    if norm_score > 0.35:
        if a_has_switch and not b_has_switch and b_if_count > a_if_count + 2:
            flags.append("switch_to_ifelse")
        elif b_has_switch and not a_has_switch and a_if_count > b_if_count + 2:
            flags.append("switch_to_ifelse")

    # ── Ternary ↔ If-Else Conversion ────────────────────────────
    a_ternary = sum(1 for t in tok_a_raw if t.text == "?")
    b_ternary = sum(1 for t in tok_b_raw if t.text == "?")
    if norm_score > 0.35:
        if a_ternary > 0 and b_ternary == 0:
            flags.append("ternary_to_ifelse")
        elif b_ternary > 0 and a_ternary == 0:
            flags.append("ternary_to_ifelse")

    return flags


def _count_loop_types(tokens: List[Token]) -> dict:
    """Count occurrences of each loop keyword."""
    counts = {"for": 0, "while": 0, "do": 0}
    for t in tokens:
        if t.text in counts:
            counts[t.text] += 1
    return counts


def _loops_swapped(a: dict, b: dict) -> bool:
    """Detect if one uses for-loops where the other uses while-loops."""
    a_total = a["for"] + a["while"]
    b_total = b["for"] + b["while"]
    if a_total == 0 or b_total == 0:
        return False

    # one is predominantly for, the other predominantly while
    a_for_ratio = a["for"] / a_total
    b_for_ratio = b["for"] / b_total
    return abs(a_for_ratio - b_for_ratio) > 0.6
