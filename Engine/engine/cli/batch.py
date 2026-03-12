"""
cli/batch.py

Batch comparison CLI. Takes a folder of submissions and runs all-vs-all.
Run from the pantheon_engine directory:
    python -m engine.cli.batch --folder samples/ --threshold 0.3 --pretty
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from engine.api import batch_analyze

ALLOWED_EXTS = {
    ".zip", ".java", ".c", ".cpp", ".cc", ".h", ".hpp",
    ".py", ".js", ".ts", ".cs", ".go", ".rs", ".rb",
}


def main():
    ap = argparse.ArgumentParser(description="Pantheon engine: batch compare a folder of submissions")
    ap.add_argument("--folder",    required=True,        help="Folder containing submissions")
    ap.add_argument("--assign",    default=None,         help="Assignment ID")
    ap.add_argument("--threshold", type=float, default=0.4)
    ap.add_argument("--workers",   type=int,   default=4)
    ap.add_argument("--workdir",   default=None)
    ap.add_argument("--pretty",    action="store_true")
    ap.add_argument("--template",  default=None,         help="Path to instructor template file")
    args = ap.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"Error: {folder} is not a directory", file=sys.stderr)
        sys.exit(1)

    submissions = []
    for p in sorted(folder.iterdir()):
        if p.is_file() and p.suffix.lower() in ALLOWED_EXTS:
            submissions.append({"id": p.stem, "path": str(p)})

    if len(submissions) < 2:
        print("Need at least 2 submissions to compare", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(submissions)} submissions, running all-vs-all...", file=sys.stderr)

    result = batch_analyze(
        submissions=submissions,
        assignment_id=args.assign,
        threshold=args.threshold,
        workdir=args.workdir,
        max_workers=args.workers,
        template_path=args.template,
    )

    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent))


if __name__ == "__main__":
    main()
