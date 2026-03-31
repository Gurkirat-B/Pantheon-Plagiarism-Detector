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

            raw_result = engine_compare(str(a_zip), str(b_zip))
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

    if len(rows) < 2:
        raise HTTPException(status_code=400, detail="At least 2 submissions with artifacts are required")

    # 2) create analysis run and attach all submissions
    with get_db_connection() as conn:
        run_row = conn.execute(
            """
            INSERT INTO analysis_runs (assignment_id, initiated_by, engine_version, parameters, status)
            VALUES (%s, %s, %s, %s::jsonb, 'running')
            RETURNING run_id
            """,
            (str(assignment_id), str(user["user_id"]), ENGINE_VERSION, '{"mode":"batch_all"}'),
        ).fetchone()
        run_id = run_row[0]

        for row in rows:
            conn.execute(
                "INSERT INTO analysis_run_submissions (run_id, submission_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (run_id, str(row[0])),
            )
        conn.commit()

    # 3) download all ZIPs and run batch_analyze
    try:
        with tempfile.TemporaryDirectory() as td:
            tmp_dir = Path(td)
            submissions_list = []
            for row in rows:
                sub_id, student_id, bucket, key = str(row[0]), str(row[1]), row[2], row[3]
                zip_path = tmp_dir / f"{sub_id}.zip"
                s3.download_file(bucket, key, str(zip_path))
                submissions_list.append({"id": sub_id, "path": str(zip_path), "student_id": student_id})

            batch_result = engine_batch_analyze(submissions_list, assignment_id=str(assignment_id), threshold=0.0)

        # 4) store a similarity_result + evidence row for each flagged pair
        #    format_report_as_json() is called here so both compare and compare-all
        #    store the same schema in similarity_evidence (same as the pairwise path)
        with get_db_connection() as conn:
            for pair in batch_result["pairs"]:
                score = pair["scores"]["weighted_final"]
                json_report = format_report_as_json(pair)
                result_row = conn.execute(
                    """
                    INSERT INTO similarity_results (run_id, score, left_submission_id, right_submission_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING result_id
                    """,
                    (run_id, score, pair["submission_a"], pair["submission_b"]),
                ).fetchone()
                conn.execute(
                    "INSERT INTO similarity_evidence (result_id, evidence_json) VALUES (%s, %s::jsonb)",
                    (result_row[0], json.dumps(json_report)),
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
            "flagged_pairs": batch_result["flagged_pairs"],
            "threshold_used": batch_result["threshold_used"],
            "pairs": [
                {
                    "submission_a": p["submission_a"],
                    "submission_b": p["submission_b"],
                    "score": p["scores"]["weighted_final"],
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


@router.get("/similarity-score")
def get_similarity_score(
    submission_id: UUID,
    user: dict = Depends(get_current_user),
):
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT ON (LEAST(sr.left_submission_id, sr.right_submission_id), GREATEST(sr.left_submission_id, sr.right_submission_id))
                sr.score, sr.left_submission_id, sr.right_submission_id
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
        left_id = str(row[1])
        right_id = str(row[2])
        other_submission_id = right_id if left_id == str(submission_id) else left_id
        results.append({
            "submission_id": str(submission_id),
            "other_submission_id": other_submission_id,
            "score": float(row[0]),
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