"""
Lexer / tokenizer for source code.

Produces a stream of Token objects from canonical text.
Two modes:
  - normalize_ids=True:  all non-keyword identifiers → "ID"
  - normalize_ids=False: keep actual identifier names (for obfuscation detection)

Similarly for literals:
  - normalize_literals=True:  strings → "STR", numbers → "NUM", chars → "CHR"
  - normalize_literals=False: keep actual literal values

The token's .line field tracks position in canonical text for evidence mapping.
"""

import re
from dataclasses import dataclass
from typing import List, Set

@dataclass(frozen=True)
class Token:
    text: str
    line: int


# ─── Keyword Sets ───────────────────────────────────────────────────

JAVA_KW: Set[str] = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch",
    "char", "class", "const", "continue", "default", "do", "double",
    "else", "enum", "extends", "final", "finally", "float", "for",
    "goto", "if", "implements", "import", "instanceof", "int", "interface",
    "long", "native", "new", "package", "private", "protected", "public",
    "return", "short", "static", "strictfp", "super", "switch",
    "synchronized", "this", "throw", "throws", "transient", "try",
    "void", "volatile", "while", "true", "false", "null",
    "var", "record", "sealed", "permits", "yield",
}

C_KW: Set[str] = {
    "auto", "break", "case", "char", "const", "continue", "default",
    "do", "double", "else", "enum", "extern", "float", "for", "goto",
    "if", "inline", "int", "long", "register", "restrict", "return",
    "short", "signed", "sizeof", "static", "struct", "switch", "typedef",
    "union", "unsigned", "void", "volatile", "while",
}

CPP_KW: Set[str] = C_KW | {
    "alignas", "alignof", "and", "and_eq", "asm", "bitand", "bitor",
    "bool", "catch", "class", "compl", "concept", "consteval",
    "constexpr", "constinit", "co_await", "co_return", "co_yield",
    "decltype", "delete", "explicit", "export", "false", "friend",
    "mutable", "namespace", "new", "noexcept", "not", "not_eq",
    "nullptr", "operator", "or", "or_eq", "override", "private",
    "protected", "public", "requires", "static_assert", "static_cast",
    "dynamic_cast", "reinterpret_cast", "const_cast", "template",
    "this", "thread_local", "throw", "true", "try", "typeid", "typename",
    "using", "virtual", "wchar_t", "xor", "xor_eq",
}

PYTHON_KW: Set[str] = {
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else",
    "except", "finally", "for", "from", "global", "if", "import",
    "in", "is", "lambda", "nonlocal", "not", "or", "pass", "raise",
    "return", "try", "while", "with", "yield",
}

JS_KW: Set[str] = {
    "abstract", "arguments", "async", "await", "boolean", "break", "byte",
    "case", "catch", "char", "class", "const", "continue", "debugger",
    "default", "delete", "do", "double", "else", "enum", "export",
    "extends", "false", "final", "finally", "float", "for", "function",
    "goto", "if", "implements", "import", "in", "instanceof", "int",
    "interface", "let", "long", "native", "new", "null", "of",
    "package", "private", "protected", "public", "return", "short",
    "static", "super", "switch", "synchronized", "this", "throw",
    "throws", "transient", "true", "try", "typeof", "undefined",
    "var", "void", "volatile", "while", "with", "yield",
}

GO_KW: Set[str] = {
    "break", "case", "chan", "const", "continue", "default", "defer",
    "else", "fallthrough", "for", "func", "go", "goto", "if",
    "import", "interface", "map", "package", "range", "return",
    "select", "struct", "switch", "type", "var",
    "true", "false", "nil",
}

RUST_KW: Set[str] = {
    "as", "async", "await", "break", "const", "continue", "crate",
    "dyn", "else", "enum", "extern", "false", "fn", "for", "if",
    "impl", "in", "let", "loop", "match", "mod", "move", "mut",
    "pub", "ref", "return", "self", "Self", "static", "struct",
    "super", "trait", "true", "type", "unsafe", "use", "where", "while",
}

# ─── Operators ──────────────────────────────────────────────────────

_OPS = sorted({
    "==", "!=", ">=", "<=", "&&", "||", "++", "--", "+=", "-=",
    "*=", "/=", "%=", "->", "::", "<<", ">>", "<<=", ">>=",
    "&=", "|=", "^=", "...", "?:", "=>", "**",
    "&", "|", "^", "~", "!", "+", "-", "*", "/", "%",
    "=", ">", "<", "?", ":", ".", ",", ";",
    "(", ")", "{", "}", "[", "]", "@",
}, key=len, reverse=True)

# ─── Regex Patterns ─────────────────────────────────────────────────

_re_whitespace = re.compile(r"[ \t\r]+")
_re_identifier = re.compile(r"[A-Za-z_\$][A-Za-z0-9_\$]*")
_re_hex        = re.compile(r"0[xX][0-9a-fA-F]+[lLuU]*")
_re_binary     = re.compile(r"0[bB][01]+[lLuU]*")
_re_octal      = re.compile(r"0[oO]?[0-7]+[lLuU]*")
_re_float      = re.compile(r"\d+\.\d*([eE][+-]?\d+)?[fFdD]?|\d+[eE][+-]?\d+[fFdD]?|\.\d+([eE][+-]?\d+)?[fFdD]?")
_re_int        = re.compile(r"\d+[lLuU]*")
_re_string     = re.compile(r'"([^"\\]|\\.)*"')
_re_char       = re.compile(r"'([^'\\]|\\.)*'")
_re_textblock  = re.compile(r'""".*?"""', re.DOTALL)
_re_raw_string = re.compile(r'R"([^(]*)\(.*?\)\1"', re.DOTALL)  # C++ raw strings
_re_fstring    = re.compile(r'f"([^"\\]|\\.)*"')  # Python f-strings (simplified)
_re_backtick   = re.compile(r'`([^`\\]|\\.)*`')  # JS template literals (simplified)


def _kw_set(lang: str) -> Set[str]:
    lang = (lang or "mixed").lower()
    if lang == "java":
        return JAVA_KW
    if lang == "c":
        return C_KW
    if lang in ("cpp", "c_or_cpp"):
        return CPP_KW
    if lang == "python":
        return PYTHON_KW
    if lang in ("javascript", "typescript"):
        return JS_KW
    if lang == "go":
        return GO_KW
    if lang == "rust":
        return RUST_KW
    # mixed: union of all
    return JAVA_KW | CPP_KW | PYTHON_KW | JS_KW | GO_KW | RUST_KW


# ─── Semantic Token Normalization ───────────────────────────────────

# Loop keywords: all map to "LOOP" in normalized mode so for↔while↔do swaps
# still produce matching k-grams. Only affects tok_norm — tok_raw is unchanged
# so detect.py can still identify which loop construct was actually used.
_LOOP_KEYWORDS = {"for", "while", "do", "loop"}  # "loop" for Rust

# Access modifiers — noise for algorithm comparison
_ACCESS_KEYWORDS = {
    "public", "private", "protected", "internal",
    "static", "final", "const", "constexpr",
    "abstract", "virtual", "override",
    "synchronized", "volatile", "transient",
    "inline", "extern", "register",
    "pub", "mut",  # Rust
}


def tokenize(text: str,
             lang: str = "mixed",
             normalize_ids: bool = True,
             normalize_literals: bool = True,
             normalize_access: bool = True) -> List[Token]:
    """
    Converts source text into a token stream.

    normalize_ids:     all non-keyword identifiers → "ID"
    normalize_literals: strings/numbers/chars → "STR"/"NUM"/"CHR"
    normalize_access:  strip access modifiers (public/private/static/final etc.)
                       since they don't affect algorithm logic
    """
    kws = _kw_set(lang)
    tokens: List[Token] = []
    i = 0
    n = len(text)
    line = 1

    def emit(t: str):
        tokens.append(Token(text=t, line=line))

    while i < n:
        ch = text[i]

        # newline
        if ch == "\n":
            line += 1
            i += 1
            continue

        # whitespace
        if ch in " \t\r":
            m = _re_whitespace.match(text, i)
            i = m.end()
            continue

        # skip file separator headers from canonicalize
        if text.startswith("# --- ", i):
            while i < n and text[i] != "\n":
                i += 1
            continue

        # Python comments that survived (shouldn't happen, but safety net)
        if ch == "#" and lang in ("python", "ruby"):
            while i < n and text[i] != "\n":
                i += 1
            continue

        # C++ raw strings: R"delim(...)delim"
        m = _re_raw_string.match(text, i)
        if m:
            emit("STR" if normalize_literals else m.group(0))
            for c in m.group(0):
                if c == "\n":
                    line += 1
            i = m.end()
            continue

        # Java text blocks
        m = _re_textblock.match(text, i)
        if m:
            emit("STR" if normalize_literals else m.group(0))
            for c in m.group(0):
                if c == "\n":
                    line += 1
            i = m.end()
            continue

        # JS template literals
        m = _re_backtick.match(text, i)
        if m:
            emit("STR" if normalize_literals else m.group(0))
            for c in m.group(0):
                if c == "\n":
                    line += 1
            i = m.end()
            continue

        # string literal
        m = _re_string.match(text, i)
        if m:
            emit("STR" if normalize_literals else m.group(0))
            i = m.end()
            continue

        # char literal
        m = _re_char.match(text, i)
        if m:
            emit("CHR" if normalize_literals else m.group(0))
            i = m.end()
            continue

        # hex number
        m = _re_hex.match(text, i)
        if m:
            emit("NUM" if normalize_literals else m.group(0))
            i = m.end()
            continue

        # binary number
        m = _re_binary.match(text, i)
        if m:
            emit("NUM" if normalize_literals else m.group(0))
            i = m.end()
            continue

        # float (check before int)
        m = _re_float.match(text, i)
        if m:
            emit("NUM" if normalize_literals else m.group(0))
            i = m.end()
            continue

        # integer
        m = _re_int.match(text, i)
        if m:
            emit("NUM" if normalize_literals else m.group(0))
            i = m.end()
            continue

        # identifier or keyword
        m = _re_identifier.match(text, i)
        if m:
            word = m.group(0)
            if word in kws:
                # normalize access modifiers to nothing — they're noise
                if normalize_access and word in _ACCESS_KEYWORDS:
                    i = m.end()
                    continue
                # normalize all loop constructs to LOOP so for↔while↔do swaps
                # still produce matching k-grams (only in normalized mode)
                if normalize_ids and word in _LOOP_KEYWORDS:
                    emit("LOOP")
                else:
                    emit(word)
            else:
                emit("ID" if normalize_ids else word)
            i = m.end()
            continue

        # operators (greedy, longest match first)
        matched = False
        for op in _OPS:
            if text.startswith(op, i):
                emit(op)
                i += len(op)
                matched = True
                break
        if matched:
            continue

        # skip anything else
        i += 1

    return tokens
