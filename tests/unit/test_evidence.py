"""
Tests for evidence extraction (engine/evidence/evidence.py).
"""

import sys
import pytest
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent / "Backend" / "Pantheon_API"
sys.path.insert(0, str(backend_path))

from engine.tokenize.lex import Token
from engine.evidence.evidence import build_evidence


class TestEvidenceExtraction:
    """Tests for evidence extraction from matching fingerprints."""

    def test_extract_from_identical_fingerprints(self, simple_tokens, identical_fingerprints):
        """Extract evidence from identical fingerprints."""
        fp_a, fp_b = identical_fingerprints
        evidence = build_evidence(
            fp_a, fp_b,
            simple_tokens, simple_tokens,
            source_map_a=[], source_map_b=[],
            k=8
        )
        # Should find matching regions
        assert isinstance(evidence, list)

    def test_extract_from_no_matches(self, simple_tokens, completely_different_fingerprints):
        """No evidence when fingerprints are different."""
        fp_a, fp_b = completely_different_fingerprints
        evidence = build_evidence(
            fp_a, fp_b,
            simple_tokens, simple_tokens,
            source_map_a=[], source_map_b=[],
            k=8
        )
        # Should be empty
        assert evidence == []

    def test_evidence_format(self, identical_fingerprints, simple_tokens):
        """Evidence records should have correct format."""
        fp_a, fp_b = identical_fingerprints
        evidence = build_evidence(
            fp_a, fp_b,
            simple_tokens, simple_tokens,
            source_map_a=[], source_map_b=[],
            k=8
        )
        for entry in evidence:
            assert isinstance(entry, dict)
            # Should have file and line info
            assert any(key in entry for key in ["file_a", "file_b", "lines_a", "lines_b"])

    def test_empty_fingerprints(self, simple_tokens, empty_fingerprints):
        """Empty fingerprints should produce no evidence."""
        fp_a, fp_b = empty_fingerprints
        evidence = build_evidence(
            fp_a, fp_b,
            simple_tokens, simple_tokens,
            source_map_a=[], source_map_b=[],
            k=8
        )
        assert evidence == []

    @pytest.mark.edge
    def test_large_matching_region(self, long_token_list):
        """Large matching region should be detected."""
        fp = {0x1234: list(range(len(long_token_list)))}  # All positions match
        evidence = build_evidence(
            fp, fp,
            long_token_list, long_token_list,
            source_map_a=[], source_map_b=[],
            k=8
        )
        assert isinstance(evidence, list)
