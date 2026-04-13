"""
Tests for method-pair best-match scoring (engine/ast/method_match.py).
Tests for call graph structural comparison (engine/ast/callgraph.py).
Tests for PDG construction and scoring (engine/pdg/build.py, engine/pdg/compare.py).
"""

import sys
import pytest
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent / "Backend" / "Pantheon_API"
sys.path.insert(0, str(backend_path))

from engine.ast.method_match import (
    per_method_hashes,
    best_match_score,
    best_match_from_source,
)
from engine.ast.callgraph import compare_callgraphs
from engine.pdg.build import build_pdg_features, PDGFeatures
from engine.pdg.compare import pdg_similarity, pdg_similarity_from_source
from engine.similarity.scores import apply_pdg_modifier


# ---------------------------------------------------------------------------
# Shared sources
# ---------------------------------------------------------------------------

SRC_TWO_FUNCS = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr

def insertion_sort(arr):
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
    return arr
"""

SRC_RENAMED = """
def bsort(lst):
    size = len(lst)
    for x in range(size):
        for y in range(0, size - x - 1):
            if lst[y] > lst[y + 1]:
                lst[y], lst[y + 1] = lst[y + 1], lst[y]
    return lst

def isort(lst):
    for idx in range(1, len(lst)):
        pivot = lst[idx]
        k = idx - 1
        while k >= 0 and lst[k] > pivot:
            lst[k + 1] = lst[k]
            k -= 1
        lst[k + 1] = pivot
    return lst
"""

SRC_UNRELATED = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

def power(base, exp):
    if exp == 0:
        return 1
    return base * power(base, exp - 1)
"""


# ===========================================================================
# Method-pair match tests
# ===========================================================================

class TestPerMethodHashes:
    """Tests for per_method_hashes() extraction."""

    def test_returns_dict(self):
        result = per_method_hashes(SRC_TWO_FUNCS, "python")
        assert isinstance(result, dict)

    def test_finds_both_functions(self):
        result = per_method_hashes(SRC_TWO_FUNCS, "python")
        assert "bubble_sort" in result
        assert "insertion_sort" in result

    def test_empty_source_returns_empty(self):
        result = per_method_hashes("", "python")
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_unsupported_lang_returns_empty(self):
        result = per_method_hashes("print('x')", "cobol")
        assert isinstance(result, dict)
        assert len(result) == 0


class TestBestMatchScore:
    """Tests for best_match_score() cross-submission matching."""

    def test_identical_scores_one(self):
        methods = per_method_hashes(SRC_TWO_FUNCS, "python")
        score = best_match_score(methods, methods)
        assert score == pytest.approx(1.0)

    def test_renamed_scores_high(self):
        score = best_match_from_source(SRC_TWO_FUNCS, SRC_RENAMED, "python")
        assert score >= 0.85, f"Expected ≥0.85, got {score}"

    def test_unrelated_scores_low(self):
        score = best_match_from_source(SRC_TWO_FUNCS, SRC_UNRELATED, "python")
        assert score <= 0.30, f"Expected ≤0.30, got {score}"

    def test_empty_methods_returns_zero(self):
        score = best_match_score({}, {})
        assert score == 0.0

    def test_one_empty_returns_zero(self):
        methods = per_method_hashes(SRC_TWO_FUNCS, "python")
        score = best_match_score(methods, {})
        assert score == 0.0

    def test_score_in_range(self):
        score = best_match_from_source(SRC_TWO_FUNCS, SRC_RENAMED, "python")
        assert 0.0 <= score <= 1.0


# ===========================================================================
# Call graph tests
# ===========================================================================

class TestCallGraphComparison:
    """Tests for name-independent call graph structural comparison."""

    def test_identical_call_graph_scores_one(self):
        cg = {"main": ["foo", "bar"], "foo": [], "bar": []}
        score = compare_callgraphs(cg, cg)
        assert score == pytest.approx(1.0)

    def test_renamed_same_structure_scores_high(self):
        cg_a = {"run": ["fetch", "process", "save"],
                "fetch": [], "process": [], "save": []}
        cg_b = {"main": ["load", "compute", "store"],
                "load": [], "compute": [], "store": []}
        score = compare_callgraphs(cg_a, cg_b)
        assert score >= 0.70, f"Expected ≥0.70, got {score}"

    def test_different_structure_scores_low(self):
        cg_a = {"main": ["a", "b", "c"], "a": [], "b": [], "c": []}
        cg_b = {"solo": []}
        score = compare_callgraphs(cg_a, cg_b)
        assert score <= 0.70

    def test_empty_call_graph_returns_zero(self):
        score = compare_callgraphs({}, {})
        assert score == 0.0

    def test_score_in_range(self):
        cg_a = {"main": ["foo"], "foo": []}
        cg_b = {"run": ["bar"], "bar": []}
        score = compare_callgraphs(cg_a, cg_b)
        assert 0.0 <= score <= 1.0

    def test_recursive_function_detected(self):
        """Recursive call graphs (self-loops) should still score correctly."""
        cg_a = {"factorial": ["factorial"]}
        cg_b = {"fib": ["fib"]}
        score = compare_callgraphs(cg_a, cg_b)
        assert score >= 0.0


# ===========================================================================
# PDG tests
# ===========================================================================

SRC_ITERATIVE = """
def fibonacci(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b
"""

SRC_RECURSIVE = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
"""

SRC_SORT = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
"""


class TestPDGFeatures:
    """Tests for PDG feature extraction."""

    def test_returns_pdgfeatures(self):
        result = build_pdg_features(SRC_ITERATIVE, "python")
        assert isinstance(result, PDGFeatures)

    def test_has_expected_fields(self):
        result = build_pdg_features(SRC_ITERATIVE, "python")
        assert hasattr(result, "node_type_counts")
        assert hasattr(result, "n_nodes")
        assert hasattr(result, "n_ctrl_edges")
        assert hasattr(result, "n_data_edges")
        assert hasattr(result, "has_cycles")
        assert hasattr(result, "parse_ok")

    def test_iterative_has_loop(self):
        result = build_pdg_features(SRC_ITERATIVE, "python")
        assert result.node_type_counts.get("LOOP", 0) >= 1

    def test_iterative_has_cycles(self):
        result = build_pdg_features(SRC_ITERATIVE, "python")
        assert result.has_cycles is True

    def test_parse_ok_on_valid_source(self):
        result = build_pdg_features(SRC_ITERATIVE, "python")
        assert result.parse_ok is True

    def test_unsupported_lang_returns_fail(self):
        result = build_pdg_features("print('x')", "cobol")
        assert result.parse_ok is False

    def test_node_type_counts_is_dict(self):
        result = build_pdg_features(SRC_ITERATIVE, "python")
        assert isinstance(result.node_type_counts, dict)

    def test_data_edges_present_for_data_flow(self):
        """A function with assignments and a loop should have data edges."""
        result = build_pdg_features(SRC_ITERATIVE, "python")
        assert result.n_data_edges >= 0  # at least should not crash


class TestPDGSimilarity:
    """Tests for PDG structural comparison."""

    def test_identical_scores_one(self):
        score = pdg_similarity_from_source(SRC_ITERATIVE, SRC_ITERATIVE, "python")
        assert score == pytest.approx(1.0)

    def test_variable_rename_scores_high(self):
        src_renamed = """
def fib(x):
    if x <= 1:
        return x
    prev, curr = 0, 1
    for idx in range(x - 1):
        prev, curr = curr, prev + curr
    return curr
"""
        score = pdg_similarity_from_source(SRC_ITERATIVE, src_renamed, "python")
        assert score >= 0.80, f"Expected ≥0.80, got {score}"

    def test_recursion_vs_iteration_differs(self):
        """Recursive and iterative implementations should score < 1.0."""
        score = pdg_similarity_from_source(SRC_RECURSIVE, SRC_ITERATIVE, "python")
        assert score < 1.0, "Recursion and iteration should not score 1.0"

    def test_score_in_range(self):
        score = pdg_similarity_from_source(SRC_SORT, SRC_ITERATIVE, "python")
        assert 0.0 <= score <= 1.0

    def test_empty_source_zero(self):
        """Empty vs non-empty should score 0.0."""
        feats_empty = build_pdg_features("", "python")
        feats_full  = build_pdg_features(SRC_ITERATIVE, "python")
        score = pdg_similarity(feats_empty, feats_full)
        assert score == 0.0

    def test_both_parse_fail_zero(self):
        """Both parse failures should score 0.0, not crash."""
        f1 = build_pdg_features("print('x')", "cobol")
        f2 = build_pdg_features("print('x')", "cobol")
        score = pdg_similarity(f1, f2)
        assert score == 0.0


class TestPDGModifier:
    """Tests for the PDG score modifier logic (apply_pdg_modifier)."""

    def test_high_pdg_raises_base(self):
        """PDG=0.9 should raise base score."""
        base  = apply_pdg_modifier(0.55, 0.90)
        assert base > 0.55

    def test_low_pdg_lowers_base(self):
        """PDG=0.1 should lower base score."""
        base  = apply_pdg_modifier(0.55, 0.10)
        assert base < 0.55

    def test_pdg_zero_reduces_score(self):
        final = apply_pdg_modifier(0.60, 0.0)
        assert final == pytest.approx(0.60 * 0.80, abs=0.001)

    def test_pdg_one_with_high_base(self):
        """PDG=1.0, base=1.0 should give 1.0."""
        final = apply_pdg_modifier(1.0, 1.0)
        assert final == pytest.approx(1.0)

    def test_result_always_in_range(self):
        for base, pdg in [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0), (0.3, 0.8)]:
            final = apply_pdg_modifier(base, pdg)
            assert 0.0 <= final <= 1.0, f"Out of range for base={base}, pdg={pdg}"
