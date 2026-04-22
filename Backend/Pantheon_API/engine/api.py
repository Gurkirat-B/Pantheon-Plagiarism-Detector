"""
This is the only file the rest of the system needs to interact with. It exposes
two functions: compare() runs a full side-by-side analysis on two submissions and
returns similarity scores, matching code blocks, and any detected obfuscation.
batch_analyze() scores every possible pair within a set of submissions and returns
them ranked from most to least suspicious.

    from engine.api import compare, batch_analyze

v2 pipeline (ENGINE_DESIGN.md §3):

    Phase 1  — AST parse (always, sequential — both Phase 2 passes need its output)
               Extracts function boundaries, call graph, complexity.

    Phase 2A — Adaptive k-gram (always, parallel with Phase 2B)
               Per-function adaptive k (Pass 1) + global (Pass 2) + loop-normalised (Pass 3)

    Phase 2B — AST comparison (always, parallel with Phase 2A)
               Subtree hashing + method-pair best-match + call graph comparison

    Base score = weighted_score(kgram_signals + AST_signals)

    Phase 3  — PDG (conditional — triggered by 3 conditions, see _should_trigger_pdg())
               Modifies final score if triggered: final = base×0.80 + pdg×0.20
"""

import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Union

from engine.version import ENGINE_VERSION
from engine.exceptions import EngineError
from engine.ingest.ingest import ingest_to_dir
from engine.preprocess.canonicalize import canonicalize
from engine.preprocess.stdlib_filter import blank_output_boilerplate
from engine.preprocess.strip_comments import strip_comments
from engine.tokenize.lex import tokenize
from engine.fingerprint.kgrams import winnow, build_fingerprints, build_per_function_fingerprints
from engine.similarity.scores import weighted_score, apply_pdg_modifier
from engine.evidence.evidence import build_evidence, build_ast_evidence
from engine.obfuscation.detect import detect_obfuscation, is_pdg_trigger_flag, flag_name
# AST imports — used in Phase 1 and Phase 2B
from engine.ast.parse import parse_submission
from engine.ast.subtree import compute_subtree_hashes, subtree_similarity
from engine.ast.method_match import per_method_hashes, best_match_score
from engine.ast.callgraph import compare_callgraphs
# PDG imports — used in Phase 3 (conditional)
from engine.pdg.build import build_pdg_features
from engine.pdg.compare import pdg_similarity

# k is the chunk size used by the Winnowing fingerprinting algorithm — it controls
# how many consecutive tokens must match before we call it a shared sequence.
# k=10 means roughly 4-5 lines of code. k=8 is used for the short-method pass
# to catch small helper functions the primary pass misses. k=5 produced too many
# false positives — after identifier/literal normalization, 5-token sequences
# coincidentally match across completely unrelated algorithms.
_K = 10
_W = 5
_K_SHORT = 8
_W_SHORT = 4


def _process_submission(path: Union[str, Path], work_dir: Path, lang_hint: str = "mixed"):
    """
    Runs the full preparation pipeline on one submission: ingests files, cleans
    them, converts to fingerprints, and now also runs AST Phase 1 to build the
    function boundary map that Phase 2A and 2B both need.
    """
    path = Path(path)
    _, detected_lang, source_files = ingest_to_dir(path, work_dir)
    lang = detected_lang if detected_lang != "mixed" else lang_hint

    canon = canonicalize(source_files, work_dir, lang=lang)

    fp_text = blank_output_boilerplate(canon.canonical_text, lang)

    tok_norm = tokenize(fp_text, lang=lang,
                        normalize_ids=True, normalize_literals=True,
                        normalize_access=True)

    tok_raw = tokenize(fp_text, lang=lang,
                       normalize_ids=False, normalize_literals=False,
                       normalize_access=False)

    tok_norm = tok_norm[:50000]
    tok_raw  = tok_raw[:50000]

    n_tokens = len(tok_norm)
    dyn_k = max(8, min(15, n_tokens // 200))
    dyn_w = max(4, min(8, dyn_k // 2))

    fp       = winnow(tok_norm, k=dyn_k, window=dyn_w)
    fp_full  = build_fingerprints(tok_norm, k=12)
    fp_short = build_fingerprints(tok_norm, k=_K_SHORT)

    # ── Phase 1: AST parse — build function boundary map and call graph ──
    # parse_submission reads the original source files (before canonicalization)
    # so it sees real identifiers, not normalized tokens. This is intentional:
    # tree-sitter needs real syntax, not our token stream.
    ast_result = parse_submission(source_files, lang)

    # ── Per-function adaptive k fingerprints (Phase 2A Pass 1) ──
    # Built here alongside the other fingerprints so the result dict is complete.
    fp_per_func = build_per_function_fingerprints(
        tok_norm, ast_result["functions"]
    ) if ast_result["parse_ok"] else {}

    # ── Subtree hashes for Phase 2B ──
    # Use the original source files (same as parse_submission) so tree-sitter
    # gets valid syntax. Canonical text strips too many constructs for C/C++
    # and causes parse_ok=False, producing empty hash sets and a zero AST score.
    raw_src = "\n".join(
        p.read_text(encoding="utf-8", errors="replace")
        for p in source_files if p.is_file()
    )
    subtree_hashes = compute_subtree_hashes(raw_src, lang)

    # ── Per-method hashes for Phase 2B method-pair matching ──
    method_hashes = per_method_hashes(raw_src, lang)

    return {
        "lang":          lang,
        "canon":         canon,
        "tok_norm":      tok_norm,
        "tok_raw":       tok_raw,
        "fp":            fp,
        "fp_full":       fp_full,
        "fp_short":      fp_short,
        "dyn_k":         dyn_k,
        "dyn_w":         dyn_w,
        # Phase 1 outputs
        "ast_result":    ast_result,       # {functions, call_graph, parse_ok}
        "fp_per_func":   fp_per_func,      # per-function fingerprints
        # Phase 2B inputs
        "subtree_hashes": subtree_hashes,  # SubtreeHashes object
        "method_hashes":  method_hashes,   # {func_name: SubtreeHashes}
        "source_files":   source_files,    # original Path list for PDG
    }


def compare(
    submission_a_path: Union[str, Path],
    submission_b_path: Union[str, Path],
    submission_a_id: str = "A",
    submission_b_id: str = "B",
    assignment_id: Optional[str] = None,
    workdir: Optional[Union[str, Path]] = None,
    template_path: Optional[Union[str, Path]] = None,
) -> dict:
    """
    Runs the full comparison between two submissions and returns everything the
    backend needs for the report: similarity scores, a list of matching code blocks
    with exact line numbers, and any obfuscation patterns detected.

    If template_path is provided, fingerprints from the instructor's starter code
    are removed from both submissions before scoring. This prevents boilerplate
    that every student starts with from inflating the similarity score.

    submission_a_id and submission_b_id are the database identifiers the backend
    uses to refer to each submission. The engine never sees student names.
    """
    use_temp = workdir is None
    if use_temp:
        tmp = tempfile.mkdtemp(prefix="pantheon_")
        workdir = Path(tmp)
    else:
        workdir = Path(workdir)
        workdir.mkdir(parents=True, exist_ok=True)

    try:
        dir_a = workdir / "A"
        dir_b = workdir / "B"

        proc_a = _process_submission(submission_a_path, dir_a)
        proc_b = _process_submission(submission_b_path, dir_b)

        lang = proc_a["lang"] if proc_a["lang"] == proc_b["lang"] else "mixed"

        fp_a = proc_a["fp"]
        fp_b = proc_b["fp"]

        if template_path:
            template_fp = _get_template_fingerprints(template_path, workdir / "template")
            fp_a = _subtract_fingerprints(fp_a, template_fp)
            fp_b = _subtract_fingerprints(proc_b["fp"], template_fp)

        # ── Phase 2A + 2B: run in parallel ──
        # Both phases depend on Phase 1 (ast_result), which is already done inside
        # _process_submission(). We parallelise the heavy per-pair work here.
        with ThreadPoolExecutor(max_workers=2) as pool:

            # Phase 2B: AST comparison signals
            def _run_ast_phase():
                ast_sub   = subtree_similarity(proc_a["subtree_hashes"], proc_b["subtree_hashes"])
                meth_pair = best_match_score(proc_a["method_hashes"],  proc_b["method_hashes"])
                cg_sim    = compare_callgraphs(
                    proc_a["ast_result"]["call_graph"],
                    proc_b["ast_result"]["call_graph"],
                )
                return ast_sub, meth_pair, cg_sim

            # Phase 2A: k-gram scoring (uses existing winnow fingerprints)
            def _run_kgram_phase():
                return weighted_score(
                    fp_a, fp_b,
                    tok_a=proc_a["tok_norm"],
                    tok_b=proc_b["tok_norm"],
                    # AST signals fed in after the AST future resolves below
                )

            fut_ast   = pool.submit(_run_ast_phase)
            fut_kgram = pool.submit(_run_kgram_phase)

            kgram_scores          = fut_kgram.result()
            ast_sub, meth_pair, cg_sim = fut_ast.result()

        # ── Combined base score (Phase 2A + 2B signals together) ──
        scores = weighted_score(
            fp_a, fp_b,
            tok_a=proc_a["tok_norm"],
            tok_b=proc_b["tok_norm"],
            ast_subtree_similarity=ast_sub,
            method_pair_match=meth_pair,
        )
        scores["callgraph_sim"] = round(cg_sim, 4)

        final = scores["weighted_final"]

        # ── Obfuscation detection ──
        obfuscation_flags = detect_obfuscation(
            tok_a_raw=proc_a["tok_raw"],
            tok_b_raw=proc_b["tok_raw"],
            tok_a_norm=proc_a["tok_norm"],
            tok_b_norm=proc_b["tok_norm"],
            fp_a_norm=fp_a,
            fp_b_norm=fp_b,
        )

        # ── Phase 3: PDG trigger evaluation ──
        pdg_triggered = False
        pdg_sim       = None
        triggered_by  = None

        if _should_trigger_pdg(scores, obfuscation_flags):
            triggered_by = _pdg_trigger_reason(scores, obfuscation_flags)
            # Build PDG from original source files (need real syntax for tree-sitter)
            src_a = "\n".join(
                p.read_text(encoding="utf-8", errors="replace")
                for p in proc_a["source_files"] if p.is_file()
            )
            src_b = "\n".join(
                p.read_text(encoding="utf-8", errors="replace")
                for p in proc_b["source_files"] if p.is_file()
            )
            feats_a = build_pdg_features(src_a, lang)
            feats_b = build_pdg_features(src_b, lang)
            pdg_sim = pdg_similarity(feats_a, feats_b)

            final   = apply_pdg_modifier(final, pdg_sim)
            scores["pdg_similarity"] = round(pdg_sim, 4)
            scores["weighted_final"] = final
            pdg_triggered = True

        # ── Evidence building ──
        # Keep merge gaps small. A gap of 20 was absorbing entire neighbouring
        # methods into one block when only one method actually matched, producing
        # wildly asymmetric A/B regions. The upward walk below already recovers
        # function signatures above the matched region, so a large merge gap is
        # not needed for that purpose.
        if final >= 0.90:
            merge_gap = 6
        elif final >= 0.70:
            merge_gap = 4
        else:
            merge_gap = 2

        # Primary k-gram evidence pass (k=12)
        evidence = build_evidence(
            proc_a["fp_full"], proc_b["fp_full"],
            tok_a=proc_a["tok_norm"],
            tok_b=proc_b["tok_norm"],
            source_map_a=proc_a["canon"].source_map,
            source_map_b=proc_b["canon"].source_map,
            k=12, merge_gap=merge_gap,
            work_dir_a=dir_a, work_dir_b=dir_b,
            canonical_text_a=proc_a["canon"].canonical_text,
            canonical_text_b=proc_b["canon"].canonical_text,
            lang=lang, evidence_source="kgram",
        )

        # Short-method pass (k=5)
        evidence_short = build_evidence(
            proc_a["fp_short"], proc_b["fp_short"],
            tok_a=proc_a["tok_norm"],
            tok_b=proc_b["tok_norm"],
            source_map_a=proc_a["canon"].source_map,
            source_map_b=proc_b["canon"].source_map,
            k=_K_SHORT, merge_gap=merge_gap,
            work_dir_a=dir_a, work_dir_b=dir_b,
            canonical_text_a=proc_a["canon"].canonical_text,
            canonical_text_b=proc_b["canon"].canonical_text,
            lang=lang, evidence_source="kgram_short",
        )

        # Loop-normalized pass
        tok_loop_a = _normalize_loops(proc_a["tok_norm"])
        tok_loop_b = _normalize_loops(proc_b["tok_norm"])
        fp_loop_a  = build_fingerprints(tok_loop_a, k=12)
        fp_loop_b  = build_fingerprints(tok_loop_b, k=12)
        evidence_loop = build_evidence(
            fp_loop_a, fp_loop_b,
            tok_a=tok_loop_a, tok_b=tok_loop_b,
            source_map_a=proc_a["canon"].source_map,
            source_map_b=proc_b["canon"].source_map,
            k=12, merge_gap=merge_gap,
            work_dir_a=dir_a, work_dir_b=dir_b,
            canonical_text_a=proc_a["canon"].canonical_text,
            canonical_text_b=proc_b["canon"].canonical_text,
            lang=lang, evidence_source="kgram_loop",
        )

        # AST method-pair evidence (Phase 2B)
        evidence_ast = build_ast_evidence(
            methods_a=proc_a["method_hashes"],
            methods_b=proc_b["method_hashes"],
            function_map_a=proc_a["ast_result"]["functions"],
            function_map_b=proc_b["ast_result"]["functions"],
        )

        # Merge all four evidence sources then deduplicate
        evidence = _merge_evidence(evidence,       evidence_loop)
        evidence = _merge_evidence(evidence,       evidence_short)
        evidence = _merge_evidence(evidence,       evidence_ast)
        evidence = _deduplicate_evidence_1to1(evidence)

        obfuscation_flags = detect_obfuscation(
            tok_a_raw=proc_a["tok_raw"],
            tok_b_raw=proc_b["tok_raw"],
            tok_a_norm=proc_a["tok_norm"],
            tok_b_norm=proc_b["tok_norm"],
            fp_a_norm=fp_a,
            fp_b_norm=fp_b,
        )
        # Load the original source files so the report shows the actual student code,
        # not the normalized version that was used internally for fingerprinting.
        original_sources_a = _load_original_sources(dir_a, proc_a["canon"].source_map)
        original_sources_b = _load_original_sources(dir_b, proc_b["canon"].source_map)

        # Strip comments and import/header lines from the display version. We replace
        # those lines with empty strings rather than removing them so that all line
        # numbers in the evidence blocks still line up with the displayed code.
        stripped_sources_a = {f: strip_comments(c, lang) for f, c in original_sources_a.items()}
        stripped_sources_b = {f: strip_comments(c, lang) for f, c in original_sources_b.items()}
        stripped_sources_a = {f: _blank_header_lines(c) for f, c in stripped_sources_a.items()}
        stripped_sources_b = {f: _blank_header_lines(c) for f, c in stripped_sources_b.items()}

        # Join all source files into one continuous text block and record where each
        # file starts, so per-file line numbers can be converted to global positions.
        full_source_a, file_offsets_a = _build_full_source(stripped_sources_a)
        full_source_b, file_offsets_b = _build_full_source(stripped_sources_b)

        full_a_lines = full_source_a.splitlines()
        full_b_lines = full_source_b.splitlines()

        # Pass 1: convert all evidence blocks from per-file local coordinates to
        # global coordinates in the concatenated fullCodeA/B. Do this in a separate
        # pass before the upward-walk loop so the floor logic operates on global
        # line numbers regardless of which file each block came from.
        for block in evidence:
            off_a = file_offsets_a.get(block.get("file_a", ""), 0)
            off_b = file_offsets_b.get(block.get("file_b", ""), 0)
            block["lines_a"] = [block["lines_a"][0] + off_a, block["lines_a"][1] + off_a]
            block["lines_b"] = [block["lines_b"][0] + off_b, block["lines_b"][1] + off_b]

        # Sort by global start line before the upward-walk loop. Without this,
        # a high-strength block at line 300 sets a floor that prevents the walk
        # for a medium-strength block at line 100 from working correctly.
        evidence.sort(key=lambda b: b["lines_a"][0])

        # Pass 2: upward extension walk + fill code + recompute highlights.
        # floor_a/floor_b track one past the end of the last finalised block so
        # the walk never lets two adjacent blocks claim the same lines.
        floor_a: int = 1
        floor_b: int = 1

        for block in evidence:
            a1, a2 = block["lines_a"]
            b1, b2 = block["lines_b"]

            # Walk upward from the top of the matched block as long as the lines
            # immediately above are identical in both submissions. Recovers function
            # signatures and class headers that sit just above the k-gram threshold.
            while a1 > floor_a and b1 > floor_b and a1 > 1 and b1 > 1:
                la = full_a_lines[a1 - 2].strip()
                lb = full_b_lines[b1 - 2].strip()
                if la and lb and la == lb:
                    a1 -= 1
                    b1 -= 1
                else:
                    break
            block["lines_a"] = [a1, a2]
            block["lines_b"] = [b1, b2]

            floor_a = a2 + 1
            floor_b = b2 + 1

            block["code_a"] = "\n".join(full_a_lines[a1 - 1:a2])
            block["code_b"] = "\n".join(full_b_lines[b1 - 1:b2])

            # Recompute highlights from the final global line range. This handles
            # three cases correctly: AST blocks (start with empty highlights),
            # k-gram blocks extended upward by the walk (new lines had no highlights),
            # and any coordinate mismatch from the old local→global transform.
            block["line_highlights_a"] = _highlight_lines(full_a_lines, a1, a2, lang)
            block["line_highlights_b"] = _highlight_lines(full_b_lines, b1, b2, lang)

        # Re-sort by strength for the final report now that line-order processing
        # is complete.
        _strength_order = {"high": 0, "medium": 1, "low": 2}
        evidence.sort(key=lambda b: (
            _strength_order.get(b.get("match_strength", "low"), 2),
            b["lines_a"][0],
        ))


        # If the submissions are essentially identical (>=95% similarity score), replace
        # all the individual matched blocks with a single block covering the entire
        # submission. Showing dozens of small fragments when everything is copied is
        # less clear than just saying "the whole thing matches."
        identical = final >= 0.95
        if identical:
            total_a = len(full_source_a.splitlines())
            total_b = len(full_source_b.splitlines())
            evidence = [{
                "file_a":         "full submission",
                "lines_a":        [1, total_a],
                "code_a":         full_source_a,
                "file_b":         "full submission",
                "lines_b":        [1, total_b],
                "code_b":         full_source_b,
                "match_strength": "high",
                "tokens_matched": total_a * 8,
            }]

        return {
            "engine_version":       ENGINE_VERSION,
            "assignment_id":        assignment_id,
            "submission_a":         submission_a_id,
            "submission_b":         submission_b_id,
            "language_detected":    lang,
            "scores":               scores,
            "obfuscation_flags":    [flag_name(f) for f in obfuscation_flags],
            "obfuscation_flags_raw": obfuscation_flags,
            "pdg_triggered":        pdg_triggered,
            "pdg_trigger_reason":   triggered_by,
            "evidence":             evidence,
            "identicalSubmissions": identical,
            "status":               "completed",
            "error":                None,
            "full_source_a":        full_source_a,
            "full_source_b":        full_source_b,
            "file_offsets_a":       file_offsets_a,
            "file_offsets_b":       file_offsets_b,
        }

    except EngineError as e:
        return _error_result(assignment_id, submission_a_id, submission_b_id, str(e), type(e).__name__)
    except Exception as e:
        return _error_result(assignment_id, submission_a_id, submission_b_id,
                             f"Unexpected error: {e}", "InternalError")
    finally:
        if use_temp:
            shutil.rmtree(workdir, ignore_errors=True)



# ---------------------------------------------------------------------------
# PDG trigger logic (ENGINE_DESIGN.md §6)
# ---------------------------------------------------------------------------

def _should_trigger_pdg(scores: dict, obfuscation_flags: list) -> bool:
    """
    Return True if the PDG layer should run on this pair.

    Three independent trigger conditions — any one is sufficient:

    Condition 1 — Gap between AST and k-gram:
        AST subtree similarity > 0.60
        AND k-gram containment < 0.35
        AND (AST subtree − containment) > 0.30
        Meaning: structurally very similar but tokens diverged — deliberate
        obfuscation. This is exactly the case PDG was designed to resolve.

    Condition 2 — Base score in uncertain middle band:
        Combined base score between 0.40 and 0.65.
        Below 0.40 = not suspicious. Above 0.65 = already sufficient signal.
        The middle band is where PDG adds the most value.

    Condition 3 — Specific obfuscation flag combinations:
        method_decomposition
        OR code_reordering
        OR (loop_type_swap AND identifier_renaming together)
        These are the three flags most predictive of semantic-level obfuscation.

    PDG trigger is never based on k-gram failure alone.
    """
    ast_sub    = scores.get("ast_subtree",  0.0)
    cont       = scores.get("containment",  0.0)
    base       = scores.get("weighted_final", 0.0)

    # Condition 1
    if ast_sub > 0.60 and cont < 0.35 and (ast_sub - cont) > 0.30:
        return True

    # Condition 2
    if 0.40 <= base <= 0.65:
        return True

    # Condition 3 — read structured flags
    trigger_flag_names = {
        flag_name(f) for f in obfuscation_flags if is_pdg_trigger_flag(f)
    }
    all_flag_names = {flag_name(f) for f in obfuscation_flags}

    if "method_decomposition" in trigger_flag_names:
        return True
    if "code_reordering" in trigger_flag_names:
        return True
    if "loop_type_swap" in trigger_flag_names and "identifier_renaming" in all_flag_names:
        return True

    return False


def _pdg_trigger_reason(scores: dict, obfuscation_flags: list) -> str:
    """Return a human-readable reason string for why PDG was triggered."""
    ast_sub = scores.get("ast_subtree", 0.0)
    cont    = scores.get("containment", 0.0)
    base    = scores.get("weighted_final", 0.0)

    if ast_sub > 0.60 and cont < 0.35 and (ast_sub - cont) > 0.30:
        return f"condition_1: ast_subtree={ast_sub:.2f} containment={cont:.2f}"
    if 0.40 <= base <= 0.65:
        return f"condition_2: base_score={base:.2f} in [0.40, 0.65]"

    trigger_flag_names = {
        flag_name(f) for f in obfuscation_flags if is_pdg_trigger_flag(f)
    }
    all_flag_names = {flag_name(f) for f in obfuscation_flags}

    if "method_decomposition" in trigger_flag_names:
        return "condition_3: method_decomposition"
    if "code_reordering" in trigger_flag_names:
        return "condition_3: code_reordering"
    if "loop_type_swap" in trigger_flag_names and "identifier_renaming" in all_flag_names:
        return "condition_3: loop_type_swap + identifier_renaming"
    return "unknown"


def batch_analyze(

    submissions: List[dict],
    assignment_id: Optional[str] = None,
    workdir: Optional[Union[str, Path]] = None,
    max_workers: int = 4,
    template_path: Optional[Union[str, Path]] = None,
    skip_same_student: bool = True,
) -> dict:
    """
    Scores every possible pair of submissions against each other and returns
    them ranked from most to least similar. This is intended as a fast screening
    pass over a whole class — it only computes scores, not detailed evidence.
    Call compare() separately on any suspicious pair to get the full line-level
    match report with highlighted code.

    Each submission in the list should be a dict with at least "id" and "path".
    You can also include "student_id" to skip pairs from the same student
    (useful for group submissions), or "group" to skip pairs that share the
    same group label (useful for excluding known reference files).
    """
    if len(submissions) < 2:
        return {
            "engine_version": ENGINE_VERSION,
            "assignment_id":  assignment_id,
            "status":         "completed",
            "total_pairs":    0,
            "pairs":          [],
        }

    use_temp = workdir is None
    if use_temp:
        tmp = tempfile.mkdtemp(prefix="pantheon_batch_")
        workdir = Path(tmp)
    else:
        workdir = Path(workdir)
        workdir.mkdir(parents=True, exist_ok=True)

    template_fp = {}
    if template_path:
        template_fp = _get_template_fingerprints(template_path, workdir / "template")

    processed = {}
    errors = {}

    def _proc(sub):
        sub_id = sub["id"]
        path   = sub["path"]
        work   = workdir / f"sub_{sub_id}"
        try:
            result = _process_submission(path, work)
            if template_fp:
                result["fp"]       = _subtract_fingerprints(result["fp"],       template_fp)
                result["fp_short"] = _subtract_fingerprints(result["fp_short"], template_fp)
            return sub_id, result, None
        except Exception as e:
            return sub_id, None, str(e)

    # Process all submissions in parallel so we don't wait for one at a time.
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_proc, sub): sub for sub in submissions}
        for fut in as_completed(futures):
            sub_id, result, err = fut.result()
            if result is not None:
                processed[sub_id] = result
            else:
                errors[sub_id] = err

    student_map = {}
    group_map = {}
    for sub in submissions:
        if "student_id" in sub:
            student_map[sub["id"]] = sub["student_id"]
        if "group" in sub:
            group_map[sub["id"]] = sub["group"]

    ids = list(processed.keys())
    n   = len(ids)
    total_pairs = n * (n - 1) // 2

    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            id_a = ids[i]
            id_b = ids[j]

            if skip_same_student and student_map:
                sa = student_map.get(id_a)
                sb = student_map.get(id_b)
                if sa and sb and sa == sb:
                    continue

            if group_map:
                ga = group_map.get(id_a)
                gb = group_map.get(id_b)
                if ga and gb and ga == gb:
                    continue

            pa = processed[id_a]
            pb = processed[id_b]

            # Skip pairs in completely different languages — a Java submission compared
            # to a C++ submission would score near zero regardless, and including these
            # pairs just adds noise to the results.
            if pa["lang"] != pb["lang"] and "mixed" not in (pa["lang"], pb["lang"]):
                continue

            scores = weighted_score(pa["fp"], pb["fp"], tok_a=pa["tok_norm"], tok_b=pb["tok_norm"])
            lang = pa["lang"] if pa["lang"] == pb["lang"] else "mixed"

            pairs.append({
                "submission_a":      id_a,
                "submission_b":      id_b,
                "language_detected": lang,
                "score":             scores["weighted_final"],
                "scores":            scores,
            })

    pairs.sort(key=lambda p: p["score"], reverse=True)

    return {
        "engine_version": ENGINE_VERSION,
        "assignment_id":  assignment_id,
        "status":         "completed",
        "total_pairs":    total_pairs,
        "pairs":          pairs,
        "preprocessing_errors": errors if errors else None,
    }


def _merge_evidence(primary: list, supplementary: list) -> list:
    """
    Combines two lists of matched blocks into one. Blocks from the supplementary
    list are only added if they cover regions not already covered by the primary
    list — both the A-side and B-side regions must not overlap. This prevents
    the same section of code from being reported multiple times across the
    three evidence passes.
    """
    if not supplementary:
        return primary

    def overlaps(b1, b2):
        a_overlap = b1["lines_a"][0] <= b2["lines_a"][1] and b2["lines_a"][0] <= b1["lines_a"][1]
        b_overlap = b1["lines_b"][0] <= b2["lines_b"][1] and b2["lines_b"][0] <= b1["lines_b"][1]
        return a_overlap and b_overlap

    merged = list(primary)
    for sup in supplementary:
        if not any(overlaps(sup, p) for p in primary):
            merged.append(sup)

    strength_order = {"high": 0, "medium": 1, "low": 2}
    merged.sort(key=lambda e: strength_order.get(e["match_strength"], 3))
    return merged


def _deduplicate_evidence_1to1(evidence: list) -> list:
    """
    Ensures that each line in each submission belongs to at most one matched block
    in the final report. Without this, the same copied lines could appear in several
    overlapping blocks from the three different evidence passes.

    We process blocks from strongest and largest to weakest. Each block "claims" its
    lines. If a later block overlaps already-claimed lines, those lines are trimmed
    away. If not enough meaningful lines remain after trimming, the block is dropped.
    """
    strength_rank = {"high": 2, "medium": 1, "low": 0}

    def sort_key(b):
        rank = strength_rank.get(b.get("match_strength", "low"), 0)
        size = (b["lines_a"][1] - b["lines_a"][0]) + (b["lines_b"][1] - b["lines_b"][0])
        return (rank, size)

    claimed_a: set = set()
    claimed_b: set = set()
    result = []

    for block in sorted(evidence, key=sort_key, reverse=True):
        a1, a2 = block["lines_a"]
        b1, b2 = block["lines_b"]

        while a1 <= a2 and a1 in claimed_a:
            a1 += 1
        while a2 >= a1 and a2 in claimed_a:
            a2 -= 1
        while b1 <= b2 and b1 in claimed_b:
            b1 += 1
        while b2 >= b1 and b2 in claimed_b:
            b2 -= 1

        if a2 - a1 < 2 or b2 - b1 < 2:
            continue

        trimmed = dict(block)
        trimmed["lines_a"] = [a1, a2]
        trimmed["lines_b"] = [b1, b2]
        result.append(trimmed)
        claimed_a |= set(range(a1, a2 + 1))
        claimed_b |= set(range(b1, b2 + 1))

    result.sort(key=lambda b: (
        -strength_rank.get(b.get("match_strength", "low"), 0),
        b["lines_a"][0],
    ))
    return result


def _highlight_lines(src_lines: list, g1: int, g2: int, lang: str) -> list:
    """
    Return the global line numbers within [g1, g2] that contain real code —
    not blank lines, lone braces, or comments. Called after the upward-extension
    walk so highlights always cover the final extended range, and for AST evidence
    blocks that start with empty highlight lists.

    All returned line numbers are in the same global coordinate space as g1/g2
    (i.e. positions in the concatenated fullCodeA/B string) so the frontend can
    apply them directly without any further conversion.
    """
    _STRUCTURAL_ONLY = {"{", "}", "};", "{;", "});", "})"}
    snippet = "\n".join(src_lines[g1 - 1:g2])
    stripped = strip_comments(snippet, lang)
    result = []
    for i, line in enumerate(stripped.splitlines()):
        content = line.strip()
        if content and content not in _STRUCTURAL_ONLY:
            result.append(g1 + i)
    return result


def _normalize_loops(tokens):
    """
    Returns a copy of the token list where every for, while, and do keyword is
    replaced with a generic LOOP token. This is used for the loop-normalized
    evidence pass only — the original token list is not modified.
    """
    from engine.tokenize.lex import Token
    _LOOP_KW = {"for", "while", "do"}
    return [Token(text="LOOP", line=t.line) if t.text in _LOOP_KW else t
            for t in tokens]


def _blank_header_lines(code: str) -> str:
    """
    Replaces import statements, #include lines, package declarations, and other
    header boilerplate with empty lines in the display version of the code. We blank
    rather than delete so that line numbers in all the evidence blocks remain accurate.
    """
    import re
    _HEADER_RE = re.compile(
        r"^\s*("
        r"import\b"
        r"|package\b"
        r"|from\b.+\bimport\b"
        r"|#\s*include\b"
        r"|#\s*define\b"
        r"|#\s*pragma\b"
        r"|#\s*ifndef\b"
        r"|#\s*ifdef\b"
        r"|#\s*endif\b"
        r"|using\s+namespace\b"
        r"|using\b.+;"
        r"|extern\s+\"C\""
        r")"
    )
    lines = code.splitlines()
    result = ["" if _HEADER_RE.match(line) else line for line in lines]
    return "\n".join(result)


def _build_full_source(original_sources: dict) -> tuple:
    """
    Joins all source files from a submission into one continuous block of text,
    sorted alphabetically by filename (the same order used during canonicalization
    so line numbers stay consistent). Returns the combined text and a dictionary
    mapping each filename to the line offset where it starts in the combined view,
    so per-file line numbers can be converted to global positions in the report.
    """
    ordered = sorted(original_sources.items(), key=lambda x: x[0].lower())
    parts = []
    offsets = {}
    current_line = 1

    for fname, content in ordered:
        offsets[fname] = current_line - 1
        lines = content.splitlines()
        parts.append(content if content.endswith("\n") else content + "\n")
        current_line += len(lines)

    return "".join(parts), offsets


def _get_template_fingerprints(template_path: Union[str, Path], work_dir: Path) -> dict:
    """
    Processes the instructor's template file through the same pipeline as a
    student submission and returns its fingerprints. These are then subtracted
    from both submissions so that starter code everyone copies from the handout
    doesn't contribute to the similarity score.
    """
    try:
        proc = _process_submission(template_path, work_dir)
        return proc["fp"]
    except Exception:
        return {}


def _load_original_sources(work_dir: Path, source_map) -> dict:
    """
    Reads the original (unmodified) source files from the working directory and
    returns their contents as strings keyed by relative filename. These are the
    files the instructor sees in the report — not the normalized version used
    internally. Any file that can't be read is silently skipped.
    """
    result = {}
    for entry in source_map:
        fname = entry.original_file
        if fname in result:
            continue
        try:
            matches = list(work_dir.rglob(Path(fname).name))
            if not matches:
                continue
            best = matches[0]
            for m in matches:
                if str(m).replace("\\", "/").endswith(fname.replace("\\", "/")):
                    best = m
                    break
            result[fname] = best.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
    return result


def _subtract_fingerprints(fp: dict, template_fp: dict) -> dict:
    """
    Removes any fingerprint hashes that appear in the template from a submission's
    fingerprint set. What remains are the fingerprints that belong to the student's
    own code rather than code they received in the handout.
    """
    if not template_fp:
        return fp
    return {h: positions for h, positions in fp.items() if h not in template_fp}


def _error_result(assignment_id, sub_a, sub_b, msg, err_type):
    return {
        "engine_version":    ENGINE_VERSION,
        "assignment_id":     assignment_id,
        "submission_a":      sub_a,
        "submission_b":      sub_b,
        "language_detected": None,
        "scores":            None,
        "obfuscation_flags": [],
        "evidence":          [],
        "status":            "failed",
        "error":             f"{err_type}: {msg}",
    }
