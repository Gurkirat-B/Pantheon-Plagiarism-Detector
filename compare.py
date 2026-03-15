#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Backend/Pantheon_API'))
from engine import compare
from format_output import format_report_for_backend
from engine.report_html import format_report_html

if len(sys.argv) < 3:
    print("Usage: python3 compare.py <file_a> <file_b> [--html <output.html>]")
    print("  Files can be bare names (e.g. BST_original.java) — will search samples/ automatically")
    sys.exit(1)

SAMPLES = os.path.join(os.path.dirname(__file__), 'samples')
ENGINE_SAMPLES = os.path.join(os.path.dirname(__file__), 'Engine', 'samples')

def resolve_file(name):
    """Return the file path, searching samples directories if not found directly."""
    if os.path.exists(name):
        return name
    for folder in (SAMPLES, ENGINE_SAMPLES):
        candidate = os.path.join(folder, os.path.basename(name))
        if os.path.exists(candidate):
            return candidate
    return name  # let engine report the error

a = resolve_file(sys.argv[1])
b = resolve_file(sys.argv[2])

# Parse optional --html flag
html_out = None
args = sys.argv[3:]
if '--html' in args:
    idx = args.index('--html')
    if idx + 1 < len(args):
        html_out = args[idx + 1]
    else:
        html_out = 'pantheon_report.html'

result = compare(a, b, os.path.basename(a), os.path.basename(b))

if result.get('status') == 'failed':
    print(f"\n  ERROR: {result.get('error', 'Unknown error')}\n")
    if html_out:
        html = format_report_html(result)
        with open(html_out, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"  HTML error report saved to: {html_out}\n")
    sys.exit(1)

print(format_report_for_backend(result))

if html_out:
    html = format_report_html(result)
    with open(html_out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n  HTML report saved to: {html_out}")
