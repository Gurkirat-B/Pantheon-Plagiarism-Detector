import argparse, json
from pathlib import Path

from engine.ingest.ingest import ingest_to_dir
from engine.preprocess.canonicalize import canonicalize
from engine.tokenize.lex import tokenize
from engine.fingerprint.kgrams import fingerprints, jaccard
from engine.evidence.evidence import evidence_from_shared

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="Path to .zip or source file")
    ap.add_argument("--b", required=True, help="Path to .zip or source file")
    ap.add_argument("--lang", default="java", choices=["java","c","cpp","mixed"])
    ap.add_argument("--k", type=int, default=7)
    ap.add_argument("--strip-comments", action="store_true")
    ap.add_argument("--normalize-ids", action="store_true", default=True)
    ap.add_argument("--normalize-literals", action="store_true", default=True)
    args = ap.parse_args()

    work = Path(".pantheon_work")
    work.mkdir(exist_ok=True)

    subA = ingest_to_dir(Path(args.a), work / "A")
    subB = ingest_to_dir(Path(args.b), work / "B")

    canA = canonicalize(subA, strip_comments=args.strip_comments)
    canB = canonicalize(subB, strip_comments=args.strip_comments)

    tokA = tokenize(canA.read_text(encoding="utf-8", errors="ignore"),
                    lang=args.lang,
                    normalize_ids=args.normalize_ids,
                    normalize_literals=args.normalize_literals)
    tokB = tokenize(canB.read_text(encoding="utf-8", errors="ignore"),
                    lang=args.lang,
                    normalize_ids=args.normalize_ids,
                    normalize_literals=args.normalize_literals)

    fpA = fingerprints(tokA, k=args.k)
    fpB = fingerprints(tokB, k=args.k)
    score = jaccard(fpA, fpB)

    evidence = evidence_from_shared(fpA, fpB, tokA, tokB, k=args.k)

    print(json.dumps({
        "score": round(score, 4),
        "k": args.k,
        "lang": args.lang,
        "evidence": evidence
    }, indent=2))

if __name__ == "__main__":
    main()