"""
This file reads source code as plain text and breaks it into a list of tokens —
the individual meaningful pieces like keywords, variable names, operators, and
literals. Each token also records which line of the original file it came from,
so we can trace matches back to specific lines later.

When normalizing (the default mode), variable names become "ID", numbers become
"NUM", strings become "STR", and loop keywords (for/while/do) all become "LOOP".
This lets us compare the structure of two programs without caring about what
the variables are called or what values are used.
"""

import re
from dataclasses import dataclass
from typing import List, Set

@dataclass(frozen=True)
class Token:
    text: str
    line: int


# Reserved keywords for each supported language. These are kept as-is during
# normalization because they define the structure of the code, not the content.

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

# Operators sorted longest-first so we always match the longest valid operator
# at any given position (e.g. <<= before << before <).
_OPS = sorted({
    "==", "!=", ">=", "<=", "&&", "||", "++", "--", "+=", "-=",
    "*=", "/=", "%=", "->", "::", "<<", ">>", "<<=", ">>=",
    "&=", "|=", "^=", "...", "?:", "=>", "**",
    "&", "|", "^", "~", "!", "+", "-", "*", "/", "%",
    "=", ">", "<", "?", ":", ".", ",", ";",
    "(", ")", "{", "}", "[", "]", "@",
}, key=len, reverse=True)

# Regular expressions for recognizing each kind of token in the source text.
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
_re_raw_string = re.compile(r'R"([^(]*)\(.*?\)\1"', re.DOTALL)
_re_fstring    = re.compile(r'f"([^"\\]|\\.)*"')
_re_backtick   = re.compile(r'`([^`\\]|\\.)*`')


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
    return JAVA_KW | CPP_KW | PYTHON_KW | JS_KW | GO_KW | RUST_KW


# In normalized mode, all loop keywords collapse to the same token "LOOP" so that
# a for-loop and a while-loop doing the same thing produce matching fingerprints.
# The raw token stream is left unchanged so the obfuscation detector can still
# see which loop construct was actually written.
_LOOP_KEYWORDS = {"for", "while", "do", "loop"}  # "loop" is a keyword in Rust

# Access modifiers like public/private/static don't affect what an algorithm does,
# only who can call it. We drop them in normalized mode to avoid false negatives
# when one student wrote `public void sort()` and another wrote `void sort()`.
_ACCESS_KEYWORDS = {
    "public", "private", "protected", "internal",
    "static", "final", "const", "constexpr",
    "abstract", "virtual", "override",
    "synchronized", "volatile", "transient",
    "inline", "extern", "register",
    "pub", "mut",
}

# Students often swap primitive types to make copied code look different — using
# long instead of int, or double instead of float. In normalized mode we collapse
# all of these to "TYPE" so the swap doesn't break fingerprint matching.
_TYPE_KEYWORDS = {
    "int", "long", "short", "byte", "float", "double", "char", "boolean",
    "void", "unsigned", "signed",
    "ArrayList", "LinkedList", "HashMap", "HashSet", "TreeMap", "TreeSet",
    "LinkedHashMap", "LinkedHashSet", "ArrayDeque", "PriorityQueue",
    "List", "Map", "Set", "Queue", "Deque", "Collection", "Iterator",
    "Exception", "RuntimeException", "IllegalArgumentException",
    "NullPointerException", "IndexOutOfBoundsException",
    "IllegalStateException", "UnsupportedOperationException",
    "IOException", "ArithmeticException",
    "vector", "list", "map", "set", "unordered_map", "unordered_set",
    "deque", "queue", "stack", "pair", "string", "wstring",
    "int", "float", "str", "bool", "list", "dict", "set", "tuple",
}


def tokenize(text: str,
             lang: str = "mixed",
             normalize_ids: bool = True,
             normalize_literals: bool = True,
             normalize_access: bool = True) -> List[Token]:
    """
    Reads through source code character by character and produces a list of tokens.
    Each token records its text and the line number it came from in the source.

    When normalize_ids is True, every variable and function name becomes "ID".
    When normalize_literals is True, every number becomes "NUM" and every string
    becomes "STR". This makes structurally identical code produce identical token
    sequences even when the variable names and values differ.
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

        if ch == "\n":
            line += 1
            i += 1
            continue

        if ch in " \t\r":
            m = _re_whitespace.match(text, i)
            i = m.end()
            continue

        if text.startswith("# --- ", i):  # file separator inserted by canonicalize, skip it
            while i < n and text[i] != "\n":
                i += 1
            continue

        if ch == "#" and lang in ("python", "ruby"):  # hash comments that survived stripping
            while i < n and text[i] != "\n":
                i += 1
            continue

        m = _re_raw_string.match(text, i)  # C++ raw strings: R"delim(content)delim"
        if m:
            emit("STR" if normalize_literals else m.group(0))
            for c in m.group(0):
                if c == "\n":
                    line += 1
            i = m.end()
            continue

        m = _re_textblock.match(text, i)  # Java text blocks: """..."""
        if m:
            emit("STR" if normalize_literals else m.group(0))
            for c in m.group(0):
                if c == "\n":
                    line += 1
            i = m.end()
            continue

        m = _re_backtick.match(text, i)  # JavaScript template literals: `...`
        if m:
            emit("STR" if normalize_literals else m.group(0))
            for c in m.group(0):
                if c == "\n":
                    line += 1
            i = m.end()
            continue

        m = _re_string.match(text, i)
        if m:
            emit("STR" if normalize_literals else m.group(0))
            i = m.end()
            continue

        m = _re_char.match(text, i)
        if m:
            emit("CHR" if normalize_literals else m.group(0))
            i = m.end()
            continue

        m = _re_hex.match(text, i)
        if m:
            emit("NUM" if normalize_literals else m.group(0))
            i = m.end()
            continue

        m = _re_binary.match(text, i)
        if m:
            emit("NUM" if normalize_literals else m.group(0))
            i = m.end()
            continue

        m = _re_float.match(text, i)  # must be checked before int to avoid consuming "3" from "3.14"
        if m:
            emit("NUM" if normalize_literals else m.group(0))
            i = m.end()
            continue

        m = _re_int.match(text, i)
        if m:
            emit("NUM" if normalize_literals else m.group(0))
            i = m.end()
            continue

        m = _re_identifier.match(text, i)
        if m:
            word = m.group(0)
            if word in kws:
                if normalize_access and word in _ACCESS_KEYWORDS:
                    i = m.end()
                    continue
                if normalize_ids and word in _LOOP_KEYWORDS:
                    emit("LOOP")
                else:
                    emit(word)
            else:
                if normalize_ids and word in _TYPE_KEYWORDS:
                    emit("TYPE")
                else:
                    emit("ID" if normalize_ids else word)
            i = m.end()
            continue

        matched = False  # try each operator pattern, longest first
        for op in _OPS:
            if text.startswith(op, i):
                emit(op)
                i += len(op)
                matched = True
                break
        if matched:
            continue

        i += 1  # skip any character we don't recognize

    return tokens
