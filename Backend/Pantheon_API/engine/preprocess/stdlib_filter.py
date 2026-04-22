"""
This file removes standard boilerplate that every student writes just because
the language requires it — things like import statements, package declarations,
and #include lines. Since every submission has these, matching on them would
produce false positives. We blank out those lines (replace with empty string)
rather than deleting them so that all the line numbers in the file stay the same.

There are two stages of filtering. The first stage (filter_boilerplate) runs
during canonicalization and removes things like imports and annotations from
the text that gets fingerprinted. The second stage (blank_output_boilerplate)
removes I/O calls and main() declarations — those are kept visible in the
display view so instructors can see the full code, but excluded from fingerprinting
because they appear identically in almost every student submission.
"""

import re


# All standard Java package prefixes. Imports from these are automatically
# removed because every student uses them — they don't indicate copying.
JAVA_STDLIB_PREFIXES = (
    "java.lang.", "java.util.", "java.io.", "java.nio.", "java.net.",
    "java.math.", "java.text.", "java.time.", "java.awt.", "java.swing.",
    "javax.swing.", "javax.servlet.", "javax.xml.", "javax.crypto.",
    "java.applet.", "java.beans.", "java.security.", "java.sql.",
    "javafx.", "org.junit.", "org.hamcrest.",
)

JAVA_BOILERPLATE_ANNOTATIONS = {
    "@Override", "@SuppressWarnings", "@Deprecated",
    "@FunctionalInterface", "@SafeVarargs",
}

# We use [ \t]* instead of \s* at the start and end of each pattern because \s
# also matches newline characters. With re.MULTILINE, using \s* would cause the
# regex to greedily consume the blank line before a match and delete it entirely
# rather than just replacing the matched line with an empty string.
_java_import_re  = re.compile(r"^[ \t]*import[ \t]+(?:static[ \t]+)?([\w.]+(?:\.\*)?)\s*;", re.MULTILINE)
_java_package_re = re.compile(r"^[ \t]*package[ \t]+[\w.]+\s*;", re.MULTILINE)
_java_annotation_boilerplate_re = re.compile(
    r"^[ \t]*@(Override|SuppressWarnings|Deprecated|FunctionalInterface|SafeVarargs)\b.*$",
    re.MULTILINE,
)

# Only blank System.out/err calls whose entire argument is a plain string literal
# or empty — these are pure labels like System.out.println("--- Results ---")
# that appear in nearly every submission and carry no algorithmic content.
# Calls that include variables (System.out.println("In-order: " + tree.inOrder()))
# are kept because: (a) if the professor included them in a template they will be
# removed by template fingerprint subtraction, and (b) if a student added them
# independently and another student has the exact same call, that is genuine
# evidence of copying.
_java_sysout_re = re.compile(
    r"^[ \t]*System\s*\.\s*(?:out|err)\s*\.\s*\w+\s*\(\s*(?:\"[^\"]*\"|\'[^\']*\'|)\s*\);[ \t]*$",
    re.MULTILINE,
)

# Common Scanner input calls. After normalization these collapse to ID.ID()
# which matches across any program that reads input, regardless of what it reads.
_java_scanner_re = re.compile(
    r"^[ \t]*(?:\w+\s*=\s*)?\w+\s*\.\s*next(?:Line|Int|Double|Float|Long|Short|Byte|Boolean)?\s*\(\s*\);[ \t]*$",
    re.MULTILINE,
)

_java_main_re = re.compile(
    r"^[ \t]*(?:public[ \t]+|private[ \t]+|protected[ \t]+)?(?:static[ \t]+)?void[ \t]+main[ \t]*"
    r"\([ \t]*String[ \t]*(?:\[[ \t]*\]|\[[ \t]*\])[ \t]*\w*[ \t]*\)"
    r"[ \t]*(?:throws[ \t]+[\w\t ,]+?)?[ \t]*\{?[ \t]*$",
    re.MULTILINE,
)

_java_null_guard_re = re.compile(
    r"^[ \t]*if\s*\(\s*\w+\s*==\s*null\s*\)\s*return(?:\s+(?:null|false|true|0|-1|0\.0))?\s*;[ \t]*$",
    re.MULTILINE,
)

_java_this_assign_re = re.compile(
    r"^[ \t]*this\s*\.\s*\w+\s*=\s*\w+\s*;[ \t]*$",
    re.MULTILINE,
)


def filter_java_boilerplate(text: str) -> str:
    # System.out calls and main() are handled separately by blank_output_boilerplate
    # so they still appear in the display view shown to instructors.
    text = _java_package_re.sub("", text)
    text = _java_annotation_boilerplate_re.sub("", text)

    def _should_strip_import(match):
        pkg = match.group(1)
        for prefix in JAVA_STDLIB_PREFIXES:
            if pkg.startswith(prefix) or pkg == prefix.rstrip("."):
                return ""
        if pkg.endswith(".*"):
            base = pkg[:-2]
            for prefix in JAVA_STDLIB_PREFIXES:
                if base.startswith(prefix.rstrip(".")):
                    return ""
        return match.group(0)

    text = _java_import_re.sub(_should_strip_import, text)
    return text


# Standard C and C++ library headers. #include lines for these are removed
# because they appear in virtually every C/C++ submission.
C_STDLIB_HEADERS = {
    "stdio.h", "stdlib.h", "string.h", "math.h", "ctype.h",
    "time.h", "assert.h", "limits.h", "float.h", "stddef.h",
    "stdint.h", "stdbool.h", "stdarg.h", "errno.h", "signal.h",
    "setjmp.h", "locale.h", "complex.h", "fenv.h", "inttypes.h",
    "iso646.h", "wchar.h", "wctype.h", "tgmath.h",
    "iostream", "fstream", "sstream", "string", "vector",
    "list", "map", "set", "unordered_map", "unordered_set",
    "queue", "stack", "deque", "array", "tuple", "pair",
    "algorithm", "numeric", "functional", "iterator",
    "memory", "utility", "typeinfo", "type_traits",
    "exception", "stdexcept", "cassert", "cmath", "cstring",
    "cstdlib", "cstdio", "ctime", "climits", "cctype",
    "chrono", "thread", "mutex", "condition_variable", "future",
    "regex", "random", "ratio", "atomic", "bitset",
    "initializer_list", "any", "optional", "variant", "filesystem",
    "bits/stdc++.h", "windows.h", "pthread.h",
    "iomanip", "ios", "iosfwd", "ostream", "istream", "streambuf",
}

_c_include_re = re.compile(r"^[ \t]*#[ \t]*include[ \t]*[<\"]([\w./]+)[>\"]", re.MULTILINE)
_c_pragma_re  = re.compile(r"^[ \t]*#[ \t]*pragma[ \t]+once[ \t]*$", re.MULTILINE)
_c_define_guard_re = re.compile(
    r"^[ \t]*#[ \t]*(?:ifndef|define|endif)[ \t]+\w+_H(?:PP|XX)?[ \t]*(?://.*)?$",
    re.MULTILINE,
)

# Blank scanf/input calls entirely — they carry no algorithmic content and
# always normalize to the same token sequence regardless of which variable is read.
# For printf/cout: only blank pure-string-literal or empty calls (same logic as Java).
_c_stdio_re = re.compile(
    r"^[ \t]*(?:scanf|fscanf|sscanf|gets|fgets|getchar|getc|fflush)\s*\(.*\);[ \t]*$"
    r"|^[ \t]*(?:printf|fprintf|sprintf|snprintf|puts|fputs|perror|putchar|putc|vprintf|vfprintf)"
    r"\s*\(\s*(?:\"[^\"]*\"|\'[^\']*\'|stderr\s*,\s*\"[^\"]*\"|stdout\s*,\s*\"[^\"]*\"|)\s*\);[ \t]*$",
    re.MULTILINE,
)

_cpp_stream_cin_re = re.compile(
    r"^[ \t]*(?:std\s*::\s*)?(?:cin|clog)\s*>>.*;[ \t]*$",
    re.MULTILINE,
)
# Only blank cout/cerr chains that contain no variables — purely string/endl output.
_cpp_stream_re = re.compile(
    r"^[ \t]*(?:std\s*::\s*)?(?:cout|cerr|clog)\s*<<\s*"
    r"(?:(?:\"[^\"]*\"|\'[^\']*\'|std\s*::\s*endl|endl|\"\\n\"|\s*)\s*(?:<<\s*(?:\"[^\"]*\"|\'[^\']*\'|std\s*::\s*endl|endl|\"\\n\"|\s*))*)\s*;[ \t]*$",
    re.MULTILINE,
)

_cpp_using_ns_re = re.compile(
    r"^[ \t]*using[ \t]+namespace[ \t]+\w+\s*;[ \t]*$",
    re.MULTILINE,
)

_c_main_re = re.compile(
    r"^[ \t]*(?:int|void)[ \t]+main[ \t]*\([^{;\n]*\)[ \t]*\{?[ \t]*$",
    re.MULTILINE,
)

_c_null_guard_re = re.compile(
    r"^[ \t]*if\s*\(\s*\w+\s*==\s*NULL\s*\)\s*return(?:\s+(?:NULL|false|true|0|-1))?\s*;[ \t]*$",
    re.MULTILINE,
)


def filter_c_boilerplate(text: str) -> str:
    # I/O calls, stream statements, and main() are handled separately by
    # blank_output_boilerplate so they remain visible in the display view.
    def _should_strip_include(match):
        header = match.group(1).strip()
        bare = header.split("/")[-1]
        if header in C_STDLIB_HEADERS or bare in C_STDLIB_HEADERS:
            return ""
        return match.group(0)

    text = _c_include_re.sub(_should_strip_include, text)
    text = _c_pragma_re.sub("", text)
    text = _c_define_guard_re.sub("", text)
    return text


PYTHON_STDLIB_MODULES = {
    "os", "sys", "re", "math", "random", "time", "datetime",
    "collections", "itertools", "functools", "operator",
    "json", "csv", "io", "pathlib", "shutil", "glob",
    "typing", "abc", "copy", "enum", "dataclasses",
    "unittest", "pytest", "doctest",
    "string", "textwrap", "struct", "array",
    "heapq", "bisect", "queue", "threading", "multiprocessing",
    "subprocess", "socket", "http", "urllib", "hashlib",
    "logging", "argparse", "configparser", "pprint",
    "pickle", "shelve", "sqlite3",
}

_python_import_re = re.compile(
    r"^[ \t]*(?:from[ \t]+([\w.]+)[ \t]+import[ \t]+.*|import[ \t]+([\w., ]+))[ \t]*$",
    re.MULTILINE,
)

# Blank all print() and input() calls — after normalization they collapse to
# the same token sequence across any two programs that do terminal I/O.
_python_print_re = re.compile(
    r"^[ \t]*print\s*\(.*\)[ \t]*$",
    re.MULTILINE,
)
_python_input_re = re.compile(
    r"^[ \t]*(?:\w+\s*=\s*)?input\s*\(.*\)[ \t]*$",
    re.MULTILINE,
)


def filter_python_boilerplate(text: str) -> str:
    def _should_strip(match):
        from_mod = match.group(1)
        import_mods = match.group(2)

        if from_mod:
            root = from_mod.split(".")[0]
            if root in PYTHON_STDLIB_MODULES:
                return ""
        elif import_mods:
            mods = [m.strip().split(".")[0] for m in import_mods.split(",")]
            if all(m in PYTHON_STDLIB_MODULES for m in mods):
                return ""
        return match.group(0)

    text = _python_import_re.sub(_should_strip, text)
    text = re.sub(r'^\s*if\s+__name__\s*==\s*["\']__main__["\']\s*:\s*$', "", text, flags=re.MULTILINE)
    return text


_js_import_re = re.compile(
    r"^\s*import\s+.*\s+from\s+['\"]([^'\"]+)['\"];?\s*$",
    re.MULTILINE,
)
_js_require_re = re.compile(
    r"^\s*(?:const|let|var)\s+\w+\s*=\s*require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)\s*;?\s*$",
    re.MULTILINE,
)

JS_STDLIB_MODULES = {"fs", "path", "http", "https", "os", "util", "stream", "events"}

_js_console_re = re.compile(
    r"^[ \t]*console\s*\.\s*(?:log|warn|error|info|debug)\s*\(.*\);?[ \t]*$",
    re.MULTILINE,
)


def filter_js_boilerplate(text: str) -> str:
    def _strip_import(match):
        mod = match.group(1)
        if mod in JS_STDLIB_MODULES or mod.startswith("node:"):
            return ""
        return match.group(0)

    text = _js_import_re.sub(_strip_import, text)
    text = _js_require_re.sub(_strip_import, text)
    return text


def filter_boilerplate(text: str, lang: str) -> str:
    """Routes to the language-specific filter based on the detected language."""
    lang = (lang or "mixed").lower()

    if lang == "java":
        return filter_java_boilerplate(text)
    if lang in ("c", "cpp", "c_or_cpp"):
        return filter_c_boilerplate(text)
    if lang == "python":
        return filter_python_boilerplate(text)
    if lang in ("javascript", "typescript"):
        return filter_js_boilerplate(text)
    text = filter_java_boilerplate(text)
    text = filter_c_boilerplate(text)
    text = filter_python_boilerplate(text)
    text = filter_js_boilerplate(text)
    return text


def blank_output_boilerplate(text: str, lang: str) -> str:
    """
    Replaces I/O calls and main() declarations with empty lines so they are
    excluded from fingerprinting without shifting any line numbers. Applied to
    the fingerprint text only — the display version shown to instructors is
    untouched so they can read the full submission.

    All output/input calls are blanked regardless of their argument content.
    After token normalization, print("label: " + x) and print("other: " + y)
    produce identical token sequences, so keeping them creates false positives
    across unrelated programs that happen to do I/O.
    """
    lang = (lang or "mixed").lower()

    if lang == "java":
        text = _java_sysout_re.sub("", text)
        text = _java_scanner_re.sub("", text)
        text = _java_main_re.sub("", text)
        text = _java_null_guard_re.sub("", text)
        text = _java_this_assign_re.sub("", text)
    elif lang in ("c", "cpp", "c_or_cpp"):
        text = _c_stdio_re.sub("", text)
        text = _cpp_stream_cin_re.sub("", text)
        text = _cpp_stream_re.sub("", text)
        text = _cpp_using_ns_re.sub("", text)
        text = _c_main_re.sub("", text)
        text = _c_null_guard_re.sub("", text)
    elif lang == "python":
        text = _python_print_re.sub("", text)
        text = _python_input_re.sub("", text)
    elif lang in ("javascript", "typescript"):
        text = _js_console_re.sub("", text)
    elif lang == "mixed":
        text = _java_sysout_re.sub("", text)
        text = _java_scanner_re.sub("", text)
        text = _java_main_re.sub("", text)
        text = _java_null_guard_re.sub("", text)
        text = _java_this_assign_re.sub("", text)
        text = _c_stdio_re.sub("", text)
        text = _cpp_stream_cin_re.sub("", text)
        text = _cpp_stream_re.sub("", text)
        text = _cpp_using_ns_re.sub("", text)
        text = _c_main_re.sub("", text)
        text = _c_null_guard_re.sub("", text)
        text = _python_print_re.sub("", text)
        text = _python_input_re.sub("", text)
        text = _js_console_re.sub("", text)
    return text
