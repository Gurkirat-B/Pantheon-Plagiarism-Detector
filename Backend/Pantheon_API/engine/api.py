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
from engine.preprocess.strip_comments import strip_comments
from engine.tokenize.lex import tokenize
from engine.fingerprint.kgrams import winnow, build_fingerprints
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

    # Scale k and W to submission length — short submissions need smaller k
    # to produce any fingerprints, long ones benefit from higher k to reduce
    # noise. W stays roughly k//2 so the guaranteed-match length scales too.
    n_tokens = len(tok_norm)
    dyn_k = max(8, min(15, n_tokens // 200))
    dyn_w = max(4, min(8, dyn_k // 2))

    # Winnowed fingerprints — used for scoring only (fast, statistically accurate)
    fp = winnow(tok_norm, k=dyn_k, window=dyn_w)

    # Full k-grams at k=12 — used for evidence building only (complete coverage,
    # no Winnowing gaps). Higher k=12 means ~5-6 lines minimum match — precise
    # blocks with correct high/medium/low ratings and no missing regions.
    fp_full = build_fingerprints(tok_norm, k=12)

    # Supplementary short pass — catches methods too short for k=12.
    fp_short = build_fingerprints(tok_norm, k=_K_SHORT)

    return {
        "lang":     lang,
        "canon":    canon,
        "tok_norm": tok_norm,
        "tok_raw":  tok_raw,
        "fp":       fp,
        "fp_full":  fp_full,
        "fp_short": fp_short,
        "dyn_k":    dyn_k,
        "dyn_w":    dyn_w,
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

        # subtract template fingerprints from scoring pass if provided
        if template_path:
            template_fp = _get_template_fingerprints(template_path, workdir / "template")
            fp_a = _subtract_fingerprints(fp_a, template_fp)

        scores = weighted_score(fp_a, fp_b, tok_a=proc_a["tok_norm"], tok_b=proc_b["tok_norm"])

        # Scale merge_gap with similarity — high-similarity files have large
        # Winnowing gaps that would otherwise leave unhighlighted regions between
        # matched blocks. A larger merge_gap closes those gaps.
        final = scores["weighted_final"]
        if final >= 0.90:
            merge_gap = 20
        elif final >= 0.70:
            merge_gap = 6
        else:
            merge_gap = 3

        # Evidence uses full k-grams (no Winnowing) for complete coverage.
        # k=12 primary — precise blocks ~5-6 lines minimum.
        # k=5 supplementary — catches short methods too small for k=12.
        evidence = build_evidence(
            proc_a["fp_full"], proc_b["fp_full"],
            tok_a=proc_a["tok_norm"],
            tok_b=proc_b["tok_norm"],
            source_map_a=proc_a["canon"].source_map,
            source_map_b=proc_b["canon"].source_map,
            k=12,
            merge_gap=merge_gap,
            work_dir_a=dir_a,
            work_dir_b=dir_b,
            canonical_text_a=proc_a["canon"].canonical_text,
            canonical_text_b=proc_b["canon"].canonical_text,
            lang=lang,
        )
        evidence_short = build_evidence(
            proc_a["fp_short"], proc_b["fp_short"],
            tok_a=proc_a["tok_norm"],
            tok_b=proc_b["tok_norm"],
            source_map_a=proc_a["canon"].source_map,
            source_map_b=proc_b["canon"].source_map,
            k=_K_SHORT,
            merge_gap=merge_gap,
            work_dir_a=dir_a,
            work_dir_b=dir_b,
            canonical_text_a=proc_a["canon"].canonical_text,
            canonical_text_b=proc_b["canon"].canonical_text,
            lang=lang,
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

        # Strip comments from original sources before building the full code view.
        # strip_comments preserves line count (blanks comment lines) so evidence
        # line numbers remain correct for highlighting.
        stripped_sources_a = {f: strip_comments(c, lang) for f, c in original_sources_a.items()}
        stripped_sources_b = {f: strip_comments(c, lang) for f, c in original_sources_b.items()}

        # Build concatenated full source and per-file line offsets.
        # Evidence lines_a/b are converted from per-file to concatenated line numbers
        # so the frontend can highlight sections in a single unified code view.
        full_source_a, file_offsets_a = _build_full_source(stripped_sources_a)
        full_source_b, file_offsets_b = _build_full_source(stripped_sources_b)

        for block in evidence:
            off_a = file_offsets_a.get(block.get("file_a", ""), 0)
            off_b = file_offsets_b.get(block.get("file_b", ""), 0)
            block["lines_a"] = [block["lines_a"][0] + off_a, block["lines_a"][1] + off_a]
            block["lines_b"] = [block["lines_b"][0] + off_b, block["lines_b"][1] + off_b]

        # For near-identical submissions (>=95%), replace evidence with a single
        # synthetic block covering the entire file — no Winnowing gaps, full match.
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
            "obfuscation_flags":    obfuscation_flags,
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


def batch_analyze(
    submissions: List[dict],
    assignment_id: Optional[str] = None,
    workdir: Optional[Union[str, Path]] = None,
    max_workers: int = 4,
    template_path: Optional[Union[str, Path]] = None,
    skip_same_student: bool = True,
) -> dict:
    """
    Run all-vs-all scoring pass for a set of submissions.

    submissions: list of {
        "id": str,
        "path": str/Path,
        "student_id": str (optional) — skip pairs from the same student,
        "group": str (optional) — skip pairs where both share the same group,
    }
    max_workers: parallel processing workers
    template_path: instructor template — fingerprints subtracted before scoring
    skip_same_student: if True and submissions have "student_id", skip self-comparisons

    Returns ALL pairs ranked by score descending. No threshold filtering.
    Evidence is not built here — call compare() on a specific pair for full details.
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

    # build student_id and group mappings
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

    # step 2: all-vs-all scoring only — no evidence building, no obfuscation detection
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

            # skip if same group (e.g. both are professor reference files)
            if group_map:
                ga = group_map.get(id_a)
                gb = group_map.get(id_b)
                if ga and gb and ga == gb:
                    continue

            pa = processed[id_a]
            pb = processed[id_b]

            # skip cross-language pairs — Java vs C etc. score near zero anyway
            # but explicit skip keeps results clean and avoids wasted work
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
        a1, a2 = block["lines_a"]
        b1, b2 = block["lines_b"]

        # trim A side — skip lines already claimed
        while a1 <= a2 and a1 in claimed_a:
            a1 += 1
        while a2 >= a1 and a2 in claimed_a:
            a2 -= 1

        # trim B side
        while b1 <= b2 and b1 in claimed_b:
            b1 += 1
        while b2 >= b1 and b2 in claimed_b:
            b2 -= 1

        # drop if nothing meaningful left after trimming
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


def _build_full_source(original_sources: dict) -> tuple:
    """
    Concatenate original source files in sorted order (same sort as canonicalize.py)
    into a single string for the full code view.

    Returns (full_source_text, file_offsets) where file_offsets is
    {filename: line_offset} — the number of lines preceding that file in the
    concatenated view. Add this offset to per-file line numbers to get the
    correct line number in the concatenated display.
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
