import re
import tempfile
from pathlib import Path
from pydantic import BaseModel
from uuid import UUID

import boto3
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from engine import ENGINE_VERSION
from database import get_db_connection
from auth import get_current_user
from config import S3_BUCKET
from engine import compare as engine_compare
from format_output import format_report_for_backend

router = APIRouter(prefix="/engine", tags=["engine"])
s3 = boto3.client("s3")

PRESIGN_EXPIRY = 3600 # 1 hour

class CompareSubmissionsRequest(BaseModel):
    submission_a_id: UUID
    submission_b_id: UUID

def _require_professor(user: dict):
    if user["role"] != "professor":
        raise HTTPException(status_code=403, detail="Professor role required")

def _extract_similarity_score(report_text: str) -> float:
    """
    Parse 'SIMILARITY SCORE      100.0%' from report text.
    """
    m = re.search(r"SIMILARITY SCORE\s+([0-9]+(?:\.[0-9]+)?)%", report_text)
    if not m:
        raise ValueError("Could not parse similarity score from engine report")
    return float(m.group(1))
    
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
            report_text = format_report_for_backend(raw_result)
            score = _extract_similarity_score(report_text)        

        with get_db_connection() as conn:
            # 4) store similarity result
            conn.execute(
                """
                INSERT INTO similarity_results (
                    run_id, score, left_submission_id, right_submission_id
                )
                VALUES (%s, %s, %s, %s)
                """,
                (run_id, score, str(body.submission_a_id), str(body.submission_b_id)),
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
        
                
        # --- PREVIOUS JSON RESPONSE (commented out — revert by uncommenting below and removing the PlainTextResponse return) ---
        # score_decimal = result.get("scores", {}).get("weighted_final", 0.0)
        # score_percentage = f"{round(score_decimal * 100, 1)}%"
        # flag_labels = {
        #     "identifier_renaming":  "Variable / identifier renaming detected",
        #     "loop_type_swap":       "Loop type swap detected (for <> while <> do-while)",
        #     "literal_substitution": "Constant / literal values substituted",
        #     "dead_code_insertion":  "Dead code insertion detected",
        #     "code_reordering":      "Code block reordering detected",
        #     "switch_to_ifelse":     "Switch <> if-else conversion detected",
        #     "ternary_to_ifelse":    "Ternary <> if-else conversion detected",
        #     "exception_wrapping":   "Try-catch exception wrapping added",
        #     "for_each_to_indexed":  "For-each loop converted to indexed for loop",
        # }
        # alterations_detected = [flag_labels.get(f, f) for f in result.get("obfuscation_flags", [])]
        # matching_sections = []
        # for block in result.get("evidence", []):
        #     matching_sections.append({
        #         "match_strength": block.get("strength", block.get("match_strength", "medium")).upper(),
        #         "file_a": block.get("file_a", ""),
        #         "lines_a": block.get("lines_a", []),
        #         "file_b": block.get("file_b", ""),
        #         "lines_b": block.get("lines_b", []),
        #         "code_a": block.get("code_a", ""),
        #         "code_b": block.get("code_b", ""),
        #     })
        # return {
        #     "formatted_report": formatted_report,
        #     "similarity_score": score_percentage,
        #     "alterations_detected": alterations_detected,
        #     "assignment_id": result["assignment_id"],
        #     "left_submission_id": result["left_submission_id"],
        #     "right_submission_id": result["right_submission_id"],
        #     "language": result.get("language_detected", "unknown"),
        #     "matching_sections": matching_sections,
        # }

        '''
        FUTURE — Full Submission View (add these fields to the return dict above when frontend is ready):
            "source_code_a": result.get("source_code_a", ""),
            "source_code_b": result.get("source_code_b", ""),
            "line_mapping":   result.get("line_mapping", []),
            "line_mapping_b": result.get("line_mapping_b", []),
        source_code_a / source_code_b -> full text of each submission, split by \n and render line by line.
        line_mapping  -> flagged lines for submission A: [{ line_a, line_b, color, score, match_count }, ...]
        line_mapping_b -> same for submission B lines.
        Frontend builds a { line_number: color } lookup from the mapping, colors flagged lines, leaves rest white.
        '''

        return PlainTextResponse(report_text)
    
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
    

@router.get("/similarity-score")
def get_similarity_score(
    submission_a_id: UUID,
    submission_b_id: UUID,
    user: dict = Depends(get_current_user),
):
    _require_professor(user)

    if submission_a_id == submission_b_id:
        raise HTTPException(status_code=400, detail="submission_a_id and submission_b_id must be different")

    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT sr.result_id, sr.run_id, sr.score, sr.created_at
            FROM similarity_results sr
            WHERE LEAST(sr.left_submission_id, sr.right_submission_id) = LEAST(%s::uuid, %s::uuid)
              AND GREATEST(sr.left_submission_id, sr.right_submission_id) = GREATEST(%s::uuid, %s::uuid)
            ORDER BY sr.created_at DESC
            LIMIT 1
            """,
            (str(submission_a_id), str(submission_b_id), str(submission_a_id), str(submission_b_id)),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="No similarity result found for specified submission IDs")

    return {
        "submission_a_id": str(submission_a_id),
        "submission_b_id": str(submission_b_id),
        "result_id": str(row[0]),
        "run_id": str(row[1]),
        "score": float(row[2]),
        "created_at": row[3].isoformat() if row[3] else None,
    }