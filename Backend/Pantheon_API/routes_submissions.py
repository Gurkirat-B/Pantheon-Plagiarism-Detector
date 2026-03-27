from uuid import UUID

import io
import zipfile
from typing import Iterable
import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException

from database import get_db_connection
from auth import get_current_user
from config import S3_BUCKET

router = APIRouter(prefix="/submissions", tags=["submissions"])
s3 = boto3.client("s3")
ALLOWED_SOURCE_EXTS = {".java", ".cpp", ".c"}

def _zip_contains_allowed_source(file_bytes: bytes, allowed_exts: Iterable[str] = ALLOWED_SOURCE_EXTS) -> bool:
    """
    Returns True if the zip contains at least one file ending in an allowed extension.
    Raises HTTPException for invalid/corrupt zip.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            for info in z.infolist():
                name = info.filename

                # skip directories
                if name.endswith("/"):
                    continue

                # skip common junk
                lowered = name.lower()
                if lowered.startswith("__macosx/") or lowered.endswith(".ds_store"):
                    continue

                # check extension
                dot = lowered.rfind(".")
                ext = lowered[dot:] if dot != -1 else ""
                if ext in allowed_exts:
                    return True

            return False
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid .zip archive")

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

    # verify zip contains at least one allowed source file
    if not _zip_contains_allowed_source(file_bytes):
        raise HTTPException(
            status_code=400,
            detail="ZIP must contain at least one .java, .cpp, or .c file",
        )
    
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

@router.get("/repo/uploads")
def get_uploads(user: dict = Depends(get_current_user)):
    if user["role"] != "professor":
        raise HTTPException(status_code=403, detail="Only professors can view repository uploads")

    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT ru.upload_id, ru.filename, ru.uploaded_at
            FROM repository_uploads ru
            JOIN repositories r ON r.repository_id = ru.repository_id
            WHERE r.owner_id = %s
            ORDER BY ru.uploaded_at DESC
            """,
            (str(user["user_id"]),),
        ).fetchall()

    return {
        "uploads": [
            {"upload_id": str(row[0]), "filename": row[1], "uploaded_at": row[2].isoformat()}
            for row in rows
        ]
    }

@router.post("/repo")
async def upload_to_repo(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    if user["role"] != "professor":
        raise HTTPException(status_code=403, detail="Only professors can upload to a repository")

    # check file type
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are allowed")

    # read file bytes
    file_bytes = await file.read()
    size = len(file_bytes)

    # verify zip contains at least one allowed source file
    if not _zip_contains_allowed_source(file_bytes):
        raise HTTPException(
            status_code=400,
            detail="ZIP must contain at least one .java, .cpp, or .c file",
        )

    # look up the repository belonging to this professor
    with get_db_connection() as conn:
        repo = conn.execute(
            "SELECT repository_id FROM repositories WHERE owner_id = %s",
            (str(user["user_id"]),),
        ).fetchone()

    if not repo:
        raise HTTPException(status_code=404, detail="No repository found for this user")

    repository_id = repo[0]

    # upload to S3
    new_key = f"repositories/{repository_id}/{file.filename}"
    try:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=new_key,
            Body=file_bytes,
            ContentType="application/zip",
        )
    except ClientError as e:
        raise HTTPException(status_code=502, detail=f"Failed to upload to S3: {e}")

    # upsert artifact, insert new repository_upload record
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

        upload_row = conn.execute(
            """
            INSERT INTO repository_uploads (repository_id, artifact_id, filename)
            VALUES (%s, %s, %s)
            RETURNING upload_id
            """,
            (str(repository_id), str(artifact_row[0]), file.filename),
        ).fetchone()

        conn.commit()

    return {
        "upload_id": str(upload_row[0]),
        "s3_key": new_key,
        "size_bytes": size,
        "message": "File uploaded to repository successfully"
    }