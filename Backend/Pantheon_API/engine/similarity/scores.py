"""
engine/similarity/scores.py

Similarity metrics used to compare two sets of fingerprints.

Jaccard is the standard set overlap measure. Containment is the most
important fingerprint metric for catching partial plagiarism — it asks
how much of the smaller submission appears in the larger one.

cosine_similarity_tokens computes cosine similarity on raw token
frequency vectors — catches semantic similarity even when fingerprints
diverge (e.g. after heavy refactoring).

structural_cosine computes cosine on structural keyword frequency
vectors — catches programs with the same control-flow shape.

weighted_score() combines all four into a single final score.
"""

import math
from collections import Counter
from typing import Dict, List, Optional


def jaccard(fp_a: Dict[int, List[int]], fp_b: Dict[int, List[int]]) -> float:
    """
    |A ∩ B| / |A ∪ B|

    Standard set similarity. Good general measure but understimates similarity
    when one submission is much longer than the other (e.g. student added
    a bunch of their own code on top of copied code).
    """
    a = set(fp_a.keys())
    b = set(fp_b.keys())
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def containment(fp_a: Dict[int, List[int]], fp_b: Dict[int, List[int]]) -> float:
    """
    |A ∩ B| / min(|A|, |B|)

    This is the key metric for catching partial plagiarism.
    If a student copies 80% of someone else's short assignment into their
    longer submission, Jaccard might be 0.4 but containment is ~0.8.
    We use the smaller set as denominator because we want to know:
    "how much of the smaller submission appears in the larger one?"
    """
    a = set(fp_a.keys())
    b = set(fp_b.keys())
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    smaller = min(len(a), len(b))
    return len(a & b) / smaller


def _cosine(vec_a: Dict, vec_b: Dict) -> float:
    """Cosine similarity between two frequency dicts. Pure Python."""
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
    """Accept either List[str] or List[Token] (with .text attr)."""
    if not tokens:
        return []
    if hasattr(tokens[0], "text"):
        return [t.text for t in tokens]
    return list(tokens)


def cosine_similarity_tokens(tok_a, tok_b) -> float:
    """
    Cosine similarity on raw token frequency vectors (bag-of-words).

    Uses sublinear (log-normalised) TF: weight(t) = 1 + log(tf) when tf > 0.
    Sublinear TF prevents a single repeated token (e.g. a variable used 50×)
    from dominating the vector and masking other differences.

    Plain TF-IDF doesn't apply here because we have exactly 2 documents —
    shared terms get IDF=0 and unique terms get full weight, which is
    backwards for plagiarism detection. Bag-of-words cosine is the right
    metric: two copies with identical token distributions score ~1.0.

    Catches semantic similarity even when fingerprints diverge — e.g. a
    student who rewrites every function name but keeps the same token
    distribution will still score high here.
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


# Structural keywords: control-flow constructs that define program shape.
# Language-agnostic at the token level since the lexer normalises keywords.
_STRUCTURAL_KEYWORDS = {
    "LOOP",  # for/while/do/loop — all normalized to LOOP in tok_norm
    "if", "else", "elif", "switch", "case",
    "return", "break", "continue", "try", "catch", "throw",
    "class", "def", "function", "lambda", "yield",
}


def structural_cosine(tok_a, tok_b) -> float:
    """
    Cosine similarity on structural keyword frequency vectors.

    Ignores variable names, literals, and identifiers entirely — only
    counts occurrences of control-flow and structure keywords. Two programs
    with the same loop/branch/function shape will score high even if every
    identifier is renamed.
    """
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
) -> dict:
    """
    Computes all scores and a weighted final.

    Weights (sum to 1.0):
      - Jaccard     0.20  - overall fingerprint overlap
      - Containment 0.35  - catches partial copying (most important)
      - Cosine      0.30  - token-level semantic similarity
      - Structural  0.15  - control-flow shape similarity

    When tok_a/tok_b are not supplied, cosine and structural fall back to
    0.0 and their weight is redistributed to the fingerprint metrics.

    Returns a dict so the caller can store all scores separately in the DB.
    """
    j = jaccard(fp_a, fp_b)
    c = containment(fp_a, fp_b)

    if tok_a is not None and tok_b is not None:
        cos = cosine_similarity_tokens(tok_a, tok_b)
        struct = structural_cosine(tok_a, tok_b)
        final = round(0.20 * j + 0.35 * c + 0.30 * cos + 0.15 * struct, 4)
    else:
        cos = None
        struct = None
        # Fallback: jaccard + containment only, containment weighted higher
        final = round(0.36 * j + 0.64 * c, 4)

    result = {
        "jaccard":        round(j, 4),
        "containment":    round(c, 4),
        "weighted_final": final,
    }
    if cos is not None:
        result["cosine"]     = round(cos, 4)
        result["structural"] = round(struct, 4)
    return result
