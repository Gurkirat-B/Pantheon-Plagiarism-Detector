"""
Strip comments from source code.

Handles:
- C/C++/Java line comments (//)
- C/C++/Java block comments (/* */)
- Python/Ruby hash comments (#)
- Python triple-quote docstrings (''' and \""")
- Preserves line count (replaces comment content with empty lines) for source mapping
- Preserves comment-like patterns inside string and char literals
- Strips C/C++ preprocessor directives (#include, #define, #pragma)
  only for C-family languages (not Python, where # is a comment)
"""

def strip_comments(text: str, lang: str = "mixed") -> str:
    """
    Remove comments from source code.

    lang: 'java', 'c', 'cpp', 'python', 'ruby', 'javascript', 'typescript',
          'csharp', 'go', 'rust', 'mixed'
    """
    # normalize line endings first
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # strip BOM if present
    if text.startswith("\ufeff"):
        text = text[1:]
    if text.startswith("\xef\xbb\xbf"):
        text = text[3:]

    lang = (lang or "mixed").lower()

    if lang == "python":
        return _strip_python(text)
    elif lang == "ruby":
        return _strip_ruby(text)
    else:
        return _strip_c_family(text, lang)


def _strip_c_family(text: str, lang: str) -> str:
    """
    Strip comments from C-family languages (C, C++, Java, JavaScript, etc).
    Also strips preprocessor directives for C/C++ since those are noise.
    """
    is_c_cpp = lang in ("c", "cpp", "c_or_cpp", "mixed")

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

        # -- inside line comment --
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
                result.append("\n")
            i += 1
            continue

        # -- inside block comment --
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
            else:
                if ch == "\n":
                    result.append("\n")
                i += 1
            continue

        # -- inside string literal --
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

        # -- inside char literal --
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

        # -- preprocessor directives for C/C++ --
        if is_c_cpp and ch == "#":
            # check if at start of logical line
            pos = len(result)
            line_so_far = ""
            j = pos - 1
            while j >= 0 and result[j] != "\n":
                line_so_far = result[j] + line_so_far
                j -= 1
            if line_so_far.strip() == "":
                # preprocessor line — skip to end, handling backslash continuation
                while i < n and text[i] != "\n":
                    if text[i] == "\\" and i + 1 < n and text[i + 1] == "\n":
                        result.append("\n")
                        i += 2
                        continue
                    i += 1
                continue

        # -- opening a string --
        if ch == '"':
            in_string = True
            result.append(ch)
            i += 1
            continue

        # -- opening a char literal --
        if ch == "'" and not in_string:
            in_char = True
            result.append(ch)
            i += 1
            continue

        # -- line comment --
        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue

        # -- block comment --
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue

        result.append(ch)
        i += 1

    return "".join(result)


def _strip_python(text: str) -> str:
    """
    Strip Python comments and docstrings.
    - # line comments
    - Triple-quoted strings used as docstrings (''' and \""")
    """
    result = []
    i = 0
    n = len(text)
    in_string_single = False
    in_string_double = False
    in_triple_single = False
    in_triple_double = False
    escaped = False

    while i < n:
        ch = text[i]

        # inside triple-double-quoted string
        if in_triple_double:
            if ch == "\n":
                result.append("\n")
            if not escaped and text[i:i+3] == '"""':
                in_triple_double = False
                i += 3
            else:
                escaped = (ch == "\\" and not escaped)
                i += 1
            continue

        # inside triple-single-quoted string
        if in_triple_single:
            if ch == "\n":
                result.append("\n")
            if not escaped and text[i:i+3] == "'''":
                in_triple_single = False
                i += 3
            else:
                escaped = (ch == "\\" and not escaped)
                i += 1
            continue

        # inside single-quoted string
        if in_string_single:
            result.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "'":
                in_string_single = False
            i += 1
            continue

        # inside double-quoted string
        if in_string_double:
            result.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string_double = False
            i += 1
            continue

        # triple-quoted strings / docstrings — strip them (they're noise)
        if text[i:i+3] == '"""':
            in_triple_double = True
            i += 3
            continue
        if text[i:i+3] == "'''":
            in_triple_single = True
            i += 3
            continue

        # hash comment
        if ch == "#":
            while i < n and text[i] != "\n":
                i += 1
            continue

        # opening a string
        if ch == '"':
            in_string_double = True
            result.append(ch)
            i += 1
            continue
        if ch == "'":
            in_string_single = True
            result.append(ch)
            i += 1
            continue

        result.append(ch)
        i += 1

    return "".join(result)


def _strip_ruby(text: str) -> str:
    """Strip Ruby comments: # line comments and =begin/=end block comments."""
    lines = text.split("\n")
    out = []
    in_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("=begin"):
            in_block = True
            out.append("")
            continue
        if stripped.startswith("=end"):
            in_block = False
            out.append("")
            continue
        if in_block:
            out.append("")
            continue
        # strip inline # comments (but not inside strings)
        result = []
        in_str_d = False
        in_str_s = False
        esc = False
        for c in line:
            if esc:
                result.append(c)
                esc = False
                continue
            if c == "\\" and (in_str_d or in_str_s):
                result.append(c)
                esc = True
                continue
            if c == '"' and not in_str_s:
                in_str_d = not in_str_d
                result.append(c)
                continue
            if c == "'" and not in_str_d:
                in_str_s = not in_str_s
                result.append(c)
                continue
            if c == "#" and not in_str_d and not in_str_s:
                break
            result.append(c)
        out.append("".join(result))
    return "\n".join(out)
