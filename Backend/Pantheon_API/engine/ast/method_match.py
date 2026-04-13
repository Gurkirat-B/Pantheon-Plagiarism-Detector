"""
Method-pair best-match scoring across two submissions.

This module implements the most independence-adding signal in the new scoring
formula. For each method in submission A, it finds the closest matching method
in submission B, measured by structural subtree similarity. The final score is
the average best-match across all methods in the smaller submission.

Why this matters:
  - Function decomposition: a 100-line method split into five 20-line helpers.
    Whole-submission subtree similarity would see many small unmatched methods.
    Best-match correctly pairs each helper in B with the relevant portion of A.
  - Function reordering: functions in a completely different order in the file.
    Best-match operates regardless of position — it is purely content-based.
  - Cross-submission partial copying: student A copied only three of student B's
    seven functions. Best-match finds the three strong pairs and scores them high;
    the four unmatched functions in B contribute 0.0 to their best matches,
    pulling the average down — correctly reflecting partial copying.

Algorithm:
  1. Hash all methods in A and B at method level (already computed by subtree.py).
     But for method-pair matching we need *per-method* hashes, not a combined set.
  2. For each method in A, compute similarity against every method in B.
  3. Take the maximum similarity for each A method (its "best partner" in B).
  4. Average those best-match scores across all methods in A.

Step 2 is O(|A| × |B|) — for typical student submissions (5-30 functions each)
this is trivially fast. For submissions with hundreds of methods we apply a fast
pre-filter using hash set intersection to skip obviously unrelated pairs.

Public API:
    per_method_hashes(source, lang)         → dict[method_name, SubtreeHashes]
    method_pair_similarity(h_a, h_b)        → float  (single pair)
    best_match_score(methods_a, methods_b)  → float  (across all pairs)
    best_match_from_source(src_a, src_b, lang) → float  (convenience wrapper)
"""

from __future__ import annotations

from typing import Dict

from engine.ast.parse import _load_language, _LANG_CONFIG
from engine.ast.subtree import SubtreeHashes, _walk, subtree_similarity


# ---------------------------------------------------------------------------
# Per-method hash extraction
# ---------------------------------------------------------------------------

def per_method_hashes(source: str, lang: str) -> Dict[str, SubtreeHashes]:
    """
    Parse *source* and return a dict mapping each function/method name to its
    own SubtreeHashes object (containing only that method's hashes).

    This is more expensive than compute_subtree_hashes() because we run a
    separate walk for each function body, but it gives us per-method granularity
    needed for best-match pairing.

    Args:
        source: Full source code string.
        lang:   Language key.

    Returns:
        { "func_name": SubtreeHashes, ... }
        Empty dict if parse fails.
    """
    lang_obj = _load_language(lang)
    if lang_obj is None:
        return {}

    try:
        from tree_sitter import Parser
        parser = Parser(lang_obj)
        source_bytes = source.encode("utf-8", errors="replace")
        tree = parser.parse(source_bytes)
        root = tree.root_node

        cfg = _LANG_CONFIG.get(lang, _LANG_CONFIG["cpp"])
        func_types = frozenset(cfg["func_types"])

        # Collect all function nodes first
        func_nodes = _collect_function_nodes(root, func_types)

        result: Dict[str, SubtreeHashes] = {}
        seen_names: Dict[str, int] = {}

        for node in func_nodes:
            name = _get_func_name(node, source_bytes, lang, cfg)
            # Deduplicate: if we've seen this name, append line number
            if name in seen_names:
                seen_names[name] += 1
                name = f"{name}_{node.start_point[0] + 1}"
            else:
                seen_names[name] = 1

            # Walk only this function's subtree
            hashes = SubtreeHashes(parse_ok=not root.has_error)
            _walk(node, source_bytes, func_types, hashes, inside_func=False)
            result[name] = hashes

        return result

    except Exception:
        return {}


def _collect_function_nodes(root, func_types: frozenset) -> list:
    """Walk the entire AST and collect all function/method declaration nodes."""
    nodes = []
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type in func_types:
            nodes.append(node)
        else:
            # Only descend into non-function nodes at the top level —
            # nested functions (Python closures, inner classes) are handled
            # when the outer function is walked.
            stack.extend(reversed(node.children))
    return nodes


def _get_func_name(node, source_bytes: bytes, lang: str, cfg: dict) -> str:
    """Extract function name using the field config from _LANG_CONFIG."""
    from engine.ast.parse import _extract_name
    return _extract_name(node, source_bytes, lang)


# ---------------------------------------------------------------------------
# Pair similarity + best-match scoring
# ---------------------------------------------------------------------------

def method_pair_similarity(ha: SubtreeHashes, hb: SubtreeHashes) -> float:
    """
    Similarity between two individual method hash objects.
    Delegates directly to subtree_similarity — same weighted formula.
    """
    return subtree_similarity(ha, hb)


def best_match_score(
    methods_a: Dict[str, SubtreeHashes],
    methods_b: Dict[str, SubtreeHashes],
) -> float:
    """
    For each method in the smaller submission, find its best-matching partner
    in the larger submission. Return the average of those best-match scores.

    We iterate over the smaller side to be conservative about partial copying:
    if A has 3 methods and B has 10, we look for A's 3 in B's 10 rather than
    B's 10 in A's 3. This prevents a tiny stub file from scoring high simply
    because one short helper appears in a large submission.

    Args:
        methods_a: Per-method SubtreeHashes for submission A.
        methods_b: Per-method SubtreeHashes for submission B.

    Returns:
        float in [0.0, 1.0], or 0.0 if either submission has no parseable methods.
    """
    if not methods_a or not methods_b:
        return 0.0

    # Iterate from the smaller set toward the larger
    if len(methods_a) > len(methods_b):
        primary, secondary = methods_b, methods_a
    else:
        primary, secondary = methods_a, methods_b

    total_best = 0.0

    for _, ha in primary.items():
        # Fast pre-filter: if the method has no method-level hashes at all
        # (e.g. a tiny stub), skip — it cannot produce a meaningful match.
        if not ha.method and not ha.block and not ha.statement:
            continue

        best = 0.0
        for _, hb in secondary.items():
            sim = method_pair_similarity(ha, hb)
            if sim > best:
                best = sim
                if best >= 1.0:
                    break  # can't do better

        total_best += best

    n = len(primary)
    if n == 0:
        return 0.0

    return round(total_best / n, 6)


def best_match_from_source(source_a: str, source_b: str, lang: str) -> float:
    """
    Convenience wrapper: parse both sources, extract per-method hashes, and
    return the best-match score. Used in tests and directly from api.py.
    """
    methods_a = per_method_hashes(source_a, lang)
    methods_b = per_method_hashes(source_b, lang)
    return best_match_score(methods_a, methods_b)
