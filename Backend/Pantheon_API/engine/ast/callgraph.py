"""
Call graph structural comparison.

Extracts the caller→callee relationship graph from each submission and computes
a normalized structural similarity score. Two submissions with the same call
graph structure — even if all function names are different — are likely copies.

Call graph comparison handles a specific obfuscation pattern that subtree hashing
partially misses: when a student renames every function AND restructures the code
so that the same set of inter-function calls exists. The call graph structure
(which function calls which, and how many callees each caller has) is preserved
through renaming.

What we compare:
  1. Degree distribution — how many functions each caller calls. Two call graphs
     with identical degree sequences (sorted list of out-degrees) likely have the
     same structure even if all names differ.

  2. Normalized adjacency signature — for each caller, the sorted tuple of
     (out_degree_of_callee) values. This captures one hop of structural context
     per node without relying on names.

  3. Recursive call presence — whether each function calls itself. A recursive
     function converted to an iterative one changes this flag; it is preserved
     under renaming.

These three signals are combined into a single call graph similarity score.
This score is supporting evidence — it is not used in the base scoring formula
directly but is attached to the result dict for api.py to inspect.

Public API:
    compare_callgraphs(cg_a, cg_b) → float in [0.0, 1.0]
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, List


# ---------------------------------------------------------------------------
# Structural feature extraction
# ---------------------------------------------------------------------------

def _out_degrees(cg: Dict[str, List[str]]) -> List[int]:
    """Sorted list of out-degrees (number of distinct callees) for each function."""
    return sorted(len(set(callees)) for callees in cg.values())


def _recursive_flags(cg: Dict[str, List[str]]) -> int:
    """Count of self-recursive functions in the call graph."""
    return sum(1 for fn, callees in cg.items() if fn in callees)


def _callee_degree_tuples(cg: Dict[str, List[str]]) -> List[tuple]:
    """
    For each function f, produce a sorted tuple of out-degrees of f's callees.
    This gives a one-hop structural fingerprint for f that is name-independent.
    Sort and return the full list of such tuples so we can compare them as bags.
    """
    tuples = []
    for fn, callees in cg.items():
        callee_degrees = tuple(
            sorted(len(set(cg.get(c, []))) for c in set(callees))
        )
        tuples.append(callee_degrees)
    return sorted(tuples)


# ---------------------------------------------------------------------------
# Similarity scoring
# ---------------------------------------------------------------------------

def _degree_distribution_similarity(cg_a, cg_b) -> float:
    """
    Compare the sorted out-degree sequences of two call graphs.
    Uses a simple overlap metric: how many entries match pairwise.
    """
    deg_a = _out_degrees(cg_a)
    deg_b = _out_degrees(cg_b)
    if not deg_a or not deg_b:
        return 0.0

    # Truncate to the shorter list (conservative — same as containment logic)
    n = min(len(deg_a), len(deg_b))
    matches = sum(1 for a, b in zip(sorted(deg_a)[:n], sorted(deg_b)[:n]) if a == b)
    return matches / n


def _neighbor_profile_similarity(cg_a, cg_b) -> float:
    """
    Compare the multisets of one-hop structural tuples.
    Uses Jaccard on the Counter objects.
    """
    tuples_a = Counter(_callee_degree_tuples(cg_a))
    tuples_b = Counter(_callee_degree_tuples(cg_b))
    if not tuples_a or not tuples_b:
        return 0.0

    intersection = sum((tuples_a & tuples_b).values())
    union        = sum((tuples_a | tuples_b).values())
    return intersection / union if union > 0 else 0.0


def _recursive_similarity(cg_a, cg_b) -> float:
    """
    Binary signal: do the two submissions have the same count of recursive functions?
    1.0 if equal, 0.0 otherwise (or 1.0 if both have none).
    """
    ra = _recursive_flags(cg_a)
    rb = _recursive_flags(cg_b)
    if ra == 0 and rb == 0:
        return 1.0
    if ra == 0 or rb == 0:
        return 0.0
    return 1.0 if ra == rb else max(0.0, 1.0 - abs(ra - rb) / max(ra, rb))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compare_callgraphs(
    cg_a: Dict[str, List[str]],
    cg_b: Dict[str, List[str]],
) -> float:
    """
    Compute a structural similarity score between two call graphs.

    Args:
        cg_a: Call graph dict from parse_submission/parse_source for submission A.
              Shape: { caller_name: [callee_name, ...] }
        cg_b: Same for submission B.

    Returns:
        float in [0.0, 1.0] representing structural call graph similarity.
        0.0 if either submission has no functions.
    """
    if not cg_a or not cg_b:
        return 0.0

    degree_sim    = _degree_distribution_similarity(cg_a, cg_b)
    neighbor_sim  = _neighbor_profile_similarity(cg_a, cg_b)
    recursive_sim = _recursive_similarity(cg_a, cg_b)

    # Weights:
    #   degree distribution: 0.40 — most stable under renaming
    #   neighbor profile:    0.40 — captures one-hop structure
    #   recursive flags:     0.20 — supporting binary signal
    score = (
        0.40 * degree_sim
        + 0.40 * neighbor_sim
        + 0.20 * recursive_sim
    )

    return round(min(score, 1.0), 6)
