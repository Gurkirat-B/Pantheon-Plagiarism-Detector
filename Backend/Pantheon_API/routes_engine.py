import tempfile
from pathlib import Path
from pydantic import BaseModel
from uuid import UUID

import boto3
from fastapi import APIRouter, Depends, HTTPException

from database import get_db_connection
from auth import get_current_user
from config import S3_BUCKET
from engine import compare as engine_compare

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

    # Patch metadata so the response refers to submission ids (more useful than filenames)
    result["assignment_id"] = str(assignment_id)
    result["left_submission_id"] = str(body.submission_a_id)
    result["right_submission_id"] = str(body.submission_b_id)

    return result