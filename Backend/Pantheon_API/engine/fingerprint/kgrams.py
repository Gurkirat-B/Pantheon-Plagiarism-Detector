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

--- v2 addition: per-function adaptive k (Pass 1) ---

build_per_function_fingerprints() is the new Phase 2A Pass 1. It consumes the
function boundary map produced by engine.ast.parse and builds fingerprints
for each function individually, using a k value tuned to that function's
token count. This is more precise than the global adaptive k because a short
helper function needs k=3 to produce any useful fingerprints, while a 300-token
method should use k=15 to avoid false positives from coincidental short matches.

k-selection table (from ENGINE_DESIGN.md):
    < 20 tokens   →  k = 3
    20–50         →  k = 5
    50–150        →  k = 8
    150–300       →  k = 12
    > 300         →  k = 15–18 (scaled)
"""

from typing import Dict, List, Optional, Tuple
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


# ---------------------------------------------------------------------------
# v2: Per-function adaptive k fingerprinting (Phase 2A — Pass 1)
# ---------------------------------------------------------------------------

def select_k(token_count: int) -> int:
    """
    Choose the k value for Winnowing fingerprinting based on a function's
    approximate token count.

    Short functions produce almost no fingerprints at large k — they simply
    do not contain 12-token sequences that are distinct enough to be meaningful.
    Using a small k on short functions produces dense, useful fingerprints.
    Long functions at large k produce only the strongest, most certain matches —
    appropriate because a randomly-coincidental k=15 match is nearly impossible.

    This table is defined in ENGINE_DESIGN.md § 4 and must not be changed
    without updating the design document.

    Args:
        token_count: Approximate token count of the function (from parse.py).

    Returns:
        int k value in the range [3, 18].
    """
    if token_count < 20:
        return 3
    if token_count < 50:
        return 5
    if token_count < 150:
        return 8
    if token_count < 300:
        return 12
    # Scale linearly from 15 to 18 for very large functions
    return min(18, 15 + (token_count - 300) // 300)


def build_per_function_fingerprints(
    tokens: List[Token],
    function_map: Dict[str, dict],
    token_line_index: Optional[Dict[int, int]] = None,
) -> Dict[str, Dict[int, List[int]]]:
    """
    Build fingerprints for each function independently, using a k value tuned
    to that function's token count (Pass 1 of Phase 2A).

    Args:
        tokens:           Full normalized token list for the submission
                          (the same list passed to build_fingerprints).
        function_map:     Output of engine.ast.parse.parse_submission — maps
                          function name to {start_line, end_line, token_count, ...}.
        token_line_index: Optional pre-built {token_position: line_number} map.
                          If None, it is built from the tokens' .line attributes.

    Returns:
        Dict mapping function name to its fingerprint dict
        {hash: [token_positions...]}. The token positions are local to the
        function's slice — add the function's start offset for global positions.

        Also includes a special key "__meta__" mapping each function name to
        its {start_offset, end_offset, k} for use by the evidence builder.
    """
    if not tokens or not function_map:
        return {}

    # Build a position → line_number map so we can slice tokens by line range.
    # Tokens carry a .line attribute (1-indexed); we build a fast list here.
    if token_line_index is None:
        token_line_index = {i: t.line for i, t in enumerate(tokens)}

    result: Dict[str, Dict[int, List[int]]] = {}
    meta: Dict[str, dict] = {}

    for func_name, info in function_map.items():
        start_line = info.get("start_line", 1)
        end_line   = info.get("end_line",   start_line)
        tc         = info.get("token_count", 0)
        k          = select_k(tc)

        # Slice out the tokens that belong to this function by line range.
        func_tokens = [
            t for i, t in enumerate(tokens)
            if start_line <= token_line_index.get(i, t.line) <= end_line
        ]

        if len(func_tokens) < k:
            # Too short even for the adaptive k — skip this function.
            continue

        fp = build_fingerprints(func_tokens, k=k)
        result[func_name] = fp
        meta[func_name] = {
            "start_line": start_line,
            "end_line":   end_line,
            "k":          k,
            "token_count": len(func_tokens),
        }

    result["__meta__"] = meta   # type: ignore[assignment]
    return result
