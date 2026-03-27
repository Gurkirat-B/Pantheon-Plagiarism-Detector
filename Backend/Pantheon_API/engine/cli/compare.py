"""
cli/compare.py

Local testing script. Not used by the backend.
Run from the pantheon_engine_v2 directory:
    python -m engine.cli.compare --a samples/similar1.java --b samples/similar2.java
"""
import argparse
import json
import sys
from pathlib import Path

# add parent to path so engine imports work when run directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from engine.api import compare


def main():
    ap = argparse.ArgumentParser(description="Pantheon engine: compare two submissions")
    ap.add_argument("--a",       required=True, help="Path to zip or source file")
    ap.add_argument("--b",       required=True, help="Path to zip or source file")
    ap.add_argument("--id-a",    default="A",   help="Submission ID for A")
    ap.add_argument("--id-b",    default="B",   help="Submission ID for B")
    ap.add_argument("--assign",  default=None,  help="Assignment ID")
    ap.add_argument("--workdir",     default=None,  help="Working directory (default: temp)")
    ap.add_argument("--pretty",      action="store_true", help="Pretty-print JSON output")
    ap.add_argument("--report",      action="store_true", help="Print clean human-readable report")
    ap.add_argument("--save-report", default=None,  metavar="FILE", help="Save report to a .txt file")
    ap.add_argument("--save-html",   default=None,  metavar="FILE", help="Save interactive HTML report to a file")
    args = ap.parse_args()

    result = compare(
        submission_a_path=args.a,
        submission_b_path=args.b,
        submission_a_id=args.id_a,
        submission_b_id=args.id_b,
        assignment_id=args.assign,
        workdir=args.workdir,
    )

    if args.save_html:
        from engine.report_html import format_report_html
        html = format_report_html(result)
        with open(args.save_html, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"HTML report saved to: {args.save_html}")

    if args.report or args.save_report:
        from engine.report import format_report, save_report
        if args.report:
            print(format_report(result))
        if args.save_report:
            save_report(result, args.save_report)

    if not args.save_html and not args.report and not args.save_report:
        indent = 2 if args.pretty else None
        print(json.dumps(result, indent=indent))


if __name__ == "__main__":
    main()
