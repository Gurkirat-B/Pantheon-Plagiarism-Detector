"""
format_output.py

Formatters to convert the new detailed backend output to old formats.
"""


def convert_to_old_format(result):
    """
    Converts new backend output format to old simple format.
    
    New format has:
    {
        'engine_version': '3.0.0',
        'scores': {'jaccard': ..., 'dice': ..., 'containment': ..., 'weighted_final': ...},
        'source_code_a': '...',
        'source_code_b': '...',
        'line_mapping': [...],
        ...
    }
    
    Old format expected:
    {
        'submission_a': 'filename',
        'submission_b': 'filename',
        'similarity_score': 0.95,
        'obfuscation_flags': ['identifier_renaming'],
        'evidence': [...]
    }
    """
    
    # Extract fields from new format
    submission_a = result.get("submission_a", "A")
    submission_b = result.get("submission_b", "B")
    
    # Get similarity score from scores dict, use weighted_final
    scores = result.get("scores", {})
    similarity_score = scores.get("weighted_final", 0.0)
    
    # Get obfuscation flags
    obfuscation_flags = result.get("obfuscation_flags", [])
    
    # Get evidence blocks
    evidence = result.get("evidence", [])
    
    # Return in old format
    return {
        "submission_a": submission_a,
        "submission_b": submission_b,
        "similarity_score": similarity_score,
        "obfuscation_flags": obfuscation_flags,
        "evidence": evidence,
    }


def format_report_for_backend(result):
    """
    Format the new backend result as a human-readable text report.
    Clean, simple format without special characters.
    """
    lines = []
    
    # Get data from result
    submission_a = result.get("submission_a", "A")
    submission_b = result.get("submission_b", "B")
    language = result.get("language_detected", "unknown").upper()
    scores = result.get("scores", {})
    similarity_score = scores.get("weighted_final", 0.0)
    obfuscation_flags = result.get("obfuscation_flags", [])
    evidence = result.get("evidence", [])
    
    # Format percentage and risk level
    pct = f"{round(similarity_score * 100, 1)}%"
    if similarity_score >= 0.85:
        risk = "CRITICAL"
    elif similarity_score >= 0.65:
        risk = "HIGH"
    elif similarity_score >= 0.40:
        risk = "MEDIUM"
    else:
        risk = "LOW"
    
    # Header
    lines.append("")
    lines.append("PANTHEON SIMILARITY REPORT")
    lines.append("-" * 60)
    lines.append("")
    lines.append(f"Assignment   : -")
    lines.append(f"Submission A : {submission_a}")
    lines.append(f"Submission B : {submission_b}")
    lines.append(f"Language     : {language}")
    lines.append("")
    lines.append("-" * 60)
    lines.append(f"Overall Score : {pct}")
    lines.append(f"Similarity Level : {risk}")
    lines.append("-" * 60)
    
    # Obfuscation flags
    if obfuscation_flags:
        lines.append("")
        lines.append("ALTERATIONS DETECTED:")
        flag_labels = {
            "identifier_renaming":  "Variable / identifier renaming detected",
            "loop_type_swap":       "Loop type swap detected (for <> while)",
            "literal_substitution": "Constant / literal values substituted",
            "dead_code_insertion":  "Dead code insertion detected",
            "code_reordering":      "Code block reordering detected",
            "switch_to_ifelse":     "Switch <> if-else conversion detected",
            "ternary_to_ifelse":    "Ternary <> if-else conversion detected",
        }
        for flag in obfuscation_flags:
            label = flag_labels.get(flag, flag)
            lines.append(f"  - {label}")
        lines.append("-" * 60)
    
    # Matching sections
    lines.append("")
    if not evidence:
        lines.append("No matching code sections found.")
    else:
        lines.append(f"MATCHING SECTIONS ({len(evidence)} found)")
        lines.append("")
        
        for i, block in enumerate(evidence, 1):
            file_a = block.get("file_a", "File A")
            file_b = block.get("file_b", "File B")
            lines_a = block.get("lines_a", [1, 1])
            lines_b = block.get("lines_b", [1, 1])
            code_a = block.get("code_a", "")
            code_b = block.get("code_b", "")
            match_strength = block.get("match_strength", "medium").upper()
            
            lines.append(f"[{i}] Match Strength: {match_strength}")
            lines.append(f"    File A -> {file_a} (lines {lines_a[0]} - {lines_a[1]})")
            lines.append(f"    File B -> {file_b} (lines {lines_b[0]} - {lines_b[1]})")
            lines.append("")
            
            # Code A
            lines.append("    Submission A:")
            if code_a:
                for code_line in code_a.split('\n'):
                    lines.append(f"      {code_line}")
            else:
                lines.append("      (no code)")
            lines.append("")
            
            # Code B
            lines.append("    Submission B:")
            if code_b:
                for code_line in code_b.split('\n'):
                    lines.append(f"      {code_line}")
            else:
                lines.append("      (no code)")
            lines.append("")
            lines.append("-" * 60)
    
    # Footer
    lines.append("")
    lines.append("Engine v3.0.0")
    lines.append("")
    
    return "\n".join(lines)


def format_report_text(result):
    """
    Alias for format_report_for_backend for backwards compatibility.
    """
    return format_report_for_backend(result)
