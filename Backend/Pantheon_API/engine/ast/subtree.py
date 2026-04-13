"""
AST subtree hashing at three granularity levels.

This is the core of Phase 2B. The idea is simple: rather than comparing token
sequences, we compare the *structure* of the code by hashing subtrees of the AST
at three different levels:

  Statement level — individual statements hashed separately.
                    "total += arr[i]" hashes identically whether it is inside a
                    for-loop or a while-loop, because we hash the statement node
                    type structure, not the surrounding context.

  Block level     — entire loop bodies, if-else bodies, and try-catch blocks
                    hashed as units. The block hash is the same regardless of
                    which loop type wraps it. This catches loop-type swaps at a
                    coarser granularity than the statement pass.

  Method level    — entire method bodies hashed with the method name stripped out.
                    Two methods that do the same thing hash identically even if
                    they have completely different names.

All three levels normalize identifier names to "ID", numeric literals to "NUM",
and string literals to "STR". This makes the hashes invariant to:
    - Variable renaming
    - Literal value substitution (changing constants)
    - Method name changes
    - Loop type swap (for → while) — the body hash is identical
    - Dead code insertion — only new leaf nodes appear; existing subtrees unchanged
    - Try-catch wrapping — only adds a wrapper node; inner subtrees unchanged

Public API:
    compute_subtree_hashes(source, lang)  → SubtreeHashes
    subtree_similarity(hashes_a, hashes_b) → float in [0.0, 1.0]
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Set

from engine.ast.parse import _load_language, _LANG_CONFIG


# ---------------------------------------------------------------------------
# Node type classification tables
# ---------------------------------------------------------------------------
# These are used to decide whether a node is:
#   - an identifier (normalize to "ID")
#   - a numeric literal (normalize to "NUM")
#   - a string literal (normalize to "STR")
#   - a statement-level node (include in statement hash set)
#   - a block-level node (include in block hash set — these are the *bodies*)
#   - a function/method node (include in method hash set)
#
# We use broad cross-language sets because tree-sitter types are consistent
# enough across C-family, Java, Python, Go, and Rust to share these tables.
# ---------------------------------------------------------------------------

_IDENTIFIER_TYPES: frozenset[str] = frozenset({
    "identifier", "type_identifier", "field_identifier",
    "property_identifier", "namespace_identifier",
    "simple_identifier",        # Kotlin / Rust
    "name",                     # some grammars use "name" as a leaf
})

_NUMBER_TYPES: frozenset[str] = frozenset({
    "integer", "float", "integer_literal", "float_literal",
    "decimal_integer_literal", "decimal_floating_point_literal",
    "hex_integer_literal", "octal_integer_literal",
    "number", "number_literal",
})

_STRING_TYPES: frozenset[str] = frozenset({
    "string", "string_literal", "interpreted_string_literal",
    "raw_string_literal", "char_literal", "character_literal",
    "string_content",
})

_BOOL_TYPES: frozenset[str] = frozenset({
    "true", "false", "boolean_literal",
    "nil", "null", "none",
})

# Statement-level node types: at least one of these must match for a node to
# be included in the statement hash set. We take a broad approach — if a node
# type ends with "_statement" or "_declaration" it is fair game.
_STATEMENT_SUFFIXES: tuple[str, ...] = (
    "_statement", "_declaration", "_expression_statement",
    "assignment", "augmented_assignment", "short_variable_declaration",
    "return_statement", "break_statement", "continue_statement",
    "expression_statement", "local_variable_declaration",
)

# Block-level node types: these are the *body* containers of control-flow nodes.
# We hash the block itself, not the surrounding for/while/if node, so that the
# block hash is the same regardless of what control structure wraps it.
_BLOCK_TYPES: frozenset[str] = frozenset({
    "block",                    # Java, Go, Rust, JS/TS
    "compound_statement",       # C, C++
    "suite",                    # Python (the indented block)
    "statement_block",          # JS/TS (inside {})
    "block_statement",          # some grammars
    "body",                     # Go method body
})

# Control-flow node types whose *body* or *consequence*/*alternative* children
# we specifically want to hash at block level.
_CONTROL_FLOW_TYPES: frozenset[str] = frozenset({
    "if_statement", "if_expression",
    "for_statement", "for_in_statement", "for_each_statement",
    "while_statement", "do_statement", "loop_expression",
    "try_statement", "try_expression", "catch_clause",
    "switch_statement", "match_expression",
})

# Field names that contain the body of control-flow statements
_BODY_FIELDS: tuple[str, ...] = (
    "body", "consequence", "alternative", "update",
    "then", "else", "finally",
)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class SubtreeHashes:
    """
    Holds the three sets of structural hashes extracted from one submission.
    Each hash in a set is a 16-character hex string (MD5 truncated).
    """
    statement: Set[str] = field(default_factory=set)
    block:     Set[str] = field(default_factory=set)
    method:    Set[str] = field(default_factory=set)
    parse_ok:  bool = True


# ---------------------------------------------------------------------------
# Canonical representation engine
# ---------------------------------------------------------------------------

def _hash(text: str) -> str:
    """Stable 16-hex-char hash of a string. Uses MD5 (not cryptographic — just stable)."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:16]


def _canonical(node, source_bytes: bytes, strip_name: bool = False) -> str:
    """
    Build a canonical structural string for an AST node.

    Rules:
      - Identifier nodes → "ID"
      - Number literals  → "NUM"
      - String literals  → "STR"
      - Boolean/null     → "BOOL"
      - Named function nodes with strip_name=True → omit the name child
      - All other nodes  → (node_type child1_canonical child2_canonical ...)

    The result is deterministic and invariant to variable names, literals, and
    (when strip_name=True) method names.
    """
    ntype = node.type

    # --- Leaf normalization ---
    if ntype in _IDENTIFIER_TYPES:
        return "ID"
    if ntype in _NUMBER_TYPES:
        return "NUM"
    if ntype in _STRING_TYPES:
        return "STR"
    if ntype in _BOOL_TYPES:
        return "BOOL"

    # True leaf (no children) that isn't a normalizable type — use raw text
    # for keywords, operators, punctuation (these are structurally meaningful)
    if not node.children:
        raw = source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
        # Keep short tokens as-is; collapse long ones to their type name
        return raw if len(raw) <= 16 else ntype

    # --- Internal node ---
    parts = [ntype]
    for child in node.children:
        # When strip_name is set, skip the "name" field child of the function node.
        # We detect this by checking if the parent node is a function type AND
        # child.type is an identifier type or the child is named "name" in the field map.
        if strip_name and child.type in _IDENTIFIER_TYPES:
            # Only skip the identifier that is the direct function name (first identifier child)
            # Use a sentinel to track that we have already skipped one name
            strip_name = False   # skip the first identifier only
            continue
        parts.append(_canonical(child, source_bytes, strip_name=False))

    return "(" + " ".join(parts) + ")"


def _is_statement_node(node) -> bool:
    """True if this AST node represents a standalone statement worth hashing."""
    ntype = node.type
    if any(ntype.endswith(sfx) for sfx in _STATEMENT_SUFFIXES):
        return True
    # Explicit common names that don't follow a consistent suffix pattern
    return ntype in {
        "assignment",            # Python
        "augmented_assignment",  # Python
        "expression_statement",  # C/Java
        "return_statement",
        "throw_statement",
        "assert_statement",
        "delete_statement",
        "raise_statement",
        "yield_expression",
    }


# ---------------------------------------------------------------------------
# Tree walk
# ---------------------------------------------------------------------------

def _walk(
    node,
    source_bytes: bytes,
    lang_func_types: frozenset,
    result: SubtreeHashes,
    inside_func: bool = False,
):
    """
    Depth-first walk of the AST. Collect statement, block, and method hashes.

    Args:
        node:            Current AST node.
        source_bytes:    Raw UTF-8 bytes of the source.
        lang_func_types: Set of node types that are function/method declarations
                         for this language (from _LANG_CONFIG).
        result:          The SubtreeHashes object being built in-place.
        inside_func:     Whether we are currently inside a function body.
                         Statement hashes are only meaningful inside a function.
    """
    ntype = node.type

    # --- Method level ---
    if ntype in lang_func_types:
        # Hash the entire method body with the name stripped.
        # strip_name=True causes the first identifier child (the method name)
        # to be omitted from the canonical representation.
        method_repr = _canonical(node, source_bytes, strip_name=True)
        result.method.add(_hash(method_repr))
        # Recurse into the function body, marking that we are inside a function
        for child in node.children:
            _walk(child, source_bytes, lang_func_types, result, inside_func=True)
        return  # don't double-process children below

    # --- Block level ---
    # Hash the body nodes of control-flow statements as blocks.
    # We target the body field children of control-flow parents.
    if ntype in _CONTROL_FLOW_TYPES:
        for child in node.children:
            if child.type in _BLOCK_TYPES:
                block_repr = _canonical(child, source_bytes, strip_name=False)
                result.block.add(_hash(block_repr))
            # Also hash named consequence/alternative fields
            _walk(child, source_bytes, lang_func_types, result, inside_func)
        return

    # Hash standalone block nodes that appear in other contexts (e.g. bare blocks)
    if ntype in _BLOCK_TYPES and inside_func:
        block_repr = _canonical(node, source_bytes, strip_name=False)
        result.block.add(_hash(block_repr))

    # --- Statement level ---
    if inside_func and _is_statement_node(node):
        stmt_repr = _canonical(node, source_bytes, strip_name=False)
        # Only hash statements that resolve to more than a trivial string
        if len(stmt_repr) > 8:
            result.statement.add(_hash(stmt_repr))

    # --- Recurse ---
    for child in node.children:
        _walk(child, source_bytes, lang_func_types, result, inside_func)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_subtree_hashes(source: str, lang: str) -> SubtreeHashes:
    """
    Parse *source* and extract statement, block, and method-level structural hashes.

    Args:
        source: Full source code of the submission (may be multi-file concatenated).
        lang:   Language key matching ingest.detect_language output.

    Returns:
        SubtreeHashes with three sets of hash strings.
        On parse failure, returns an empty SubtreeHashes with parse_ok=False.
    """
    lang_obj = _load_language(lang)
    if lang_obj is None:
        return SubtreeHashes(parse_ok=False)

    try:
        from tree_sitter import Parser
        parser = Parser(lang_obj)
        source_bytes = source.encode("utf-8", errors="replace")
        tree = parser.parse(source_bytes)
        root = tree.root_node

        cfg = _LANG_CONFIG.get(lang, _LANG_CONFIG["cpp"])
        lang_func_types = frozenset(cfg["func_types"])

        result = SubtreeHashes(parse_ok=not root.has_error)
        _walk(root, source_bytes, lang_func_types, result)
        return result

    except Exception:
        return SubtreeHashes(parse_ok=False)


def subtree_similarity(a: SubtreeHashes, b: SubtreeHashes) -> float:
    """
    Compute a weighted similarity score from two SubtreeHashes objects.

    Scoring strategy:
      - Method level  : weight 0.50 — most discriminative; an entire method body
                        matching is very strong signal.
      - Block level   : weight 0.30 — loop/if bodies matching independent of the
                        surrounding loop type.
      - Statement level: weight 0.20 — individual statement matching; less specific
                        because common idioms produce the same hash across many
                        submissions (e.g. "return ID" appears everywhere).

    For each level we use containment: |A ∩ B| / min(|A|, |B|).
    Containment is the right metric here for the same reason it is the right metric
    for overall scoring — one student may have copied only some functions from a
    larger submission, so the smaller set's coverage matters more than symmetric
    overlap.

    Returns 0.0 if both submissions have empty hash sets (parse failed, tiny file).
    """
    def _containment(set_a: set, set_b: set) -> float:
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        return intersection / min(len(set_a), len(set_b))

    method_sim    = _containment(a.method,    b.method)
    block_sim     = _containment(a.block,     b.block)
    statement_sim = _containment(a.statement, b.statement)

    # Weighted combination
    score = (
        0.50 * method_sim
        + 0.30 * block_sim
        + 0.20 * statement_sim
    )

    return round(min(score, 1.0), 6)


def subtree_similarity_from_source(source_a: str, source_b: str, lang: str) -> float:
    """
    Convenience wrapper: compute hashes for both sources and return similarity.
    Used in tests and from api.py when source strings are already available.
    """
    hashes_a = compute_subtree_hashes(source_a, lang)
    hashes_b = compute_subtree_hashes(source_b, lang)
    return subtree_similarity(hashes_a, hashes_b)
