from uuid import UUID

import boto3
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException

from database import get_db_connection
from auth import get_current_user
from config import S3_BUCKET

router = APIRouter(prefix="/submissions", tags=["submissions"])
s3 = boto3.client("s3")


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

    # generate S3 key
    s3_key = f"submissions/{assignment_id}/{user['user_id']}/{file.filename}"

    # upload to S3
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=file_bytes,
        ContentType="application/zip",
    )

    # insert artifact + submission record in DB
    with get_db_connection() as conn:
        artifact_row = conn.execute(
            """
            INSERT INTO artifacts (s3_bucket, s3_key, original_name, content_type, size_bytes)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (s3_bucket, s3_key) DO UPDATE
              SET original_name = EXCLUDED.original_name,
                  size_bytes    = EXCLUDED.size_bytes
            RETURNING artifact_id
            """,
            (S3_BUCKET, s3_key, file.filename, "application/zip", size)
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
            (user['user_id'], str(assignment_id), artifact_row[0], file.filename)
        ).fetchone()

        conn.commit()

    return {
        "submission_id": str(submission_row[0]),
        "s3_key": s3_key,
        "size_bytes": size,
        "message": "Submission uploaded successfully"
    }