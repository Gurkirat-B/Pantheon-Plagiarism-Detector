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

@router.post("/repo/{assignment_id}")
async def upload_to_repo(
    assignment_id: UUID,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    if user["role"] != "professor":
        raise HTTPException(status_code=403, detail="Only professors can upload to a repository")

    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are allowed")

    file_bytes = await file.read()

    try:
        outer_zip = zipfile.ZipFile(io.BytesIO(file_bytes))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid .zip archive")

    # Look up the repository linked to this assignment, owned by this professor
    with get_db_connection() as conn:
        repo = conn.execute(
            """
            SELECT repository_id FROM repositories
            WHERE assignment_id = %s AND owner_id = %s
            """,
            (str(assignment_id), str(user["user_id"])),
        ).fetchone()

    if not repo:
        raise HTTPException(status_code=404, detail="No repository found for this assignment")

    repository_id = repo[0]

    # Collect inner zip entries, ignoring directories and macOS junk
    with outer_zip:
        inner_files = [
            info for info in outer_zip.infolist()
            if not info.filename.endswith("/")
            and info.filename.lower().endswith(".zip")
            and not info.filename.lower().startswith("__macosx/")
        ]

        if not inner_files:
            raise HTTPException(status_code=400, detail="Repository ZIP contains no inner .zip files")

        uploaded = []
        with get_db_connection() as conn:
            for info in inner_files:
                inner_bytes = outer_zip.read(info.filename)
                inner_name = info.filename.split("/")[-1]  # strip any directory prefix from path
                s3_key = f"repositories/{repository_id}/{inner_name}"

                try:
                    s3.put_object(
                        Bucket=S3_BUCKET,
                        Key=s3_key,
                        Body=inner_bytes,
                        ContentType="application/zip",
                    )
                except ClientError as e:
                    raise HTTPException(status_code=502, detail=f"Failed to upload {inner_name} to S3: {e}")

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
                    (S3_BUCKET, s3_key, inner_name, "application/zip", len(inner_bytes)),
                ).fetchone()

                upload_row = conn.execute(
                    """
                    INSERT INTO repository_uploads (repository_id, artifact_id, filename)
                    VALUES (%s, %s, %s)
                    RETURNING upload_id
                    """,
                    (str(repository_id), str(artifact_row[0]), inner_name),
                ).fetchone()

                uploaded.append({
                    "upload_id": str(upload_row[0]),
                    "filename": inner_name,
                    "s3_key": s3_key,
                    "size_bytes": len(inner_bytes),
                })

            conn.commit()

    return {
        "repository_id": str(repository_id),
        "uploaded_count": len(uploaded),
        "uploads": uploaded,
        "message": "Repository uploaded successfully"
    }

@router.post("/boilerplate/{assignment_id}")
async def upload_boilerplate(
    assignment_id: UUID,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    if user["role"] != "professor":
        raise HTTPException(status_code=403, detail="Only professors can upload boilerplate")

    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are allowed")

    file_bytes = await file.read()

    try:
        zipfile.ZipFile(io.BytesIO(file_bytes)).close()
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid .zip archive")

    with get_db_connection() as conn:
        repo = conn.execute(
            """
            SELECT repository_id FROM repositories
            WHERE assignment_id = %s AND owner_id = %s
            """,
            (str(assignment_id), str(user["user_id"])),
        ).fetchone()

    if not repo:
        raise HTTPException(status_code=404, detail="No repository found for this assignment")

    repository_id = repo[0]
    filename = file.filename
    s3_key = f"repositories/{repository_id}/{filename}"

    try:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=file_bytes,
            ContentType="application/zip",
        )
    except ClientError as e:
        raise HTTPException(status_code=502, detail=f"Failed to upload boilerplate to S3: {e}")

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
            (S3_BUCKET, s3_key, filename, "application/zip", len(file_bytes)),
        ).fetchone()

        boilerplate_row = conn.execute(
            """
            INSERT INTO assignment_boilerplate (assignment_id, artifact_id, name, uploaded_by)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (assignment_id, name) DO UPDATE
              SET artifact_id = EXCLUDED.artifact_id,
                  uploaded_by = EXCLUDED.uploaded_by,
                  uploaded_at = now()
            RETURNING boilerplate_id, uploaded_at
            """,
            (str(assignment_id), str(artifact_row[0]), filename, str(user["user_id"])),
        ).fetchone()

        conn.commit()

    return {
        "boilerplate_id": str(boilerplate_row[0]),
        "assignment_id": str(assignment_id),
        "name": filename,
        "s3_key": s3_key,
        "size_bytes": len(file_bytes),
        "uploaded_at": boilerplate_row[1].isoformat(),
        "message": "Boilerplate uploaded successfully"
    }


@router.post("/{assignment_id}")
async def upload_submission(
    assignment_id: UUID,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    # check file type
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are allowed")

    # fetch assignment language from DB
    with get_db_connection() as conn:
        assignment_row = conn.execute(
            "SELECT language FROM assignments WHERE assignment_id = %s",
            (str(assignment_id),),
        ).fetchone()

    if not assignment_row:
        raise HTTPException(status_code=404, detail="Assignment not found")

    allowed_exts = {f".{assignment_row[0].lower()}"}

    # read file bytes
    file_bytes = await file.read()
    size = len(file_bytes)

    # verify zip contains at least one source file matching the assignment language
    if not _zip_contains_allowed_source(file_bytes, allowed_exts):
        raise HTTPException(
            status_code=400,
            detail=f"ZIP must contain at least one .{assignment_row[0].lower()} file",
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

