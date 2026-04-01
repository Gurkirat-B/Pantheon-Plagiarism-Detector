#!/usr/bin/env python3
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Backend/Pantheon_API'))
from engine import compare, batch_analyze
from format_output import format_report_as_json

SAMPLES = os.path.join(os.path.dirname(__file__), 'samples')

def resolve_file(name):
    if os.path.exists(name):
        return name
    candidate = os.path.join(SAMPLES, os.path.basename(name))
    if os.path.exists(candidate):
        return candidate
    return name

# ── Batch mode ────────────────────────────────────────────────────────────────
if len(sys.argv) >= 3 and sys.argv[1] == "--batch":
    folder = sys.argv[2]

    if not os.path.isdir(folder):
        print(f"ERROR: '{folder}' is not a directory")
        sys.exit(1)

    ALLOWED = {".java", ".c", ".cpp", ".cc", ".cxx", ".py", ".js", ".ts"}
    files = sorted([
        os.path.join(folder, f) for f in os.listdir(folder)
        if os.path.splitext(f)[1].lower() in ALLOWED
        or f.endswith(".zip")
    ])

    if len(files) < 2:
        print(f"ERROR: need at least 2 source files or ZIPs in '{folder}'")
        sys.exit(1)

    submissions = [{"id": os.path.basename(f), "path": f} for f in files]

    print(f"Running round robin on {len(submissions)} submissions ({len(submissions)*(len(submissions)-1)//2} pairs)...\n")

    results = batch_analyze(submissions)

    pairs = results.get("pairs", [])
    if not pairs:
        print("No suspicious pairs found above threshold.")
        sys.exit(0)

    print(f"{'#':<4} {'Score':>6}  {'Level':<10}  {'File A':<35} {'File B'}")
    print("-" * 90)
    for i, pair in enumerate(pairs, 1):
        score = pair.get("score", 0) * 100
        if score >= 90:
            level = "CRITICAL"
        elif score >= 70:
            level = "HIGH"
        elif score >= 50:
            level = "MEDIUM"
        else:
            level = "LOW"
        a = pair.get("submission_a", "")
        b = pair.get("submission_b", "")
        print(f"{i:<4} {score:>5.1f}%  {level:<10}  {a:<35} {b}")

    print(f"\nTotal pairs compared: {len(pairs)} / {results.get('total_pairs', 0)}")
    sys.exit(0)

# ── Pairwise mode ─────────────────────────────────────────────────────────────
if len(sys.argv) < 3:
    print("Usage:")
    print("  python3 compare.py <file_a> <file_b>")
    print("  python3 compare.py --batch <folder>")
    print()
    print("Examples:")
    print("  python3 compare.py BST_original.java BST_copied.java")
    print("  python3 compare.py --batch Engine/samples/")
    sys.exit(1)

a = resolve_file(sys.argv[1])
b = resolve_file(sys.argv[2])

result = compare(a, b, os.path.basename(a), os.path.basename(b))

if result.get('status') == 'failed':
    print(f"\n  ERROR: {result.get('error', 'Unknown error')}\n")
    sys.exit(1)

print(json.dumps(format_report_as_json(result), indent=2))
