import re

# ─── Java ───────────────────────────────────────────────────────────

JAVA_STDLIB_PREFIXES = (
    "java.lang.", "java.util.", "java.io.", "java.nio.", "java.net.",
    "java.math.", "java.text.", "java.time.", "java.awt.", "java.swing.",
    "javax.swing.", "javax.servlet.", "javax.xml.", "javax.crypto.",
    "java.applet.", "java.beans.", "java.security.", "java.sql.",
    "javafx.", "org.junit.", "org.hamcrest.",
)

# Boilerplate annotations every student uses
JAVA_BOILERPLATE_ANNOTATIONS = {
    "@Override", "@SuppressWarnings", "@Deprecated",
    "@FunctionalInterface", "@SafeVarargs",
}

# NOTE: All patterns below use ^[ \t]* (not ^\s*) at the start and [ \t]*$ (not \s*$)
# at the end.  \s includes \n, so ^\s* with re.MULTILINE can greedily consume
# preceding blank lines, causing sub("", ...) to DELETE those lines rather than
# just blanking the matched line.  Using [ \t]* restricts matching to spaces/tabs
# on the same line, preserving line count exactly.
_java_import_re  = re.compile(r"^[ \t]*import[ \t]+(?:static[ \t]+)?([\w.]+(?:\.\*)?)\s*;", re.MULTILINE)
_java_package_re = re.compile(r"^[ \t]*package[ \t]+[\w.]+\s*;", re.MULTILINE)
_java_annotation_boilerplate_re = re.compile(
    r"^[ \t]*@(Override|SuppressWarnings|Deprecated|FunctionalInterface|SafeVarargs)\b.*$",
    re.MULTILINE,
)

# System.out.* and System.err.* output calls — every Java student uses these;
# they don't reflect algorithm logic and create false-positive k-gram matches.
# Matches single-line calls: System.out.println(...); / System.err.print(...); etc.
_java_sysout_re = re.compile(
    r"^[ \t]*System\s*\.\s*(?:out|err)\s*\.\s*\w+\s*\(.*\);[ \t]*$",
    re.MULTILINE,
)

# public static void main(String[] args) { — identical in every Java program.
# Strips the declaration line; body tokens are preserved (students may put logic there).
_java_main_re = re.compile(
    r"^[ \t]*(?:public[ \t]+|private[ \t]+|protected[ \t]+)?(?:static[ \t]+)?void[ \t]+main[ \t]*"
    r"\([ \t]*String[ \t]*(?:\[[ \t]*\]|\[[ \t]*\])[ \t]*\w*[ \t]*\)"
    r"[ \t]*(?:throws[ \t]+[\w\t ,]+?)?[ \t]*\{?[ \t]*$",
    re.MULTILINE,
)


def filter_java_boilerplate(text: str) -> str:
    # NOTE: _java_sysout_re and _java_main_re are intentionally NOT applied here.
    # These lines are kept in the canonical (display) text so they appear in the
    # HTML report. They are blanked for fingerprinting only via blank_output_boilerplate().
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


# ─── C / C++ ───────────────────────────────────────────────────────

C_STDLIB_HEADERS = {
    # C standard
    "stdio.h", "stdlib.h", "string.h", "math.h", "ctype.h",
    "time.h", "assert.h", "limits.h", "float.h", "stddef.h",
    "stdint.h", "stdbool.h", "stdarg.h", "errno.h", "signal.h",
    "setjmp.h", "locale.h", "complex.h", "fenv.h", "inttypes.h",
    "iso646.h", "wchar.h", "wctype.h", "tgmath.h",
    # C++ standard
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

# C/C++ define macros that are structural noise
_c_include_re = re.compile(r"^[ \t]*#[ \t]*include[ \t]*[<\"]([\w./]+)[>\"]", re.MULTILINE)
_c_pragma_re  = re.compile(r"^[ \t]*#[ \t]*pragma[ \t]+once[ \t]*$", re.MULTILINE)
_c_define_guard_re = re.compile(
    r"^[ \t]*#[ \t]*(?:ifndef|define|endif)[ \t]+\w+_H(?:PP|XX)?[ \t]*(?://.*)?$",
    re.MULTILINE,
)

# printf/scanf/puts/gets and related C stdio output/input calls (single-line).
# These are universal output boilerplate — not algorithm logic.
_c_stdio_call_re = re.compile(
    r"^[ \t]*(?:printf|fprintf|sprintf|snprintf|scanf|fscanf|sscanf|"
    r"puts|fputs|gets|fgets|perror|putchar|putc|getchar|getc)\s*\(.*\);[ \t]*$",
    re.MULTILINE,
)

# C++ stream I/O: cout << ... ; / cin >> ... ; / cerr << ... ;
# Using std:: prefix or bare name. Single-line statements.
_cpp_stream_re = re.compile(
    r"^[ \t]*(?:std\s*::\s*)?(?:cout|cin|cerr|clog)\s*(?:<<|>>).*;[ \t]*$",
    re.MULTILINE,
)

# using namespace std; — boilerplate in virtually every C++ student program
_cpp_using_ns_re = re.compile(
    r"^[ \t]*using[ \t]+namespace[ \t]+\w+\s*;[ \t]*$",
    re.MULTILINE,
)

# int main(...) / void main(...) declaration line
# Covers: main(), main(void), main(int argc, char* argv[]), etc.
_c_main_re = re.compile(
    r"^[ \t]*(?:int|void)[ \t]+main[ \t]*\([^{;\n]*\)[ \t]*\{?[ \t]*$",
    re.MULTILINE,
)


def filter_c_boilerplate(text: str) -> str:
    # NOTE: stdio calls, stream I/O, and main() are intentionally NOT stripped here.
    # They are kept in the canonical (display) text and blanked for fingerprinting
    # only via blank_output_boilerplate().
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


# ─── Python ─────────────────────────────────────────────────────────

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

    # strip if __name__ == "__main__" boilerplate
    text = re.sub(r'^\s*if\s+__name__\s*==\s*["\']__main__["\']\s*:\s*$', "", text, flags=re.MULTILINE)
    return text


# ─── JavaScript / TypeScript ────────────────────────────────────────

_js_import_re = re.compile(
    r"^\s*import\s+.*\s+from\s+['\"]([^'\"]+)['\"];?\s*$",
    re.MULTILINE,
)
_js_require_re = re.compile(
    r"^\s*(?:const|let|var)\s+\w+\s*=\s*require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)\s*;?\s*$",
    re.MULTILINE,
)

JS_STDLIB_MODULES = {"fs", "path", "http", "https", "os", "util", "stream", "events"}


def filter_js_boilerplate(text: str) -> str:
    def _strip_import(match):
        mod = match.group(1)
        if mod in JS_STDLIB_MODULES or mod.startswith("node:"):
            return ""
        return match.group(0)

    text = _js_import_re.sub(_strip_import, text)
    text = _js_require_re.sub(_strip_import, text)
    return text


# ─── Entry Point ────────────────────────────────────────────────────

def filter_boilerplate(text: str, lang: str) -> str:
    """Entry point. Routes to the correct filter based on language."""
    lang = (lang or "mixed").lower()

    if lang == "java":
        return filter_java_boilerplate(text)
    if lang in ("c", "cpp", "c_or_cpp"):
        return filter_c_boilerplate(text)
    if lang == "python":
        return filter_python_boilerplate(text)
    if lang in ("javascript", "typescript"):
        return filter_js_boilerplate(text)
    # mixed: try all applicable ones
    text = filter_java_boilerplate(text)
    text = filter_c_boilerplate(text)
    text = filter_python_boilerplate(text)
    text = filter_js_boilerplate(text)
    return text


# ─── Fingerprint-only boilerplate blanker ───────────────────────────

def blank_output_boilerplate(text: str, lang: str) -> str:
    """
    Replace universal output/IO/main boilerplate lines with empty lines,
    PRESERVING LINE COUNT so that token.line numbers stay aligned with the
    original canonical_text used for HTML display.

    Called AFTER canonicalize() on the canonical_text.  The result (fp_text)
    is used exclusively for tokenisation and fingerprinting — never displayed.

    Why blank instead of delete:
        re.MULTILINE  ^...$  matches line content but NOT the trailing \\n.
        So sub("", ...) leaves a bare \\n, turning the line empty rather than
        removing it.  This keeps every subsequent line at the same line number
        as in canonical_text, so highlight positions in the HTML stay correct.

    Covers:
        Java  — System.out.* / System.err.* calls, main() declaration
        C     — printf / scanf / puts / gets / fprintf family
        C++   — cout / cin / cerr stream statements, using namespace std;
        C/C++ — int main(...) / void main(...) declaration
    """
    lang = (lang or "mixed").lower()

    if lang == "java":
        text = _java_sysout_re.sub("", text)
        text = _java_main_re.sub("", text)
    elif lang in ("c", "cpp", "c_or_cpp"):
        text = _c_stdio_call_re.sub("", text)
        text = _cpp_stream_re.sub("", text)
        text = _cpp_using_ns_re.sub("", text)
        text = _c_main_re.sub("", text)
    elif lang == "mixed":
        text = _java_sysout_re.sub("", text)
        text = _java_main_re.sub("", text)
        text = _c_stdio_call_re.sub("", text)
        text = _cpp_stream_re.sub("", text)
        text = _cpp_using_ns_re.sub("", text)
        text = _c_main_re.sub("", text)
    # python / javascript / typescript — no output-boilerplate blanking needed
    return text
