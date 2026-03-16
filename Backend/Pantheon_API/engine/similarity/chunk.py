"""
Method-level chunk extraction and similarity scoring.

Extracts function/method bodies from normalized token streams and computes
pairwise similarity between them. Catches code-reordering at the method
level where overall k-gram scores are diluted by order differences.

Why this matters:
  A student may copy another submission but reorder the methods so that the
  sequential fingerprint positions differ. Global Jaccard/Containment gets
  diluted, but comparing each method independently recovers the signal.
"""

from typing import Dict, List
from engine.tokenize.lex import Token
from engine.fingerprint.kgrams import build_fingerprints
from engine.similarity.scores import jaccard, containment


def _extract_method_chunks(tokens: List[Token], gram_k: int = 10) -> List[Dict[int, List[int]]]:
    """
    Split a token stream into method/function body chunks and return a
    fingerprint dict for each chunk.

    Detection heuristic: any '{' that immediately follows a ')' is treated
    as the start of a function/method body. Works for Java, C, C++ and
    closely enough for JavaScript/TypeScript and C#.

    Chunks shorter than gram_k tokens are skipped (cannot build fingerprints).
    """
    chunks = []
    n = len(tokens)
    i = 0

    while i < n:
        if tokens[i].text != '{':
            i += 1
            continue

        # Find the nearest preceding non-empty token
        prev = i - 1
        while prev >= 0 and tokens[prev].text.strip() == '':
            prev -= 1

        if prev < 0 or tokens[prev].text != ')':
            i += 1
            continue

        # Walk forward to find the matching closing brace
        depth = 0
        end = i
        for end in range(i, n):
            if tokens[end].text == '{':
                depth += 1
            elif tokens[end].text == '}':
                depth -= 1
                if depth == 0:
                    break

        chunk_toks = tokens[i:end + 1]
        if len(chunk_toks) >= gram_k:
            fp = build_fingerprints(chunk_toks, k=gram_k)
            if fp:
                chunks.append(fp)

        i = end + 1

    return chunks


def compute_method_similarity(
    tok_a: List[Token],
    tok_b: List[Token],
    gram_k: int = 10,
) -> float:
    """
    Compare submissions method-by-method and return a similarity score in [0, 1].

    For each method in submission A, find its best-matching method in B
    (using the max of Jaccard and Containment). The final score is a
    harmonic-weighted average of the per-method best matches, so that
    many matching methods count more than a single lucky match.

    Returns 0.0 if either submission has no detectable method bodies.
    """
    chunks_a = _extract_method_chunks(tok_a, gram_k)
    chunks_b = _extract_method_chunks(tok_b, gram_k)

    if not chunks_a or not chunks_b:
        return 0.0

    best_scores: List[float] = []

    for fp_a in chunks_a:
        best = 0.0
        for fp_b in chunks_b:
            # Containment: catches "A's method is a subset of B's"
            # Jaccard: catches symmetric overlap
            score = max(jaccard(fp_a, fp_b), containment(fp_a, fp_b))
            if score > best:
                best = score
        best_scores.append(best)

    if not best_scores:
        return 0.0

    # Harmonic-decay weighted average: rank-1 match counts most
    best_scores.sort(reverse=True)
    weights = [1.0 / (rank + 1) for rank in range(len(best_scores))]
    total_w = sum(weights)
    return round(sum(s * w for s, w in zip(best_scores, weights)) / total_w, 4)
