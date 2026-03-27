"""
format_output.py

Formatters to convert the detailed engine output into human-readable reports.
"""

_FLAG_LABELS = {
    "identifier_renaming":  "Variable and identifier renaming",
    "loop_type_swap":       "Loop type changed (for loop rewritten as while or do-while)",
    "literal_substitution": "Constant and literal value substitution",
    "dead_code_insertion":  "Dead code added to inflate submission",
    "code_reordering":      "Code blocks reordered or shuffled",
    "switch_to_ifelse":     "Switch statement rewritten as an if-else chain",
    "ternary_to_ifelse":    "Ternary expression expanded into an if-else block",
    "exception_wrapping":   "Code wrapped inside try-catch blocks",
    "for_each_to_indexed":  "For-each loop converted to an index-based for loop",
}

_RISK_COLORS = {
    "CRITICAL": "CRITICAL  (>= 85%)",
    "HIGH":     "HIGH      (65 - 84%)",
    "MEDIUM":   "MEDIUM    (40 - 64%)",
    "LOW":      "LOW       (< 40%)",
}

W = 64  # report width


def _risk(score: float) -> str:
    if score >= 0.85: return "CRITICAL"
    if score >= 0.65: return "HIGH"
    if score >= 0.40: return "MEDIUM"
    return "LOW"



def convert_to_old_format(result):
    """Converts new engine output to the legacy simple format."""
    scores = result.get("scores", {})
    return {
        "submission_a":      result.get("submission_a", "A"),
        "submission_b":      result.get("submission_b", "B"),
        "similarity_score":  scores.get("weighted_final", 0.0),
        "obfuscation_flags": result.get("obfuscation_flags", []),
        "evidence":          result.get("evidence", []),
    }


def format_report_for_backend(result):
    """
    Format the engine result as a clean human-readable text report
    suitable for display in the frontend or API response.
    """
    lines = []

    # Handle failed engine result
    if result.get("status") == "failed":
        lines += [
            "", "  PANTHEON PLAGIARISM DETECTION REPORT", "",
            f"  Submission A  :  {result.get('submission_a', 'A')}",
            f"  Submission B  :  {result.get('submission_b', 'B')}",
            "", "-" * W, "",
            f"  ERROR: {result.get('error', 'Unknown engine error')}",
            "",
        ]
        return "\n".join(lines)

    sub_a    = result.get("submission_a", "A")
    sub_b    = result.get("submission_b", "B")
    lang     = (result.get("language_detected") or "unknown").upper()
    scores   = result.get("scores") or {}
    final    = scores.get("weighted_final", 0.0)
    flags    = result.get("obfuscation_flags", [])
    evidence = result.get("evidence", [])
    risk     = _risk(final)
    pct      = f"{round(final * 100, 1)}%"

    dash = "-" * W

    # ── Header ───────────────────────────────────────────────────
    lines += ["", "  PANTHEON PLAGIARISM DETECTION REPORT", ""]
    lines.append(f"  Submission A  :  {sub_a}")
    lines.append(f"  Submission B  :  {sub_b}")
    lines.append(f"  Language      :  {lang}")
    lines += ["", dash]

    # ── Score block ───────────────────────────────────────────────
    lines += [
        "",
        f"  SIMILARITY SCORE      {pct}",
        f"  PLAGIARISM LEVEL      {_RISK_COLORS[risk]}",
        "",
        dash,
    ]

    # ── Obfuscation flags ─────────────────────────────────────────
    if flags:
        lines += ["", "  ALTERATION TECHNIQUES DETECTED:", ""]
        for f in flags:
            label = _FLAG_LABELS.get(f, f)
            lines.append(f"    [!]  {label}")
        lines += ["", dash]

    # ── Matching sections ─────────────────────────────────────────
    lines.append("")
    if not evidence:
        lines.append("  No matching code sections found.")
    else:
        high   = sum(1 for b in evidence if b.get("match_strength") == "high")
        medium = sum(1 for b in evidence if b.get("match_strength") == "medium")
        low    = sum(1 for b in evidence if b.get("match_strength") == "low")

        lines.append(f"  MATCHING CODE SECTIONS  ({len(evidence)} blocks found)")
        lines.append(f"  Breakdown: {high} HIGH  /  {medium} MEDIUM  /  {low} LOW")
        lines.append("")

        for i, block in enumerate(evidence, 1):
            file_a   = block.get("file_a", "File A")
            file_b   = block.get("file_b", "File B")
            lines_a  = block.get("lines_a", [1, 1])
            lines_b  = block.get("lines_b", [1, 1])
            code_a   = block.get("code_a", "")
            code_b   = block.get("code_b", "")
            strength = block.get("match_strength", "medium").upper()

            lines.append(f"  [{i}]  {strength} MATCH")
            lines.append(f"       A: {file_a}  (lines {lines_a[0]} - {lines_a[1]})")
            lines.append(f"       B: {file_b}  (lines {lines_b[0]} - {lines_b[1]})")
            lines.append("")

            lines.append("       --- Submission A ---")
            if code_a:
                for cl in code_a.split("\n"):
                    lines.append(f"       {cl}")
            else:
                lines.append("       (unavailable)")
            lines.append("")

            lines.append("       --- Submission B ---")
            if code_b:
                for cl in code_b.split("\n"):
                    lines.append(f"       {cl}")
            else:
                lines.append("       (unavailable)")

            lines += ["", dash]

    # ── Footer ────────────────────────────────────────────────────
    ver = result.get("engine_version", "3.0.0")
    lines += ["", f"  Pantheon Engine v{ver}", ""]

    return "\n".join(lines)


def format_report_text(result):
    """Alias for backwards compatibility."""
    return format_report_for_backend(result)


def format_report_as_json(result) -> dict:
    """
    Convert the engine result into a JSON-serialisable dict whose shape
    matches the ComparisonReport type in the frontend's parse_report.ts.

    The backend API returns this instead of the plain-text report.
    The frontend deserialises it directly — no regex parsing needed.
    """
    scores   = result.get("scores") or {}
    final    = scores.get("weighted_final", 0.0)
    flags    = result.get("obfuscation_flags", [])
    evidence = result.get("evidence", [])
    risk     = _risk(final)

    high   = sum(1 for b in evidence if b.get("match_strength") == "high")
    medium = sum(1 for b in evidence if b.get("match_strength") == "medium")
    low    = sum(1 for b in evidence if b.get("match_strength") == "low")

    matches = []
    for i, block in enumerate(evidence, 1):
        lines_a = block.get("lines_a", [1, 1])
        lines_b = block.get("lines_b", [1, 1])
        matches.append({
            "index":            i,
            "severity":         block.get("match_strength", "low").upper(),
            "fileA":            block.get("file_a", ""),
            "linesA":           f"{lines_a[0]} - {lines_a[1]}",
            "lineHighlightsA":  block.get("line_highlights_a", []),
            "fileB":            block.get("file_b", ""),
            "linesB":           f"{lines_b[0]} - {lines_b[1]}",
            "lineHighlightsB":  block.get("line_highlights_b", []),
            "codeA":            block.get("code_a", ""),
            "codeB":            block.get("code_b", ""),
        })

    return {
        "submissionA":                  result.get("submission_a", "A"),
        "submissionB":                  result.get("submission_b", "B"),
        "language":                     (result.get("language_detected") or "unknown").upper(),
        "similarityScore":              round(final * 100, 1),
        "similarityLevel":              risk,
        "alterationTechniquesDetected": [_FLAG_LABELS.get(f, f) for f in flags],
        "sections":                     len(evidence),
        "High":                         high,
        "Medium":                       medium,
        "Low":                          low,
        "matches":                      matches,
        "fullCodeA":                    result.get("original_sources_a", {}),
        "fullCodeB":                    result.get("original_sources_b", {}),
    }
