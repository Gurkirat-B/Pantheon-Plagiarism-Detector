"""
Obfuscation detection.

Each check is independent and documents its reasoning clearly.
Detected flags:

  1.  identifier_renaming   — normalized score >> raw score → variable names changed
  2.  loop_type_swap        — for ↔ while ↔ do-while detected by keyword distribution
  3.  literal_substitution  — different set of literal values in same structure
  4.  dead_code_insertion   — one submission is 25%+ longer by token count
  5.  code_reordering       — shared fingerprints appear at very different positions
  6.  switch_to_ifelse      — one has switch, other has equivalent if-else chain
  7.  ternary_to_ifelse     — one uses ? : operator, other uses if-else for same logic
  8.  exception_wrapping    — try-catch blocks added around existing code
  9.  for_each_to_indexed   — for-each loop converted to indexed for loop
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
    Compare normalized vs raw token streams and fingerprints to detect
    common cheating tactics.

    Two token streams per submission:
      - raw:        identifiers kept as-is, literals kept as-is
      - normalized: identifiers → "ID", literals → "NUM"/"STR"/"CHR"

    If normalized score >> raw score, student renamed variables.
    All other checks compare structural token patterns between submissions.
    """
    flags = []

    from engine.fingerprint.kgrams import build_fingerprints
    from engine.similarity.scores import jaccard

    fp_a_raw = build_fingerprints(tok_a_raw, k=8)
    fp_b_raw = build_fingerprints(tok_b_raw, k=8)

    raw_score  = jaccard(fp_a_raw, fp_b_raw)
    norm_score = jaccard(fp_a_norm, fp_b_norm)

    # ── 1. Identifier Renaming ────────────────────────────────────────
    # Reasoning: if the normalized fingerprints match much better than the
    # raw fingerprints, the code structure is the same but the names differ.
    # The 0.12 gap threshold avoids false positives from minor naming differences.
    if norm_score - raw_score > 0.12 and norm_score > 0.3:
        flags.append("identifier_renaming")

    # ── 2. Loop Type Swap (for ↔ while ↔ do-while) ───────────────────
    # Reasoning: if one submission uses predominantly for-loops and the other
    # uses while/do-while (or vice versa), at similar similarity, the student
    # rewrote the loop structure. Includes do-while in the total count.
    a_loops = _count_loop_types(tok_a_raw)
    b_loops = _count_loop_types(tok_b_raw)
    if _loops_swapped(a_loops, b_loops) and norm_score > 0.3:
        flags.append("loop_type_swap")

    # ── 3. Literal Substitution ───────────────────────────────────────
    # Reasoning: if the code structure matches but literal values are mostly
    # different, the student changed constants/strings to disguise copying.
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

    # ── 4. Dead Code Insertion ────────────────────────────────────────
    # Reasoning: if one submission has 25%+ more tokens than the other but
    # the normalized fingerprints still match well, extra non-algorithmic code
    # was inserted to pad the submission. Threshold lowered from 1.4 → 1.25
    # to catch moderate insertions (e.g. adding a few helper stubs).
    len_a = len(tok_a_norm)
    len_b = len(tok_b_norm)
    min_len = max(min(len_a, len_b), 1)
    max_len = max(len_a, len_b)
    ratio = max_len / min_len
    if ratio > 1.25 and norm_score > 0.45:
        flags.append("dead_code_insertion")

    # ── 5. Code Reordering ────────────────────────────────────────────
    # Reasoning: if shared fingerprints appear at very different relative
    # positions in each submission, the methods or code blocks were shuffled.
    # NOTE: gate removed — reordering can coexist with renaming or other flags.
    if norm_score > 0.5:
        shared_hashes = set(fp_a_norm.keys()) & set(fp_b_norm.keys())
        if shared_hashes:
            position_deltas = []
            for h in list(shared_hashes)[:50]:  # sample up to 50 fingerprints
                pos_a = fp_a_norm[h][0] / max(len(tok_a_norm), 1)
                pos_b = fp_b_norm[h][0] / max(len(tok_b_norm), 1)
                position_deltas.append(abs(pos_a - pos_b))
            avg_delta = sum(position_deltas) / len(position_deltas) if position_deltas else 0
            if avg_delta > 0.25:
                flags.append("code_reordering")

    # ── 6. Switch ↔ If-Else Conversion ───────────────────────────────
    # Reasoning: if one submission has a switch statement and the other
    # has significantly more if-statements covering the same branches,
    # the student converted between the two equivalent patterns.
    a_has_switch = any(t.text == "switch" for t in tok_a_raw)
    b_has_switch = any(t.text == "switch" for t in tok_b_raw)
    a_if_count = sum(1 for t in tok_a_raw if t.text == "if")
    b_if_count = sum(1 for t in tok_b_raw if t.text == "if")

    if norm_score > 0.35:
        if a_has_switch and not b_has_switch and b_if_count > a_if_count + 2:
            flags.append("switch_to_ifelse")
        elif b_has_switch and not a_has_switch and a_if_count > b_if_count + 2:
            flags.append("switch_to_ifelse")

    # ── 7. Ternary ↔ If-Else Conversion ──────────────────────────────
    # Reasoning: if one submission uses '?' ternary operators and the other
    # uses if-else for the same expressions, the student converted between them.
    # The canonicalize step normalizes both to if-else form before fingerprinting,
    # so this flag catches the structural difference at the raw token level.
    # Threshold is 0.10 (low) because ternary→if-else adds tokens and can
    # reduce the raw fingerprint score even when logic is identical.
    a_ternary = sum(1 for t in tok_a_raw if t.text == "?")
    b_ternary = sum(1 for t in tok_b_raw if t.text == "?")
    if norm_score > 0.10:
        if a_ternary > 0 and b_ternary == 0:
            flags.append("ternary_to_ifelse")
        elif b_ternary > 0 and a_ternary == 0:
            flags.append("ternary_to_ifelse")

    # ── 8. Exception Wrapping ─────────────────────────────────────────
    # Reasoning: a student wraps their copied code in try-catch blocks to
    # inflate line count and make the structure look different. If one submission
    # has 2+ more try blocks than the other at high similarity, flag it.
    a_try = sum(1 for t in tok_a_raw if t.text == "try")
    b_try = sum(1 for t in tok_b_raw if t.text == "try")
    if norm_score > 0.35 and abs(a_try - b_try) >= 2:
        flags.append("exception_wrapping")

    # ── 9. For-Each ↔ Indexed For Loop ───────────────────────────────
    # Reasoning: Java `for (Type x : collection)` and C-style indexed
    # `for (int i = 0; i < n; i++)` are functionally equivalent for
    # array traversal but produce very different token sequences.
    # Detected by counting ':' tokens appearing inside a for() header.
    a_enhanced = _count_enhanced_for(tok_a_raw)
    b_enhanced = _count_enhanced_for(tok_b_raw)
    if norm_score > 0.3:
        if (a_enhanced == 0 and b_enhanced > 0) or (a_enhanced > 0 and b_enhanced == 0):
            flags.append("for_each_to_indexed")

    return flags


# ─── Helpers ────────────────────────────────────────────────────────

def _count_loop_types(tokens: List[Token]) -> dict:
    """Count occurrences of each loop keyword including do-while."""
    counts = {"for": 0, "while": 0, "do": 0}
    for t in tokens:
        if t.text in counts:
            counts[t.text] += 1
    return counts


def _loops_swapped(a: dict, b: dict) -> bool:
    """
    Detect if one submission uses for-loops where the other uses while/do-while.
    Compares the proportion of 'for' loops among all loop constructs.
    A shift > 50% in the for-loop ratio signals a deliberate loop type change.
    """
    a_total = a["for"] + a["while"] + a["do"]
    b_total = b["for"] + b["while"] + b["do"]
    if a_total == 0 or b_total == 0:
        return False

    a_for_ratio = a["for"] / a_total
    b_for_ratio = b["for"] / b_total
    return abs(a_for_ratio - b_for_ratio) > 0.5


def _count_enhanced_for(tokens: List[Token]) -> int:
    """
    Count for-each style loops by detecting ':' inside a for() header.

    Java:   `for (Type x : collection)` — the ':' appears at depth 1 inside for(
    Python: `for x in collection` — uses 'in' keyword, not ':'
    C-style: `for (int i = 0; i < n; i++)` — no ':' at depth 1 inside for(

    This distinguishes enhanced-for from indexed for at the structural level.
    """
    count = 0
    for i, tok in enumerate(tokens):
        if tok.text == "for":
            depth = 0
            for j in range(i + 1, min(i + 30, len(tokens))):
                if tokens[j].text == "(":
                    depth += 1
                elif tokens[j].text == ")":
                    depth -= 1
                    if depth < 0:
                        break
                elif tokens[j].text == ":" and depth == 1:
                    count += 1
                    break
    return count
