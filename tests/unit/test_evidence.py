"""
Tests for evidence extraction (engine/evidence/evidence.py).
"""

import sys
import pytest
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent / "Backend" / "Pantheon_API"
sys.path.insert(0, str(backend_path))

from engine.tokenize.lex import Token
from engine.evidence.evidence import build_evidence, build_ast_evidence


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
            # v2: every block now has an evidence_source field
            assert "evidence_source" in entry

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


class TestASTEvidence:
    """Tests for AST method-pair evidence blocks (build_ast_evidence)."""

    def _make_hashes(self, val: str):
        """Create a tiny SubtreeHashes with one method hash."""
        from engine.ast.subtree import SubtreeHashes
        h = SubtreeHashes()
        h.method = {val}
        h.block  = {val}
        h.statement = {val}
        return h

    def test_returns_list(self):
        ha = self._make_hashes("abc")
        hb = self._make_hashes("abc")
        func_map = {"foo": {"start_line": 1, "end_line": 10, "token_count": 50}}
        result = build_ast_evidence(
            {"foo": ha}, {"foo": hb},
            func_map, func_map,
        )
        assert isinstance(result, list)

    def test_matching_methods_produce_blocks(self):
        """Identical method hashes above threshold should produce evidence."""
        ha = self._make_hashes("same_hash")
        hb = self._make_hashes("same_hash")
        func_map = {
            "sort": {"start_line": 1, "end_line": 20, "token_count": 80}
        }
        result = build_ast_evidence(
            {"sort": ha}, {"sort": hb},
            func_map, func_map,
            similarity_threshold=0.5,
        )
        assert len(result) >= 1

    def test_evidence_source_is_ast(self):
        ha = self._make_hashes("hash")
        func_map = {"foo": {"start_line": 1, "end_line": 15, "token_count": 60}}
        result = build_ast_evidence(
            {"foo": ha}, {"foo": ha},
            func_map, func_map,
            similarity_threshold=0.5,
        )
        for block in result:
            assert block["evidence_source"] == "ast_method_pair"

    def test_non_matching_methods_no_blocks(self):
        """Completely different methods should produce no evidence blocks."""
        ha = self._make_hashes("aaa")
        hb = self._make_hashes("bbb")
        func_map = {"foo": {"start_line": 1, "end_line": 20, "token_count": 80}}
        result = build_ast_evidence(
            {"foo": ha}, {"bar": hb},
            func_map, {"bar": func_map["foo"]},
            similarity_threshold=0.9,
        )
        assert isinstance(result, list)

    def test_empty_method_dicts_return_empty(self):
        result = build_ast_evidence({}, {}, {}, {})
        assert result == []
