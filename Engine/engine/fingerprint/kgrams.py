import hashlib

def _hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def fingerprints(tokens, k: int = 7):
    fp = {}
    texts = [t.text for t in tokens]
    for i in range(0, max(0, len(texts) - k + 1)):
        gram = " ".join(texts[i:i+k])
        h = _hash(gram)
        fp.setdefault(h, []).append(i)
    return fp

def jaccard(fpA, fpB) -> float:
    A, B = set(fpA.keys()), set(fpB.keys())
    if not A and not B:
        return 1.0
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)