import tempfile
from pathlib import Path
from pydantic import BaseModel
from uuid import UUID

import boto3
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

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
    # info = {UUID(r[0]): (r[1], r[2]) for r in rows}
    info = {r[0]: (r[1], r[2]) for r in rows}

    for sid in (body.submission_a_id, body.submission_b_id):
        if sid not in info or not info[sid][0] or not info[sid][1]:
            raise HTTPException(status_code=404, detail=f"Artifact not found for submission {sid}")

    # Download both zips to a temp dir
    with tempfile.TemporaryDirectory(prefix="pantheon_compare_") as td:
        td_path = Path(td)
        zip_a = td_path / f"{body.submission_a_id}.zip"
        zip_b = td_path / f"{body.submission_b_id}.zip"

        bucket_a, key_a = info[body.submission_a_id]
        bucket_b, key_b = info[body.submission_b_id]

        s3.download_file(bucket_a, key_a, str(zip_a))
        s3.download_file(bucket_b, key_b, str(zip_b))

        # Run engine
        result = engine_compare(zip_a, zip_b)

    # Use short labels in the formatted report; actual UUIDs are exposed separately
    result["submission_a"] = "A"
    result["submission_b"] = "B"

    # Patch metadata so the response refers to submission ids (more useful than filenames)
    result["assignment_id"] = str(assignment_id)
    result["left_submission_id"] = str(body.submission_a_id)
    result["right_submission_id"] = str(body.submission_b_id)

    # Format as human-readable text report
    formatted_report = format_report_for_backend(result)

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

    return PlainTextResponse(content=formatted_report)