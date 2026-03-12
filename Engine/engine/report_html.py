"""
engine/report_html.py

Generate interactive HTML reports with side-by-side code comparison
and visual highlighting of similar lines.
"""

from typing import Dict, List, Optional
from datetime import datetime


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    if not text:
        return ""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))


def format_report_html(result: Dict) -> str:
    """
    Generate an interactive HTML report with side-by-side code comparison
    and line-level similarity highlighting.
    
    Expected result structure:
    {
        "assignment_id": "...",
        "submission_a": "...",
        "submission_b": "...",
        "language_detected": "java",
        "weighted_final": 0.92,
        "obfuscation_flags": [...],
        "engine_version": "3.0.0",
        "source_code_a": "full source code",
        "source_code_b": "full source code",
        "line_mapping": [
            {"line_a": 10, "line_b": 15, "score": 92.0, "color": "red", ...},
            ...
        ],
        "evidence": [...existing evidence blocks...],
    }
    """
    
    assignment = result.get("assignment_id", "—")
    sub_a = result.get("submission_a", "A")
    sub_b = result.get("submission_b", "B")
    language = (result.get("language_detected") or "unknown").upper()
    score = result.get("weighted_final", 0.0)
    flags = result.get("obfuscation_flags", [])
    version = result.get("engine_version", "3.0.0")
    
    # Get source code and line mapping
    source_a = result.get("source_code_a", "")
    source_b = result.get("source_code_b", "")
    line_mapping = result.get("line_mapping", [])
    
    lines_a = source_a.splitlines() if source_a else []
    lines_b = source_b.splitlines() if source_b else []
    
    # Create a lookup for line colors
    line_colors_a: Dict[int, str] = {}
    line_colors_b: Dict[int, str] = {}
    for mapping in line_mapping:
        if mapping["color"] != "none":
            line_colors_a[mapping["line_a"]] = mapping["color"]
            line_colors_b[mapping["line_b"]] = mapping["color"]
    
    obfuscation_labels = {
        "identifier_renaming":  "Variable / identifier renaming detected",
        "loop_type_swap":       "Loop type swap detected (for ↔ while)",
        "literal_substitution": "Constant / literal values substituted",
        "dead_code_insertion":  "Dead code insertion detected",
        "code_reordering":      "Code block reordering detected",
        "switch_to_ifelse":     "Switch ↔ if-else conversion detected",
        "ternary_to_ifelse":    "Ternary ↔ if-else conversion detected",
    }
    
    # Start building HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pantheon Similarity Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-bottom: 3px solid #764ba2;
        }}
        
        .header h1 {{
            font-size: 28px;
            margin-bottom: 15px;
        }}
        
        .header-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            font-size: 14px;
        }}
        
        .header-item {{
            display: flex;
            flex-direction: column;
        }}
        
        .header-label {{
            font-weight: 600;
            opacity: 0.9;
        }}
        
        .header-value {{
            font-family: "Courier New", monospace;
            margin-top: 4px;
        }}
        
        .score-box {{
            background: rgba(255,255,255,0.1);
            padding: 10px 15px;
            border-radius: 4px;
            font-size: 20px;
            font-weight: bold;
        }}
        
        .section {{
            border-top: 1px solid #e0e0e0;
            padding: 25px 30px;
        }}
        
        .section h2 {{
            font-size: 18px;
            margin-bottom: 15px;
            color: #667eea;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .flags-list {{
            list-style: none;
            padding-left: 20px;
        }}
        
        .flags-list li {{
            margin: 8px 0;
            padding-left: 20px;
            position: relative;
        }}
        
        .flags-list li:before {{
            content: "●";
            position: absolute;
            left: 0;
            color: #ff6b6b;
        }}
        
        .code-comparison {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 15px;
        }}
        
        .code-panel {{
            border: 1px solid #ddd;
            border-radius: 4px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }}
        
        .code-title {{
            background: #f8f9fa;
            padding: 10px 15px;
            font-weight: 600;
            font-size: 13px;
            border-bottom: 1px solid #ddd;
            color: #555;
        }}
        
        .code-content {{
            overflow-x: auto;
            flex: 1;
            background: #fafafa;
        }}
        
        .code-table {{
            width: 100%;
            border-collapse: collapse;
            font-family: "Courier New", monospace;
            font-size: 12px;
            line-height: 1.5;
        }}
        
        .code-table tbody tr {{
            border-bottom: 1px solid #eee;
            height: 24px;
        }}
        
        .code-table tbody tr:hover {{
            background: #e8f4f8;
        }}
        
        .code-table td {{
            padding: 2px 10px;
            vertical-align: top;
        }}
        
        .line-num {{
            background: #f0f0f0;
            color: #666;
            user-select: none;
            width: 50px;
            text-align: right;
            border-right: 1px solid #ddd;
        }}
        
        .code-line {{
            white-space: pre-wrap;
            word-break: break-word;
            padding-left: 10px;
        }}
        
        .line-match-red {{
            background: #ffcccc;
        }}
        
        .line-match-yellow {{
            background: #ffffcc;
        }}
        
        .info-box {{
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 15px;
            border-radius: 2px;
            margin-bottom: 15px;
            font-size: 13px;
        }}
        
        .info-box strong {{
            color: #1976d2;
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 15px 30px;
            border-top: 1px solid #e0e0e0;
            text-align: center;
            font-size: 12px;
            color: #666;
        }}
        
        .legend {{
            display: flex;
            gap: 30px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
        }}
        
        .legend-box {{
            width: 20px;
            height: 20px;
            border-radius: 2px;
            border: 1px solid #999;
        }}
        
        .legend-red {{
            background: #ffcccc;
        }}
        
        .legend-yellow {{
            background: #ffffcc;
        }}
        
        .match-info {{
            font-size: 11px;
            color: #666;
            margin-top: 4px;
        }}
        
        @media (max-width: 1200px) {{
            .code-comparison {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>Pantheon Similarity Report</h1>
            <div class="header-grid">
                <div class="header-item">
                    <span class="header-label">Assignment</span>
                    <span class="header-value">{escape_html(assignment)}</span>
                </div>
                <div class="header-item">
                    <span class="header-label">Submission A</span>
                    <span class="header-value">{escape_html(sub_a)}</span>
                </div>
                <div class="header-item">
                    <span class="header-label">Submission B</span>
                    <span class="header-value">{escape_html(sub_b)}</span>
                </div>
                <div class="header-item">
                    <span class="header-label">Language</span>
                    <span class="header-value">{language}</span>
                </div>
                <div class="header-item">
                    <span class="header-label">Similarity Score</span>
                    <div class="score-box">{score*100:.1f}%</div>
                </div>
            </div>
        </div>
        
        <!-- Alterations Section -->
"""
    
    if flags:
        html += """        <div class="section">
            <h2>Alterations Detected</h2>
            <ul class="flags-list">
"""
        for flag in flags:
            label = obfuscation_labels.get(flag, flag)
            html += f"                <li>{escape_html(label)}</li>\n"
        html += """            </ul>
        </div>
"""
    
    # Code Comparison Section
    html += """        <div class="section">
            <h2>Side-by-Side Code Comparison</h2>
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-box legend-red"></div>
                    <span>High Similarity (≥75%)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-box legend-yellow"></div>
                    <span>Medium Similarity (40-74%)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-box"></div>
                    <span>No Match</span>
                </div>
            </div>
            
            <div class="code-comparison">
"""
    
    # Submission A
    html += f"""                <div class="code-panel">
                    <div class="code-title">Submission A: {escape_html(sub_a)}</div>
                    <div class="code-content">
                        <table class="code-table">
                            <tbody>
"""
    
    for i, line in enumerate(lines_a, 1):
        color_class = ""
        if i in line_colors_a:
            color_class = f"line-match-{line_colors_a[i]}"
        
        html += f"""                                <tr class="{color_class}">
                                    <td class="line-num">{i}</td>
                                    <td class="code-line">{escape_html(line)}</td>
                                </tr>
"""
    
    html += """                            </tbody>
                        </table>
                    </div>
                </div>
"""
    
    # Submission B
    html += f"""                <div class="code-panel">
                    <div class="code-title">Submission B: {escape_html(sub_b)}</div>
                    <div class="code-content">
                        <table class="code-table">
                            <tbody>
"""
    
    for i, line in enumerate(lines_b, 1):
        color_class = ""
        if i in line_colors_b:
            color_class = f"line-match-{line_colors_b[i]}"
        
        html += f"""                                <tr class="{color_class}">
                                    <td class="line-num">{i}</td>
                                    <td class="code-line">{escape_html(line)}</td>
                                </tr>
"""
    
    html += """                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
"""
    
    # Add match details
    if line_mapping:
        html += """        <div class="section">
            <h2>Line Mapping Details</h2>
            <div class="info-box">
                <strong>Total matches:</strong> """ + str(len(line_mapping)) + """ lines
            </div>
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <thead style="background: #f0f0f0; font-weight: 600;">
                    <tr>
                        <td style="padding: 10px; border-bottom: 2px solid #ccc;">Line A</td>
                        <td style="padding: 10px; border-bottom: 2px solid #ccc;">Line B</td>
                        <td style="padding: 10px; border-bottom: 2px solid #ccc;">Similarity</td>
                        <td style="padding: 10px; border-bottom: 2px solid #ccc;">Match Type</td>
                    </tr>
                </thead>
                <tbody>
"""
        
        for mapping in line_mapping:
            color = mapping["color"]
            score = mapping["score"]
            line_a = mapping["line_a"]
            line_b = mapping["line_b"]
            
            match_type = "High" if color == "red" else "Medium" if color == "yellow" else "Low"
            color_bg = "ffcccc" if color == "red" else "ffffcc"
            
            html += f"""                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px;">{line_a}</td>
                        <td style="padding: 10px;">{line_b}</td>
                        <td style="padding: 10px; background: #{color_bg}; font-weight: 600;">{score}%</td>
                        <td style="padding: 10px;">{match_type}</td>
                    </tr>
"""
        
        html += """                </tbody>
            </table>
        </div>
"""
    
    # Footer
    html += f"""        <div class="footer">
            Pantheon Similarity Engine v{escape_html(version)} | Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>
"""
    
    return html
