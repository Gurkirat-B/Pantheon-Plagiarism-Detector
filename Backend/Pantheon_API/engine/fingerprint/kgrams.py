"""
This file is the core of how we compare two submissions. The idea is simple:
take a sequence of tokens (words from the source code), slide a window of
k tokens across it, and compute a hash for each window. If two submissions
share many of these hashes, they share many k-token sequences — which means
chunks of their code are identical.

There are two functions here for two different purposes. build_fingerprints
computes every single k-gram hash and is used when building evidence (we need
to know every location where a match occurs so we can show it to the instructor).
winnow is more selective — it uses the Winnowing algorithm to keep only the
minimum hash within each sliding window, which produces a much smaller set of
fingerprints that is efficient for computing similarity scores.

The mathematical guarantee of Winnowing is that any shared token sequence of
length k + window - 1 or more will produce at least one matching fingerprint
in both submissions, so nothing significant gets missed.
"""

from typing import Dict, List, Tuple
from engine.tokenize.lex import Token

# Parameters for the polynomial rolling hash. We use a Mersenne prime as the
# modulus because arithmetic modulo Mersenne primes is fast and the resulting
# hashes distribute well, which minimizes accidental collisions.
_BASE = 31
_MOD  = (1 << 61) - 1   # Mersenne prime: 2^61 - 1


def _poly_hash(tokens: List[str]) -> int:
    """
    Compute a hash for a list of tokens by treating each character as a digit
    in a large base-31 number. A separator byte (0x7f) is inserted between
    tokens so that ["ab", "c"] and ["a", "bc"] produce different hashes.
    """
    h = 0
    for t in tokens:
        for ch in t:
            h = (h * _BASE + ord(ch)) % _MOD
        h = (h * _BASE + 0x7f) % _MOD  # separator between tokens
    return h


def build_fingerprints(tokens: List[Token], k: int = 8) -> Dict[int, List[int]]:
    """
    Slide a window of k tokens across the token list and hash each window.
    Returns a dictionary mapping each hash to a list of token positions where
    that k-gram starts. If the same hash appears at multiple positions, all of
    them are recorded — this is needed so the evidence builder can find every
    location where a match occurs in both submissions.
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
    A more compact fingerprint set used for computing similarity scores.
    Instead of keeping every k-gram hash, Winnowing slides a second window
    (of size `window`) across the list of k-gram hashes and keeps only the
    minimum hash in each position of that window. This keeps roughly one in
    every `window` hashes, making the set about 25% the size of the full set
    while still guaranteeing that long shared sequences are detected.
    """
    if not tokens:
        return {}

    texts = [t.text for t in tokens]
    n_tokens = len(texts)

    if n_tokens < k:
        return {}

    gram_list: List[Tuple[int, int]] = []  # (position, hash) for each k-gram
    for i in range(n_tokens - k + 1):
        h = _poly_hash(texts[i:i + k])
        gram_list.append((i, h))

    if len(gram_list) < window:
        # The file is too short to apply the windowing step, so just return all k-grams.
        return build_fingerprints(tokens, k=k)

    selected: Dict[int, List[int]] = {}
    prev_min_pos = -1

    for w_start in range(len(gram_list) - window + 1):
        window_slice = gram_list[w_start: w_start + window]

        # Pick the rightmost occurrence of the minimum hash in this window.
        # Using the rightmost (not the leftmost) avoids re-selecting the same
        # fingerprint when the window slides by one position.
        min_h = min(h for _, h in window_slice)
        min_pos = max(pos for pos, h in window_slice if h == min_h)

        if min_pos != prev_min_pos:
            if min_h not in selected:
                selected[min_h] = []
            selected[min_h].append(min_pos)
            prev_min_pos = min_pos

    return selected
