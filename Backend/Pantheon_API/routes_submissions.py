from uuid import UUID

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException

from database import get_db_connection
from auth import get_current_user
from config import S3_BUCKET

router = APIRouter(prefix="/submissions", tags=["submissions"])
s3 = boto3.client("s3")

def _delete_s3_object_if_exists(bucket: str, key: str) -> None:
    """
    Best-effort delete. If object doesn't exist, ignore.
    """
    if not bucket or not key:
        return
    try:
        s3.delete_object(Bucket=bucket, Key=key)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code in ("NoSuchKey", "404", "NotFound"):
            return
        raise

@router.post("/{assignment_id}")
async def upload_submission(
    assignment_id: UUID,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    # check file type
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are allowed")

    # read file bytes
    file_bytes = await file.read()
    size = len(file_bytes)

    # Look up current submission's S3 pointer (if any)
    with get_db_connection() as conn:
        existing = conn.execute(
            """
            SELECT a.s3_bucket, a.s3_key
            FROM submissions s
            LEFT JOIN artifacts a ON a.artifact_id = s.artifact_id
            WHERE s.assignment_id = %s
              AND s.user_id = %s
            """,
            (str(assignment_id), str(user["user_id"])),
        ).fetchone()

    old_bucket = existing[0] if existing else None
    old_key = existing[1] if existing else None

    # 2) Upload NEW object first
    new_key = f"submissions/{assignment_id}/{user['user_id']}/{file.filename}"
    try:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=new_key,
            Body=file_bytes,
            ContentType="application/zip",
        )
    except ClientError as e:
        raise HTTPException(status_code=502, detail=f"Failed to upload to S3: {e}")
    
    # 3) Upsert artifact + submission in DB pointing to NEW object
    with get_db_connection() as conn:
        artifact_row = conn.execute(
            """
            INSERT INTO artifacts (s3_bucket, s3_key, original_name, content_type, size_bytes)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (s3_bucket, s3_key) DO UPDATE
              SET original_name = EXCLUDED.original_name,
                  size_bytes    = EXCLUDED.size_bytes,
                  content_type  = EXCLUDED.content_type
            RETURNING artifact_id
            """,
            (S3_BUCKET, new_key, file.filename, "application/zip", size),
        ).fetchone()

        submission_row = conn.execute(
            """
            INSERT INTO submissions (user_id, assignment_id, status, artifact_id, original_zip_name)
            VALUES (%s, %s, 'accepted', %s, %s)
            ON CONFLICT (user_id, assignment_id) DO UPDATE
              SET artifact_id       = EXCLUDED.artifact_id,
                  original_zip_name = EXCLUDED.original_zip_name,
                  submitted_at      = now(),
                  status            = 'accepted'
            RETURNING submission_id
            """,
            (str(user["user_id"]), str(assignment_id), artifact_row[0], file.filename),
        ).fetchone()

        conn.commit()

    #Delete OLD object after DB commit (best-effort), only if it differs from new
    if old_bucket and old_key:
        if not (old_bucket == S3_BUCKET and old_key == new_key):
            _delete_s3_object_if_exists(old_bucket, old_key)

    return {
        "submission_id": str(submission_row[0]),
        "s3_key": new_key,
        "size_bytes": size,
        "message": "Submission uploaded successfully"
    }