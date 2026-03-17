"""
engine/similarity/scores.py

Three similarity metrics used to compare two sets of fingerprints.

Jaccard is the standard set overlap measure. Dice is similar but
slightly more generous to submissions of equal size. Containment
is the most important one for catching partial plagiarism — it asks
how much of the smaller submission appears in the larger one, which
Jaccard dilutes when one student adds a lot of their own code on top.

weighted_score() combines all three into a single final score.
"""

from typing import Dict, List


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


def dice(fp_a: Dict[int, List[int]], fp_b: Dict[int, List[int]]) -> float:
    """
    2 * |A ∩ B| / (|A| + |B|)

    Sorensen-Dice coefficient. Gives more weight to shared fingerprints
    relative to the combined size. Slightly more sensitive than Jaccard
    when submissions have similar lengths.
    """
    a = set(fp_a.keys())
    b = set(fp_b.keys())
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return (2 * len(a & b)) / (len(a) + len(b))


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


def weighted_score(fp_a: Dict[int, List[int]], fp_b: Dict[int, List[int]]) -> dict:
    """
    Computes all three scores and a weighted final.

    Weights:
      - Jaccard 0.35   - overall structural overlap
      - Dice    0.25   - symmetric similarity
      - Contain 0.40   - catches partial copying, weighted highest

    Returns a dict so the caller can store all scores separately in the DB.
    """
    j = jaccard(fp_a, fp_b)
    d = dice(fp_a, fp_b)
    c = containment(fp_a, fp_b)
    final = round(0.35 * j + 0.25 * d + 0.40 * c, 4)

    return {
        "jaccard":       round(j, 4),
        "dice":          round(d, 4),
        "containment":   round(c, 4),
        "weighted_final": final,
    }
