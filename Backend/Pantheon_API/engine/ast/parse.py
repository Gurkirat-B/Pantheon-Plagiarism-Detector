"""
Phase 1 AST parser — the foundation of the new engine layer.

This module is the first thing that runs after ingest+tokenize. It parses each
submission's source files into tree-sitter ASTs and extracts three things that
every later phase needs:

  1. Function boundary map  — maps each function/method name to its start line,
                              end line, and approximate token count. Used by
                              kgrams.py for per-function adaptive k selection.

  2. Per-function complexity — node count and tree depth for each function.
                               Currently informational; reserved for future
                               weight adjustments.

  3. Call graph             — dict mapping each function to the list of functions
                              it calls (names only, not resolved). Used by
                              callgraph.py for structural comparison.

The parser is language-aware: it uses the correct tree-sitter grammar for the
detected language and knows which node types represent function declarations in
that language. All other node types are ignored at this stage.

Output shape (from parse_submission):
    {
        "functions": {
            "<func_name>": {
                "start_line": int,   # 1-indexed, inclusive
                "end_line":   int,   # 1-indexed, inclusive
                "token_count": int,  # approximate — character-level estimate
                "node_count": int,   # total AST nodes in the function body
                "depth":      int,   # max tree depth within the function
            },
            ...
        },
        "call_graph": {
            "<caller>": ["<callee1>", "<callee2>", ...],
            ...
        },
        "language": str,   # the detected language string
        "parse_ok": bool,  # False if tree-sitter could not parse the source
    }
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Union

# ---------------------------------------------------------------------------
# tree-sitter language registry
# ---------------------------------------------------------------------------
# Each entry maps a language key (matching what ingest.detect_language returns)
# to a callable that returns a tree-sitter Language object.
# We import lazily so that missing grammars produce a clear error only when
# that language is actually requested, not at import time.
# ---------------------------------------------------------------------------

def _load_language(lang: str):
    """
    Return the tree-sitter Language object for the given language key.
    Raises ImportError with a clear message if the grammar package is missing.
    """
    try:
        if lang == "python":
            import tree_sitter_python as _g
            from tree_sitter import Language
            return Language(_g.language())

        if lang in ("c", "cpp"):
            if lang == "cpp":
                import tree_sitter_cpp as _g
            else:
                import tree_sitter_c as _g
            from tree_sitter import Language
            return Language(_g.language())

        if lang == "java":
            import tree_sitter_java as _g
            from tree_sitter import Language
            return Language(_g.language())

        if lang == "javascript":
            import tree_sitter_javascript as _g
            from tree_sitter import Language
            return Language(_g.language())

        if lang == "typescript":
            import tree_sitter_typescript as _ts
            from tree_sitter import Language
            # tree-sitter-typescript exposes typescript and tsx separately
            return Language(_ts.language_typescript())

        if lang == "go":
            import tree_sitter_go as _g
            from tree_sitter import Language
            return Language(_g.language())

        if lang == "rust":
            import tree_sitter_rust as _g
            from tree_sitter import Language
            return Language(_g.language())

    except ImportError as exc:
        raise ImportError(
            f"tree-sitter grammar for '{lang}' is not installed. "
            f"Run: pip install tree-sitter-{lang}"
        ) from exc

    return None


# ---------------------------------------------------------------------------
# Node type maps per language
# ---------------------------------------------------------------------------
# For each language we need to know:
#   FUNC_TYPES  — AST node types that represent a function/method declaration
#   NAME_FIELDS — the child field names that hold the function's identifier
#   CALL_TYPES  — AST node types that represent a function call expression
#   CALL_FUNC_FIELD — field/child path to extract the callee name from a call node
# ---------------------------------------------------------------------------

_LANG_CONFIG: dict[str, dict] = {
    "python": {
        "func_types":       {"function_definition", "async_function_definition"},
        "name_field":       "name",
        "call_types":       {"call"},
        "call_func_field":  "function",
    },
    "java": {
        "func_types":       {"method_declaration", "constructor_declaration"},
        "name_field":       "name",
        "call_types":       {"method_invocation"},
        "call_func_field":  "name",
    },
    "c": {
        "func_types":       {"function_definition"},
        "name_field":       "declarator",   # needs unwrapping — see _extract_c_func_name
        "call_types":       {"call_expression"},
        "call_func_field":  "function",
    },
    "cpp": {
        "func_types":       {"function_definition"},
        "name_field":       "declarator",
        "call_types":       {"call_expression"},
        "call_func_field":  "function",
    },
    "javascript": {
        "func_types":       {
            "function_declaration",
            "function_expression",
            "arrow_function",
            "method_definition",
        },
        "name_field":       "name",
        "call_types":       {"call_expression"},
        "call_func_field":  "function",
    },
    "typescript": {
        "func_types":       {
            "function_declaration",
            "function_expression",
            "arrow_function",
            "method_definition",
        },
        "name_field":       "name",
        "call_types":       {"call_expression"},
        "call_func_field":  "function",
    },
    "go": {
        "func_types":       {"function_declaration", "method_declaration"},
        "name_field":       "name",
        "call_types":       {"call_expression"},
        "call_func_field":  "function",
    },
    "rust": {
        "func_types":       {"function_item"},
        "name_field":       "name",
        "call_types":       {"call_expression"},
        "call_func_field":  "function",
    },
}

# Fall back to the cpp config for the "mixed" case — best-effort.
_LANG_CONFIG["mixed"] = _LANG_CONFIG["cpp"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _node_text(node, source_bytes: bytes) -> str:
    """Return the UTF-8 decoded source text for a node."""
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _extract_name(node, source_bytes: bytes, lang: str) -> str:
    """
    Extract the function/method name from a declaration node.
    For most languages this is straightforward — look up the 'name' field.
    C/C++ is more complex because the name is buried inside a declarator chain.
    """
    cfg = _LANG_CONFIG.get(lang, _LANG_CONFIG["cpp"])
    field = cfg["name_field"]

    if lang in ("c", "cpp"):
        return _extract_c_func_name(node, source_bytes)

    child = node.child_by_field_name(field)
    if child:
        text = _node_text(child, source_bytes).strip()
        # For JS/TS arrow functions assigned to a variable the name field may
        # be absent — return a positional placeholder instead.
        return text if text else f"_anon_{node.start_point[0]}"

    return f"_anon_{node.start_point[0]}"


def _extract_c_func_name(node, source_bytes: bytes) -> str:
    """
    In C/C++ the 'declarator' child of a function_definition is often a
    pointer_declarator or function_declarator wrapping the actual identifier.
    Walk the chain until we find an identifier node.
    """
    declarator = node.child_by_field_name("declarator")
    if declarator is None:
        return f"_anon_{node.start_point[0]}"
    return _find_identifier(declarator, source_bytes)


def _find_identifier(node, source_bytes: bytes) -> str:
    """Recursively find the first identifier node in the subtree."""
    if node.type == "identifier" or node.type == "field_identifier":
        return _node_text(node, source_bytes).strip()
    for child in node.children:
        result = _find_identifier(child, source_bytes)
        if result:
            return result
    return f"_anon_{node.start_point[0]}"


def _extract_call_name(call_node, source_bytes: bytes, lang: str) -> str | None:
    """
    Extract the name of the function being called from a call node.
    Returns None if we cannot reliably determine the callee name (e.g. calls
    through function pointers, lambdas, or complex member access chains).
    """
    cfg = _LANG_CONFIG.get(lang, _LANG_CONFIG["cpp"])
    field = cfg.get("call_func_field", "function")

    func_child = call_node.child_by_field_name(field)
    if func_child is None:
        return None

    node_type = func_child.type
    text = _node_text(func_child, source_bytes).strip()

    # member_expression / attribute: "obj.method" — take the last part
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    if "::" in text:
        text = text.rsplit("::", 1)[-1]

    # Only keep plain identifiers — discard complex expressions
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", text):
        return text
    return None


def _tree_stats(node) -> tuple[int, int]:
    """
    Walk the AST rooted at *node* and return (node_count, max_depth).
    Uses an explicit stack to avoid recursion depth limits on deep trees.
    """
    stack = [(node, 1)]
    total_nodes = 0
    max_depth = 0
    while stack:
        current, depth = stack.pop()
        total_nodes += 1
        if depth > max_depth:
            max_depth = depth
        for child in current.children:
            stack.append((child, depth + 1))
    return total_nodes, max_depth


def _approx_token_count(node, source_bytes: bytes) -> int:
    """
    Rough token count estimate: split the function's source text on whitespace
    and punctuation. This is only used to select k — it doesn't need to be exact.
    """
    text = _node_text(node, source_bytes)
    return len(re.findall(r"\w+|[^\w\s]", text))


# ---------------------------------------------------------------------------
# Core visitor
# ---------------------------------------------------------------------------

def _visit_tree(
    root,
    source_bytes: bytes,
    lang: str,
    functions: dict,
    call_graph: dict,
    current_func: list,     # mutable single-element list used as a stack frame
):
    """
    Walk the entire AST with an explicit stack. When we enter a function node we
    record its boundary and push its name onto current_func. When we enter a call
    node inside a function we record the callee. After processing all children of
    a function node we pop the name.

    We use an explicit stack of (node, entering) pairs so we can detect when we
    are leaving a function scope without real recursion.
    """
    cfg = _LANG_CONFIG.get(lang, _LANG_CONFIG["cpp"])
    func_types = cfg["func_types"]
    call_types = cfg["call_types"]

    # Stack items: (node, is_entry_step)
    # is_entry_step=True  → process this node (may push scope)
    # is_entry_step=False → we are leaving this node (may pop scope)
    stack = [(root, True)]
    # Parallel scope stack: tracks which function names are in scope
    scope_stack: list[str] = []

    while stack:
        node, entering = stack.pop()

        if entering:
            is_func = node.type in func_types
            if is_func:
                name = _extract_name(node, source_bytes, lang)
                # Deduplicate names within the same file by appending line number
                if name in functions:
                    name = f"{name}_{node.start_point[0] + 1}"

                node_count, depth = _tree_stats(node)
                token_count = _approx_token_count(node, source_bytes)

                functions[name] = {
                    "start_line":  node.start_point[0] + 1,  # 0-indexed → 1-indexed
                    "end_line":    node.end_point[0]   + 1,
                    "token_count": token_count,
                    "node_count":  node_count,
                    "depth":       depth,
                }
                call_graph.setdefault(name, [])
                scope_stack.append(name)

                # Push a sentinel to pop the scope when we leave this node
                stack.append((node, False))

            elif node.type in call_types and scope_stack:
                callee = _extract_call_name(node, source_bytes, lang)
                if callee:
                    caller = scope_stack[-1]
                    if callee not in call_graph[caller]:
                        call_graph[caller].append(callee)

            # Push children in reverse order so they are processed left-to-right
            if not (is_func and entering is False):  # don't re-push children on exit
                for child in reversed(node.children):
                    stack.append((child, True))

        else:
            # Leaving a function node — pop the scope
            if scope_stack:
                scope_stack.pop()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_source(source: str, lang: str) -> dict:
    """
    Parse a single source string and return the extracted function boundary map,
    call graph, and metadata.

    Args:
        source: UTF-8 source code as a string.
        lang:   Language key (matches ingest.detect_language output).

    Returns:
        {
            "functions": { name: {start_line, end_line, token_count, node_count, depth} },
            "call_graph": { caller: [callee, ...] },
            "language": lang,
            "parse_ok": bool,
        }
    """
    lang_obj = _load_language(lang)
    if lang_obj is None:
        # Unsupported language — return empty but valid result
        return {
            "functions": {},
            "call_graph": {},
            "language": lang,
            "parse_ok": False,
        }

    try:
        from tree_sitter import Parser
        parser = Parser(lang_obj)
        source_bytes = source.encode("utf-8", errors="replace")
        tree = parser.parse(source_bytes)
        root = tree.root_node

        functions: dict = {}
        call_graph: dict = {}
        _visit_tree(root, source_bytes, lang, functions, call_graph, [])

        return {
            "functions": functions,
            "call_graph": call_graph,
            "language": lang,
            "parse_ok": not root.has_error,
        }

    except Exception:
        return {
            "functions": {},
            "call_graph": {},
            "language": lang,
            "parse_ok": False,
        }


def parse_submission(source_files: list, lang: str) -> dict:
    """
    Parse an entire submission (a list of Path objects or strings) and merge
    the function boundary maps and call graphs from all files into one result.

    When the same function name appears in multiple files, the line number
    suffix deduplication in _visit_tree ensures no collisions.

    Args:
        source_files: List of Path objects pointing to source files.
        lang:         Language key from ingest.detect_language.

    Returns:
        Merged dict in the same shape as parse_source, covering all files.
    """
    merged_functions: dict = {}
    merged_call_graph: dict = {}
    any_ok = False

    for path in source_files:
        try:
            source = Path(path).read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        result = parse_source(source, lang)
        any_ok = any_ok or result["parse_ok"]

        # Merge — prefix function names with the relative filename so that
        # same-named functions in different files stay distinct.
        fname = Path(path).name
        for func_name, info in result["functions"].items():
            key = f"{fname}::{func_name}"
            merged_functions[key] = info

        for caller, callees in result["call_graph"].items():
            key = f"{fname}::{caller}"
            merged_call_graph.setdefault(key, [])
            for callee in callees:
                if callee not in merged_call_graph[key]:
                    merged_call_graph[key].append(callee)

    return {
        "functions":   merged_functions,
        "call_graph":  merged_call_graph,
        "language":    lang,
        "parse_ok":    any_ok,
    }
