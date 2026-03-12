"""
K-gram fingerprinting with winnowing.

The winnowing algorithm selects a representative subset of k-gram hashes.
Guarantee: if two submissions share a common token sequence of length
>= k + window - 1, at least one shared fingerprint will be selected.

This means:
  k=8, window=4 → any shared sequence of 11+ tokens WILL be caught.
  Typical student code has ~3 tokens per logical line, so that's
  roughly 4 lines of identical logic — a good detection threshold.
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
