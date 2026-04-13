"""
This file computes how similar two submissions are to each other. Rather than
relying on a single number, we compute four different similarity measures that
each capture a slightly different aspect of similarity, then combine them into
one weighted final score.

Jaccard similarity is the fraction of fingerprints shared between two sets.
It works well when submissions are roughly the same length, but underestimates
similarity when one submission is much longer than the other.

Containment similarity fixes that problem: instead of dividing by the union of
both sets, it divides by the size of the smaller set. This means a small block
of copied code still scores high even when it appears inside a much larger submission.

Cosine similarity on token frequencies catches cases where the fingerprints
diverge slightly (e.g. due to different variable names) but the overall
vocabulary of tokens is still very similar.

Structural cosine looks only at control-flow keywords like if, for, while,
return, and try. Two programs that share the same algorithmic structure will
have similar counts of these keywords even if everything else is different.

The weighted final score is: jaccard×0.20 + containment×0.35 + cosine×0.30 + structural×0.15.
Containment gets the highest weight because partial plagiarism (one student
copying a function from another) is the most common pattern we need to catch.
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
) -> dict:
    """
    Compute all four similarity metrics and combine them into one weighted score.
    If token lists are not provided, the cosine and structural components fall back
    to zero and the weights for the remaining two metrics are adjusted proportionally.
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
