"""
engine/report_html.py

Generate interactive HTML reports with side-by-side code comparison
and visual highlighting of similar lines.
"""

from typing import Dict, List, Optional
from datetime import datetime


def escape_html(text: str) -> str:
    if not text:
        return ""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))


_FLAG_LABELS = {
    "identifier_renaming":  "Variable / identifier renaming",
    "loop_type_swap":       "Loop type swap  (for ↔ while ↔ do-while)",
    "literal_substitution": "Constant / literal value substitution",
    "dead_code_insertion":  "Dead code insertion",
    "code_reordering":      "Code block reordering",
    "switch_to_ifelse":     "Switch ↔ if-else conversion",
    "ternary_to_ifelse":    "Ternary operator ↔ if-else conversion",
    "exception_wrapping":   "Try-catch exception wrapping",
    "for_each_to_indexed":  "For-each loop ↔ indexed for loop",
}

_LEVEL_META = {
    "CRITICAL": {"color": "#c0392b", "bg": "#fdecea", "border": "#e74c3c"},
    "HIGH":     {"color": "#d35400", "bg": "#fef3e2", "border": "#e67e22"},
    "MEDIUM":   {"color": "#b7950b", "bg": "#fefde2", "border": "#f1c40f"},
    "LOW":      {"color": "#1e8449", "bg": "#e9f7ef", "border": "#27ae60"},
    "CLEAN":    {"color": "#2874a6", "bg": "#eaf4fd", "border": "#2e86c1"},
}


def _score_to_level(score: float) -> str:
    if score >= 0.85:
        return "CRITICAL"
    if score >= 0.65:
        return "HIGH"
    if score >= 0.40:
        return "MEDIUM"
    if score >= 0.15:
        return "LOW"
    return "CLEAN"


def format_report_html(result: Dict) -> str:
    """
    Generate an interactive HTML report with side-by-side code comparison
    and 4-color line-level similarity highlighting.

    Colors:  red=CRITICAL  orange=HIGH  yellow=MEDIUM  green=LOW
    """
    if result.get("status") == "failed":
        return _error_html(result)

    assignment = result.get("assignment_id") or "—"
    sub_a      = result.get("submission_a", "A")
    sub_b      = result.get("submission_b", "B")
    language   = (result.get("language_detected") or "unknown").upper()
    score      = result.get("scores", {}).get("weighted_final", 0.0)
    flags      = result.get("obfuscation_flags", [])
    version    = result.get("engine_version", "3.0.0")

    # Use original (pre-canonicalization) source code so the report shows
    # what the student actually submitted, not the normalized form.
    # original_sources_a/b are dicts {filename: text}; join for single-file
    # submissions, or concatenate for multi-file ZIPs.
    orig_a = result.get("original_sources_a") or {}
    orig_b = result.get("original_sources_b") or {}
    source_a = "\n".join(orig_a.values()) if orig_a else result.get("source_code_a", "")
    source_b = "\n".join(orig_b.values()) if orig_b else result.get("source_code_b", "")

    lines_a = source_a.splitlines() if source_a else []
    lines_b = source_b.splitlines() if source_b else []

    # strength → CSS highlight class
    _strength_color = {"high": "red", "medium": "orange", "low": "yellow"}

    # Build per-line color from the deduplicated evidence highlights.
    # line_highlights_a/b: {line_number: "high"/"medium"/"low"}
    highlights_a = result.get("line_highlights_a") or {}
    highlights_b = result.get("line_highlights_b") or {}
    line_colors_a: Dict[int, str] = {
        int(ln): _strength_color.get(s, "yellow")
        for ln, s in highlights_a.items()
    }
    line_colors_b: Dict[int, str] = {
        int(ln): _strength_color.get(s, "yellow")
        for ln, s in highlights_b.items()
    }

    level    = _score_to_level(score)
    meta     = _LEVEL_META[level]
    pct      = f"{score * 100:.1f}%"
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Count highlighted lines per strength
    counts_a = {"red": 0, "orange": 0, "yellow": 0}
    for c in line_colors_a.values():
        if c in counts_a:
            counts_a[c] += 1

    # ── CSS ────────────────────────────────────────────────────────────────
    css = """
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                         "Helvetica Neue", Arial, sans-serif;
            background: #eef0f4;
            color: #333;
        }

        .container {
            max-width: 1700px;
            margin: 20px auto;
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 16px rgba(0,0,0,.12);
            overflow: hidden;
        }

        /* ── header ── */
        .header {
            background: linear-gradient(135deg, #5c6bc0 0%, #3949ab 100%);
            color: #fff;
            padding: 28px 32px 22px;
        }
        .header-top {
            display: flex;
            align-items: baseline;
            gap: 14px;
            margin-bottom: 18px;
        }
        .header h1 { font-size: 22px; font-weight: 700; letter-spacing: .3px; }
        .engine-tag {
            font-size: 11px;
            opacity: .7;
            font-family: "Courier New", monospace;
        }
        .header-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 24px;
            font-size: 13px;
        }
        .meta-item { display: flex; flex-direction: column; gap: 3px; }
        .meta-label { font-weight: 600; opacity: .8; font-size: 11px; text-transform: uppercase; letter-spacing: .5px; }
        .meta-value { font-family: "Courier New", monospace; }

        /* ── score badge ── */
        .score-badge {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            background: rgba(255,255,255,.12);
            border: 1.5px solid rgba(255,255,255,.3);
            border-radius: 6px;
            padding: 6px 14px;
        }
        .score-pct { font-size: 24px; font-weight: 800; }
        .score-level {
            font-size: 12px;
            font-weight: 700;
            letter-spacing: .8px;
            opacity: .9;
        }

        /* ── sections ── */
        .section {
            padding: 22px 32px;
            border-bottom: 1px solid #e8e8e8;
        }
        .section-title {
            font-size: 14px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: .6px;
            color: #5c6bc0;
            margin-bottom: 14px;
        }

        /* ── alteration tags ── */
        .flags-wrap { display: flex; flex-wrap: wrap; gap: 8px; }
        .flag-tag {
            background: #fdecea;
            color: #c0392b;
            border: 1px solid #e74c3c;
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 12px;
            font-weight: 500;
        }

        /* ── legend ── */
        .legend {
            display: flex;
            flex-wrap: wrap;
            gap: 18px;
            margin-bottom: 16px;
        }
        .legend-item { display: flex; align-items: center; gap: 7px; font-size: 12px; }
        .legend-swatch {
            width: 14px; height: 14px;
            border-radius: 3px;
            border: 1px solid rgba(0,0,0,.15);
            flex-shrink: 0;
        }

        /* ── code comparison ── */
        .code-comparison {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0;
            border: 1px solid #ddd;
            border-radius: 4px;
            overflow: hidden;
        }
        .code-panel { display: flex; flex-direction: column; min-width: 0; }
        .code-panel + .code-panel { border-left: 1px solid #ddd; }

        .code-panel-header {
            background: #f4f5f7;
            padding: 8px 14px;
            font-size: 12px;
            font-weight: 600;
            color: #444;
            border-bottom: 1px solid #ddd;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .line-count { font-weight: 400; color: #888; font-size: 11px; }

        .code-scroll { overflow-x: auto; max-height: 720px; overflow-y: auto; }
        .code-table {
            width: 100%;
            border-collapse: collapse;
            font-family: "SFMono-Regular", "Cascadia Code", "Fira Code",
                         "Courier New", monospace;
            font-size: 12px;
            line-height: 1.55;
        }
        .code-table tr { border-bottom: 1px solid #f0f0f0; }
        .code-table tr:hover { background: rgba(0,0,0,.025) !important; }
        .line-num {
            width: 44px;
            min-width: 44px;
            text-align: right;
            padding: 1px 8px 1px 4px;
            color: #aaa;
            user-select: none;
            border-right: 1px solid #e8e8e8;
            background: #f9f9f9;
            font-size: 11px;
        }
        .code-line { padding: 1px 4px 1px 10px; white-space: pre; }

        /* highlight classes */
        .hl-red    { background: #ffe0de !important; }
        .hl-red    .line-num { background: #ffc9c6 !important; color: #b71c1c; }
        .hl-orange { background: #fff3e0 !important; }
        .hl-orange .line-num { background: #ffe0b2 !important; color: #e65100; }
        .hl-yellow { background: #fffde7 !important; }
        .hl-yellow .line-num { background: #fff9c4 !important; color: #827717; }
        .hl-green  { background: #e8f5e9 !important; }
        .hl-green  .line-num { background: #c8e6c9 !important; color: #1b5e20; }

        /* ── stats bar ── */
        .stats-bar {
            display: flex;
            gap: 24px;
            flex-wrap: wrap;
            font-size: 12px;
            color: #666;
        }
        .stat { display: flex; align-items: center; gap: 6px; }
        .stat-dot {
            width: 10px; height: 10px;
            border-radius: 2px;
            display: inline-block;
        }

        /* ── footer ── */
        .footer {
            background: #f8f9fb;
            padding: 12px 32px;
            text-align: center;
            font-size: 11px;
            color: #aaa;
        }

        @media (max-width: 1100px) {
            .code-comparison { grid-template-columns: 1fr; }
            .code-panel + .code-panel { border-left: none; border-top: 1px solid #ddd; }
        }
    """

    # ── Flags HTML ─────────────────────────────────────────────────────────
    flags_html = ""
    if flags:
        tags = "".join(
            f'<span class="flag-tag">{escape_html(_FLAG_LABELS.get(f, f))}</span>'
            for f in flags
        )
        flags_html = f"""
        <div class="section">
            <div class="section-title">Alteration Techniques Detected</div>
            <div class="flags-wrap">{tags}</div>
        </div>"""

    # ── Code panel builder ─────────────────────────────────────────────────
    def build_panel(title, lines, colors):
        rows = []
        for i, line in enumerate(lines, 1):
            c = colors.get(i, "none")
            cls = f"hl-{c}" if c != "none" else ""
            rows.append(
                f'<tr class="{cls}">'
                f'<td class="line-num">{i}</td>'
                f'<td class="code-line">{escape_html(line)}</td>'
                f'</tr>'
            )
        body = "\n".join(rows)
        return f"""
                <div class="code-panel">
                    <div class="code-panel-header">
                        <span>{escape_html(title)}</span>
                        <span class="line-count">{len(lines)} lines</span>
                    </div>
                    <div class="code-scroll">
                        <table class="code-table">
                            <tbody>{body}</tbody>
                        </table>
                    </div>
                </div>"""

    panel_a = build_panel(f"A: {sub_a}", lines_a, line_colors_a)
    panel_b = build_panel(f"B: {sub_b}", lines_b, line_colors_b)

    total_highlighted = sum(counts_a.values())
    total_lines_a     = len(lines_a)

    # ── Full HTML ──────────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pantheon — {escape_html(sub_a)} vs {escape_html(sub_b)}</title>
    <style>{css}</style>
</head>
<body>
<div class="container">

    <!-- Header -->
    <div class="header">
        <div class="header-top">
            <h1>Pantheon Plagiarism Report</h1>
            <span class="engine-tag">v{escape_html(version)}</span>
        </div>
        <div class="header-meta">
            <div class="meta-item">
                <span class="meta-label">Assignment</span>
                <span class="meta-value">{escape_html(assignment)}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Submission A</span>
                <span class="meta-value">{escape_html(sub_a)}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Submission B</span>
                <span class="meta-value">{escape_html(sub_b)}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Language</span>
                <span class="meta-value">{language}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Plagiarism Level</span>
                <div class="score-badge">
                    <span class="score-pct">{pct}</span>
                    <span class="score-level">{level}</span>
                </div>
            </div>
        </div>
    </div>

    {flags_html}

    <!-- Code Comparison -->
    <div class="section">
        <div class="section-title">Side-by-Side Code Comparison</div>

        <div class="legend">
            <div class="legend-item">
                <div class="legend-swatch" style="background:#ffe0de;border-color:#e74c3c;"></div>
                <span><strong>HIGH</strong> match (large block)</span>
            </div>
            <div class="legend-item">
                <div class="legend-swatch" style="background:#fff3e0;border-color:#e67e22;"></div>
                <span><strong>MEDIUM</strong> match</span>
            </div>
            <div class="legend-item">
                <div class="legend-swatch" style="background:#fffde7;border-color:#f1c40f;"></div>
                <span><strong>LOW</strong> match (small block)</span>
            </div>
            <div class="legend-item">
                <div class="legend-swatch" style="background:#f9f9f9;"></div>
                <span>No match</span>
            </div>
        </div>

        <div class="stats-bar" style="margin-bottom:14px;">
            <span class="stat">
                <span class="stat-dot" style="background:#e74c3c;"></span>
                {counts_a['red']} HIGH lines
            </span>
            <span class="stat">
                <span class="stat-dot" style="background:#e67e22;"></span>
                {counts_a['orange']} MEDIUM lines
            </span>
            <span class="stat">
                <span class="stat-dot" style="background:#f1c40f;"></span>
                {counts_a['yellow']} LOW lines
            </span>
            <span class="stat" style="margin-left:8px; color:#aaa;">
                {total_highlighted} / {total_lines_a} lines flagged in submission A
            </span>
        </div>

        <div class="code-comparison">
            {panel_a}
            {panel_b}
        </div>
    </div>

    <div class="footer">
        Pantheon Similarity Engine v{escape_html(version)} &nbsp;|&nbsp; Generated {gen_time}
    </div>

</div>
</body>
</html>
"""
    return html


def _error_html(result: Dict) -> str:
    sub_a = escape_html(result.get("submission_a", "A"))
    sub_b = escape_html(result.get("submission_b", "B"))
    error = escape_html(result.get("error", "Unknown engine error"))
    version = escape_html(result.get("engine_version", "3.0.0"))
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Pantheon — Error</title>
    <style>
        body {{ font-family: sans-serif; background: #eef0f4; display: flex; justify-content: center; align-items: center; min-height: 100vh; }}
        .card {{ background: #fff; border-radius: 8px; padding: 40px 50px; box-shadow: 0 2px 16px rgba(0,0,0,.12); max-width: 600px; text-align: center; }}
        h1 {{ color: #c0392b; margin-bottom: 16px; }}
        .subs {{ font-family: monospace; color: #666; margin-bottom: 20px; }}
        .err {{ background: #fdecea; border: 1px solid #e74c3c; border-radius: 4px; padding: 12px 16px; color: #c0392b; font-family: monospace; font-size: 13px; text-align: left; }}
        .footer {{ margin-top: 24px; font-size: 11px; color: #aaa; }}
    </style>
</head>
<body>
<div class="card">
    <h1>Engine Error</h1>
    <div class="subs">{sub_a} &nbsp;vs&nbsp; {sub_b}</div>
    <div class="err">{error}</div>
    <div class="footer">Pantheon v{version} | {gen_time}</div>
</div>
</body>
</html>"""
