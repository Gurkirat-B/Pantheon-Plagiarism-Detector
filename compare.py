#!/usr/bin/env python3
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Backend/Pantheon_API'))
from engine import compare
from format_output import format_report_as_json

if len(sys.argv) < 3:
    print("Usage: python3 compare.py <file_a> <file_b>")
    print("  Files can be bare names (e.g. BST_original.java) — will search samples/ automatically")
    sys.exit(1)

SAMPLES = os.path.join(os.path.dirname(__file__), 'samples')

def resolve_file(name):
    if os.path.exists(name):
        return name
    candidate = os.path.join(SAMPLES, os.path.basename(name))
    if os.path.exists(candidate):
        return candidate
    return name

a = resolve_file(sys.argv[1])
b = resolve_file(sys.argv[2])

result = compare(a, b, os.path.basename(a), os.path.basename(b))

if result.get('status') == 'failed':
    print(f"\n  ERROR: {result.get('error', 'Unknown error')}\n")
    sys.exit(1)

print(json.dumps(format_report_as_json(result), indent=2))
