"""
engine/pdg/__init__.py — PDG layer module init.

Public API:
    from engine.pdg.build   import build_pdg_features, PDGFeatures
    from engine.pdg.compare import pdg_similarity
"""

def __getattr__(name):
    if name in ("build_pdg_features", "PDGFeatures"):
        from engine.pdg import build as _m
        return getattr(_m, name)
    if name == "pdg_similarity":
        from engine.pdg import compare as _m
        return getattr(_m, name)
    raise AttributeError(f"module 'engine.pdg' has no attribute {name!r}")
