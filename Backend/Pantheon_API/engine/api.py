"""
engine/api.py

This is the only file the backend needs to import from.
Everything else is internal implementation detail.

Usage:
    from engine.api import compare, batch_analyze

    result = compare(
        submission_a_path="/tmp/student1.zip",
        submission_b_path="/tmp/student2.zip",
        submission_a_id="sub_001",
        submission_b_id="sub_002",
        assignment_id="asgn_xyz",
    )

    results = batch_analyze(
        submissions=[
            {"id": "sub_001", "path": "/tmp/s1.zip"},
            {"id": "sub_002", "path": "/tmp/s2.zip"},
        ],
        assignment_id="asgn_xyz",
        threshold=0.4,
    )
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
from engine.tokenize.lex import tokenize
from engine.fingerprint.kgrams import winnow
from engine.similarity.scores import weighted_score
from engine.evidence.evidence import build_evidence
from engine.obfuscation.detect import detect_obfuscation

# k-gram size and winnowing window.
# k=10, W=5: guaranteed detection of any shared sequence >= 14 tokens
# (~4-5 logical lines). Raising k from 8 eliminates generic 8-gram false
# positives (e.g. any code ending a function call with ", NUM);" matches).
_K = 10
_W = 5
_K_SHORT = 5   # second pass for short methods (< 10 tokens) — evidence only
_W_SHORT = 3


def _process_submission(path: Union[str, Path], work_dir: Path, lang_hint: str = "mixed"):
    """
    Full pipeline for one submission: ingest → canonicalize → tokenize → fingerprint.
    Returns everything needed for comparison.
    Called once per submission so batch doesn't reprocess.
    """
    path = Path(path)
    _, detected_lang, source_files = ingest_to_dir(path, work_dir)
    lang = detected_lang if detected_lang != "mixed" else lang_hint

    canon = canonicalize(source_files, work_dir, lang=lang)

    # fp_text: canonical text with output/IO/main boilerplate lines blanked out
    # (same line count as canonical_text so token.line numbers stay aligned).
    # Used exclusively for tokenisation and fingerprinting — never displayed.
    fp_text = blank_output_boilerplate(canon.canonical_text, lang)

    # normalized tokens (IDs → "ID", literals → "NUM"/"STR"/"CHR", access modifiers stripped)
    tok_norm = tokenize(fp_text, lang=lang,
                        normalize_ids=True, normalize_literals=True,
                        normalize_access=True)

    # raw tokens (keep actual names) — used for obfuscation detection
    tok_raw = tokenize(fp_text, lang=lang,
                       normalize_ids=False, normalize_literals=False,
                       normalize_access=False)

    fp = winnow(tok_norm, k=_K, window=_W)

    # second pass with smaller k — catches short methods (< 10 tokens) that
    # produce zero fingerprints under k=10. Used for evidence building only,
    # never for scoring, so it cannot inflate similarity scores.
    fp_short = winnow(tok_norm, k=_K_SHORT, window=_W_SHORT)

    return {
        "lang": lang,
        "canon": canon,
        "tok_norm": tok_norm,
        "tok_raw": tok_raw,
        "fp": fp,
        "fp_short": fp_short,
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
    Compare two submissions (ZIP files or single source files).

    submission_a_id and submission_b_id are opaque DB IDs — engine never
    knows student names, only these IDs.

    template_path: optional path to instructor template code. If provided,
    fingerprints from the template are subtracted from both submissions
    so shared template code doesn't inflate the similarity score.

    Returns a structured dict ready to be inserted into the DB by the backend.
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

        fp_a  = proc_a["fp"]
        fp_b  = proc_b["fp"]
        fp_a_short = proc_a["fp_short"]
        fp_b_short = proc_b["fp_short"]

        # subtract template fingerprints from both passes if provided
        if template_path:
            template_fp = _get_template_fingerprints(template_path, workdir / "template")
            fp_a       = _subtract_fingerprints(fp_a,       template_fp)
            fp_b       = _subtract_fingerprints(fp_b,       template_fp)
            fp_a_short = _subtract_fingerprints(fp_a_short, template_fp)
            fp_b_short = _subtract_fingerprints(fp_b_short, template_fp)

        scores = weighted_score(fp_a, fp_b, tok_a=proc_a["tok_norm"], tok_b=proc_b["tok_norm"])

        # Build method-level evidence blocks. merge_gap=1 means only adjacent
        # lines merge — methods separated by a blank line stay as separate blocks,
        # each with its own HIGH/MEDIUM/LOW strength rating.
        # Two passes: k=10 for full methods, k=5 supplementary for short methods.
        evidence = build_evidence(
            fp_a, fp_b,
            tok_a=proc_a["tok_norm"],
            tok_b=proc_b["tok_norm"],
            source_map_a=proc_a["canon"].source_map,
            source_map_b=proc_b["canon"].source_map,
            k=_K,
            merge_gap=1,
            work_dir_a=dir_a,
            work_dir_b=dir_b,
            canonical_text_a=proc_a["canon"].canonical_text,
            canonical_text_b=proc_b["canon"].canonical_text,
        )
        evidence_short = build_evidence(
            fp_a_short, fp_b_short,
            tok_a=proc_a["tok_norm"],
            tok_b=proc_b["tok_norm"],
            source_map_a=proc_a["canon"].source_map,
            source_map_b=proc_b["canon"].source_map,
            k=_K_SHORT,
            merge_gap=1,
            work_dir_a=dir_a,
            work_dir_b=dir_b,
            canonical_text_a=proc_a["canon"].canonical_text,
            canonical_text_b=proc_b["canon"].canonical_text,
        )
        evidence = _merge_evidence(evidence, evidence_short)
        evidence = _deduplicate_evidence_1to1(evidence)

        obfuscation_flags = detect_obfuscation(
            tok_a_raw=proc_a["tok_raw"],
            tok_b_raw=proc_b["tok_raw"],
            tok_a_norm=proc_a["tok_norm"],
            tok_b_norm=proc_b["tok_norm"],
            fp_a_norm=fp_a,
            fp_b_norm=fp_b,
        )

        # Load original source files for display in the frontend.
        original_sources_a = _load_original_sources(dir_a, proc_a["canon"].source_map)
        original_sources_b = _load_original_sources(dir_b, proc_b["canon"].source_map)

        source_code_a = proc_a["canon"].canonical_text
        source_code_b = proc_b["canon"].canonical_text

        # Derive per-line highlights from the deduplicated evidence — same
        # blocks that appear in Match Blocks view, same lines highlighted in
        # Full Code view. Single source of truth for both views.
        line_highlights_a, line_highlights_b = _build_line_highlights(evidence)

        return {
            "engine_version":    ENGINE_VERSION,
            "assignment_id":     assignment_id,
            "submission_a":      submission_a_id,
            "submission_b":      submission_b_id,
            "language_detected": lang,
            "scores":            scores,
            "obfuscation_flags": obfuscation_flags,
            "evidence":          evidence,
            "status":            "completed",
            "error":             None,
            "source_code_a":     source_code_a,
            "source_code_b":     source_code_b,
            "original_sources_a": original_sources_a,
            "original_sources_b": original_sources_b,
            # Per-line highlight strengths derived from evidence blocks.
            # Both Match Blocks and Full Code views use this single source of truth.
            # Keys are original file line numbers (int), values are "high"/"medium"/"low".
            "line_highlights_a": line_highlights_a,
            "line_highlights_b": line_highlights_b,
        }

    except EngineError as e:
        return _error_result(assignment_id, submission_a_id, submission_b_id, str(e), type(e).__name__)
    except Exception as e:
        return _error_result(assignment_id, submission_a_id, submission_b_id,
                             f"Unexpected error: {e}", "InternalError")
    finally:
        if use_temp:
            shutil.rmtree(workdir, ignore_errors=True)


def batch_analyze(
    submissions: List[dict],
    assignment_id: Optional[str] = None,
    threshold: float = 0.4,
    workdir: Optional[Union[str, Path]] = None,
    max_workers: int = 4,
    template_path: Optional[Union[str, Path]] = None,
    skip_same_student: bool = True,
) -> dict:
    """
    Run all-vs-all comparison for a set of submissions.

    submissions: list of {"id": str, "path": str/Path, "student_id": str (optional)}
    threshold: only include pairs with weighted_final >= threshold
    max_workers: parallel processing workers
    template_path: instructor template to subtract
    skip_same_student: if True and submissions have "student_id", skip self-comparisons

    Returns dict with ranked list of suspicious pairs.
    """
    if len(submissions) < 2:
        return {
            "engine_version": ENGINE_VERSION,
            "assignment_id":  assignment_id,
            "status":         "completed",
            "total_pairs":    0,
            "flagged_pairs":  0,
            "pairs":          [],
        }

    use_temp = workdir is None
    if use_temp:
        tmp = tempfile.mkdtemp(prefix="pantheon_batch_")
        workdir = Path(tmp)
    else:
        workdir = Path(workdir)
        workdir.mkdir(parents=True, exist_ok=True)

    # preprocess template if provided
    template_fp = {}
    if template_path:
        template_fp = _get_template_fingerprints(template_path, workdir / "template")

    # step 1: preprocess all submissions (parallelised)
    processed = {}
    errors = {}

    def _proc(sub):
        sub_id = sub["id"]
        path   = sub["path"]
        work   = workdir / f"sub_{sub_id}"
        try:
            result = _process_submission(path, work)
            # subtract template from both fingerprint passes
            if template_fp:
                result["fp"]       = _subtract_fingerprints(result["fp"],       template_fp)
                result["fp_short"] = _subtract_fingerprints(result["fp_short"], template_fp)
            return sub_id, result, None
        except Exception as e:
            return sub_id, None, str(e)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_proc, sub): sub for sub in submissions}
        for fut in as_completed(futures):
            sub_id, result, err = fut.result()
            if result is not None:
                processed[sub_id] = result
            else:
                errors[sub_id] = err

    # build student_id mapping for skip_same_student
    student_map = {}
    for sub in submissions:
        if "student_id" in sub:
            student_map[sub["id"]] = sub["student_id"]

    ids = list(processed.keys())
    n   = len(ids)
    total_pairs = n * (n - 1) // 2

    # step 2: all-vs-all comparison
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            id_a = ids[i]
            id_b = ids[j]

            # skip if same student
            if skip_same_student and student_map:
                sa = student_map.get(id_a)
                sb = student_map.get(id_b)
                if sa and sb and sa == sb:
                    continue

            pa = processed[id_a]
            pb = processed[id_b]

            scores = weighted_score(pa["fp"], pb["fp"], tok_a=pa["tok_norm"], tok_b=pb["tok_norm"])

            if scores["weighted_final"] < threshold:
                continue

            evidence = build_evidence(
                pa["fp"], pb["fp"],
                tok_a=pa["tok_norm"],
                tok_b=pb["tok_norm"],
                source_map_a=pa["canon"].source_map,
                source_map_b=pb["canon"].source_map,
                k=_K,
                merge_gap=1,
                work_dir_a=workdir / f"sub_{id_a}",
                work_dir_b=workdir / f"sub_{id_b}",
                canonical_text_a=pa["canon"].canonical_text,
                canonical_text_b=pb["canon"].canonical_text,
            )
            evidence_short = build_evidence(
                pa["fp_short"], pb["fp_short"],
                tok_a=pa["tok_norm"],
                tok_b=pb["tok_norm"],
                source_map_a=pa["canon"].source_map,
                source_map_b=pb["canon"].source_map,
                k=_K_SHORT,
                merge_gap=1,
                work_dir_a=workdir / f"sub_{id_a}",
                work_dir_b=workdir / f"sub_{id_b}",
                canonical_text_a=pa["canon"].canonical_text,
                canonical_text_b=pb["canon"].canonical_text,
            )
            evidence = _merge_evidence(evidence, evidence_short)
            evidence = _deduplicate_evidence_1to1(evidence)

            flags = detect_obfuscation(
                tok_a_raw=pa["tok_raw"],
                tok_b_raw=pb["tok_raw"],
                tok_a_norm=pa["tok_norm"],
                tok_b_norm=pb["tok_norm"],
                fp_a_norm=pa["fp"],
                fp_b_norm=pb["fp"],
            )

            lang = pa["lang"] if pa["lang"] == pb["lang"] else "mixed"

            pairs.append({
                "submission_a":      id_a,
                "submission_b":      id_b,
                "language_detected": lang,
                "scores":            scores,
                "obfuscation_flags": flags,
                "evidence":          evidence,
                "status":            "completed",
            })

    pairs.sort(key=lambda p: p["scores"]["weighted_final"], reverse=True)

    return {
        "engine_version": ENGINE_VERSION,
        "assignment_id":  assignment_id,
        "status":         "completed",
        "total_pairs":    total_pairs,
        "flagged_pairs":  len(pairs),
        "threshold_used": threshold,
        "pairs":          pairs,
        "preprocessing_errors": errors if errors else None,
    }


def _merge_evidence(primary: list, supplementary: list) -> list:
    """
    Merge two evidence block lists, removing blocks from supplementary that
    are already covered by a block in primary (overlap on both A and B sides).
    Keeps all primary blocks. Only adds supplementary blocks that cover
    genuinely new line regions not already highlighted by primary.
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
    Enforce 1-to-1 mapping: each line region in A maps to at most one
    region in B, and vice versa.

    Sort by (strength, block size) descending so HIGH + large blocks
    claim their lines first. Any block that overlaps already-claimed
    lines on either side is dropped.

    This eliminates the many-to-many noise where a 2-line boilerplate
    in A matches the same 2-line pattern at every method boundary in B.
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
        a_lines = set(range(block["lines_a"][0], block["lines_a"][1] + 1))
        b_lines = set(range(block["lines_b"][0], block["lines_b"][1] + 1))
        if a_lines & claimed_a or b_lines & claimed_b:
            continue
        result.append(block)
        claimed_a |= a_lines
        claimed_b |= b_lines

    result.sort(key=lambda b: (
        -strength_rank.get(b.get("match_strength", "low"), 0),
        b["lines_a"][0],
    ))
    return result


def _build_line_highlights(evidence: list) -> tuple:
    """
    Derive per-line highlight strength from evidence blocks.
    Each line gets the maximum strength of any block it appears in.
    Returns (highlights_a, highlights_b) where each is {line_number: strength}.
    This is the single source of truth for both Match Blocks and Full Code views.
    """
    strength_rank = {"high": 2, "medium": 1, "low": 0}
    highlights_a = {}
    highlights_b = {}

    for block in evidence:
        strength = block.get("match_strength", "low")
        rank = strength_rank.get(strength, 0)

        for line in range(block["lines_a"][0], block["lines_a"][1] + 1):
            if rank > strength_rank.get(highlights_a.get(line), 0):
                highlights_a[line] = strength

        for line in range(block["lines_b"][0], block["lines_b"][1] + 1):
            if rank > strength_rank.get(highlights_b.get(line), 0):
                highlights_b[line] = strength

    return highlights_a, highlights_b


def _get_template_fingerprints(template_path: Union[str, Path], work_dir: Path) -> dict:
    """Process the instructor template and return its fingerprints."""
    try:
        proc = _process_submission(template_path, work_dir)
        return proc["fp"]
    except Exception:
        return {}


def _load_original_sources(work_dir: Path, source_map) -> dict:
    """
    Load the original (pre-canonicalization) content of every source file
    referenced in the source map.  Returns {relative_filename: full_text}.

    Called while work_dir still exists (inside the compare() try block), so
    file access is guaranteed.  Returns plain strings — safe after temp cleanup.
    Any file that can't be read is silently skipped (graceful degradation).
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
    """Remove template fingerprints from a submission's fingerprints."""
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
