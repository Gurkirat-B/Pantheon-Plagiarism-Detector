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

import tempfile
import traceback
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
from engine.similarity.line_matcher import calculate_line_similarity, build_line_mapping, get_full_source_with_mapping
from engine.evidence.evidence import build_evidence
from engine.obfuscation.detect import detect_obfuscation
from engine.similarity.chunk import compute_method_similarity

# k-gram size and winnowing window.
# k=10, W=5: guaranteed detection of any shared sequence >= 14 tokens
# (~4-5 logical lines). Raising k from 8 eliminates generic 8-gram false
# positives (e.g. any code ending a function call with ", NUM);" matches).
_K = 10
_W = 5


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

    return {
        "lang": lang,
        "canon": canon,
        "tok_norm": tok_norm,
        "tok_raw": tok_raw,
        "fp": fp,
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

        fp_a = proc_a["fp"]
        fp_b = proc_b["fp"]

        # subtract template fingerprints if provided
        if template_path:
            template_fp = _get_template_fingerprints(template_path, workdir / "template")
            fp_a = _subtract_fingerprints(fp_a, template_fp)
            fp_b = _subtract_fingerprints(fp_b, template_fp)

        scores = weighted_score(fp_a, fp_b)

        # Method-level similarity: compare submissions method-by-method.
        # Catches reordered code where global scores are diluted by position
        # differences but individual methods still match strongly.
        method_sim = compute_method_similarity(
            proc_a["tok_norm"], proc_b["tok_norm"], gram_k=_K
        )
        scores["method_similarity"] = round(method_sim, 4)

        # If method-level analysis shows significantly stronger similarity
        # than the global score, boost weighted_final accordingly.
        # Threshold: method_sim must exceed global score by >0.15 to trigger,
        # preventing noise from inflating scores on genuinely different code.
        if method_sim > scores["weighted_final"] + 0.15:
            boosted = round(0.65 * method_sim + 0.35 * scores["weighted_final"], 4)
            scores["weighted_final"] = min(1.0, boosted)

        evidence = build_evidence(
            fp_a=fp_a,
            fp_b=fp_b,
            tok_a=proc_a["tok_norm"],
            tok_b=proc_b["tok_norm"],
            source_map_a=proc_a["canon"].source_map,
            source_map_b=proc_b["canon"].source_map,
            k=_K,
            work_dir_a=dir_a,
            work_dir_b=dir_b,
            canonical_text_a=proc_a["canon"].canonical_text,
            canonical_text_b=proc_b["canon"].canonical_text,
        )

        obfuscation_flags = detect_obfuscation(
            tok_a_raw=proc_a["tok_raw"],
            tok_b_raw=proc_b["tok_raw"],
            tok_a_norm=proc_a["tok_norm"],
            tok_b_norm=proc_b["tok_norm"],
            fp_a_norm=fp_a,
            fp_b_norm=fp_b,
        )

        # Calculate line-level similarity for HTML visualization (both directions)
        line_similarity_a = calculate_line_similarity(
            tokens_a=proc_a["tok_norm"],
            tokens_b=proc_b["tok_norm"],
            fp_a=fp_a,
            fp_b=fp_b,
            k=_K,
        )
        line_similarity_b = calculate_line_similarity(
            tokens_a=proc_b["tok_norm"],
            tokens_b=proc_a["tok_norm"],
            fp_a=fp_b,
            fp_b=fp_a,
            k=_K,
        )

        line_mapping = build_line_mapping(
            tokens_a=proc_a["tok_norm"],
            tokens_b=proc_b["tok_norm"],
            line_similarity_a=line_similarity_a,
        )
        line_mapping_b = build_line_mapping(
            tokens_a=proc_b["tok_norm"],
            tokens_b=proc_a["tok_norm"],
            line_similarity_a=line_similarity_b,
        )
        
        # Load original source files for fullCodeA/fullCodeB in the JSON response.
        # Must be called here while dir_a/dir_b still exist.
        original_sources_a = _load_original_sources(dir_a, proc_a["canon"].source_map)
        original_sources_b = _load_original_sources(dir_b, proc_b["canon"].source_map)

        # Get full source code from canonical text
        source_code_a = proc_a["canon"].canonical_text
        source_code_b = proc_b["canon"].canonical_text
        
        source_with_mapping = get_full_source_with_mapping(
            source_code_a=source_code_a,
            source_code_b=source_code_b,
            line_mapping=line_mapping,
        )

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
            "line_mapping":      line_mapping,
            "line_mapping_b":    line_mapping_b,
            "source_with_mapping": source_with_mapping,
        }

    except EngineError as e:
        return _error_result(assignment_id, submission_a_id, submission_b_id, str(e), type(e).__name__)
    except Exception as e:
        return _error_result(assignment_id, submission_a_id, submission_b_id,
                             f"Unexpected error: {e}", "InternalError")


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
            # subtract template
            if template_fp:
                result["fp"] = _subtract_fingerprints(result["fp"], template_fp)
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

            scores = weighted_score(pa["fp"], pb["fp"])

            method_sim = compute_method_similarity(
                pa["tok_norm"], pb["tok_norm"], gram_k=_K
            )
            scores["method_similarity"] = round(method_sim, 4)
            if method_sim > scores["weighted_final"] + 0.15:
                boosted = round(0.65 * method_sim + 0.35 * scores["weighted_final"], 4)
                scores["weighted_final"] = min(1.0, boosted)

            if scores["weighted_final"] < threshold:
                continue

            evidence = build_evidence(
                fp_a=pa["fp"],
                fp_b=pb["fp"],
                tok_a=pa["tok_norm"],
                tok_b=pb["tok_norm"],
                source_map_a=pa["canon"].source_map,
                source_map_b=pb["canon"].source_map,
                k=_K,
                work_dir_a=workdir / f"sub_{id_a}",
                work_dir_b=workdir / f"sub_{id_b}",
            )

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
