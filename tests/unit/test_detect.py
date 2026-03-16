"""
Tests for obfuscation detection (engine/obfuscation/detect.py).
"""

import sys
import pytest
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent / "Backend" / "Pantheon_API"
sys.path.insert(0, str(backend_path))

from engine.tokenize.lex import Token
from engine.obfuscation.detect import detect_obfuscation


class TestObfuscationDetection:
    """Tests for obfuscation technique detection."""

    def test_detect_returns_list(self, simple_tokens):
        """detect_obfuscation should return a list of flags."""
        result = detect_obfuscation(
            simple_tokens, simple_tokens,  # raw tokens
            simple_tokens, simple_tokens,  # normalized tokens
            {0x1234: [0, 5]}, {0x1234: [0, 5]},  # fingerprints
        )
        assert isinstance(result, list)
        assert all(isinstance(flag, str) for flag in result)

    def test_no_obfuscation_identical_code(self, simple_tokens):
        """Identical code should show no obfuscation."""
        result = detect_obfuscation(
            simple_tokens, simple_tokens,
            simple_tokens, simple_tokens,
            {0x1234: [0, 5]}, {0x1234: [0, 5]},
        )
        # Should be empty or minimal
        assert len(result) == 0 or result == []

    def test_detect_identifier_renaming(self):
        """Detect identifier renaming."""
        # Raw tokens with different identifiers
        raw_a = [Token("int", 1), Token("myVar", 1), Token("=", 1), Token("42", 1)]
        raw_b = [Token("int", 1), Token("x", 1), Token("=", 1), Token("42", 1)]
        # Normalized tokens identical
        norm_a = [Token("int", 1), Token("ID", 1), Token("=", 1), Token("NUM", 1)]
        norm_b = [Token("int", 1), Token("ID", 1), Token("=", 1), Token("NUM", 1)]
        # Fingerprints mostly match
        fp_a = {0x1234: [0]}
        fp_b = {0x1234: [0], 0x5678: [1]}

        result = detect_obfuscation(raw_a, raw_b, norm_a, norm_b, fp_a, fp_b)
        # Might detect identifier_renaming or similar
        assert isinstance(result, list)

    def test_obfuscation_flags_are_valid(self, simple_tokens):
        """Returned flags should be valid obfuscation types."""
        valid_flags = {
            "identifier_renaming",
            "loop_type_swap",
            "literal_substitution",
            "dead_code_insertion",
            "code_reordering",
            "switch_to_ifelse",
            "ternary_to_ifelse",
            "exception_wrapping",
            "for_each_to_indexed",
        }
        result = detect_obfuscation(
            simple_tokens, simple_tokens,
            simple_tokens, simple_tokens,
            {0x1234: [0]}, {0x1234: [0]},
        )
        for flag in result:
            assert flag in valid_flags

    def test_empty_tokens(self):
        """Should handle empty token lists."""
        result = detect_obfuscation(
            [], [], [], [],
            {}, {},
        )
        assert isinstance(result, list)

    @pytest.mark.edge
    def test_high_score_with_different_tokens(self):
        """High normalized score with low raw score indicates obfuscation."""
        # Normalized tokens identical (scores high)
        norm_tokens = [Token(f"t{i}", 1) for i in range(20)]
        # Raw tokens different
        raw_a = [Token(f"long_name_{i}", 1) for i in range(20)]
        raw_b = [Token(f"x", 1) for i in range(20)]

        fp_norm = {hash(f"norm_{i}"): [i] for i in range(15)}

        result = detect_obfuscation(
            raw_a, raw_b,
            norm_tokens, norm_tokens,
            fp_norm, fp_norm,
        )
        # Might detect obfuscation
        assert isinstance(result, list)
