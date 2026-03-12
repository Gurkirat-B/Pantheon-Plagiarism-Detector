"""
engine/similarity/line_matcher.py

Line-level similarity matching for detailed code comparison.
Generates line-to-line mappings with similarity scores for HTML visualization.
"""

from typing import Dict, List, Tuple, Optional
from engine.tokenize.lex import Token


def _get_line_range(tokens: List[Token], start_idx: int, end_idx: int) -> Tuple[int, int]:
    """
    Given a token range, return the line number range it spans.
    Returns (start_line, end_line) - both 1-indexed.
    """
    if not tokens or start_idx >= len(tokens):
        return (1, 1)
    
    start_line = tokens[start_idx].line
    end_idx = min(end_idx, len(tokens) - 1)
    end_line = tokens[end_idx].line
    
    return (start_line, end_line)


def calculate_line_similarity(
    tokens_a: List[Token],
    tokens_b: List[Token],
    fp_a: Dict[int, List[int]],
    fp_b: Dict[int, List[int]],
    k: int = 8,
) -> Dict[int, Dict]:  # dict[line_number -> {matches: [], score: float}]
    """
    Calculate per-line similarity scores by analyzing which k-grams
    on each line are shared between submissions.
    
    Returns:
        Dict mapping line numbers to similarity info:
        {
            "line_5": {"score": 0.92, "matches": 3, "shared_grams": [hash1, hash2, ...]},
            "line_6": {"score": 0.45, "matches": 1, "shared_grams": [hash3]},
            ...
        }
    """
    shared_hashes = set(fp_a.keys()) & set(fp_b.keys())
    if not shared_hashes:
        return {}
    
    # Map which lines have which shared fingerprints
    line_a_hashes: Dict[int, List[int]] = {}  # line -> [shared hash indices]
    line_b_hashes: Dict[int, List[int]] = {}
    
    # For submission A: which shared hashes appear on which lines?
    for hash_val in shared_hashes:
        for token_idx in fp_a[hash_val]:
            if token_idx < len(tokens_a):
                line = tokens_a[token_idx].line
                if line not in line_a_hashes:
                    line_a_hashes[line] = []
                line_a_hashes[line].append(hash_val)
    
    # For submission B
    for hash_val in shared_hashes:
        for token_idx in fp_b[hash_val]:
            if token_idx < len(tokens_b):
                line = tokens_b[token_idx].line
                if line not in line_b_hashes:
                    line_b_hashes[line] = []
                line_b_hashes[line].append(hash_val)
    
    # Now calculate similarity for each line in A
    line_similarity_a: Dict[int, Dict] = {}
    
    for line_a, shared_on_line_a in line_a_hashes.items():
        # Count how many of A's shared hashes appear on each line of B
        best_match_line = None
        best_match_count = 0
        best_match_set = set()
        
        for line_b, shared_on_line_b in line_b_hashes.items():
            overlap = len(set(shared_on_line_a) & set(shared_on_line_b))
            if overlap > best_match_count:
                best_match_count = overlap
                best_match_line = line_b
                best_match_set = set(shared_on_line_a) & set(shared_on_line_b)
        
        # Calculate score: how much of this line's shared content matches?
        score = best_match_count / len(shared_on_line_a) if shared_on_line_a else 0.0
        
        line_similarity_a[line_a] = {
            "score": score,
            "best_match_line": best_match_line,
            "matches": best_match_count,
            "shared_grams": list(best_match_set),
            "total_shared_on_line": len(shared_on_line_a),
        }
    
    return line_similarity_a


def build_line_mapping(
    tokens_a: List[Token],
    tokens_b: List[Token],
    line_similarity_a: Dict[int, Dict],
) -> List[Dict]:
    """
    Create a list of line-to-line mappings from the similarity data.
    
    Returns list of dicts:
        [
            {"line_a": 10, "line_b": 15, "score": 0.92, "color": "red"},
            {"line_a": 11, "line_b": 16, "score": 0.88, "color": "red"},
            ...
        ]
    """
    mappings = []
    
    for line_a, sim_info in line_similarity_a.items():
        score = sim_info["score"]
        line_b = sim_info["best_match_line"]
        
        # Determine color based on score
        if score >= 0.75:
            color = "red"      # High similarity
        elif score >= 0.40:
            color = "yellow"   # Medium similarity
        else:
            color = "none"     # Low similarity
        
        if line_b is not None:  # Only add if there's a match
            mappings.append({
                "line_a": line_a,
                "line_b": line_b,
                "score": round(score * 100, 1),  # percentage
                "color": color,
                "match_count": sim_info["matches"],
            })
    
    return sorted(mappings, key=lambda x: x["line_a"])


def get_full_source_with_mapping(
    source_code_a: str,
    source_code_b: str,
    line_mapping: List[Dict],
) -> Dict:
    """
    Prepare source code with line mapping data for HTML rendering.
    
    Returns:
        {
            "submission_a": {
                "lines": ["code line 1", "code line 2", ...],
                "total": 150,
            },
            "submission_b": {
                "lines": ["code line 1", "code line 2", ...],
                "total": 142,
            },
            "line_matches": line_mapping_with_colors,
        }
    """
    lines_a = source_code_a.splitlines()
    lines_b = source_code_b.splitlines()
    
    # Create a lookup for which lines have matches
    lines_with_match_a = {m["line_a"] for m in line_mapping}
    lines_with_match_b = {m["line_b"] for m in line_mapping}
    
    # Annotate each line with match info
    enriched_mapping = []
    for mapping in line_mapping:
        line_a = mapping["line_a"]
        line_b = mapping["line_b"]
        enriched_mapping.append({
            **mapping,
            "code_a": lines_a[line_a - 1] if line_a <= len(lines_a) else "",
            "code_b": lines_b[line_b - 1] if line_b <= len(lines_b) else "",
        })
    
    return {
        "submission_a": {
            "lines": lines_a,
            "total": len(lines_a),
            "with_matches": lines_with_match_a,
        },
        "submission_b": {
            "lines": lines_b,
            "total": len(lines_b),
            "with_matches": lines_with_match_b,
        },
        "line_matches": enriched_mapping,
    }
