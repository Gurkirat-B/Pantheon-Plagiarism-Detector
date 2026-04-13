"""
This file looks at two submissions and tries to figure out if one was copied
from the other but modified to look different. It runs 13 independent checks,
each looking for a specific kind of modification students commonly use to hide
plagiarism. Any checks that fire are returned as a list of flag names.
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
    Takes two submissions in two forms each — the raw original tokens and a
    normalized version where all variable names are replaced with "ID" and all
    numbers/strings are replaced with "NUM"/"STR". By comparing the two forms
    against each other, we can spot specific modifications like renaming variables,
    swapping loop types, or reordering functions.
    """
    flags = []

    from engine.fingerprint.kgrams import build_fingerprints
    from engine.similarity.scores import jaccard

    fp_a_raw    = build_fingerprints(tok_a_raw,  k=8)
    fp_b_raw    = build_fingerprints(tok_b_raw,  k=8)

    # We fingerprint both the raw and normalized versions at the same chunk size (k=8)
    # so the similarity scores are directly comparable. The k=10 normalized fingerprints
    # passed in from the engine are only used for the position-based reordering check below.
    fp_a_norm_8 = build_fingerprints(tok_a_norm, k=8)
    fp_b_norm_8 = build_fingerprints(tok_b_norm, k=8)

    raw_score  = jaccard(fp_a_raw,    fp_b_raw)
    norm_score = jaccard(fp_a_norm_8, fp_b_norm_8)

    # If the normalized versions match much better than the raw versions, it means
    # the two submissions have the same structure but different variable names —
    # a classic sign of renaming to disguise copying.
    if norm_score - raw_score > 0.12 and norm_score > 0.3:
        flags.append("identifier_renaming")

    # Count how many for-loops, while-loops, and do-while-loops each submission uses.
    # If one uses mostly for-loops and the other uses mostly while-loops, that's a
    # deliberate structural change to make the code look different.
    a_loops = _count_loop_types(tok_a_raw)
    b_loops = _count_loop_types(tok_b_raw)
    if _loops_swapped(a_loops, b_loops) and norm_score > 0.3:
        flags.append("loop_type_swap")

    # Collect all the literal values (numbers and strings) from each submission.
    # If the code structure is similar but almost none of the literal values match,
    # the student likely changed all the constants to hide the copy.
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

    # If one submission is more than 25% longer than the other but the structure
    # still matches well, the extra code is likely dead code added to pad the
    # submission and make it look like original work.
    len_a = len(tok_a_norm)
    len_b = len(tok_b_norm)
    min_len = max(min(len_a, len_b), 1)
    max_len = max(len_a, len_b)
    ratio = max_len / min_len
    if ratio > 1.25 and norm_score > 0.45:
        flags.append("dead_code_insertion")

    # Look at where each shared code chunk appears within its submission — expressed
    # as a fraction of the total file length. If the same chunks appear at very
    # different positions (average difference > 20%), the functions were shuffled around.
    if norm_score > 0.5:
        shared_hashes = set(fp_a_norm.keys()) & set(fp_b_norm.keys())
        if shared_hashes:
            position_deltas = []
            for h in list(shared_hashes)[:50]:  # sample up to 50 to keep it fast
                pos_a = fp_a_norm[h][0] / max(len(tok_a_norm), 1)
                pos_b = fp_b_norm[h][0] / max(len(tok_b_norm), 1)
                position_deltas.append(abs(pos_a - pos_b))
            avg_delta = sum(position_deltas) / len(position_deltas) if position_deltas else 0
            if avg_delta > 0.20:
                flags.append("code_reordering")

    # A switch statement and a chain of if-else statements can express the exact same
    # logic. If one submission uses switch and the other uses significantly more if
    # statements to cover the same cases, the student converted between them.
    a_has_switch = any(t.text == "switch" for t in tok_a_raw)
    b_has_switch = any(t.text == "switch" for t in tok_b_raw)
    a_if_count = sum(1 for t in tok_a_raw if t.text == "if")
    b_if_count = sum(1 for t in tok_b_raw if t.text == "if")

    if norm_score > 0.35:
        if a_has_switch and not b_has_switch and b_if_count > a_if_count + 2:
            flags.append("switch_to_ifelse")
        elif b_has_switch and not a_has_switch and a_if_count > b_if_count + 2:
            flags.append("switch_to_ifelse")

    # A ternary expression (condition ? value_if_true : value_if_false) does the same
    # thing as an if-else block. If one submission uses the ? operator and the other
    # never does, they likely converted one form to the other. We use a low similarity
    # threshold here because expanding ternaries adds extra tokens, which naturally
    # reduces the raw similarity score even when the logic is identical.
    a_ternary = sum(1 for t in tok_a_raw if t.text == "?")
    b_ternary = sum(1 for t in tok_b_raw if t.text == "?")
    if norm_score > 0.10:
        if a_ternary > 0 and b_ternary == 0:
            flags.append("ternary_to_ifelse")
        elif b_ternary > 0 and a_ternary == 0:
            flags.append("ternary_to_ifelse")

    # If one submission wraps significantly more code in try-catch blocks than the
    # other at high structural similarity, it suggests try-catch was added purely
    # to inflate line count and change the visual structure.
    a_try = sum(1 for t in tok_a_raw if t.text == "try")
    b_try = sum(1 for t in tok_b_raw if t.text == "try")
    if norm_score > 0.35 and abs(a_try - b_try) >= 2:
        flags.append("exception_wrapping")

    # Java has two ways to loop through a collection: `for (Item x : list)` and
    # `for (int i = 0; i < list.size(); i++)`. They do the same thing but look
    # completely different. We detect this by looking for a colon inside a for-loop header.
    a_enhanced = _count_enhanced_for(tok_a_raw)
    b_enhanced = _count_enhanced_for(tok_b_raw)
    if norm_score > 0.3:
        if (a_enhanced == 0 and b_enhanced > 0) or (a_enhanced > 0 and b_enhanced == 0):
            flags.append("for_each_to_indexed")

    # Shorthand operators like i++ or x += 5 can be rewritten as i = i + 1 or
    # x = x + 5. If one submission consistently uses shorthand and the other
    # doesn't, at similar structural similarity, the operators were expanded to
    # disguise the copy.
    _COMPOUND_OPS = {"+=", "-=", "*=", "/=", "%=", "++", "--", "&=", "|=", "^=", "<<=", ">>="}
    a_compound = sum(1 for t in tok_a_raw if t.text in _COMPOUND_OPS)
    b_compound = sum(1 for t in tok_b_raw if t.text in _COMPOUND_OPS)
    if norm_score > 0.35:
        max_c = max(a_compound, b_compound)
        min_c = min(a_compound, b_compound)
        if max_c >= 4 and min_c <= max_c * 0.30:
            flags.append("compound_op_expansion")

    # Splitting one large function into several smaller helper functions is a common
    # way to break up fingerprint matches. We estimate the number of functions by
    # counting how many times an opening brace { appears right after a closing
    # parenthesis ) — the pattern that ends every function signature.
    a_methods = _count_method_braces(tok_a_raw)
    b_methods = _count_method_braces(tok_b_raw)
    if norm_score > 0.40:
        max_m = max(a_methods, b_methods)
        min_m = max(min(a_methods, b_methods), 1)
        if max_m / min_m > 1.8 and max_m >= 4:
            flags.append("method_decomposition")

    # Logical conditions can be flipped using De Morgan's law: if (a > b) becomes
    # if (!(a <= b)). This adds negation operators without changing the meaning.
    # A large asymmetry in how many ! operators each submission uses is a signal.
    a_negate = sum(1 for t in tok_a_raw if t.text == "!")
    b_negate = sum(1 for t in tok_b_raw if t.text == "!")
    if norm_score > 0.35:
        max_n = max(a_negate, b_negate)
        min_n = min(a_negate, b_negate)
        if max_n >= 3 and (min_n == 0 or max_n / min_n > 2.5):
            flags.append("condition_negation")

    # Instead of writing `return a + b` directly, a student might write
    # `int temp = a + b; return temp;` to add extra lines and obscure the copy.
    # We count plain assignment operators (=) — not += or == which are separate tokens —
    # to measure how many extra intermediate variables were introduced.
    a_assigns = sum(1 for t in tok_a_raw if t.text == "=")
    b_assigns = sum(1 for t in tok_b_raw if t.text == "=")
    if norm_score > 0.35:
        max_a = max(a_assigns, b_assigns)
        min_a = max(min(a_assigns, b_assigns), 1)
        diff  = abs(a_assigns - b_assigns)
        if diff >= 5 and max_a / min_a > 2.0:
            flags.append("intermediate_variable")

    return flags


def _count_loop_types(tokens: List[Token]) -> dict:
    """Count how many for, while, and do-while loops appear in the token stream."""
    counts = {"for": 0, "while": 0, "do": 0}
    for t in tokens:
        if t.text in counts:
            counts[t.text] += 1
    return counts


def _loops_swapped(a: dict, b: dict) -> bool:
    """
    Returns True if one submission mostly uses for-loops while the other mostly
    uses while-loops (or vice versa). We compute what fraction of all loops are
    for-loops in each submission — a difference greater than 50% is a strong signal.
    """
    a_total = a["for"] + a["while"] + a["do"]
    b_total = b["for"] + b["while"] + b["do"]
    if a_total == 0 or b_total == 0:
        return False

    a_for_ratio = a["for"] / a_total
    b_for_ratio = b["for"] / b_total
    return abs(a_for_ratio - b_for_ratio) > 0.5


def _count_method_braces(tokens: List[Token]) -> int:
    """
    Estimates the number of functions/methods by counting how many opening braces
    appear within 5 tokens after a closing parenthesis. This pattern matches the
    end of any function signature. We look back up to 5 tokens to handle cases
    like `void foo() throws Exception {` where the brace isn't immediately after.
    """
    count = 0
    for i, tok in enumerate(tokens):
        if tok.text == "{":
            for j in range(max(0, i - 5), i):
                if tokens[j].text == ")":
                    count += 1
                    break
    return count


def _count_enhanced_for(tokens: List[Token]) -> int:
    """
    Counts Java enhanced for-loops (for-each) by looking for a colon inside the
    for-loop's parentheses at depth 1. A regular indexed for-loop uses semicolons
    inside its parentheses, not a colon, so this cleanly distinguishes the two.
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
