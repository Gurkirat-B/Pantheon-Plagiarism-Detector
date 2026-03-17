"""
engine/fingerprint/kgrams.py

K-gram fingerprinting using the Winnowing algorithm.

The idea: slide a window over all consecutive k-token sequences (k-grams),
hash each one, then keep only the minimum hash from each window position.
This gives a compact but representative set of fingerprints.

The key guarantee: if two submissions share any common token sequence of
length >= k + window - 1, at least one matching fingerprint is guaranteed
to be selected from both. With k=10 and window=5 (the engine's default),
that means any shared run of 14+ tokens will definitely be caught —
roughly 4-5 lines of identical logic.

build_fingerprints() keeps every k-gram (used for method-level chunk
comparison). winnow() applies the selection window (used for global
submission-level comparison).
"""

from typing import Dict, List, Tuple
from engine.tokenize.lex import Token

# Rolling hash parameters
_BASE = 31
_MOD  = (1 << 61) - 1   # Mersenne prime


def _poly_hash(tokens: List[str]) -> int:
    """Polynomial rolling hash of a token sequence."""
    h = 0
    for t in tokens:
        for ch in t:
            h = (h * _BASE + ord(ch)) % _MOD
        h = (h * _BASE + 0x7f) % _MOD  # separator
    return h


def build_fingerprints(tokens: List[Token], k: int = 8) -> Dict[int, List[int]]:
    """
    Build ALL k-gram fingerprints from the token list.
    Returns dict mapping hash → list of token indexes where that k-gram starts.
    """
    if k <= 0:
        raise ValueError("k must be >= 1")

    texts = [t.text for t in tokens]
    fp: Dict[int, List[int]] = {}

    if len(texts) < k:
        return fp

    for i in range(len(texts) - k + 1):
        gram = texts[i:i + k]
        h = _poly_hash(gram)
        if h not in fp:
            fp[h] = []
        fp[h].append(i)

    return fp


def winnow(tokens: List[Token], k: int = 8, window: int = 4) -> Dict[int, List[int]]:
    """
    Winnowing algorithm for fingerprint selection.

    Instead of keeping every k-gram, slides a window and keeps only
    the minimum hash in each window position. This gives ~25% of
    all k-grams while guaranteeing detection of shared sequences
    of length >= k + window - 1 tokens.

    Returns same format as build_fingerprints: hash → [token indexes].
    """
    if not tokens:
        return {}

    texts = [t.text for t in tokens]
    n_tokens = len(texts)

    if n_tokens < k:
        return {}

    # build all k-gram hashes in order
    gram_list: List[Tuple[int, int]] = []  # (position, hash)
    for i in range(n_tokens - k + 1):
        h = _poly_hash(texts[i:i + k])
        gram_list.append((i, h))

    if len(gram_list) < window:
        # too short for winnowing — return all k-grams
        return build_fingerprints(tokens, k=k)

    selected: Dict[int, List[int]] = {}
    prev_min_pos = -1

    for w_start in range(len(gram_list) - window + 1):
        window_slice = gram_list[w_start: w_start + window]

        # pick the rightmost minimum (rightmost avoids re-selecting)
        min_h = min(h for _, h in window_slice)
        min_pos = max(pos for pos, h in window_slice if h == min_h)

        if min_pos != prev_min_pos:
            if min_h not in selected:
                selected[min_h] = []
            selected[min_h].append(min_pos)
            prev_min_pos = min_pos

    return selected
