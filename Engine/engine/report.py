"""
engine/report.py

Takes the raw result dict from api.compare() and formats it into
a clean human-readable report for instructors.
"""

RISK_THRESHOLDS = {
    "CRITICAL": 0.85,
    "HIGH":     0.65,
    "MEDIUM":   0.40,
    "LOW":      0.0,
}

RISK_ICONS = {
    "CRITICAL": "CRITICAL",
    "HIGH":     "⚠ HIGH",
    "MEDIUM":   "⚡ MEDIUM",
    "LOW":      "✓  LOW",
}

OBFUSCATION_LABELS = {
    "identifier_renaming":  "Variable / identifier renaming detected",
    "loop_type_swap":       "Loop type swap detected (for ↔ while)",
    "literal_substitution": "Constant / literal values substituted",
    "dead_code_insertion":  "Dead code insertion detected",
    "code_reordering":      "Code block reordering detected",
    "switch_to_ifelse":     "Switch ↔ if-else conversion detected",
    "ternary_to_ifelse":    "Ternary ↔ if-else conversion detected",
}

STRENGTH_ICONS = {
    "high":   "●●● HIGH",
    "medium": "●●○ MEDIUM",
    "low":    "●○○ LOW",
}

LINE = "━" * 52


def _risk_level(score: float) -> str:
    for level, threshold in RISK_THRESHOLDS.items():
        if score >= threshold:
            return level
    return "LOW"


def _pct(score: float) -> str:
    return f"{round(score * 100, 1)}%"


def format_report(result: dict) -> str:
    lines = []

    def ln(s=""):
        lines.append(s)

    ln()
    ln("  PANTHEON SIMILARITY REPORT")
    ln(f"  {LINE}")

    if result.get("status") == "failed":
        ln()
        ln(f"  Status  : FAILED")
        ln(f"  Error   : {result.get('error', 'Unknown error')}")
        ln()
        ln(f"  {LINE}")
        ln(f"  Engine v{result.get('engine_version', '?')}")
        ln()
        return "\n".join(lines)

    scores = result.get("scores", {})
    score  = scores.get("weighted_final", 0.0)
    risk   = _risk_level(score)
    flags  = result.get("obfuscation_flags", [])
    evidence = result.get("evidence", [])

    # metadata
    ln()
    assign = result.get("assignment_id") or "—"
    sub_a  = result.get("submission_a") or "—"
    sub_b  = result.get("submission_b") or "—"
    lang   = (result.get("language_detected") or "unknown").upper()

    ln(f"  Assignment   : {assign}")
    ln(f"  Submission A : {sub_a}")
    ln(f"  Submission B : {sub_b}")
    ln(f"  Language     : {lang}")
    ln()

    # score block with breakdown
    ln(f"  {LINE}")
    ln(f"  Overall Score : {_pct(score)}")
    ln(f"  Similarity Level : {RISK_ICONS[risk]}")
    ln(f"  {LINE}")

    # obfuscation
    if flags:
        ln()
        ln("  ALTERATIONS DETECTED")
        for f in flags:
            label = OBFUSCATION_LABELS.get(f, f)
            ln(f"    •  {label}")
        ln()
        ln(f"  {LINE}")

    # matching sections
    ln()
    count = len(evidence)
    if count == 0:
        ln("  No significant matching sections found.")
    else:
        ln(f"  MATCHING SECTIONS  ({count} found)")
        ln()
        for i, block in enumerate(evidence, 1):
            strength = block.get("match_strength", "low")
            file_a   = block.get("file_a", "?")
            file_b   = block.get("file_b", "?")
            la       = block.get("lines_a", [0, 0])
            lb       = block.get("lines_b", [0, 0])
            code_a   = block.get("code_a", "")
            code_b   = block.get("code_b", "")

            ln(f"  [{i}]  Match Strength : {STRENGTH_ICONS.get(strength, strength.upper())}")
            ln(f"       File A  →  {file_a}  (lines {la[0]} – {la[1]})")
            ln(f"       File B  →  {file_b}  (lines {lb[0]} – {lb[1]})")
            ln()

            if code_a:
                ln("       ── Submission A " + "─" * 32)
                for code_line in code_a.splitlines():
                    ln(f"       {code_line}")
            ln()

            if code_b:
                ln("       ── Submission B " + "─" * 32)
                for code_line in code_b.splitlines():
                    ln(f"       {code_line}")
            ln()

            if i < count:
                ln(f"  {'─' * 48}")
                ln()

    # footer
    ln(f"  {LINE}")
    ln(f"  Engine v{result.get('engine_version', '?')}")
    ln()

    return "\n".join(lines)


def save_report(result: dict, path: str) -> None:
    text = format_report(result)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Report saved to: {path}")
