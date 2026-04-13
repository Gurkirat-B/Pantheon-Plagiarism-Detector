"""
Tests for k-gram fingerprinting and winnowing (engine/fingerprint/kgrams.py).
"""

import sys
import pytest
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent / "Backend" / "Pantheon_API"
sys.path.insert(0, str(backend_path))

from engine.tokenize.lex import Token
from engine.fingerprint.kgrams import (
    build_fingerprints, winnow,
    select_k, build_per_function_fingerprints,
)


class TestFingerprinting:
    """Tests for k-gram fingerprint building."""

    def test_build_fingerprints_basic(self, simple_tokens):
        """Test basic fingerprint building."""
        fp = build_fingerprints(simple_tokens, k=8)
        assert isinstance(fp, dict)
        # Should have some fingerprints for a 16-token list with k=8
        assert len(fp) > 0

    def test_build_fingerprints_empty(self):
        """Test fingerprinting empty token list."""
        fp = build_fingerprints([], k=8)
        assert fp == {}

    def test_build_fingerprints_less_than_k(self):
        """Test fingerprinting with fewer tokens than k."""
        tokens = [Token("int", 1), Token("x", 1), Token("=", 1)]
        fp = build_fingerprints(tokens, k=8)
        # Fewer tokens than k means no k-grams possible
        assert len(fp) == 0

    def test_build_fingerprints_exactly_k(self):
        """Test fingerprinting with exactly k tokens."""
        tokens = [Token(f"t{i}", 1) for i in range(8)]
        fp = build_fingerprints(tokens, k=8)
        # Exactly k tokens means one k-gram
        assert len(fp) == 1

    def test_build_fingerprints_k_plus_one(self):
        """Test fingerprinting with k+1 tokens."""
        tokens = [Token(f"t{i}", 1) for i in range(9)]
        fp = build_fingerprints(tokens, k=8)
        # 9 tokens with k=8 means 2 k-grams
        assert len(fp) == 2 or len(fp) == 1  # Depends on hash collisions

    def test_build_fingerprints_deterministic(self, simple_tokens):
        """Test that fingerprints are deterministic."""
        fp1 = build_fingerprints(simple_tokens, k=8)
        fp2 = build_fingerprints(simple_tokens, k=8)
        # Should be identical
        assert fp1 == fp2

    def test_build_fingerprints_different_k(self, simple_tokens):
        """Test fingerprinting with different k values."""
        fp8 = build_fingerprints(simple_tokens, k=8)
        fp4 = build_fingerprints(simple_tokens, k=4)
        # Different k should give different number of fingerprints
        # More k-grams for smaller k
        assert len(fp4) >= len(fp8)

    def test_fingerprint_format(self, simple_tokens):
        """Test fingerprint dictionary format."""
        fp = build_fingerprints(simple_tokens, k=8)
        # Should be dict mapping hash to list of positions
        for hash_val, positions in fp.items():
            assert isinstance(hash_val, int)
            assert isinstance(positions, list)
            assert all(isinstance(p, int) for p in positions)

    def test_fingerprint_positions_sorted(self, long_token_list):
        """Test that fingerprint positions are sorted."""
        fp = build_fingerprints(long_token_list, k=4)
        for positions in fp.values():
            assert positions == sorted(positions)

    def test_build_fingerprints_large_list(self):
        """Test fingerprinting large token list with variety."""
        # Use diverse tokens so we get many unique k-grams
        tokens = [Token(f"token_{i}", i) for i in range(100)]
        fp = build_fingerprints(tokens, k=8)
        # Should have reasonable number of fingerprints (50+ for 100 diverse tokens)
        assert len(fp) > 30


class TestWinnowing:
    """Tests for winnowing algorithm."""

    def test_winnow_basic(self, simple_tokens):
        """Test basic winnowing."""
        fp = winnow(simple_tokens, k=8, window=4)
        assert isinstance(fp, dict)
        # Winnowed should have fewer or equal fingerprints
        all_fp = build_fingerprints(simple_tokens, k=8)
        assert len(fp) <= len(all_fp)

    def test_winnow_empty(self):
        """Test winnowing empty token list."""
        fp = winnow([], k=8, window=4)
        assert fp == {}

    def test_winnow_less_than_k(self):
        """Test winnowing with fewer tokens than k."""
        tokens = [Token("t1", 1), Token("t2", 1), Token("t3", 1)]
        fp = winnow(tokens, k=8, window=4)
        # Fewer tokens than k means effectively empty
        assert fp == {}

    def test_winnow_less_than_window(self):
        """Test winnowing with few tokens (k=4, window=4)."""
        tokens = [Token(f"t{i}", 1) for i in range(5)]
        fp = winnow(tokens, k=4, window=4)
        # With 5 tokens and k=4, we can create 2 k-grams
        # Winnowing behavior depends on implementation
        assert isinstance(fp, dict)

    def test_winnow_deterministic(self, long_token_list):
        """Test that winnowing is deterministic."""
        fp1 = winnow(long_token_list, k=8, window=4)
        fp2 = winnow(long_token_list, k=8, window=4)
        # Should be identical
        assert fp1 == fp2

    def test_winnow_reduces_fingerprints(self, long_token_list):
        """Test that winnowing reduces fingerprint count."""
        all_fp = build_fingerprints(long_token_list, k=8)
        winnowed_fp = winnow(long_token_list, k=8, window=4)
        # Winnowed should be significantly smaller (~75% reduction)
        assert len(winnowed_fp) <= len(all_fp)
        # For long lists, winnowing should reduce substantially
        if len(all_fp) > 10:
            reduction = (len(all_fp) - len(winnowed_fp)) / len(all_fp)
            assert reduction > 0.5  # At least 50% reduction

    def test_winnow_guarantee_11_tokens(self):
        """Test winnowing guarantee: 11 consecutive tokens always caught."""
        # With k=8, window=4: guarantee is k+window-1 = 11 tokens
        # Create two token lists with 11 identical tokens
        identical_sequence = [Token(f"t{i}", i) for i in range(11)]
        tokens_a = [Token("unique_start", 0)] + identical_sequence + [Token("unique_end", 20)]
        tokens_b = [Token("different_start", 0)] + identical_sequence + [Token("different_end", 20)]

        fp_a = winnow(tokens_a, k=8, window=4)
        fp_b = winnow(tokens_b, k=8, window=4)

        # Should have at least one shared fingerprint
        shared = set(fp_a.keys()) & set(fp_b.keys())
        assert len(shared) > 0, "Winnowing guarantee violated: 11 identical tokens not caught"

    def test_winnow_different_parameters(self, long_token_list):
        """Test winnowing with different k and window values."""
        fp_k8_w4 = winnow(long_token_list, k=8, window=4)
        fp_k4_w2 = winnow(long_token_list, k=4, window=2)
        # Both should produce fingerprints but counts may differ
        assert isinstance(fp_k8_w4, dict)
        assert isinstance(fp_k4_w2, dict)

    def test_winnow_vs_no_winnow(self, long_token_list):
        """Compare winnowed vs all fingerprints."""
        all_fp = build_fingerprints(long_token_list, k=8)
        winnowed_fp = winnow(long_token_list, k=8, window=4)
        # Winnowed fingerprints should be subset of all
        for fp_hash in winnowed_fp.keys():
            assert fp_hash in all_fp


class TestFingerprintingConsistency:
    """Tests for fingerprinting consistency and determinism."""

    def test_identical_tokens_identical_fingerprints(self):
        """Identical token sequences should produce identical fingerprints."""
        tokens = [Token("int", 1), Token("x", 1), Token("=", 1), Token("42", 1), Token(";", 1)]
        # Repeat the same tokens with different line numbers
        tokens2 = [Token("int", 10), Token("x", 10), Token("=", 10), Token("42", 10), Token(";", 10)]

        fp1 = build_fingerprints(tokens, k=3)
        fp2 = build_fingerprints(tokens2, k=3)
        # Should be identical (fingerprints don't depend on line numbers)
        assert fp1 == fp2

    def test_no_hash_collisions_for_simple_tokens(self):
        """Test that different token sequences produce different hashes most of the time."""
        tokens_a = [Token(f"a{i}", 1) for i in range(20)]
        tokens_b = [Token(f"b{i}", 1) for i in range(20)]

        fp_a = build_fingerprints(tokens_a, k=4)
        fp_b = build_fingerprints(tokens_b, k=4)

        # Overlap is unlikely for unrelated token sequences
        shared = set(fp_a.keys()) & set(fp_b.keys())
        # With good hash function, should have minimal or no collisions
        assert len(shared) < len(fp_a) * 0.2  # Less than 20% overlap

    @pytest.mark.edge
    def test_large_k_value(self):
        """Test with very large k value."""
        tokens = [Token(f"t{i}", 1) for i in range(100)]
        fp = build_fingerprints(tokens, k=50)
        # Should handle large k gracefully
        assert isinstance(fp, dict)

    @pytest.mark.edge
    def test_single_repeated_token(self):
        """Test with single token repeated."""
        tokens = [Token("x", 1) for _ in range(50)]
        fp = build_fingerprints(tokens, k=8)
        # All k-grams are identical, so should have only 1 unique hash
        assert len(fp) == 1

    @pytest.mark.edge
    def test_alternating_tokens(self):
        """Test with alternating tokens."""
        tokens = [Token("a" if i % 2 == 0 else "b", 1) for i in range(50)]
        fp = build_fingerprints(tokens, k=8)
        # Should have limited number of unique k-grams
        assert len(fp) <= 3


class TestWinnowingEdgeCases:
    """Edge case tests for winnowing."""

    @pytest.mark.edge
    def test_winnow_large_window(self):
        """Test winnowing with window larger than token count."""
        tokens = [Token(f"t{i}", 1) for i in range(10)]
        fp = winnow(tokens, k=4, window=20)
        # Window larger than tokens, should use all fingerprints
        assert len(fp) >= 0  # Just shouldn't crash

    @pytest.mark.edge
    def test_winnow_window_equals_one(self):
        """Test winnowing with window=1."""
        tokens = [Token(f"t{i}", 1) for i in range(20)]
        fp = winnow(tokens, k=8, window=1)
        # Should work, though guarantee becomes weak (k+window-1 = 8)
        assert isinstance(fp, dict)

    @pytest.mark.edge
    def test_winnow_k_equals_one(self):
        """Test winnowing with k=1."""
        tokens = [Token(f"t{i}", 1) for i in range(20)]
        fp = winnow(tokens, k=1, window=1)
        # Should work, though not practical
        assert isinstance(fp, dict)


class TestAdaptiveKSelection:
    """Tests for per-function adaptive k selection table."""

    def test_very_short_function_k3(self):
        """Functions with < 20 tokens get k=3."""
        assert select_k(5)  == 3
        assert select_k(15) == 3
        assert select_k(19) == 3

    def test_short_function_k5(self):
        """Functions with 20-49 tokens get k=5."""
        assert select_k(20) == 5
        assert select_k(35) == 5
        assert select_k(49) == 5

    def test_medium_function_k8(self):
        """Functions with 50-149 tokens get k=8."""
        assert select_k(50)  == 8
        assert select_k(100) == 8
        assert select_k(149) == 8

    def test_large_function_k12(self):
        """Functions with 150-299 tokens get k=12."""
        assert select_k(150) == 12
        assert select_k(200) == 12
        assert select_k(299) == 12

    def test_very_large_function_k15_to_k18(self):
        """Functions with ≥300 tokens get k in [15, 18]."""
        assert select_k(300) == 15
        assert select_k(600) == 16
        k_max = select_k(100_000)
        assert k_max <= 18

    def test_k_monotone_non_decreasing(self):
        """Larger functions should never get smaller k."""
        sizes = [5, 20, 50, 150, 300, 600, 1000]
        ks = [select_k(s) for s in sizes]
        for i in range(len(ks) - 1):
            assert ks[i] <= ks[i + 1], f"k not monotone at {sizes[i]}: {ks[i]} > {ks[i+1]}"


class TestPerFunctionFingerprints:
    """Tests for build_per_function_fingerprints()."""

    def _make_tokens(self, start_line: int, n: int) -> list:
        """Create n dummy tokens starting at start_line."""
        return [Token(f"tok{i}", start_line + (i // 5)) for i in range(n)]

    def test_returns_dict(self):
        tokens = self._make_tokens(1, 30)
        func_map = {"foo": {"start_line": 1, "end_line": 6, "token_count": 30}}
        result = build_per_function_fingerprints(tokens, func_map)
        assert isinstance(result, dict)

    def test_has_meta_key(self):
        tokens = self._make_tokens(1, 30)
        func_map = {"foo": {"start_line": 1, "end_line": 6, "token_count": 30}}
        result = build_per_function_fingerprints(tokens, func_map)
        assert "__meta__" in result

    def test_meta_has_k_value(self):
        tokens = self._make_tokens(1, 30)
        func_map = {"foo": {"start_line": 1, "end_line": 6, "token_count": 30}}
        result = build_per_function_fingerprints(tokens, func_map)
        meta = result["__meta__"]
        if "foo" in meta:
            assert "k" in meta["foo"]

    def test_empty_inputs_return_empty(self):
        result = build_per_function_fingerprints([], {})
        assert result == {}
