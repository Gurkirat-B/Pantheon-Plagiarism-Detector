"""
engine.ast — AST-based analysis layer (Phase 1 + Phase 2B).

Public API:
    from engine.ast.parse        import parse_submission, parse_source
    from engine.ast.subtree      import compute_subtree_hashes, subtree_similarity
    from engine.ast.method_match import best_match_score
    from engine.ast.callgraph    import compare_callgraphs
"""

# Lazy imports — each sub-module is imported only when actually used.
# This allows parse.py to be tested in isolation before subtree/method_match
# /callgraph are written.

def __getattr__(name):
    if name in ("parse_submission", "parse_source"):
        from engine.ast import parse as _m
        return getattr(_m, name)
    if name in ("compute_subtree_hashes", "subtree_similarity"):
        from engine.ast import subtree as _m
        return getattr(_m, name)
    if name == "best_match_score":
        from engine.ast import method_match as _m
        return getattr(_m, name)
    if name == "compare_callgraphs":
        from engine.ast import callgraph as _m
        return getattr(_m, name)
    raise AttributeError(f"module 'engine.ast' has no attribute {name!r}")
