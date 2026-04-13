"""
Tests for AST subtree hashing and similarity (engine/ast/subtree.py) — Phase 2B.

The key property we test is *invariance*: structural hashes must be identical
under variable renaming, method name changes, and loop type swaps.
"""

import sys
import pytest
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent / "Backend" / "Pantheon_API"
sys.path.insert(0, str(backend_path))

from engine.ast.subtree import (
    compute_subtree_hashes,
    subtree_similarity,
    subtree_similarity_from_source,
    SubtreeHashes,
)


SORT_ORIGINAL = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
"""

SORT_RENAMED = """
def bsort(lst):
    size = len(lst)
    for x in range(size):
        for y in range(0, size - x - 1):
            if lst[y] > lst[y + 1]:
                lst[y], lst[y + 1] = lst[y + 1], lst[y]
    return lst
"""

SORT_WHILE = """
def sort_while(lst):
    size = len(lst)
    i = 0
    while i < size:
        j = 0
        while j < size - i - 1:
            if lst[j] > lst[j + 1]:
                lst[j], lst[j + 1] = lst[j + 1], lst[j]
            j += 1
        i += 1
    return lst
"""

UNRELATED = """
def fibonacci(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b
"""


class TestSubtreeHashesStruct:
    """Tests for the SubtreeHashes data structure returned by compute_subtree_hashes."""

    def test_returns_subhashstruct(self):
        result = compute_subtree_hashes(SORT_ORIGINAL, "python")
        assert isinstance(result, SubtreeHashes)

    def test_has_three_hash_sets(self):
        result = compute_subtree_hashes(SORT_ORIGINAL, "python")
        assert isinstance(result.statement, set)
        assert isinstance(result.block,     set)
        assert isinstance(result.method,    set)

    def test_non_empty_for_valid_source(self):
        result = compute_subtree_hashes(SORT_ORIGINAL, "python")
        # At least one level should have hashes
        assert len(result.statement) > 0 or len(result.block) > 0 or len(result.method) > 0

    def test_method_level_has_one_hash(self):
        result = compute_subtree_hashes(SORT_ORIGINAL, "python")
        assert len(result.method) == 1

    def test_hash_values_are_strings(self):
        result = compute_subtree_hashes(SORT_ORIGINAL, "python")
        for h in result.method:
            assert isinstance(h, str)


class TestHashInvariances:
    """Core invariance tests — the most important correctness properties."""

    def test_identical_source_same_hashes(self):
        """Exact copy should produce exactly equal hash sets at all levels."""
        h1 = compute_subtree_hashes(SORT_ORIGINAL, "python")
        h2 = compute_subtree_hashes(SORT_ORIGINAL, "python")
        assert h1.method    == h2.method
        assert h1.block     == h2.block
        assert h1.statement == h2.statement

    def test_variable_rename_same_method_hash(self):
        """Variable renaming must not change method-level hashes."""
        h_orig    = compute_subtree_hashes(SORT_ORIGINAL, "python")
        h_renamed = compute_subtree_hashes(SORT_RENAMED,  "python")
        # Method hashes should be equal (both implement the same algorithm)
        assert h_orig.method == h_renamed.method

    def test_method_name_change_same_hash(self):
        """Renaming the method itself must not change its body hash."""
        src_a = "def foo(x):\n    return x + 1\n"
        src_b = "def completely_different_name(x):\n    return x + 1\n"
        h_a = compute_subtree_hashes(src_a, "python")
        h_b = compute_subtree_hashes(src_b, "python")
        assert h_a.method == h_b.method

    def test_unrelated_code_different_hashes(self):
        """Different algorithms must produce different hash sets."""
        h_sort = compute_subtree_hashes(SORT_ORIGINAL, "python")
        h_fib  = compute_subtree_hashes(UNRELATED,     "python")
        # Method hashes should differ
        assert h_sort.method != h_fib.method


class TestSubtreeSimilarityScores:
    """Tests for the similarity scoring function."""

    def test_identical_scores_one(self):
        h = compute_subtree_hashes(SORT_ORIGINAL, "python")
        score = subtree_similarity(h, h)
        assert score == pytest.approx(1.0)

    def test_variable_rename_scores_high(self):
        score = subtree_similarity_from_source(SORT_ORIGINAL, SORT_RENAMED, "python")
        assert score >= 0.85, f"Expected ≥0.85, got {score}"

    def test_different_algo_scores_low(self):
        score = subtree_similarity_from_source(SORT_ORIGINAL, UNRELATED, "python")
        assert score <= 0.25, f"Expected ≤0.25, got {score}"

    def test_loop_swap_non_zero(self):
        """Loop type swap should still retain some similarity (block bodies match)."""
        score = subtree_similarity_from_source(SORT_ORIGINAL, SORT_WHILE, "python")
        assert score > 0.0, "Loop swap should produce non-zero similarity"

    def test_similarity_range(self):
        """Score must always be in [0, 1]."""
        score = subtree_similarity_from_source(SORT_ORIGINAL, UNRELATED, "python")
        assert 0.0 <= score <= 1.0

    def test_empty_source_graceful(self):
        result = compute_subtree_hashes("", "python")
        assert isinstance(result, SubtreeHashes)

    @pytest.mark.edge
    def test_unsupported_language_returns_parse_fail(self):
        result = compute_subtree_hashes("print('x')", "cobol")
        assert result.parse_ok is False
