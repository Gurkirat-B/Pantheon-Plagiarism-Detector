"""
pantheon.py — Compare two source files for similarity.

Usage:
    python3 pantheon.py file1.java file2.java
    python3 pantheon.py student1.zip student2.zip
    python3 pantheon.py samples/BST_original.java samples/BST_copied.java
    python3 pantheon.py                          <- lists available sample files
"""

import sys
import json
from pathlib import Path

from engine import compare, format_report
from engine.report_html import format_report_html

SAMPLES_DIR = Path(__file__).resolve().parent / "samples"


def find_file(name):
    p = Path(name)
    if p.exists():
        return p.resolve()
    p = SAMPLES_DIR / name
    if p.exists():
        return p.resolve()
    for ext in (".java", ".c", ".cpp", ".py", ".js", ".zip"):
        p = SAMPLES_DIR / (name + ext)
        if p.exists():
            return p.resolve()
    return None


def list_samples():
    print("\n  Available sample files:")
    print("  " + "-" * 35)
    if not SAMPLES_DIR.exists():
        print("  samples/ folder not found")
        return
    exts = {".java", ".c", ".cpp", ".h", ".hpp", ".py", ".js", ".zip"}
    for f in sorted(SAMPLES_DIR.iterdir()):
        if f.suffix.lower() in exts:
            print(f"  *  {f.name}")
    print("\n  Usage: python3 pantheon.py file1.java file2.java\n")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    use_json = "--json" in sys.argv
    use_html = "--html" in sys.argv

    if len(args) < 2:
        if len(args) == 1:
            print(f"\n  Got one file: {args[0]}")
            print("  Need at least two files to compare.\n")
        list_samples()
        return

    # Find all files
    files = []
    missing = []
    for arg in args:
        f = find_file(arg)
        if f:
            files.append(f)
        else:
            missing.append(arg)
    
    if missing:
        for m in missing:
            print(f"  X  Could not find: {m}")
        list_samples()
        return

    # Case 1: Exactly 2 files - single comparison
    if len(files) == 2:
        file_a, file_b = files
        if not use_json and not use_html:
            print(f"\n  Comparing:")
            print(f"    A  ->  {file_a.name}")
            print(f"    B  ->  {file_b.name}\n")

        result = compare(file_a, file_b)

        if use_json:
            print(json.dumps(result, indent=2))
        elif use_html:
            html_content = format_report_html(result)
            output_file = Path("pantheon_report.html")
            output_file.write_text(html_content, encoding="utf-8")
            print(f"\n✓ HTML report generated: {output_file.resolve()}\n")
        else:
            print(format_report(result))

    # Case 2: More than 2 files - all-vs-all comparison
    else:
        print(f"\n  Comparing {len(files)} files (all-vs-all)...")
        print(f"  This will run {len(files) * (len(files) - 1) // 2} comparisons\n")
        
        results = []
        
        # Compare all pairs
        for i in range(len(files)):
            for j in range(i + 1, len(files)):
                file_a = files[i]
                file_b = files[j]
                
                result = compare(file_a, file_b)
                score = result.get("scores", {}).get("weighted_final", 0.0)
                
                results.append({
                    "file_a": file_a.name,
                    "file_b": file_b.name,
                    "score": score,
                    "result": result,
                })
        
        # Sort by similarity score (highest first)
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # Display results
        if use_json:
            output = {
                "total_comparisons": len(results),
                "results": [
                    {
                        "file_a": r["file_a"],
                        "file_b": r["file_b"],
                        "score": r["score"],
                    }
                    for r in results
                ]
            }
            print(json.dumps(output, indent=2))
        else:
            print("\n" + "=" * 70)
            print("  ALL-VS-ALL COMPARISON RESULTS")
            print("=" * 70)
            print(f"\n  Total Pairs Compared: {len(results)}\n")
            print(f"  {'Rank':<6} {'File A':<25} {'File B':<25} {'Score':<10}")
            print("  " + "-" * 66)
            
            for idx, r in enumerate(results, 1):
                score_pct = f"{r['score']*100:.1f}%"
                print(f"  {idx:<6} {r['file_a']:<25} {r['file_b']:<25} {score_pct:<10}")
            
            print("\n" + "=" * 70)
            print(f"\n  ⚠️  Top 5 highest similarity pairs:\n")
            
            for idx, r in enumerate(results[:5], 1):
                score_pct = f"{r['score']*100:.1f}%"
                print(f"  [{idx}] {r['file_a']} ↔ {r['file_b']}")
                print(f"       Similarity: {score_pct}")
                
                # Show obfuscation flags if high similarity
                flags = r["result"].get("obfuscation_flags", [])
                if flags:
                    print(f"       Alterations detected:")
                    for flag in flags:
                        if flag == "identifier_renaming":
                            print(f"         • Variable/identifier renaming")
                        elif flag == "loop_type_swap":
                            print(f"         • Loop type swap")
                        elif flag == "literal_substitution":
                            print(f"         • Literal substitution")
                        elif flag == "dead_code_insertion":
                            print(f"         • Dead code insertion")
                        else:
                            print(f"         • {flag}")
                print()
            
            print("=" * 70)
            print(f"\n  💡 Run with specific pair to see detailed evidence:")
            print(f"     python3 pantheon.py {results[0]['file_a']} {results[0]['file_b']}\n")


if __name__ == "__main__":
    main()
