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

_java_import_re  = re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+(?:\.\*)?)\s*;", re.MULTILINE)
_java_package_re = re.compile(r"^\s*package\s+[\w.]+\s*;", re.MULTILINE)
_java_annotation_boilerplate_re = re.compile(
    r"^\s*@(Override|SuppressWarnings|Deprecated|FunctionalInterface|SafeVarargs)\b.*$",
    re.MULTILINE,
)


def filter_java_boilerplate(text: str) -> str:
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
_c_include_re = re.compile(r"^\s*#\s*include\s*[<\"]([\w./]+)[>\"]", re.MULTILINE)
_c_pragma_re  = re.compile(r"^\s*#\s*pragma\s+once\s*$", re.MULTILINE)
_c_define_guard_re = re.compile(
    r"^\s*#\s*(?:ifndef|define|endif)\s+\w+_H(?:PP|XX)?\s*(?://.*)?$",
    re.MULTILINE,
)


def filter_c_boilerplate(text: str) -> str:
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
    r"^\s*(?:from\s+([\w.]+)\s+import\s+.*|import\s+([\w., ]+))\s*$",
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
