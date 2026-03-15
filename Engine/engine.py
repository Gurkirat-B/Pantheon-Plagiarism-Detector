"""
Pantheon Engine v3 — Code Similarity Detection

100% custom. Zero external libraries. Only Python builtins.

Pipeline:
    1. Read source files (from ZIP or single files)
    2. Concatenate all source into one blob
    3. Strip all comments
    4. Filter out boilerplate (stdlib imports, package declarations)
    5. Tokenize (normalize identifiers and literals)
    6. Build k-gram fingerprints using winnowing
    7. Compare fingerprint sets → single similarity score
    8. Trace matching fingerprints back to original source lines
    9. Output report with full matching code shown side by side
"""

import os
import re
import zipfile
import shutil
import tempfile
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════
# SECTION 1: FILE INGESTION
# ═══════════════════════════════════════════════════════════════════

ALLOWED_EXTENSIONS = {".java", ".c", ".cpp", ".cc", ".h", ".hpp", ".py", ".js"}

MAX_ZIP_FILES = 5000
MAX_DECOMPRESSED_BYTES = 500 * 1024 * 1024  # 500 MB


def extract_submission(path, work_dir):
    """
    Takes a file path (ZIP or single source file) and returns a list
    of source file paths ready for processing.

    If ZIP: extracts safely, then finds all source files inside.
    If single source file: copies to work_dir.

    Returns: list of Path objects pointing to source files.
    """
    path = Path(path).resolve()
    work_dir = Path(work_dir)
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    ext = path.suffix.lower()

    if ext == ".zip":
        return _extract_zip(path, work_dir)
    elif ext in ALLOWED_EXTENSIONS:
        dest = work_dir / path.name
        shutil.copy2(path, dest)
        return [dest]
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _extract_zip(zip_path, dest, depth=0):
    """
    Safely extract a ZIP file. Handles:
    - Path traversal attacks (../../etc/passwd)
    - ZIP bombs (checks decompressed size)
    - Nested ZIPs (recursively extracts up to depth 3)
    - Symlinks (skipped)
    - macOS junk files (__MACOSX, .DS_Store)
    """
    if depth > 3:
        return []

    try:
        zf = zipfile.ZipFile(zip_path, "r")
    except zipfile.BadZipFile:
        raise ValueError(f"Corrupt ZIP file: {zip_path}")

    entries = zf.infolist()

    if len(entries) > MAX_ZIP_FILES:
        zf.close()
        raise ValueError(f"ZIP has too many files: {len(entries)}")

    total_size = sum(e.file_size for e in entries)
    if total_size > MAX_DECOMPRESSED_BYTES:
        zf.close()
        raise ValueError(f"ZIP decompressed size too large: {total_size} bytes")

    dest.mkdir(parents=True, exist_ok=True)
    dest_str = str(dest.resolve())
    nested_zips = []

    for entry in entries:
        if entry.is_dir():
            continue
        if "__MACOSX" in entry.filename or ".DS_Store" in entry.filename:
            continue

        # sanitize path — block traversal attacks
        clean_name = entry.filename.replace("\\", "/")
        parts = [p for p in clean_name.split("/") if p not in ("", ".", "..")]
        if not parts:
            continue
        clean_name = "/".join(parts)

        out_path = (dest / clean_name).resolve()
        if not str(out_path).startswith(dest_str):
            continue  # path traversal — skip

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(entry) as src:
            with open(out_path, "wb") as dst:
                dst.write(src.read())

        if out_path.suffix.lower() == ".zip":
            nested_zips.append(out_path)

    zf.close()

    # recursively extract nested ZIPs
    for nested in nested_zips:
        try:
            _extract_zip(nested, nested.parent / nested.stem, depth + 1)
        except Exception:
            pass
        nested.unlink(missing_ok=True)

    # collect all source files
    found = []
    for p in dest.rglob("*"):
        if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS:
            found.append(p)

    if not found:
        raise ValueError("ZIP contained no supported source files")

    return sorted(found, key=lambda p: str(p).lower())


# ═══════════════════════════════════════════════════════════════════
# SECTION 2: COMMENT STRIPPING
# ═══════════════════════════════════════════════════════════════════

def strip_comments(text):
    """
    Remove all comments from source code.

    Handles:
    - C/C++/Java line comments (//)
    - C/C++/Java block comments (/* ... */)
    - Python hash comments (#)
    - Preprocessor directives (#include, #define)

    Preserves line count by keeping newlines so source mapping stays accurate.
    Does NOT strip comment-like chars inside string or char literals.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # strip BOM
    if text.startswith("\ufeff"):
        text = text[1:]

    result = []
    i = 0
    n = len(text)
    in_string = False
    in_char = False
    in_line_comment = False
    in_block_comment = False
    escaped = False

    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
                result.append("\n")
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
            else:
                if ch == "\n":
                    result.append("\n")
                i += 1
            continue

        if in_string:
            result.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        if in_char:
            result.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "'":
                in_char = False
            i += 1
            continue

        # preprocessor directives
        if ch == "#":
            line_start = ""
            j = len(result) - 1
            while j >= 0 and result[j] != "\n":
                line_start = result[j] + line_start
                j -= 1
            if line_start.strip() == "":
                while i < n and text[i] != "\n":
                    i += 1
                continue

        if ch == '"':
            in_string = True
            result.append(ch)
            i += 1
            continue

        if ch == "'":
            in_char = True
            result.append(ch)
            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue

        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue

        if ch == "#":
            while i < n and text[i] != "\n":
                i += 1
            continue

        result.append(ch)
        i += 1

    return "".join(result)


# ═══════════════════════════════════════════════════════════════════
# SECTION 3: BOILERPLATE FILTERING
# ═══════════════════════════════════════════════════════════════════

JAVA_STDLIB = (
    "java.lang.", "java.util.", "java.io.", "java.nio.", "java.net.",
    "java.math.", "java.text.", "java.time.", "java.awt.", "javax.swing.",
    "java.sql.", "javafx.",
)

C_STDLIB = {
    "stdio.h", "stdlib.h", "string.h", "math.h", "ctype.h", "time.h",
    "assert.h", "limits.h", "stdint.h", "stdbool.h", "stdarg.h",
    "iostream", "fstream", "sstream", "string", "vector", "list", "map",
    "set", "unordered_map", "unordered_set", "queue", "stack", "deque",
    "array", "algorithm", "numeric", "functional", "memory", "utility",
    "cmath", "cstring", "cstdlib", "cstdio", "climits", "cassert",
    "bits/stdc++.h",
}

_java_import_re = re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+(?:\.\*)?)\s*;", re.MULTILINE)
_java_package_re = re.compile(r"^\s*package\s+[\w.]+\s*;", re.MULTILINE)
_c_include_re = re.compile(r'^\s*#\s*include\s*[<"]([\w./]+)[>"]', re.MULTILINE)
_python_import_re = re.compile(r"^\s*(?:import\s+[\w., ]+|from\s+\w+\s+import\s+.+)\s*$", re.MULTILINE)


def filter_boilerplate(text):
    """
    Remove standard library imports and package declarations.
    Every student has these identically — not meaningful for comparison.
    """
    text = _java_package_re.sub("", text)

    def check_java_import(match):
        pkg = match.group(1)
        for prefix in JAVA_STDLIB:
            if pkg.startswith(prefix):
                return ""
        return match.group(0)
    text = _java_import_re.sub(check_java_import, text)

    def check_c_include(match):
        header = match.group(1).strip()
        bare = header.split("/")[-1]
        if header in C_STDLIB or bare in C_STDLIB:
            return ""
        return match.group(0)
    text = _c_include_re.sub(check_c_include, text)

    text = _python_import_re.sub("", text)
    return text


# ═══════════════════════════════════════════════════════════════════
# SECTION 4: CONCATENATION + SOURCE MAP
# ═══════════════════════════════════════════════════════════════════

def concatenate_files(source_files):
    """
    Read all source files, strip comments and boilerplate,
    concatenate into one string.

    Also builds a source_map to trace any line back to its original file.

    Returns: (concatenated_text, source_map)
    source_map: list of (canon_start, canon_end, filename, orig_start)
    """
    parts = []
    source_map = []
    current_line = 1

    for src_file in source_files:
        try:
            raw = src_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        cleaned = strip_comments(raw)
        cleaned = filter_boilerplate(cleaned)
        cleaned = _collapse_blanks(cleaned)

        lines = cleaned.splitlines()
        if not lines:
            continue

        source_map.append((
            current_line,
            current_line + len(lines) - 1,
            src_file.name,
            1,
        ))

        parts.append(cleaned)
        if not cleaned.endswith("\n"):
            parts.append("\n")
        current_line += len(lines) + 1

    return "\n".join(parts) if parts else "", source_map


def _collapse_blanks(text):
    """Collapse 3+ consecutive blank lines to 1."""
    lines = text.split("\n")
    out = []
    blank_count = 0
    for line in lines:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= 1:
                out.append(line)
        else:
            blank_count = 0
            out.append(line)
    return "\n".join(out)


# ═══════════════════════════════════════════════════════════════════
# SECTION 5: TOKENIZER
# ═══════════════════════════════════════════════════════════════════

ALL_KEYWORDS = {
    # Java
    "abstract", "assert", "boolean", "break", "byte", "case", "catch",
    "char", "class", "const", "continue", "default", "do", "double",
    "else", "enum", "extends", "final", "finally", "float", "for",
    "goto", "if", "implements", "import", "instanceof", "int", "interface",
    "long", "native", "new", "package", "private", "protected", "public",
    "return", "short", "static", "strictfp", "super", "switch",
    "synchronized", "this", "throw", "throws", "transient", "try",
    "void", "volatile", "while", "true", "false", "null",
    # C/C++
    "auto", "register", "extern", "unsigned", "signed", "sizeof",
    "struct", "union", "typedef", "inline", "restrict",
    "bool", "namespace", "template", "typename", "using", "virtual",
    "delete", "friend", "mutable", "operator", "override",
    "nullptr", "constexpr",
    # Python
    "def", "lambda", "yield", "pass", "raise", "with", "as",
    "global", "nonlocal", "async", "await", "elif", "except",
    "and", "or", "not", "in", "is", "None", "True", "False",
}

ACCESS_MODIFIERS = {
    "public", "private", "protected", "static", "final", "abstract",
    "synchronized", "volatile", "transient", "native", "strictfp",
    "virtual", "override", "inline", "extern", "register", "const",
    "constexpr", "mutable",
}

OPERATORS = sorted([
    "==", "!=", ">=", "<=", "&&", "||", "++", "--", "+=", "-=",
    "*=", "/=", "%=", "->", "::", "<<", ">>",
    "&", "|", "^", "~", "!", "+", "-", "*", "/", "%",
    "=", ">", "<", "?", ":", ".", ",", ";",
    "(", ")", "{", "}", "[", "]",
], key=len, reverse=True)

_re_whitespace = re.compile(r"[ \t\r]+")
_re_identifier = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
_re_hex = re.compile(r"0[xX][0-9a-fA-F]+[lLuU]*")
_re_float = re.compile(r"\d+\.\d*([eE][+-]?\d+)?[fFdD]?|\d+[eE][+-]?\d+[fFdD]?")
_re_int = re.compile(r"\d+[lLuU]*")
_re_string = re.compile(r'"([^"\\]|\\.)*"')
_re_char = re.compile(r"'([^'\\]|\\.)*'")


def tokenize(text, normalize=True):
    """
    Convert source text into a list of (token_text, line_number) tuples.

    When normalize=True:
      - Non-keyword identifiers → "ID" (renaming doesn't matter)
      - String literals → "STR"
      - Numbers → "NUM"
      - Char literals → "CHR"
      - Access modifiers (public/private/static) → SKIPPED

    When normalize=False:
      - Everything kept as-is (for obfuscation detection)
    """
    tokens = []
    i = 0
    n = len(text)
    line = 1

    while i < n:
        ch = text[i]

        if ch == "\n":
            line += 1
            i += 1
            continue

        if ch in " \t\r":
            m = _re_whitespace.match(text, i)
            i = m.end()
            continue

        m = _re_string.match(text, i)
        if m:
            tokens.append(("STR" if normalize else m.group(0), line))
            i = m.end()
            continue

        m = _re_char.match(text, i)
        if m:
            tokens.append(("CHR" if normalize else m.group(0), line))
            i = m.end()
            continue

        m = _re_hex.match(text, i)
        if m:
            tokens.append(("NUM" if normalize else m.group(0), line))
            i = m.end()
            continue

        m = _re_float.match(text, i)
        if m:
            tokens.append(("NUM" if normalize else m.group(0), line))
            i = m.end()
            continue

        m = _re_int.match(text, i)
        if m:
            tokens.append(("NUM" if normalize else m.group(0), line))
            i = m.end()
            continue

        m = _re_identifier.match(text, i)
        if m:
            word = m.group(0)
            if word in ALL_KEYWORDS:
                if normalize and word in ACCESS_MODIFIERS:
                    i = m.end()
                    continue
                tokens.append((word, line))
            else:
                tokens.append(("ID" if normalize else word, line))
            i = m.end()
            continue

        matched = False
        for op in OPERATORS:
            if text[i:i+len(op)] == op:
                tokens.append((op, line))
                i += len(op)
                matched = True
                break
        if matched:
            continue

        i += 1

    return tokens


# ═══════════════════════════════════════════════════════════════════
# SECTION 6: FINGERPRINTING (K-GRAMS + WINNOWING)
# ═══════════════════════════════════════════════════════════════════

HASH_BASE = 31
HASH_MOD = (1 << 61) - 1


def _hash_kgram(token_texts):
    """Polynomial rolling hash for a sequence of token strings."""
    h = 0
    for t in token_texts:
        for ch in t:
            h = (h * HASH_BASE + ord(ch)) % HASH_MOD
        h = (h * HASH_BASE + 0x7F) % HASH_MOD
    return h


def build_fingerprints(tokens, k=8):
    """
    Build k-gram fingerprints. Slides a window of size k across tokens.
    Returns: dict mapping hash → [list of starting positions]
    """
    texts = [t[0] for t in tokens]
    if len(texts) < k:
        return {}

    fingerprints = {}
    for i in range(len(texts) - k + 1):
        h = _hash_kgram(texts[i:i+k])
        if h not in fingerprints:
            fingerprints[h] = []
        fingerprints[h].append(i)

    return fingerprints


def winnow(tokens, k=8, window=4):
    """
    Winnowing — selects representative subset of fingerprints.
    Guarantees: shared sequence of k+window-1 = 11 tokens WILL be caught.
    Reduces fingerprint count by ~75% without losing detection power.
    """
    texts = [t[0] for t in tokens]
    if len(texts) < k:
        return {}

    all_hashes = []
    for i in range(len(texts) - k + 1):
        h = _hash_kgram(texts[i:i+k])
        all_hashes.append((i, h))

    if len(all_hashes) < window:
        return build_fingerprints(tokens, k)

    selected = {}
    prev_pos = -1

    for w in range(len(all_hashes) - window + 1):
        w_slice = all_hashes[w:w+window]
        min_hash = min(h for _, h in w_slice)
        min_pos = max(pos for pos, h in w_slice if h == min_hash)

        if min_pos != prev_pos:
            if min_hash not in selected:
                selected[min_hash] = []
            selected[min_hash].append(min_pos)
            prev_pos = min_pos

    return selected


# ═══════════════════════════════════════════════════════════════════
# SECTION 7: SIMILARITY SCORING
# ═══════════════════════════════════════════════════════════════════

def compute_similarity(fp_a, fp_b):
    """
    Compute a single similarity score between two fingerprint sets.

    Uses a weighted blend of:
      - Jaccard:     |A∩B| / |A∪B|  (overall structural overlap)
      - Containment: |A∩B| / min(|A|,|B|)  (catches partial copying)

    Containment weighted higher because partial copying is the most
    common cheating pattern — student copies the hard part but writes
    their own boilerplate.

    Returns: float from 0.0 to 1.0
    """
    a = set(fp_a.keys())
    b = set(fp_b.keys())

    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0

    intersection = len(a & b)
    union = len(a | b)
    smaller = min(len(a), len(b))

    jaccard = intersection / union
    containment = intersection / smaller

    # weighted: 40% jaccard + 60% containment
    return round(0.40 * jaccard + 0.60 * containment, 4)


# ═══════════════════════════════════════════════════════════════════
# SECTION 8: EVIDENCE — FIND THE MATCHING LINES
# ═══════════════════════════════════════════════════════════════════

def find_matching_regions(fp_a, fp_b, tokens_a, tokens_b, source_map_a,
                          source_map_b, files_a, files_b, k=8):
    """
    For every shared fingerprint, trace it back to original source files
    and extract the FULL matching code blocks.

    Groups nearby matches so instructor sees "lines 10-25" not 15 tiny fragments.

    Returns list of match blocks with full code from both sides.
    """
    shared_hashes = set(fp_a.keys()) & set(fp_b.keys())
    if not shared_hashes:
        return []

    # collect all matching line positions
    raw_matches = []
    for h in shared_hashes:
        for pos_a in fp_a[h]:
            for pos_b in fp_b[h]:
                a_start = tokens_a[pos_a][1]
                a_end = tokens_a[min(pos_a + k - 1, len(tokens_a) - 1)][1]
                b_start = tokens_b[pos_b][1]
                b_end = tokens_b[min(pos_b + k - 1, len(tokens_b) - 1)][1]
                raw_matches.append((a_start, a_end, b_start, b_end))

    if not raw_matches:
        return []

    raw_matches.sort()

    # merge matches within 3 lines of each other
    merged = [raw_matches[0]]
    for a1, a2, b1, b2 in raw_matches[1:]:
        pa1, pa2, pb1, pb2 = merged[-1]
        if a1 <= pa2 + 3 and b1 <= pb2 + 3:
            merged[-1] = (pa1, max(pa2, a2), pb1, max(pb2, b2))
        else:
            merged.append((a1, a2, b1, b2))

    # load source files for code extraction
    file_cache = {}
    for f in files_a + files_b:
        try:
            file_cache[str(f)] = f.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            file_cache[str(f)] = []

    evidence = []
    for a1, a2, b1, b2 in merged:
        file_a, orig_a1, orig_a2 = _map_to_source(a1, a2, source_map_a)
        file_b, orig_b1, orig_b2 = _map_to_source(b1, b2, source_map_b)

        code_a = _extract_lines(file_cache, files_a, file_a, orig_a1, orig_a2)
        code_b = _extract_lines(file_cache, files_b, file_b, orig_b1, orig_b2)

        # classify by how many lines match
        span = max(orig_a2 - orig_a1, orig_b2 - orig_b1) + 1
        if span >= 12:
            strength = "high"
        elif span >= 5:
            strength = "medium"
        else:
            strength = "low"

        evidence.append({
            "file_a": file_a,
            "lines_a": [orig_a1, orig_a2],
            "code_a": code_a,
            "file_b": file_b,
            "lines_b": [orig_b1, orig_b2],
            "code_b": code_b,
            "strength": strength,
        })

    # strongest first
    strength_order = {"high": 0, "medium": 1, "low": 2}
    evidence.sort(key=lambda e: strength_order.get(e["strength"], 3))

    return evidence


def _map_to_source(canon_start, canon_end, source_map):
    """Map canonical line numbers back to original file + line."""
    for (cs, ce, filename, orig_start) in source_map:
        if cs <= canon_start <= ce:
            offset_start = canon_start - cs
            offset_end = canon_end - cs
            return filename, orig_start + offset_start, orig_start + offset_end
    return "unknown", canon_start, canon_end


def _extract_lines(file_cache, file_list, filename, start, end):
    """Pull lines start..end from the original file."""
    for f in file_list:
        if f.name == filename:
            lines = file_cache.get(str(f), [])
            s = max(0, start - 1)
            e = min(len(lines), end)
            return "\n".join(lines[s:e])
    return ""


# ═══════════════════════════════════════════════════════════════════
# SECTION 9: OBFUSCATION DETECTION
# ═══════════════════════════════════════════════════════════════════

def detect_obfuscation(tokens_a_raw, tokens_b_raw, tokens_a_norm, tokens_b_norm,
                       fp_a, fp_b):
    """
    Compare normalized vs raw tokens to detect cheating tactics.
    If normalized score >> raw score → student renamed variables.
    """
    flags = []

    fp_a_raw = build_fingerprints(tokens_a_raw, k=8)
    fp_b_raw = build_fingerprints(tokens_b_raw, k=8)

    a_raw = set(fp_a_raw.keys())
    b_raw = set(fp_b_raw.keys())
    a_norm = set(fp_a.keys())
    b_norm = set(fp_b.keys())

    raw_j = len(a_raw & b_raw) / max(len(a_raw | b_raw), 1)
    norm_j = len(a_norm & b_norm) / max(len(a_norm | b_norm), 1)

    if norm_j - raw_j > 0.12 and norm_j > 0.3:
        flags.append("identifier_renaming")

    # loop type swap
    a_for = sum(1 for t, _ in tokens_a_raw if t == "for")
    a_while = sum(1 for t, _ in tokens_a_raw if t == "while")
    b_for = sum(1 for t, _ in tokens_b_raw if t == "for")
    b_while = sum(1 for t, _ in tokens_b_raw if t == "while")
    a_total = a_for + a_while
    b_total = b_for + b_while
    if a_total > 0 and b_total > 0 and norm_j > 0.3:
        a_ratio = a_for / a_total
        b_ratio = b_for / b_total
        if abs(a_ratio - b_ratio) > 0.6:
            flags.append("loop_type_swap")

    # literal substitution
    a_lits = set(t for t, _ in tokens_a_raw if t.startswith('"') or t.startswith("'") or t[0:1].isdigit())
    b_lits = set(t for t, _ in tokens_b_raw if t.startswith('"') or t.startswith("'") or t[0:1].isdigit())
    if a_lits and b_lits:
        shared = a_lits & b_lits
        total = a_lits | b_lits
        if total and len(shared) / len(total) < 0.3 and norm_j > 0.4:
            flags.append("literal_substitution")

    # dead code insertion
    len_a = len(tokens_a_norm)
    len_b = len(tokens_b_norm)
    ratio = max(len_a, len_b) / max(min(len_a, len_b), 1)
    if ratio > 1.4 and norm_j > 0.45:
        flags.append("dead_code_insertion")

    return flags


# ═══════════════════════════════════════════════════════════════════
# SECTION 10: REPORT GENERATION
# ═══════════════════════════════════════════════════════════════════

def format_report(result):
    """
    Produce a clean human-readable report with:
    - Single similarity score (no Jaccard/Dice/Containment breakdown)
    - Full matching code side by side
    """
    lines = []
    ln = lines.append

    score = result["similarity_score"]
    pct = f"{round(score * 100, 1)}%"

    sep = "━" * 56

    ln("")
    ln("  PANTHEON SIMILARITY REPORT")
    ln(f"  {sep}")
    ln("")
    ln(f"  Submission A : {result['submission_a']}")
    ln(f"  Submission B : {result['submission_b']}")
    ln("")
    ln(f"  {sep}")
    ln(f"  Similarity Score : {pct}")
    ln(f"  {sep}")

    # obfuscation flags
    flags = result.get("obfuscation_flags", [])
    flag_labels = {
        "identifier_renaming":  "Variable / identifier renaming detected",
        "loop_type_swap":       "Loop type swap detected (for ↔ while)",
        "literal_substitution": "Constant / literal values changed",
        "dead_code_insertion":  "Dead code insertion detected",
    }
    if flags:
        ln("")
        ln("  OBFUSCATION DETECTED")
        for f in flags:
            ln(f"    •  {flag_labels.get(f, f)}")
        ln(f"  {sep}")

    # matching sections with full code
    evidence = result.get("evidence", [])
    ln("")
    if not evidence:
        ln("  No matching code sections found.")
    else:
        ln(f"  MATCHING CODE SECTIONS  ({len(evidence)} found)")

        for i, block in enumerate(evidence, 1):
            ln("")
            ln(f"  {'─' * 56}")
            ln(f"  Match {i}")
            ln("")

            file_a = block["file_a"]
            file_b = block["file_b"]
            la = block["lines_a"]
            lb = block["lines_b"]
            code_a = block["code_a"]
            code_b = block["code_b"]

            # submission A code
            ln(f"  Submission A — {file_a} (lines {la[0]}–{la[1]})")
            ln(f"  {'─' * 56}")
            if code_a:
                for line_num, code_line in enumerate(code_a.splitlines(), la[0]):
                    ln(f"    {line_num:4d} │ {code_line}")
            else:
                ln("    (no code)")
            ln("")

            # submission B code
            ln(f"  Submission B — {file_b} (lines {lb[0]}–{lb[1]})")
            ln(f"  {'─' * 56}")
            if code_b:
                for line_num, code_line in enumerate(code_b.splitlines(), lb[0]):
                    ln(f"    {line_num:4d} │ {code_line}")
            else:
                ln("    (no code)")

    ln("")
    ln(f"  {sep}")
    ln("  Engine v3.0.0")
    ln("")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# SECTION 11: MAIN COMPARE FUNCTION
# ═══════════════════════════════════════════════════════════════════

def compare(path_a, path_b):
    """
    Compare two submissions end-to-end.

    path_a, path_b: paths to ZIP files or single source files.

    Returns a result dict with:
      - similarity_score (single float 0.0–1.0)
      - obfuscation_flags (list of detected tricks)
      - evidence (list of matching code blocks with full source)
    """
    path_a = Path(path_a).resolve()
    path_b = Path(path_b).resolve()

    tmp = tempfile.mkdtemp(prefix="pantheon_")
    work_a = Path(tmp) / "A"
    work_b = Path(tmp) / "B"

    try:
        # step 1: extract files
        files_a = extract_submission(path_a, work_a)
        files_b = extract_submission(path_b, work_b)

        # step 2: concatenate + strip comments + filter boilerplate
        text_a, source_map_a = concatenate_files(files_a)
        text_b, source_map_b = concatenate_files(files_b)

        # step 3: tokenize (normalized for comparison)
        tokens_a_norm = tokenize(text_a, normalize=True)
        tokens_b_norm = tokenize(text_b, normalize=True)

        # step 3b: tokenize (raw for obfuscation detection)
        tokens_a_raw = tokenize(text_a, normalize=False)
        tokens_b_raw = tokenize(text_b, normalize=False)

        # step 4: fingerprint using winnowing
        fp_a = winnow(tokens_a_norm, k=8, window=4)
        fp_b = winnow(tokens_b_norm, k=8, window=4)

        # step 5: compute single similarity score
        similarity = compute_similarity(fp_a, fp_b)

        # step 6: find matching lines with full code
        evidence = find_matching_regions(
            fp_a, fp_b, tokens_a_norm, tokens_b_norm,
            source_map_a, source_map_b, files_a, files_b, k=8,
        )

        # step 7: detect obfuscation
        obfuscation = detect_obfuscation(
            tokens_a_raw, tokens_b_raw,
            tokens_a_norm, tokens_b_norm,
            fp_a, fp_b,
        )

        return {
            "submission_a": path_a.name,
            "submission_b": path_b.name,
            "similarity_score": similarity,
            "obfuscation_flags": obfuscation,
            "evidence": evidence,
        }

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
