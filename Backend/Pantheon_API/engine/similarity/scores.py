"""
Similarity scoring — v2 formula (ENGINE_DESIGN.md §7).

Base score (always computed, every pair):

    K-gram group (0.45 total):
        Jaccard              × 0.10
        Containment          × 0.20
        Cosine               × 0.15

    AST group (0.45 total):
        Subtree similarity   × 0.25
        Method-pair match    × 0.20

    Supporting (0.10 total):
        Structural cosine    × 0.10
                              ──────
        Base total            1.00

K-gram and AST groups carry exactly equal total weight (0.45 each). This is
the central design decision — both are primary signals, neither can gate the
other. A pair that scores near zero on k-grams but 0.72 on AST still lands
in the suspicious range.

PDG modifier (conditional, applied by apply_pdg_modifier()):
    final_score = base_score × 0.80 + pdg_similarity × 0.20

The individual metric functions (jaccard, containment, cosine_similarity_tokens,
structural_cosine) are unchanged from v1. Only weighted_score() has new
parameters for the AST signals.

Fallback behaviour: if AST signals are not provided (e.g. tree-sitter unavailable
or language unsupported), the AST group collapses to 0 and the k-gram group
weights are scaled proportionally so the formula still sums to 1.0.
"""

import math
from collections import Counter
from typing import Dict, List, Optional


def jaccard(fp_a: Dict[int, List[int]], fp_b: Dict[int, List[int]]) -> float:
    """|A ∩ B| / |A ∪ B| — underestimates similarity when one submission is much longer."""
    a = set(fp_a.keys())
    b = set(fp_b.keys())
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def containment(fp_a: Dict[int, List[int]], fp_b: Dict[int, List[int]]) -> float:
    """|A ∩ B| / min(|A|, |B|) — the key metric for catching partial plagiarism,
    where a student copies one function from another's much larger submission."""
    a = set(fp_a.keys())
    b = set(fp_b.keys())
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    smaller = min(len(a), len(b))
    return len(a & b) / smaller


def _cosine(vec_a: Dict, vec_b: Dict) -> float:
    """Cosine similarity between two frequency dictionaries."""
    if not vec_a or not vec_b:
        return 0.0
    dot = sum(vec_a[k] * vec_b[k] for k in vec_a if k in vec_b)
    if dot == 0:
        return 0.0
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _to_str_list(tokens) -> List[str]:
    """Accept either a list of strings or a list of Token objects (with a .text attribute)."""
    if not tokens:
        return []
    if hasattr(tokens[0], "text"):
        return [t.text for t in tokens]
    return list(tokens)


def cosine_similarity_tokens(tok_a, tok_b) -> float:
    """
    Compute cosine similarity on token frequency vectors. We use a sublinear
    term frequency formula (1 + log(count)) so that a token appearing 100 times
    doesn't completely dominate the score over one that appears 10 times.
    This catches semantic similarity even when fingerprints diverge due to
    renaming or other minor structural changes.
    """
    tok_a = _to_str_list(tok_a)
    tok_b = _to_str_list(tok_b)
    if not tok_a or not tok_b:
        return 0.0

    tf_a = Counter(tok_a)
    tf_b = Counter(tok_b)

    vec_a = {t: 1 + math.log(c) for t, c in tf_a.items()}
    vec_b = {t: 1 + math.log(c) for t, c in tf_b.items()}
    return _cosine(vec_a, vec_b)


# The keywords that define the structure of a program — the branching, looping,
# and flow-control constructs that determine what an algorithm actually does.
# Two programs with the same algorithmic logic will have similar counts of
# these keywords regardless of what the variables or function names are called.
_STRUCTURAL_KEYWORDS = {
    "LOOP",  # for/while/do/loop — all normalized to LOOP in tok_norm
    "if", "else", "elif", "switch", "case",
    "return", "break", "continue", "try", "catch", "throw",
    "class", "def", "function", "lambda", "yield",
}


def structural_cosine(tok_a, tok_b) -> float:
    """Cosine similarity computed only on control-flow keyword counts.
    Two programs with the same algorithmic shape will score high here even
    if their variable names, literal values, and function names are all different."""
    tok_a = _to_str_list(tok_a)
    tok_b = _to_str_list(tok_b)
    if not tok_a or not tok_b:
        return 0.0

    vec_a = Counter(t for t in tok_a if t in _STRUCTURAL_KEYWORDS)
    vec_b = Counter(t for t in tok_b if t in _STRUCTURAL_KEYWORDS)
    return _cosine(vec_a, vec_b)


def weighted_score(
    fp_a: Dict[int, List[int]],
    fp_b: Dict[int, List[int]],
    tok_a: Optional[List[str]] = None,
    tok_b: Optional[List[str]] = None,
    ast_subtree_similarity: Optional[float] = None,
    method_pair_match:      Optional[float] = None,
) -> dict:
    """
    Compute all similarity signals and combine them into a weighted base score.

    v2 formula (ENGINE_DESIGN.md §7):
        K-gram group  (0.45): jaccard×0.10 + containment×0.20 + cosine×0.15
        AST group     (0.45): subtree×0.25 + method_pair×0.20
        Supporting    (0.10): structural_cosine×0.10

    Fallback when AST signals are absent:
        The 0.45 AST weight is redistributed to the k-gram group proportionally:
        jaccard×0.16 + containment×0.32 + cosine×0.24 + structural×0.28
        (ratios preserved relative to original v1 formula)

    Fallback when token lists are absent (no cosine/structural):
        Only jaccard and containment are used, scaled to sum to 1.

    Args:
        fp_a, fp_b:              Winnowed fingerprint dicts from kgrams.winnow()
        tok_a, tok_b:            Normalized token lists (for cosine/structural)
        ast_subtree_similarity:  Output of subtree.subtree_similarity() in [0,1]
        method_pair_match:       Output of method_match.best_match_score() in [0,1]

    Returns:
        Dict with individual scores and 'weighted_final' (base score, no PDG).
    """
    j = jaccard(fp_a, fp_b)
    c = containment(fp_a, fp_b)

    has_tokens = tok_a is not None and tok_b is not None
    has_ast    = ast_subtree_similarity is not None and method_pair_match is not None

    cos    = cosine_similarity_tokens(tok_a, tok_b) if has_tokens else None
    struct = structural_cosine(tok_a, tok_b)        if has_tokens else None

    if has_ast and has_tokens:
        # Full v2 formula
        final = round(
            0.10 * j
            + 0.20 * c
            + 0.15 * cos
            + 0.25 * ast_subtree_similarity
            + 0.20 * method_pair_match
            + 0.10 * struct,
            4,
        )
    elif has_ast and not has_tokens:
        # AST available, no token lists
        final = round(
            0.15 * j
            + 0.30 * c
            + 0.25 * ast_subtree_similarity
            + 0.20 * method_pair_match,
            4,
        )
    elif not has_ast and has_tokens:
        # Fallback: no AST — redistribute 0.45 AST weight to k-gram group
        # (preserves relative k-gram weights from v1)
        final = round(
            0.16 * j
            + 0.32 * c
            + 0.24 * cos
            + 0.28 * struct,
            4,
        )
    else:
        # Minimal fallback: only jaccard + containment
        final = round(0.36 * j + 0.64 * c, 4)

    result = {
        "jaccard":        round(j, 4),
        "containment":    round(c, 4),
        "weighted_final": final,
    }
    if cos is not None:
        result["cosine"]     = round(cos, 4)
        result["structural"] = round(struct, 4)
    if has_ast:
        result["ast_subtree"]   = round(ast_subtree_similarity, 4)
        result["method_pair"]   = round(method_pair_match, 4)
    return result


def apply_pdg_modifier(base_score: float, pdg_similarity: float) -> float:
    """
    Apply the PDG modifier to a base score.

    Formula (ENGINE_DESIGN.md §7):
        final = base_score × 0.80 + pdg_similarity × 0.20

    The 80/20 split means PDG can meaningfully shift a borderline result
    without overriding the primary signals. A pair at 0.55 base score
    that PDG scores at 0.90 would land at 0.62 — clearly suspicious.
    A pair at 0.55 that PDG scores at 0.10 would land at 0.46 — clears suspicion.

    This is only called from api.py when the PDG trigger conditions are met.

    Args:
        base_score:     The weighted_final from weighted_score().
        pdg_similarity: Output of pdg.compare.pdg_similarity() in [0.0, 1.0].

    Returns:
        float in [0.0, 1.0]
    """
    return round(min(base_score * 0.80 + pdg_similarity * 0.20, 1.0), 4)
