"""
PDG construction — Phase 3 (conditional layer).

A Program Dependence Graph represents code as a network of dependencies rather
than a sequence of tokens or a tree of syntax. It has two edge types:

  Control dependence: statement B only executes if condition A is true.
                      An if-body statement is control-dependent on the if-condition.
                      A loop-body statement is control-dependent on the loop.

  Data dependence:    statement B uses the value computed by statement A.
                      After x = 5; the statement y = x + 1 is data-dependent
                      on the assignment of x.

Two programs with isomorphic PDGs are semantically equivalent regardless of
surface differences — this is why PDG catches obfuscations that k-gram and AST
cannot. Specifically:

  Recursion → iteration:
      Recursive: contains CALL nodes that have data edges from the previous
      call's result. The call-chain creates a recognizable data-edge pattern.
      Iterative: same computation expressed as a LOOP with ASSIGN nodes that
      depend on each other. The data-edge pattern differs structurally.
      PDG sees both as "something that repeatedly computes from a prior state"
      by comparing data fan-out and cycle structure.

  Function inlining:
      When a called function's body is copy-pasted inline, the control and
      data dependencies of that body are preserved exactly. The PDG of the
      inlined code contains the same dependency subgraph as the original
      function's PDG, just embedded inside the caller.

Implementation strategy
-----------------------
Rather than building a full formal PDG (which requires dominator-tree computation
and precise data-flow analysis), we build a *structural PDG approximation* that:

  1. Is fast — O(n) over AST nodes
  2. Is language-agnostic — uses normalized statement type labels
  3. Captures the key dependency patterns that distinguish the obfuscations above

The approximation is sufficient for a *modifier* (not a primary signal). It
shifts scores on borderline pairs, not make/break decisions.

Output: PDGFeatures — a compact representation of the PDG's structural properties
used by compare.py. No large graph objects are retained after feature extraction.

Public API:
    build_pdg_features(source, lang) → PDGFeatures
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from engine.ast.parse import _load_language, _LANG_CONFIG


# ---------------------------------------------------------------------------
# Normalized PDG node types
# ---------------------------------------------------------------------------
# All loop types (for, while, do-while, Rust's `loop`) normalize to LOOP.
# This makes the PDG invariant to loop-type swaps — the key post-AST use case.
# Switch and if both normalize to BRANCH — they represent alternate execution paths.
# ---------------------------------------------------------------------------

_STMT_TO_PDG_TYPE: Dict[str, str] = {
    # Assignments
    "assignment":                "ASSIGN",
    "augmented_assignment":      "ASSIGN",
    "compound_assignment_expr":  "ASSIGN",   # Rust
    "assignment_statement":      "ASSIGN",
    "short_variable_declaration": "ASSIGN",  # Go :=
    "expression_statement":      "ASSIGN",   # catch-all; refined below

    # Declarations
    "local_variable_declaration": "DECL",
    "variable_declaration":      "DECL",
    "declaration":               "DECL",
    "let_declaration":           "DECL",     # Rust
    "var_declaration":           "DECL",     # Go

    # Returns / yields
    "return_statement":  "RETURN",
    "return_expression": "RETURN",   # Rust
    "yield_expression":  "RETURN",   # Python generator

    # Branches (the condition node, not its body)
    "if_statement":       "BRANCH",
    "if_expression":      "BRANCH",  # Rust
    "switch_statement":   "BRANCH",
    "match_expression":   "BRANCH",  # Rust
    "when_expression":    "BRANCH",  # Kotlin

    # Loops — ALL types → LOOP (normalization is the point)
    "for_statement":      "LOOP",
    "for_in_statement":   "LOOP",
    "for_each_statement": "LOOP",
    "while_statement":    "LOOP",
    "do_statement":       "LOOP",
    "loop_expression":    "LOOP",   # Rust

    # Loop control
    "break_statement":    "BREAK",
    "continue_statement": "BREAK",

    # Exceptions
    "throw_statement":    "THROW",
    "raise_statement":    "THROW",
    "try_statement":      "TRY",
    "try_expression":     "TRY",

    # Function calls (as statements)
    "call_expression":    "CALL",
    "method_invocation":  "CALL",  # Java
}

# Node types that open a new control scope (their body statements are
# control-dependent on them)
_CONTROL_OPENERS: frozenset[str] = frozenset({
    "BRANCH", "LOOP", "TRY",
})


# ---------------------------------------------------------------------------
# PDG node and edge representation
# ---------------------------------------------------------------------------

@dataclass
class _PDGNode:
    node_id:  int
    pdg_type: str   # one of the PDG_TYPE values above
    line:     int
    # Which variables this statement defines (LHS of assignments)
    defines:  Set[str] = field(default_factory=set)
    # Which variables this statement uses (RHS / conditions / call args)
    uses:     Set[str] = field(default_factory=set)


@dataclass
class _PDGEdge:
    src:   int       # source node_id
    dst:   int       # destination node_id
    etype: str       # "ctrl" or "data"


# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------

@dataclass
class PDGFeatures:
    """
    Compact structural representation of a program's PDG.
    Computed once from source; compare.py reads these fields.
    """
    # Node type histogram: {"ASSIGN": 5, "LOOP": 2, ...}
    node_type_counts: Dict[str, int] = field(default_factory=dict)

    # Raw counts
    n_nodes:      int = 0
    n_ctrl_edges: int = 0
    n_data_edges: int = 0

    # Sorted out-degree sequences for control and data edges separately.
    # These capture the "fan-out" structure of each dependency type.
    ctrl_out_degrees: List[int] = field(default_factory=list)
    data_out_degrees: List[int] = field(default_factory=list)

    # Maximum control nesting depth (how deeply nested the code is)
    max_ctrl_depth: int = 0

    # Ratio of data edges to control edges (captures data-flow intensity)
    data_to_ctrl_ratio: float = 0.0

    # Whether the source contains any cycles (i.e., loops or recursion)
    has_cycles: bool = False

    # Whether parse succeeded
    parse_ok: bool = True


# ---------------------------------------------------------------------------
# Variable extraction helpers
# ---------------------------------------------------------------------------
# These extract identifier names from AST nodes to build def-use edges.
# We keep this lightweight — we care about variable names, not full types.
# ---------------------------------------------------------------------------

_IDENTIFIER_TYPES: frozenset[str] = frozenset({
    "identifier", "simple_identifier", "field_identifier",
    "property_identifier", "type_identifier",
})

_ASSIGNMENT_TARGETS: frozenset[str] = frozenset({
    "assignment", "augmented_assignment", "compound_assignment_expr",
    "short_variable_declaration", "local_variable_declaration",
    "variable_declaration", "let_declaration",
})

_KNOWN_BUILTINS: frozenset[str] = frozenset({
    # Python
    "print", "len", "range", "int", "str", "float", "list", "dict", "set",
    "tuple", "bool", "type", "isinstance", "append", "extend", "sorted",
    "enumerate", "zip", "map", "filter", "open", "input", "abs", "max", "min",
    # Java
    "System", "out", "println", "String", "Integer", "List", "ArrayList",
    "Math", "Object", "Arrays", "Collections", "size", "get", "add",
    # C/C++
    "printf", "scanf", "malloc", "free", "sizeof", "nullptr", "NULL",
    # Go
    "fmt", "Println", "make", "append", "len", "cap",
    # Common
    "self", "this", "super", "new",
})


def _collect_identifiers(node, source_bytes: bytes) -> Set[str]:
    """Collect all identifier names in a subtree (for use-set extraction)."""
    ids: Set[str] = set()
    stack = [node]
    while stack:
        n = stack.pop()
        if n.type in _IDENTIFIER_TYPES:
            name = source_bytes[n.start_byte:n.end_byte].decode("utf-8", errors="replace").strip()
            if name and name not in _KNOWN_BUILTINS and len(name) <= 64:
                ids.add(name)
        else:
            stack.extend(n.children)
    return ids


def _extract_defines(node, source_bytes: bytes) -> Set[str]:
    """
    Extract variable names that are *defined* (written) by this statement.
    For assignments: the left-hand side identifier(s).
    For declarations: the declared variable name.
    """
    if node.type not in _ASSIGNMENT_TARGETS:
        return set()

    # Get the left/target field — varies by language
    target = (
        node.child_by_field_name("left")     # Python assignment
        or node.child_by_field_name("declarator")  # C/C++ declaration
        or node.child_by_field_name("name")   # Go short decl
        or node.child_by_field_name("pattern")  # Rust let
        or (node.children[0] if node.children else None)  # fallback
    )
    if target is None:
        return set()
    return _collect_identifiers(target, source_bytes)


def _extract_uses(node, source_bytes: bytes, defines: Set[str]) -> Set[str]:
    """
    Extract variable names that are *used* (read) by this statement.
    We collect all identifiers in the node then subtract the defined set.
    """
    all_ids = _collect_identifiers(node, source_bytes)
    return all_ids - defines


# ---------------------------------------------------------------------------
# AST walker — builds PDG nodes and edges for one function body
# ---------------------------------------------------------------------------

def _classify_stmt(node) -> Optional[str]:
    """Map an AST node type to a PDG node type, or None if not a statement."""
    pdg_type = _STMT_TO_PDG_TYPE.get(node.type)
    if pdg_type:
        return pdg_type
    # Catch statement suffixes not explicitly listed
    ntype = node.type
    if ntype.endswith("_statement") or ntype.endswith("_declaration"):
        return "OTHER"
    return None


def _build_function_pdg(
    func_node,
    source_bytes: bytes,
    func_types: frozenset,
) -> Tuple[List[_PDGNode], List[_PDGEdge]]:
    """
    Build PDG nodes and edges for a single function body.

    Uses an explicit stack for DFS with a control-scope stack to track
    which control node currently "owns" each statement.

    Returns (nodes, edges).
    """
    nodes: List[_PDGNode] = []
    edges: List[_PDGEdge] = []
    id_counter = [0]

    # Control scope stack: list of node_ids of currently-open BRANCH/LOOP/TRY nodes
    ctrl_stack: List[int] = []
    # Def table: variable → node_id of last definition
    def_table: Dict[str, int] = {}
    # Set of node_ids that are control-opener nodes (BRANCH, LOOP, TRY)
    opener_ids: Set[int] = set()

    def new_id() -> int:
        nid = id_counter[0]
        id_counter[0] += 1
        return nid

    def visit(node, depth: int = 0):
        # Don't recurse into nested function definitions — their scope is self-contained
        if node.type in func_types and depth > 0:
            return

        pdg_type = _classify_stmt(node)
        if pdg_type is not None:
            nid = new_id()

            # Variable def/use
            defs = _extract_defines(node, source_bytes)
            uses = _extract_uses(node, source_bytes, defs)

            n = _PDGNode(
                node_id=nid,
                pdg_type=pdg_type,
                line=node.start_point[0] + 1,
                defines=defs,
                uses=uses,
            )
            nodes.append(n)

            # Control edge: this node is control-dependent on the current ctrl scope
            if ctrl_stack:
                edges.append(_PDGEdge(src=ctrl_stack[-1], dst=nid, etype="ctrl"))

            # Data edges: for each variable used, find its definition
            for var in uses:
                if var in def_table:
                    def_nid = def_table[var]
                    if def_nid != nid:  # skip self-edges
                        edges.append(_PDGEdge(src=def_nid, dst=nid, etype="data"))

            # Update def table for variables this statement defines
            for var in defs:
                def_table[var] = nid

            # If this is a control opener, push it onto the scope stack
            if pdg_type in _CONTROL_OPENERS:
                opener_ids.add(nid)
                ctrl_stack.append(nid)
                # Recurse into children with the new scope active
                for child in node.children:
                    visit(child, depth + 1)
                ctrl_stack.pop()
                return  # don't double-recurse below

        # Default: recurse into children
        for child in node.children:
            visit(child, depth + 1)

    # Start the walk from the function body (skip the function header)
    body = (
        func_node.child_by_field_name("body")
        or func_node.child_by_field_name("suite")     # Python
        or func_node.child_by_field_name("block")
    )
    root = body if body is not None else func_node
    for child in root.children:
        visit(child, depth=0)

    return nodes, edges


# ---------------------------------------------------------------------------
# Feature extraction from raw PDG nodes + edges
# ---------------------------------------------------------------------------

def _extract_features(
    nodes: List[_PDGNode],
    edges: List[_PDGEdge],
    parse_ok: bool,
) -> PDGFeatures:
    """Compute the PDGFeatures summary from raw nodes and edges."""
    if not nodes:
        return PDGFeatures(parse_ok=parse_ok)

    node_type_counts = dict(Counter(n.pdg_type for n in nodes))
    n_nodes = len(nodes)

    ctrl_edges = [e for e in edges if e.etype == "ctrl"]
    data_edges = [e for e in edges if e.etype == "data"]
    n_ctrl = len(ctrl_edges)
    n_data = len(data_edges)

    # Out-degree sequences per edge type
    ctrl_out: Dict[int, int] = Counter(e.src for e in ctrl_edges)
    data_out: Dict[int, int] = Counter(e.src for e in data_edges)
    ctrl_out_degrees = sorted(ctrl_out.values())
    data_out_degrees = sorted(data_out.values())

    # Max control nesting depth using BFS on control edges
    max_depth = 0
    if ctrl_edges:
        # Build adjacency for ctrl edges
        ctrl_adj: Dict[int, List[int]] = defaultdict(list)
        for e in ctrl_edges:
            ctrl_adj[e.src].append(e.dst)
        # Find root control nodes (no incoming ctrl edge)
        all_ctrl_dst = {e.dst for e in ctrl_edges}
        roots = [e.src for e in ctrl_edges if e.src not in all_ctrl_dst]
        # BFS from each root
        for root in roots:
            queue = [(root, 1)]
            while queue:
                nid, d = queue.pop()
                if d > max_depth:
                    max_depth = d
                for child in ctrl_adj.get(nid, []):
                    queue.append((child, d + 1))

    has_cycles = (
        "LOOP" in node_type_counts
        or "BREAK" in node_type_counts
        # Also detect recursive CALL — proxy: a CALL node has a data self-path
        or any(e.src == e.dst for e in edges)
    )

    ratio = n_data / n_ctrl if n_ctrl > 0 else float(n_data)

    return PDGFeatures(
        node_type_counts=node_type_counts,
        n_nodes=n_nodes,
        n_ctrl_edges=n_ctrl,
        n_data_edges=n_data,
        ctrl_out_degrees=ctrl_out_degrees,
        data_out_degrees=data_out_degrees,
        max_ctrl_depth=max_depth,
        data_to_ctrl_ratio=round(ratio, 4),
        has_cycles=has_cycles,
        parse_ok=parse_ok,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_pdg_features(source: str, lang: str) -> PDGFeatures:
    """
    Parse *source* and build a compact PDGFeatures representation.

    The function walks all function/method bodies in the source, builds a
    per-function PDG for each, and merges the features into one aggregate
    PDGFeatures object covering the whole submission.

    Aggregation strategy: sum all node counts and edge counts, concatenate
    and re-sort the degree sequences. This preserves the total structural
    information across all functions without requiring a cross-function graph.

    Args:
        source: Full source code string (may be multi-file concatenated).
        lang:   Language key from ingest.detect_language.

    Returns:
        PDGFeatures on success, PDGFeatures(parse_ok=False) on failure.
    """
    lang_obj = _load_language(lang)
    if lang_obj is None:
        return PDGFeatures(parse_ok=False)

    try:
        from tree_sitter import Parser
        parser = Parser(lang_obj)
        source_bytes = source.encode("utf-8", errors="replace")
        tree = parser.parse(source_bytes)
        root = tree.root_node

        cfg = _LANG_CONFIG.get(lang, _LANG_CONFIG["cpp"])
        func_types = frozenset(cfg["func_types"])

        # Collect all function nodes
        func_nodes = []
        stack = [root]
        while stack:
            node = stack.pop()
            if node.type in func_types:
                func_nodes.append(node)
            else:
                stack.extend(reversed(node.children))

        if not func_nodes:
            # No functions — build PDG from top-level statements (scripts, etc.)
            func_nodes = [root]

        # Build and merge per-function PDGs
        all_nodes: List[_PDGNode] = []
        all_edges: List[_PDGEdge] = []
        id_offset = 0

        for fn_node in func_nodes:
            fn_nodes, fn_edges = _build_function_pdg(fn_node, source_bytes, func_types)
            # Offset node IDs to avoid collisions between functions
            for n in fn_nodes:
                n.node_id += id_offset
            for e in fn_edges:
                e.src += id_offset
                e.dst += id_offset
            all_nodes.extend(fn_nodes)
            all_edges.extend(fn_edges)
            id_offset += len(fn_nodes) + 1

        return _extract_features(all_nodes, all_edges, parse_ok=not root.has_error)

    except Exception:
        return PDGFeatures(parse_ok=False)
