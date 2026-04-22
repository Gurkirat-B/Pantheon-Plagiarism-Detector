"""
Local engine test — runs every sample pair and prints a structured report.
Shows individual AST / k-gram / PDG signals alongside the evidence blocks
and their highlight line numbers so you can verify that highlights match
the reported line ranges.

Usage:
    python3 test_engine.py
    python3 test_engine.py --pair pair1   # run one pair only
    python3 test_engine.py --html         # also write report.html
"""

import argparse
import os
import sys
import tempfile
import textwrap
from pathlib import Path

# ── path setup ────────────────────────────────────────────────────────────────
HERE = Path(__file__).parent
SAMPLES = Path(__file__).parent.parent.parent / "samples"
sys.path.insert(0, str(HERE))

# ── colour helpers (works on macOS / Linux terminals) ─────────────────────────
BOLD  = "\033[1m"
CYAN  = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED   = "\033[31m"
DIM   = "\033[2m"
RESET = "\033[0m"

SEP = "─" * 80


def colour_score(s: float) -> str:
    pct = s * 100
    col = GREEN if pct < 40 else YELLOW if pct < 65 else RED
    return f"{col}{pct:.1f}%{RESET}"


# ── individual signal tests ───────────────────────────────────────────────────

def test_kgram(src_a: str, src_b: str, lang: str) -> dict:
    from engine.tokenize.lex import tokenize
    from engine.fingerprint.kgrams import winnow
    from engine.similarity.scores import weighted_score
    from engine.preprocess.stdlib_filter import blank_output_boilerplate

    fp_a_text = blank_output_boilerplate(src_a, lang)
    fp_b_text = blank_output_boilerplate(src_b, lang)

    tok_a = tokenize(fp_a_text, lang=lang, normalize_ids=True, normalize_literals=True, normalize_access=True)
    tok_b = tokenize(fp_b_text, lang=lang, normalize_ids=True, normalize_literals=True, normalize_access=True)

    fp_a = winnow(tok_a, k=10, window=5)
    fp_b = winnow(tok_b, k=10, window=5)

    scores = weighted_score(fp_a, fp_b, tok_a=tok_a, tok_b=tok_b)
    return {
        "jaccard":     scores["jaccard"],
        "containment": scores["containment"],
        "cosine":      scores.get("cosine", 0.0),
        "structural":  scores.get("structural", 0.0),
        "tokens_a":    len(tok_a),
        "tokens_b":    len(tok_b),
        "fp_a_size":   len(fp_a),
        "fp_b_size":   len(fp_b),
        "shared":      len(set(fp_a) & set(fp_b)),
    }


def test_ast(src_a: str, src_b: str, lang: str) -> dict:
    from engine.ast.subtree import compute_subtree_hashes, subtree_similarity
    from engine.ast.method_match import per_method_hashes, best_match_score
    from engine.ast.callgraph import compare_callgraphs
    from engine.ast.parse import parse_source

    h_a = compute_subtree_hashes(src_a, lang)
    h_b = compute_subtree_hashes(src_b, lang)

    sub_sim = subtree_similarity(h_a, h_b)
    mh_a    = per_method_hashes(src_a, lang)
    mh_b    = per_method_hashes(src_b, lang)
    mp_sim  = best_match_score(mh_a, mh_b)

    parse_a = parse_source(src_a, lang)
    parse_b = parse_source(src_b, lang)
    cg_sim  = compare_callgraphs(parse_a["call_graph"], parse_b["call_graph"])

    return {
        "subtree_similarity":  sub_sim,
        "method_pair_score":   mp_sim,
        "callgraph_sim":       cg_sim,
        "parse_ok_a":          h_a.parse_ok,
        "parse_ok_b":          h_b.parse_ok,
        "stmt_hashes_a":       len(h_a.statement),
        "stmt_hashes_b":       len(h_b.statement),
        "block_hashes_a":      len(h_a.block),
        "block_hashes_b":      len(h_b.block),
        "method_hashes_a":     len(h_a.method),
        "method_hashes_b":     len(h_b.method),
        "methods_a":           list(mh_a.keys()),
        "methods_b":           list(mh_b.keys()),
    }


def test_pdg(src_a: str, src_b: str, lang: str) -> dict:
    from engine.pdg.build import build_pdg_features
    from engine.pdg.compare import pdg_similarity

    f_a = build_pdg_features(src_a, lang)
    f_b = build_pdg_features(src_b, lang)

    sim = pdg_similarity(f_a, f_b)

    return {
        "pdg_similarity": sim,
        "parse_ok_a":     f_a.parse_ok,
        "parse_ok_b":     f_b.parse_ok,
        "nodes_a":        f_a.n_nodes,
        "nodes_b":        f_b.n_nodes,
        "ctrl_edges_a":   f_a.n_ctrl_edges,
        "data_edges_a":   f_a.n_data_edges,
        "ctrl_depth_a":   f_a.max_ctrl_depth,
        "has_cycles_a":   f_a.has_cycles,
        "has_cycles_b":   f_b.has_cycles,
        "type_counts_a":  f_a.node_type_counts,
    }


def run_full_compare(path_a: Path, path_b: Path, lang: str) -> dict:
    from engine.api import compare
    result = compare(str(path_a), str(path_b),
                     submission_a_id=path_a.name,
                     submission_b_id=path_b.name)
    return result


# ── display helpers ───────────────────────────────────────────────────────────

def print_kgram(k: dict):
    print(f"  {BOLD}K-GRAM{RESET}")
    print(f"    Jaccard:     {colour_score(k['jaccard'])}")
    print(f"    Containment: {colour_score(k['containment'])}")
    print(f"    Cosine:      {colour_score(k['cosine'])}")
    print(f"    Structural:  {colour_score(k['structural'])}")
    print(f"    Fingerprints A:{k['fp_a_size']}  B:{k['fp_b_size']}  Shared:{k['shared']}")
    print(f"    Tokens       A:{k['tokens_a']}  B:{k['tokens_b']}")


def print_ast(a: dict):
    ok_a = f"{GREEN}OK{RESET}" if a["parse_ok_a"] else f"{RED}FAIL{RESET}"
    ok_b = f"{GREEN}OK{RESET}" if a["parse_ok_b"] else f"{RED}FAIL{RESET}"
    print(f"  {BOLD}AST{RESET}  parse: A={ok_a} B={ok_b}")
    print(f"    Subtree similarity: {colour_score(a['subtree_similarity'])}")
    print(f"    Method-pair score:  {colour_score(a['method_pair_score'])}")
    print(f"    Call-graph sim:     {colour_score(a['callgraph_sim'])}")
    print(f"    Stmt hashes   A:{a['stmt_hashes_a']}  B:{a['stmt_hashes_b']}")
    print(f"    Block hashes  A:{a['block_hashes_a']}  B:{a['block_hashes_b']}")
    print(f"    Method hashes A:{a['method_hashes_a']}  B:{a['method_hashes_b']}")
    if a["methods_a"]:
        print(f"    Methods A: {', '.join(a['methods_a'][:8])}")
    if a["methods_b"]:
        print(f"    Methods B: {', '.join(a['methods_b'][:8])}")


def print_pdg(p: dict):
    ok_a = f"{GREEN}OK{RESET}" if p["parse_ok_a"] else f"{RED}FAIL{RESET}"
    ok_b = f"{GREEN}OK{RESET}" if p["parse_ok_b"] else f"{RED}FAIL{RESET}"
    print(f"  {BOLD}PDG{RESET}  parse: A={ok_a} B={ok_b}")
    print(f"    PDG similarity:  {colour_score(p['pdg_similarity'])}")
    print(f"    Nodes     A:{p['nodes_a']}  B:{p['nodes_b']}")
    print(f"    Ctrl edges A:{p['ctrl_edges_a']}  Data edges A:{p['data_edges_a']}")
    print(f"    Max ctrl depth A:{p['ctrl_depth_a']}")
    print(f"    Has cycles    A:{p['has_cycles_a']}  B:{p['has_cycles_b']}")
    if p["type_counts_a"]:
        counts = "  ".join(f"{k}:{v}" for k, v in sorted(p["type_counts_a"].items()))
        print(f"    Node types: {counts}")


def print_evidence(result: dict, src_a_lines: list, src_b_lines: list):
    evidence = result.get("evidence", [])
    scores   = result.get("scores") or {}

    print(f"\n  {BOLD}COMBINED SCORE{RESET}")
    for k, v in scores.items():
        if isinstance(v, float):
            bar = "█" * int(v * 20)
            print(f"    {k:<22} {colour_score(v)}  {DIM}{bar}{RESET}")

    print(f"\n  {BOLD}EVIDENCE BLOCKS  ({len(evidence)} total){RESET}")

    if not evidence:
        print(f"    {DIM}(none){RESET}")
        return

    highlight_ok = 0
    highlight_bad = 0

    for i, block in enumerate(evidence, 1):
        strength = block.get("match_strength", "?").upper()
        col = RED if strength == "HIGH" else YELLOW if strength == "MEDIUM" else GREEN
        src = block.get("evidence_source", "?")
        fa  = block.get("file_a", "?")
        fb  = block.get("file_b", "?")
        la  = block.get("lines_a", [0, 0])
        lb  = block.get("lines_b", [0, 0])
        ha  = block.get("line_highlights_a", [])
        hb  = block.get("line_highlights_b", [])

        print(f"\n    {col}[{strength}]{RESET}  Block {i}  source={src}")
        print(f"      A: {fa}  lines {la[0]}–{la[1]}  ({la[1]-la[0]+1} lines)  highlights: {len(ha)}")
        print(f"      B: {fb}  lines {lb[0]}–{lb[1]}  ({lb[1]-lb[0]+1} lines)  highlights: {len(hb)}")

        # ── Highlight validation ──────────────────────────────────────────
        # Every highlight line number should be within the block's line range.
        # Also check that highlighted lines actually contain non-empty content
        # in the full source (not blank lines or lone braces).
        full_a = result.get("full_source_a", "").splitlines()
        full_b = result.get("full_source_b", "").splitlines()

        issues = []
        for ln in ha:
            if not (la[0] <= ln <= la[1]):
                issues.append(f"A:{ln} outside [{la[0]},{la[1]}]")
            elif ln - 1 < len(full_a):
                content = full_a[ln - 1].strip()
                if not content or content in ("{", "}", "};"):
                    issues.append(f"A:{ln} is blank/brace")
        for ln in hb:
            if not (lb[0] <= ln <= lb[1]):
                issues.append(f"B:{ln} outside [{lb[0]},{lb[1]}]")
            elif ln - 1 < len(full_b):
                content = full_b[ln - 1].strip()
                if not content or content in ("{", "}", "};"):
                    issues.append(f"B:{ln} is blank/brace")

        if issues:
            highlight_bad += 1
            print(f"      {RED}HIGHLIGHT ISSUES: {', '.join(issues[:5])}{RESET}")
        else:
            highlight_ok += 1
            print(f"      {GREEN}Highlights OK{RESET}")

        # Show first 3 highlighted lines from each side for sanity check
        if ha and full_a:
            sample = []
            for ln in sorted(ha)[:3]:
                if ln - 1 < len(full_a):
                    sample.append(f"L{ln}: {full_a[ln-1].strip()[:60]}")
            print(f"      A sample highlights: {DIM}{' | '.join(sample)}{RESET}")
        if hb and full_b:
            sample = []
            for ln in sorted(hb)[:3]:
                if ln - 1 < len(full_b):
                    sample.append(f"L{ln}: {full_b[ln-1].strip()[:60]}")
            print(f"      B sample highlights: {DIM}{' | '.join(sample)}{RESET}")

    total = highlight_ok + highlight_bad
    if total:
        print(f"\n  Highlight check: {GREEN}{highlight_ok}/{total} OK{RESET}", end="")
        if highlight_bad:
            print(f"  {RED}{highlight_bad} with issues{RESET}", end="")
        print()


# ── HTML report ───────────────────────────────────────────────────────────────

def build_html_report(all_results: list) -> str:
    def esc(s):
        return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

    def score_color(v: float) -> str:
        if v < 0.40: return "#22c55e"
        if v < 0.65: return "#f59e0b"
        return "#ef4444"

    rows = []
    for r in all_results:
        name   = r["name"]
        scores = r.get("full_scores") or {}
        final  = scores.get("weighted_final", 0.0)
        ast_s  = scores.get("ast_subtree", 0.0)
        mp_s   = scores.get("method_pair", 0.0)
        cont   = scores.get("containment", 0.0)
        cos    = scores.get("cosine", 0.0)
        pdg    = scores.get("pdg_similarity", 0.0)
        ev     = r.get("evidence", [])

        def pct(v):
            return f"{v*100:.1f}%"

        rows.append(f"""
        <tr>
          <td><b>{esc(name)}</b></td>
          <td style="color:{score_color(final)};font-weight:bold">{pct(final)}</td>
          <td>{pct(ast_s)}</td>
          <td>{pct(mp_s)}</td>
          <td>{pct(cont)}</td>
          <td>{pct(cos)}</td>
          <td>{pct(pdg) if pdg else "—"}</td>
          <td>{len(ev)}</td>
        </tr>""")

    detail_sections = []
    for r in all_results:
        name = r["name"]
        ev   = r.get("evidence", [])
        full_a = (r.get("full_result") or {}).get("full_source_a", "").splitlines()
        full_b = (r.get("full_result") or {}).get("full_source_b", "").splitlines()

        blocks_html = []
        for i, block in enumerate(ev, 1):
            la  = block.get("lines_a", [0, 0])
            lb  = block.get("lines_b", [0, 0])
            ha  = set(block.get("line_highlights_a", []))
            hb  = set(block.get("line_highlights_b", []))
            str_= block.get("match_strength", "low")
            col = "#dc2626" if str_=="high" else "#d97706" if str_=="medium" else "#16a34a"

            def render_code(lines_full, g1, g2, highlights):
                if not lines_full:
                    return "<em>unavailable</em>"
                out = []
                for ln in range(g1, min(g2+1, len(lines_full)+1)):
                    content = esc(lines_full[ln-1]) if ln-1 < len(lines_full) else ""
                    bg = "background:#fef08a" if ln in highlights else ""
                    out.append(f'<span style="display:block;{bg}"><span style="color:#6b7280;user-select:none;margin-right:8px">{ln:4d}</span>{content}</span>')
                return "".join(out)

            code_a = render_code(full_a, la[0], la[1], ha)
            code_b = render_code(full_b, lb[0], lb[1], hb)

            blocks_html.append(f"""
            <div style="margin:12px 0;border:1px solid #e2e8f0;border-radius:6px;overflow:hidden">
              <div style="background:{col};color:white;padding:6px 12px;font-weight:bold;font-size:13px">
                Block {i} — {str_.upper()} — {esc(block.get('evidence_source','?'))}
                &nbsp;|&nbsp; A lines {la[0]}–{la[1]} &nbsp;|&nbsp; B lines {lb[0]}–{lb[1]}
                &nbsp;|&nbsp; highlights A:{len(ha)} B:{len(hb)}
              </div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:0">
                <pre style="margin:0;padding:8px;background:#0f172a;color:#e2e8f0;font-size:12px;overflow-x:auto;border-right:1px solid #334155">{code_a}</pre>
                <pre style="margin:0;padding:8px;background:#0f172a;color:#e2e8f0;font-size:12px;overflow-x:auto">{code_b}</pre>
              </div>
            </div>""")

        detail_sections.append(f"""
        <details style="margin:16px 0;border:1px solid #cbd5e1;border-radius:8px">
          <summary style="padding:12px;cursor:pointer;font-weight:bold;background:#f8fafc">{esc(name)}</summary>
          <div style="padding:12px">
            {''.join(blocks_html) if blocks_html else '<em style="color:#6b7280">No evidence blocks</em>'}
          </div>
        </details>""")

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Pantheon Engine Test</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 1400px; margin: 0 auto; padding: 20px; background: #f1f5f9 }}
  h1 {{ color: #1e293b }}
  table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.1) }}
  th {{ background: #1e293b; color: white; padding: 10px 12px; text-align: left; font-size: 13px }}
  td {{ padding: 9px 12px; border-bottom: 1px solid #e2e8f0; font-size: 13px }}
  tr:hover td {{ background: #f8fafc }}
  details summary::-webkit-details-marker {{ display: none }}
</style>
</head>
<body>
<h1>Pantheon Engine — Local Test Report</h1>

<h2>Score Summary</h2>
<table>
  <tr>
    <th>Pair</th><th>Final</th><th>AST Subtree</th><th>Method Pair</th>
    <th>Containment</th><th>Cosine</th><th>PDG</th><th>Blocks</th>
  </tr>
  {''.join(rows)}
</table>

<h2>Evidence Blocks with Highlights</h2>
{''.join(detail_sections)}
</body></html>"""


# ── main ──────────────────────────────────────────────────────────────────────

PAIRS = [
    ("pair1_original.java",          "pair1_identifier_renaming.java",  "java",  "Identifier renaming"),
    ("pair2_original.java",          "pair2_loop_type_swap.java",       "java",  "Loop type swap"),
    ("pair3_original.cpp",           "pair3_literal_substitution.cpp",  "cpp",   "Literal substitution"),
    ("pair4_original.java",          "pair4_dead_code_insertion.java",  "java",  "Dead code insertion"),
    ("pair5_original.c",             "pair5_code_reordering.c",         "c",     "Code reordering"),
    ("pair6_original.java",          "pair6_switch_to_ifelse.java",     "java",  "Switch to if-else"),
    ("pair7_original.cpp",           "pair7_ternary_to_ifelse.cpp",     "cpp",   "Ternary to if-else"),
    ("pair8_original.java",          "pair8_exception_wrapping.java",   "java",  "Exception wrapping"),
    ("pair9_original.cpp",           "pair9_for_each_to_indexed.cpp",   "cpp",   "For-each to indexed"),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", default=None, help="Filter to pairs matching this prefix")
    parser.add_argument("--html", action="store_true", help="Write report.html")
    parser.add_argument("--no-full", action="store_true", help="Skip full compare() call (faster)")
    args = parser.parse_args()

    all_results = []

    for file_a, file_b, lang, description in PAIRS:
        if args.pair and args.pair not in file_a:
            continue

        path_a = SAMPLES / file_a
        path_b = SAMPLES / file_b

        if not path_a.exists() or not path_b.exists():
            print(f"{RED}SKIP{RESET} {description} — files missing")
            continue

        src_a = path_a.read_text(encoding="utf-8", errors="replace")
        src_b = path_b.read_text(encoding="utf-8", errors="replace")

        print(f"\n{SEP}")
        print(f"{BOLD}{CYAN}{description.upper()}{RESET}")
        print(f"  A: {file_a}  ({len(src_a.splitlines())} lines)")
        print(f"  B: {file_b}  ({len(src_b.splitlines())} lines)")
        print()

        # ── Individual signals ─────────────────────────────────────────────
        try:
            k = test_kgram(src_a, src_b, lang)
            print_kgram(k)
        except Exception as e:
            print(f"  {RED}K-GRAM ERROR: {e}{RESET}")
            k = {}

        print()

        try:
            a = test_ast(src_a, src_b, lang)
            print_ast(a)
        except Exception as e:
            print(f"  {RED}AST ERROR: {e}{RESET}")
            a = {}

        print()

        try:
            p = test_pdg(src_a, src_b, lang)
            print_pdg(p)
        except Exception as e:
            print(f"  {RED}PDG ERROR: {e}{RESET}")
            p = {}

        # ── Full compare ───────────────────────────────────────────────────
        full_result = {}
        if not args.no_full:
            print(f"\n  {BOLD}FULL COMPARE{RESET} (running engine.api.compare)...")
            try:
                full_result = run_full_compare(path_a, path_b, lang)
                if full_result.get("status") == "failed":
                    print(f"  {RED}Engine error: {full_result.get('error')}{RESET}")
                else:
                    print_evidence(full_result, src_a.splitlines(), src_b.splitlines())
            except Exception as e:
                import traceback
                print(f"  {RED}COMPARE ERROR: {e}{RESET}")
                traceback.print_exc()

        all_results.append({
            "name":        description,
            "kgram":       k,
            "ast":         a,
            "pdg":         p,
            "full_scores": (full_result.get("scores") or {}),
            "evidence":    full_result.get("evidence", []),
            "full_result": full_result,
        })

    print(f"\n{SEP}")
    print(f"{BOLD}DONE — {len(all_results)} pairs tested{RESET}\n")

    if args.html:
        html = build_html_report(all_results)
        out = HERE / "report.html"
        out.write_text(html, encoding="utf-8")
        print(f"HTML report written to: {out}")


if __name__ == "__main__":
    main()
