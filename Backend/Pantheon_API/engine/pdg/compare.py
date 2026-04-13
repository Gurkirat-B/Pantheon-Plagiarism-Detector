"""
PDG similarity scoring — Phase 3 comparison.

Takes two PDGFeatures objects (built by build.py) and computes a structural
similarity score in [0.0, 1.0].

The comparison operates on compact feature representations — no graph objects
cross this module boundary. This keeps the comparison fast and memory-efficient.

Scoring strategy
----------------
Rather than full graph isomorphism (NP-hard in general), we compare five
structural properties that are invariant to variable names and capture the
key semantic relationships:

  1. Node type distribution (weight 0.35)
     The histogram of normalized statement types (ASSIGN, LOOP, BRANCH, etc.).
     Two programs implementing the same algorithm use similar mixes of these
     statement types regardless of variable names. A sorting algorithm has many
     COMPAREs/ASSIGNs and one LOOP; a Fibonacci function has BRANCHes and RETURNs.
     Compared with cosine similarity on the type count vectors.

  2. Data-flow fan-out similarity (weight 0.25)
     The sorted sequence of out-degrees on data edges captures how widely each
     computed value is used. A recursive function creates deep data chains (each
     call result feeds the next); an iterative version creates local fan-out at
     the accumulator. Compared with sequence overlap.

  3. Data-to-control ratio (weight 0.20)
     The ratio of data edges to control edges. Programs with the same logic but
     different structure (recursion vs iteration) have different ratios — recursive
     code is control-light (one branch check, deep data chain), iterative is
     control-heavy (explicit loop, explicit accumulator). This ratio is preserved
     under renaming and reordering.

  4. Control nesting depth (weight 0.10)
     Maximum depth of the control-dependence tree. Functionally equivalent code
     tends to have the same nesting depth even under obfuscation. A function
     flattened by decomposition will have shallower nesting; this signal catches
     that.

  5. Cycle presence (weight 0.10)
     Binary: does the code contain loops or recursive calls? This is 1.0 when
     both submissions agree and 0.0 when they disagree. It cleanly separates
     iterative computation from non-iterative computation.

Public API:
    pdg_similarity(feats_a, feats_b) → float in [0.0, 1.0]
"""

from __future__ import annotations

import math
from typing import Dict, List

from engine.pdg.build import PDGFeatures


# ---------------------------------------------------------------------------
# Feature comparison helpers
# ---------------------------------------------------------------------------

def _cosine(vec_a: Dict[str, int], vec_b: Dict[str, int]) -> float:
    """
    Cosine similarity between two count vectors (as dicts).
    Returns 0.0 for empty or zero vectors.
    """
    if not vec_a or not vec_b:
        return 0.0

    # Use the union of all keys
    all_keys = set(vec_a) | set(vec_b)
    dot   = sum(vec_a.get(k, 0) * vec_b.get(k, 0) for k in all_keys)
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))

    if mag_a == 0 or mag_b == 0:
        return 0.0
    return min(dot / (mag_a * mag_b), 1.0)


def _degree_seq_similarity(seq_a: List[int], seq_b: List[int]) -> float:
    """
    Compare two sorted degree sequences.

    Truncates both to the shorter length (conservative — partial copying
    should not score as 1.0 just because the shorter sequence matches).
    Computes element-wise match rate with a tolerance of ±1 for near-matches.
    Returns 0.0 if either sequence is empty.
    """
    if not seq_a or not seq_b:
        # If both are empty they have the same (trivial) degree structure
        if not seq_a and not seq_b:
            return 1.0
        return 0.0

    n = min(len(seq_a), len(seq_b))
    a = sorted(seq_a)[:n]
    b = sorted(seq_b)[:n]

    matches = sum(1 for x, y in zip(a, b) if abs(x - y) <= 1)
    return matches / n


def _ratio_similarity(r_a: float, r_b: float) -> float:
    """
    Similarity between two non-negative ratios.
    Returns 1.0 when equal, decays toward 0.0 as the ratio diverges.
    Uses a symmetric log-ratio to handle the case where one ratio is 0.
    """
    if r_a == 0.0 and r_b == 0.0:
        return 1.0
    if r_a == 0.0 or r_b == 0.0:
        # One has data-flow, the other doesn't — meaningful structural difference
        return 0.0

    # log ratio: 0 = identical, grows with divergence
    log_diff = abs(math.log(r_a + 1e-9) - math.log(r_b + 1e-9))
    # Decay: score = exp(-log_diff) so score=1 at log_diff=0,
    #        score≈0.37 at log_diff=1, score≈0.14 at log_diff=2
    return math.exp(-log_diff)


def _depth_similarity(d_a: int, d_b: int) -> float:
    """
    Similarity between two nesting depth values.
    Returns 1.0 when equal, decreases as depths diverge.
    """
    if d_a == d_b:
        return 1.0
    max_d = max(d_a, d_b, 1)
    return max(0.0, 1.0 - abs(d_a - d_b) / max_d)


def _cycle_similarity(a: bool, b: bool) -> float:
    """Binary signal: same cycle presence = 1.0, different = 0.0."""
    return 1.0 if a == b else 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def pdg_similarity(feats_a: PDGFeatures, feats_b: PDGFeatures) -> float:
    """
    Compute structural PDG similarity between two submissions.

    Args:
        feats_a: PDGFeatures extracted from submission A.
        feats_b: PDGFeatures extracted from submission B.

    Returns:
        float in [0.0, 1.0].
        Returns 0.0 if either submission failed to parse.
        Returns 0.0 if both submissions have zero statement nodes
        (empty files or files that could not be walked).
    """
    # Graceful degradation: if either side failed to parse, contribute 0.0
    # so the PDG modifier doesn't push a borderline pair into false-positive
    # territory based on a parsing artifact.
    if not feats_a.parse_ok or not feats_b.parse_ok:
        return 0.0

    if feats_a.n_nodes == 0 and feats_b.n_nodes == 0:
        return 1.0  # both empty — trivially equivalent
    if feats_a.n_nodes == 0 or feats_b.n_nodes == 0:
        return 0.0

    # ── 1. Node type distribution (0.35) ──
    type_sim = _cosine(feats_a.node_type_counts, feats_b.node_type_counts)

    # ── 2. Data-flow fan-out degree sequence (0.25) ──
    data_deg_sim = _degree_seq_similarity(
        feats_a.data_out_degrees, feats_b.data_out_degrees
    )

    # ── 3. Data-to-control edge ratio (0.20) ──
    ratio_sim = _ratio_similarity(
        feats_a.data_to_ctrl_ratio, feats_b.data_to_ctrl_ratio
    )

    # ── 4. Control nesting depth (0.10) ──
    depth_sim = _depth_similarity(feats_a.max_ctrl_depth, feats_b.max_ctrl_depth)

    # ── 5. Cycle presence (0.10) ──
    cycle_sim = _cycle_similarity(feats_a.has_cycles, feats_b.has_cycles)

    score = (
        0.35 * type_sim
        + 0.25 * data_deg_sim
        + 0.20 * ratio_sim
        + 0.10 * depth_sim
        + 0.10 * cycle_sim
    )

    return round(min(score, 1.0), 6)


def pdg_similarity_from_source(source_a: str, source_b: str, lang: str) -> float:
    """
    Convenience wrapper: build features for both sources and return similarity.
    Used in tests and from api.py when source strings are already available.
    """
    from engine.pdg.build import build_pdg_features
    feats_a = build_pdg_features(source_a, lang)
    feats_b = build_pdg_features(source_b, lang)
    return pdg_similarity(feats_a, feats_b)
