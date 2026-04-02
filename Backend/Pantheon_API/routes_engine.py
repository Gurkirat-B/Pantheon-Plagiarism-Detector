import json
import tempfile
from pathlib import Path
from pydantic import BaseModel
from uuid import UUID

import boto3
from fastapi import APIRouter, Depends, HTTPException

from engine import ENGINE_VERSION
from database import get_db_connection
from auth import get_current_user
from config import S3_BUCKET
from engine import compare as engine_compare, batch_analyze as engine_batch_analyze
from format_output import format_report_as_json
# from format_output import format_report_for_backend  # plain-text version, kept for reference

router = APIRouter(prefix="/engine", tags=["engine"])
s3 = boto3.client("s3")

PRESIGN_EXPIRY = 3600 # 1 hour

class CompareSubmissionsRequest(BaseModel):
    submission_a_id: UUID
    submission_b_id: UUID

def _require_professor(user: dict):
    if user["role"] != "professor":
        raise HTTPException(status_code=403, detail="Professor role required")

# def _extract_similarity_score(report_text: str) -> float:
#     """Parse 'SIMILARITY SCORE      100.0%' from plain-text report."""
#     import re
#     m = re.search(r"SIMILARITY SCORE\s+([0-9]+(?:\.[0-9]+)?)%", report_text)
#     if not m:
#         raise ValueError("Could not parse similarity score from engine report")
#     return float(m.group(1))
    
@router.get("/assignments/{assignment_id}/submissions")
def list_submissions(assignment_id: UUID, user: dict = Depends(get_current_user)):
    _require_professor(user)
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT s.submission_id, s.user_id, u.email,
                   s.original_zip_name, s.submitted_at, s.status,
                   a.s3_bucket, a.s3_key
            FROM submissions s
            JOIN users u ON u.user_id = s.user_id
            LEFT JOIN artifacts a ON a.artifact_id = s.artifact_id
            WHERE s.assignment_id = %s
            ORDER BY s.submitted_at
            """,
            (assignment_id,)
        ).fetchall()
    
    return [
        {
            "submission_id": str(r[0]),
            "user_id": str(r[1]),
            "email": r[2],
            "original_zip_name": r[3],
            "submitted_at": r[4].isoformat() if r[4] else None,
            "status": r[5],
            "s3_bucket": r[6],
            "s3_key": r[7],
        }
        for r in rows
    ]

@router.get("/assignments/{assignment_id}/submissions/{submission_id}/download")
def download_submission(
    assignment_id: UUID,
    submission_id: UUID,
    user: dict = Depends(get_current_user),
):
    _require_professor(user)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT a.s3_bucket, a.s3_key
            FROM submissions s
            JOIN artifacts a ON a.artifact_id = s.artifact_id
            WHERE s.submission_id = %s AND s.assignment_id = %s
            """,
            (submission_id, assignment_id)
        ).fetchone()
    
    if not row or not row[0] or not row[1]:
        raise HTTPException(status_code=404, detail="Submission or artifact not found")
    
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": row[0], "Key": row[1]},
        ExpiresIn=PRESIGN_EXPIRY,
    )
    return {"download_url": url, "expires_in": PRESIGN_EXPIRY}

@router.post("/assignments/{assignment_id}/compare")
def compare_two_submissions(
    assignment_id: UUID,
    body: CompareSubmissionsRequest,
    user: dict = Depends(get_current_user),
):
    _require_professor(user)

    if body.submission_a_id == body.submission_b_id:
        raise HTTPException(status_code=400, detail="submission_a_id and submission_b_id must be different")

    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT s.submission_id, a.s3_bucket, a.s3_key
            FROM submissions s
            JOIN artifacts a ON a.artifact_id = s.artifact_id
            WHERE s.assignment_id = %s
              AND s.submission_id IN (%s, %s)
            """,
            (assignment_id, body.submission_a_id, body.submission_b_id),
        ).fetchall()

        if len(rows) != 2:
            raise HTTPException(
                status_code=404,
                detail="One or both submissions not found for this assignment, or missing artifact.",
            )
    
        # Map submission_id -> (bucket, key)
        # submission_id -> {"bucket": ..., "key": ...}
        info = {str(r[0]): {"bucket": r[1], "key": r[2]} for r in rows}

        a_info = info.get(str(body.submission_a_id))
        b_info = info.get(str(body.submission_b_id))
        if not a_info or not b_info:
            raise HTTPException(status_code=404, detail="Submission mapping failed")

        # 1) create analysis run
        run_row = conn.execute(
            """
            INSERT INTO analysis_runs (assignment_id, initiated_by, engine_version, parameters, status)
            VALUES (%s, %s, %s, %s::jsonb, 'running')
            RETURNING run_id
            """,
            (
                str(assignment_id),
                str(user["user_id"]),
                ENGINE_VERSION,
                (
                    '{"mode":"submission_submission",'
                    f'"submission_a_id":"{body.submission_a_id}",'
                    f'"submission_b_id":"{body.submission_b_id}"}}'
                ),
            ),
        ).fetchone()
        run_id = run_row[0]

        # 2) attach run -> submissions
        conn.execute(
            """
            INSERT INTO analysis_run_submissions (run_id, submission_id)
            VALUES (%s, %s), (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (run_id, str(body.submission_a_id), run_id, str(body.submission_b_id)),
        )
        conn.commit()

    # 3) run engine outside transaction
    try:
        with tempfile.TemporaryDirectory() as td:
            tmp_dir = Path(td)

            a_zip = tmp_dir / "submission_a.zip"
            b_zip = tmp_dir / "submission_b.zip"

            s3.download_file(a_info["bucket"], a_info["key"], str(a_zip))
            s3.download_file(b_info["bucket"], b_info["key"], str(b_zip))

            # fetch boilerplate for this assignment (if any) and subtract it
            template_path = None
            with get_db_connection() as conn:
                bp_row = conn.execute(
                    """
                    SELECT a.s3_bucket, a.s3_key
                    FROM assignment_boilerplate ab
                    JOIN artifacts a ON a.artifact_id = ab.artifact_id
                    WHERE ab.assignment_id = %s
                    ORDER BY ab.uploaded_at DESC
                    LIMIT 1
                    """,
                    (str(assignment_id),),
                ).fetchone()
            if bp_row:
                bp_zip = tmp_dir / "boilerplate.zip"
                s3.download_file(bp_row[0], bp_row[1], str(bp_zip))
                template_path = str(bp_zip)

            raw_result = engine_compare(str(a_zip), str(b_zip), template_path=template_path)
            json_report = format_report_as_json(raw_result)
            score = json_report["similarityScore"] / 100.0

        with get_db_connection() as conn:
            # 4) store similarity result
            result_row = conn.execute(
                """
                INSERT INTO similarity_results (
                    run_id, score, left_submission_id, right_submission_id
                )
                VALUES (%s, %s, %s, %s)
                RETURNING result_id
                """,
                (run_id, score, str(body.submission_a_id), str(body.submission_b_id)),
            ).fetchone()
            result_id = result_row[0]

            # 4b) store JSON report as evidence
            conn.execute(
                """
                INSERT INTO similarity_evidence (result_id, evidence_json)
                VALUES (%s, %s::jsonb)
                """,
                (result_id, json.dumps(json_report)),
            )

            # 5) mark run complete
            conn.execute(
                """
                UPDATE analysis_runs
                SET status = 'completed', completed_at = now()
                WHERE run_id = %s
                """,
                (run_id,),
            )
            conn.commit()

        # --- PLAIN TEXT RESPONSE (commented out — revert by uncommenting and removing the json_report return) ---
        # report_text = format_report_for_backend(raw_result)
        # return PlainTextResponse(report_text)

        return json_report
    
    except Exception as e:
        with get_db_connection() as conn:
            conn.execute(
                """
                UPDATE analysis_runs
                SET status = 'failed', completed_at = now()
                WHERE run_id = %s
                """,
                (run_id,),
            )
            conn.commit()
        raise HTTPException(status_code=500, detail=f"Comparison failed: {e}")
    
@router.post("/assignments/{assignment_id}/compare-all")
def compare_all(
    assignment_id: UUID,
    user: dict = Depends(get_current_user),
):
    _require_professor(user)

    # 1) fetch all submissions with artifacts for this assignment
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT s.submission_id, s.user_id, a.s3_bucket, a.s3_key
            FROM submissions s
            JOIN artifacts a ON a.artifact_id = s.artifact_id
            WHERE s.assignment_id = %s
            """,
            (str(assignment_id),),
        ).fetchall()

        # check for boilerplate upload for this assignment
        boilerplate_row = conn.execute(
            """
            SELECT ab.boilerplate_id, a.s3_bucket, a.s3_key
            FROM assignment_boilerplate ab
            JOIN artifacts a ON a.artifact_id = ab.artifact_id
            WHERE ab.assignment_id = %s
            ORDER BY ab.uploaded_at DESC
            LIMIT 1
            """,
            (str(assignment_id),),
        ).fetchone()

    if len(rows) < 2:
        raise HTTPException(status_code=400, detail="At least 2 submissions with artifacts are required")

    has_boilerplate = boilerplate_row is not None
    parameters_json = json.dumps({"mode": "batch_all", "boilerplate": has_boilerplate})

    # 2) create analysis run and attach all submissions
    with get_db_connection() as conn:
        run_row = conn.execute(
            """
            INSERT INTO analysis_runs (assignment_id, initiated_by, engine_version, parameters, status)
            VALUES (%s, %s, %s, %s::jsonb, 'running')
            RETURNING run_id
            """,
            (str(assignment_id), str(user["user_id"]), ENGINE_VERSION, parameters_json),
        ).fetchone()
        run_id = run_row[0]

        for row in rows:
            conn.execute(
                "INSERT INTO analysis_run_submissions (run_id, submission_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (run_id, str(row[0])),
            )
        conn.commit()

    # 3) download all ZIPs, run batch_analyze for ranking, then full compare per pair
    try:
        with tempfile.TemporaryDirectory() as td:
            tmp_dir = Path(td)
            submissions_list = []
            sub_paths = {}
            for row in rows:
                sub_id, student_id, bucket, key = str(row[0]), str(row[1]), row[2], row[3]
                zip_path = tmp_dir / f"{sub_id}.zip"
                s3.download_file(bucket, key, str(zip_path))
                submissions_list.append({"id": sub_id, "path": str(zip_path), "student_id": student_id})
                sub_paths[sub_id] = str(zip_path)

            template_path = None
            if has_boilerplate:
                bp_zip = tmp_dir / "boilerplate.zip"
                s3.download_file(boilerplate_row[1], boilerplate_row[2], str(bp_zip))
                template_path = str(bp_zip)

            batch_result = engine_batch_analyze(
                submissions_list,
                assignment_id=str(assignment_id),
                template_path=template_path,
            )

            # Run full engine_compare in parallel for every pair so that evidence,
            # full source code and match blocks are stored in the DB.
            # ZIPs are already on disk — no re-download needed.
            def _full_compare(pair):
                a_id = pair["submission_a"]
                b_id = pair["submission_b"]
                try:
                    raw = engine_compare(
                        sub_paths[a_id], sub_paths[b_id],
                        submission_a_id=a_id,
                        submission_b_id=b_id,
                        assignment_id=str(assignment_id),
                        template_path=template_path,
                    )
                    return (a_id, b_id), format_report_as_json(raw)
                except Exception:
                    return (a_id, b_id), None

            from concurrent.futures import ThreadPoolExecutor, as_completed as _as_completed
            pair_reports = {}
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = {pool.submit(_full_compare, p): p for p in batch_result["pairs"]}
                for fut in _as_completed(futures):
                    key, report = fut.result()
                    if report:
                        pair_reports[key] = report

        # 4) store similarity_result + evidence for every pair
        with get_db_connection() as conn:
            for pair in batch_result["pairs"]:
                a_id = pair["submission_a"]
                b_id = pair["submission_b"]
                result_row = conn.execute(
                    """
                    INSERT INTO similarity_results (run_id, score, left_submission_id, right_submission_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING result_id
                    """,
                    (run_id, pair["score"], a_id, b_id),
                ).fetchone()
                report = pair_reports.get((a_id, b_id))
                if report:
                    conn.execute(
                        "INSERT INTO similarity_evidence (result_id, evidence_json) VALUES (%s, %s::jsonb)",
                        (result_row[0], json.dumps(report)),
                    )
            conn.execute(
                "UPDATE analysis_runs SET status = 'completed', completed_at = now() WHERE run_id = %s",
                (run_id,),
            )
            compared_ids = list({p["submission_a"] for p in batch_result["pairs"]} | {p["submission_b"] for p in batch_result["pairs"]})
            if compared_ids:
                conn.execute(
                    "UPDATE submissions SET has_comparison = TRUE WHERE submission_id = ANY(%s::uuid[])",
                    (compared_ids,),
                )
            conn.commit()

        return {
            "run_id": str(run_id),
            "assignment_id": str(assignment_id),
            "total_pairs": batch_result["total_pairs"],
            "pairs": [
                {
                    "submission_a": p["submission_a"],
                    "submission_b": p["submission_b"],
                    "score": p["score"],
                    "language_detected": p["language_detected"],
                }
                for p in batch_result["pairs"]
            ],
            "preprocessing_errors": batch_result.get("preprocessing_errors"),
        }

    except Exception as e:
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE analysis_runs SET status = 'failed', completed_at = now() WHERE run_id = %s",
                (run_id,),
            )
            conn.commit()
        raise HTTPException(status_code=500, detail=f"Batch comparison failed: {e}")


@router.post("/assignments/{assignment_id}/compare-repo")
def compare_repo(
    assignment_id: UUID,
    user: dict = Depends(get_current_user),
):
    _require_professor(user)

    with get_db_connection() as conn:
        # Fetch all repo uploads for the repository linked to this assignment
        repo_rows = conn.execute(
            """
            SELECT ru.upload_id, ru.filename, a.s3_bucket, a.s3_key
            FROM repository_uploads ru
            JOIN artifacts a ON a.artifact_id = ru.artifact_id
            JOIN repositories r ON r.repository_id = ru.repository_id
            WHERE r.assignment_id = %s AND r.owner_id = %s
            """,
            (str(assignment_id), str(user["user_id"])),
        ).fetchall()

        # Fetch all student submissions for this assignment
        sub_rows = conn.execute(
            """
            SELECT s.submission_id, a.s3_bucket, a.s3_key
            FROM submissions s
            JOIN artifacts a ON a.artifact_id = s.artifact_id
            WHERE s.assignment_id = %s
            """,
            (str(assignment_id),),
        ).fetchall()

        # Check for boilerplate upload for this assignment
        boilerplate_row = conn.execute(
            """
            SELECT a.s3_bucket, a.s3_key
            FROM assignment_boilerplate ab
            JOIN artifacts a ON a.artifact_id = ab.artifact_id
            WHERE ab.assignment_id = %s
            ORDER BY ab.uploaded_at DESC
            LIMIT 1
            """,
            (str(assignment_id),),
        ).fetchone()

    if not repo_rows:
        raise HTTPException(status_code=404, detail="No repository uploads found for this assignment")
    if not sub_rows:
        raise HTTPException(status_code=400, detail="No student submissions found for this assignment")

    with get_db_connection() as conn:
        run_row = conn.execute(
            """
            INSERT INTO analysis_runs (assignment_id, initiated_by, engine_version, parameters, status)
            VALUES (%s, %s, %s, %s::jsonb, 'running')
            RETURNING run_id
            """,
            (str(assignment_id), str(user["user_id"]), ENGINE_VERSION, '{"mode":"repo_submission"}'),
        ).fetchone()
        run_id = run_row[0]

        for repo_row in repo_rows:
            conn.execute(
                "INSERT INTO analysis_run_repository_uploads (run_id, upload_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (run_id, str(repo_row[0])),
            )
        for sub_row in sub_rows:
            conn.execute(
                "INSERT INTO analysis_run_submissions (run_id, submission_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (run_id, str(sub_row[0])),
            )
        conn.commit()

    try:
        pairs = []
        with tempfile.TemporaryDirectory() as td:
            tmp_dir = Path(td)

            # Pre-download all submission zips once
            sub_paths = {}
            for sub_row in sub_rows:
                sub_id, bucket, key = str(sub_row[0]), sub_row[1], sub_row[2]
                zip_path = tmp_dir / f"sub_{sub_id}.zip"
                s3.download_file(bucket, key, str(zip_path))
                sub_paths[sub_id] = zip_path

            template_path = None
            if boilerplate_row:
                bp_zip = tmp_dir / "boilerplate.zip"
                s3.download_file(boilerplate_row[0], boilerplate_row[1], str(bp_zip))
                template_path = str(bp_zip)

            for repo_row in repo_rows:
                upload_id, repo_bucket, repo_key = (
                    str(repo_row[0]), repo_row[2], repo_row[3]
                )
                repo_zip = tmp_dir / f"repo_{upload_id}.zip"
                s3.download_file(repo_bucket, repo_key, str(repo_zip))

                for sub_row in sub_rows:
                    sub_id = str(sub_row[0])
                    sub_zip = sub_paths[sub_id]

                    if template_path:
                        raw_result = engine_compare(
                            str(repo_zip),
                            str(sub_zip),
                            submission_a_id=upload_id,
                            submission_b_id=sub_id,
                            assignment_id=str(assignment_id),
                            template_path=template_path,
                        )
                    else:
                        raw_result = engine_compare(
                            str(repo_zip),
                            str(sub_zip),
                            submission_a_id=upload_id,
                            submission_b_id=sub_id,
                            assignment_id=str(assignment_id),
                        )
                    json_report = format_report_as_json(raw_result)
                    score = json_report["similarityScore"] / 100.0

                    pairs.append({
                        "upload_id": upload_id,
                        "submission_id": sub_id,
                        "score": score,
                        "json_report": json_report,
                    })

        with get_db_connection() as conn:
            for pair in pairs:
                result_row = conn.execute(
                    """
                    INSERT INTO similarity_results (
                        run_id, score, left_upload_id, right_submission_id, prof_comparison
                    )
                    VALUES (%s, %s, %s, %s, TRUE)
                    RETURNING result_id
                    """,
                    (run_id, pair["score"], pair["upload_id"], pair["submission_id"]),
                ).fetchone()
                conn.execute(
                    """
                    INSERT INTO similarity_evidence (result_id, evidence_json, prof_comparison)
                    VALUES (%s, %s::jsonb, TRUE)
                    """,
                    (result_row[0], json.dumps(pair["json_report"])),
                )
            conn.execute(
                "UPDATE analysis_runs SET status = 'completed', completed_at = now() WHERE run_id = %s",
                (run_id,),
            )
            conn.commit()

        return {
            "run_id": str(run_id),
            "assignment_id": str(assignment_id),
            "total_pairs": len(pairs),
            "pairs": [
                {
                    "upload_id": p["upload_id"],
                    "submission_id": p["submission_id"],
                    "score": p["score"],
                }
                for p in pairs
            ],
        }

    except Exception as e:
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE analysis_runs SET status = 'failed', completed_at = now() WHERE run_id = %s",
                (run_id,),
            )
            conn.commit()
        raise HTTPException(status_code=500, detail=f"Repo comparison failed: {e}")


@router.get("/similarity-score")
def get_similarity_score(
    submission_id: UUID,
    user: dict = Depends(get_current_user),
):
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT ON (LEAST(sr.left_submission_id, sr.right_submission_id), GREATEST(sr.left_submission_id, sr.right_submission_id))
                sr.score, sr.left_submission_id, sr.right_submission_id, sr.prof_comparison
            FROM similarity_results sr
            WHERE sr.left_submission_id = %s::uuid
               OR sr.right_submission_id = %s::uuid
            ORDER BY LEAST(sr.left_submission_id, sr.right_submission_id), GREATEST(sr.left_submission_id, sr.right_submission_id), sr.created_at DESC
            """,
            (str(submission_id), str(submission_id)),
        ).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="No similarity results found for the specified submission ID")

    results = []
    for row in rows:
        left_id = str(row[1]) if row[1] else None
        right_id = str(row[2]) if row[2] else None
        other_submission_id = right_id if left_id == str(submission_id) else left_id
        results.append({
            "submission_id": str(submission_id),
            "other_submission_id": other_submission_id,
            "score": float(row[0]),
            "prof_comparison": row[3],
        })

    return results

@router.get("/similarity-report")
def get_similarity_report(
    submission_id: UUID,
    user: dict = Depends(get_current_user),
):
    _require_professor(user)

    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT ON (LEAST(sr.left_submission_id, sr.right_submission_id), GREATEST(sr.left_submission_id, sr.right_submission_id))
                se.evidence_json
            FROM similarity_results sr
            JOIN similarity_evidence se ON se.result_id = sr.result_id
            WHERE sr.left_submission_id = %s::uuid
               OR sr.right_submission_id = %s::uuid
            ORDER BY LEAST(sr.left_submission_id, sr.right_submission_id), GREATEST(sr.left_submission_id, sr.right_submission_id), sr.created_at DESC, se.created_at DESC
            """,
            (str(submission_id), str(submission_id)),
        ).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="No similarity reports found for the specified submission ID")

    return [row[0] for row in rows]