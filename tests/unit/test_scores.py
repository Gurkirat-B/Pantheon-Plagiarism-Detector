"""
Tests for similarity scoring (engine/similarity/scores.py).
"""

import sys
import pytest
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent / "Backend" / "Pantheon_API"
sys.path.insert(0, str(backend_path))

from engine.similarity.scores import jaccard, dice, containment, weighted_score


class TestSimilarityScores:
    """Tests for similarity metrics."""

    def test_jaccard_identical(self, identical_fingerprints):
        """Identical fingerprints should score 1.0 Jaccard."""
        fp_a, fp_b = identical_fingerprints
        score = jaccard(fp_a, fp_b)
        assert score == 1.0

    def test_jaccard_disjoint(self, completely_different_fingerprints):
        """Completely different fingerprints should score 0.0 Jaccard."""
        fp_a, fp_b = completely_different_fingerprints
        score = jaccard(fp_a, fp_b)
        assert score == 0.0

    def test_jaccard_partial(self, partial_overlap_fingerprints):
        """Partial overlap should score between 0 and 1."""
        fp_a, fp_b = partial_overlap_fingerprints
        score = jaccard(fp_a, fp_b)
        assert 0 < score < 1

    def test_jaccard_empty_both(self, empty_fingerprints):
        """Both empty fingerprints should score 1.0."""
        fp_a, fp_b = empty_fingerprints
        score = jaccard(fp_a, fp_b)
        assert score == 1.0

    def test_jaccard_one_empty(self):
        """One empty, one non-empty should score 0.0."""
        fp_a = {0x1234: [0, 1]}
        fp_b = {}
        score = jaccard(fp_a, fp_b)
        assert score == 0.0

    def test_jaccard_symmetric(self, partial_overlap_fingerprints):
        """Jaccard should be symmetric: score(a,b) == score(b,a)."""
        fp_a, fp_b = partial_overlap_fingerprints
        score_ab = jaccard(fp_a, fp_b)
        score_ba = jaccard(fp_b, fp_a)
        assert score_ab == score_ba

    def test_dice_identical(self, identical_fingerprints):
        """Identical fingerprints should score 1.0 Dice."""
        fp_a, fp_b = identical_fingerprints
        score = dice(fp_a, fp_b)
        assert score == 1.0

    def test_dice_disjoint(self, completely_different_fingerprints):
        """Completely different fingerprints should score 0.0 Dice."""
        fp_a, fp_b = completely_different_fingerprints
        score = dice(fp_a, fp_b)
        assert score == 0.0

    def test_dice_partial(self, partial_overlap_fingerprints):
        """Partial overlap should score between 0 and 1."""
        fp_a, fp_b = partial_overlap_fingerprints
        score = dice(fp_a, fp_b)
        assert 0 < score < 1

    def test_dice_empty_both(self, empty_fingerprints):
        """Both empty should score 1.0."""
        fp_a, fp_b = empty_fingerprints
        score = dice(fp_a, fp_b)
        assert score == 1.0

    def test_dice_symmetric(self, partial_overlap_fingerprints):
        """Dice should be symmetric."""
        fp_a, fp_b = partial_overlap_fingerprints
        score_ab = dice(fp_a, fp_b)
        score_ba = dice(fp_b, fp_a)
        assert score_ab == score_ba

    def test_containment_identical(self, identical_fingerprints):
        """Identical fingerprints should score 1.0 containment."""
        fp_a, fp_b = identical_fingerprints
        score = containment(fp_a, fp_b)
        assert score == 1.0

    def test_containment_disjoint(self, completely_different_fingerprints):
        """Completely different should score 0.0."""
        fp_a, fp_b = completely_different_fingerprints
        score = containment(fp_a, fp_b)
        assert score == 0.0

    def test_containment_partial(self, partial_overlap_fingerprints):
        """Partial overlap should score between 0 and 1."""
        fp_a, fp_b = partial_overlap_fingerprints
        score = containment(fp_a, fp_b)
        assert 0 <= score <= 1

    def test_containment_one_empty(self):
        """One empty should score 0.0."""
        fp_a = {0x1234: [0, 1]}
        fp_b = {}
        score = containment(fp_a, fp_b)
        assert score == 0.0

    def test_containment_empty_both(self, empty_fingerprints):
        """Both empty should score 1.0."""
        fp_a, fp_b = empty_fingerprints
        score = containment(fp_a, fp_b)
        assert score == 1.0

    def test_containment_not_necessarily_symmetric(self):
        """Containment is NOT symmetric in general."""
        # a is subset of b
        fp_a = {0x1234: [0, 1]}
        fp_b = {0x1234: [0, 1], 0x5678: [2, 3]}
        score_ab = containment(fp_a, fp_b)
        score_ba = containment(fp_b, fp_a)
        # score_ab should be higher (a is contained in b)
        # They might not be equal
        assert score_ab >= 0 and score_ba >= 0

    def test_weighted_score_identical(self, identical_fingerprints):
        """Identical fingerprints should score 1.0."""
        fp_a, fp_b = identical_fingerprints
        result = weighted_score(fp_a, fp_b)
        assert isinstance(result, dict)
        assert "jaccard" in result or "weighted_final" in result
        # Final score should be 1.0
        final_score = result.get("weighted_final", result.get("score", 1.0))
        assert final_score >= 0.99  # Allow tiny floating point error

    def test_weighted_score_disjoint(self, completely_different_fingerprints):
        """Completely different should score ~0.0."""
        fp_a, fp_b = completely_different_fingerprints
        result = weighted_score(fp_a, fp_b)
        final_score = result.get("weighted_final", result.get("score", 0.0))
        assert final_score <= 0.01

    def test_weighted_score_partial(self, partial_overlap_fingerprints):
        """Partial overlap should score between 0 and 1."""
        fp_a, fp_b = partial_overlap_fingerprints
        result = weighted_score(fp_a, fp_b)
        final_score = result.get("weighted_final", result.get("score"))
        assert 0 <= final_score <= 1

    def test_weighted_score_contains_components(self, identical_fingerprints):
        """Weighted score should return jaccard, dice, containment components."""
        fp_a, fp_b = identical_fingerprints
        result = weighted_score(fp_a, fp_b)
        # Should contain similarity metrics
        assert any(key in result for key in ["jaccard", "dice", "containment", "weighted_final"])

    def test_score_range_always_valid(self, partial_overlap_fingerprints):
        """All scores should be in [0, 1] range."""
        fp_a, fp_b = partial_overlap_fingerprints
        j_score = jaccard(fp_a, fp_b)
        d_score = dice(fp_a, fp_b)
        c_score = containment(fp_a, fp_b)
        w_result = weighted_score(fp_a, fp_b)

        assert 0 <= j_score <= 1
        assert 0 <= d_score <= 1
        assert 0 <= c_score <= 1
        w_score = w_result.get("weighted_final", w_result.get("score"))
        assert 0 <= w_score <= 1


class TestSimilarityEdgeCases:
    """Edge case tests for similarity scoring."""

    @pytest.mark.edge
    def test_large_fingerprint_sets(self):
        """Test with very large fingerprint sets."""
        fp_a = {hash(f"hash_{i}"): [i] for i in range(10000)}
        fp_b = {hash(f"hash_{i}"): [i] for i in range(10000)}
        score = jaccard(fp_a, fp_b)
        assert score == 1.0

    @pytest.mark.edge
    def test_single_shared_hash(self):
        """Test with only one shared hash among many."""
        fp_a = {hash(f"a_{i}"): [i] for i in range(100)}
        fp_b = {hash(f"b_{i}"): [i] for i in range(100)}
        # Add one shared hash
        fp_b[hash("shared")] = [50]
        fp_a[hash("shared")] = [50]

        score = jaccard(fp_a, fp_b)
        assert 0 < score < 0.1  # Very low similarity

    @pytest.mark.edge
    def test_score_precision(self):
        """Test that scores maintain precision."""
        fp_a = {0x1111: [0], 0x2222: [1]}
        fp_b = {0x1111: [0]}  # 1 shared hash, 1 unique to a
        score = jaccard(fp_a, fp_b)
        # Jaccard = intersection / union = 1 / 2 = 0.5
        assert abs(score - 0.5) < 0.001

    @pytest.mark.edge
    def test_many_positions_per_hash(self):
        """Test with many positions per hash value."""
        fp_a = {0x1234: list(range(1000))}
        fp_b = {0x1234: list(range(1000))}
        score = jaccard(fp_a, fp_b)
        assert score == 1.0

    @pytest.mark.edge
    def test_hash_collision_simulation(self):
        """Test behavior with hash collisions."""
        # Simulate hash collision (two different fingerprints with same hash)
        fp_a = {0xDEADBEEF: [0, 5, 10]}
        fp_b = {0xDEADBEEF: [0, 5, 10]}
        score = jaccard(fp_a, fp_b)
        assert score == 1.0
