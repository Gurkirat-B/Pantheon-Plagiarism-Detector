from uuid import UUID
from datetime import datetime, timezone
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from psycopg.types.json import Jsonb

from database import get_db_connection
from auth import get_current_user

router = APIRouter(prefix="/assignments", tags=["assignments"])


def _require_professor(user: dict):
    if user["role"] != "professor":
        raise HTTPException(status_code=403, detail="Professor role required")


def _check_due_date_not_in_past(due_date: datetime | None):
    if due_date is None:
        return
    now = datetime.now(timezone.utc)
    # make due_date offset-aware if it isn't already
    if due_date.tzinfo is None:
        due_date = due_date.replace(tzinfo=timezone.utc)
    if due_date <= now:
        raise HTTPException(status_code=400, detail="due_date must be in the future")

# Enum for supported languages
class SupportedLanguage(str, Enum):
    java = "java"
    cpp = "cpp"
    c = "c"

class CreateAssignmentRequest(BaseModel):
    course_id: UUID
    title: str
    language: str
    due_date: datetime | None = None

# Request model for editing an assignment
class EditAssignmentRequest(BaseModel):
    title: str
    due_date: str  # ISO 8601 format for dates (e.g., "2023-04-01T23:59:59Z")
    language: SupportedLanguage

@router.post("/")
def create_assignment(body: CreateAssignmentRequest, user: dict = Depends(get_current_user)):
    _require_professor(user)

    allowed_languages = {"java", "c", "cpp"}
    if body.language not in allowed_languages:
        raise HTTPException(
            status_code=400,
            detail=f"language must be one of {sorted(allowed_languages)}"
        )

    _check_due_date_not_in_past(body.due_date)

    with get_db_connection() as conn:
        course = conn.execute(
            "SELECT course_id FROM courses WHERE course_id = %s",
            (str(body.course_id),)
        ).fetchone()

        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        row = conn.execute(
            """
            INSERT INTO assignments (course_id, title, due_date, language)
            VALUES (%s, %s, %s, %s)
            RETURNING assignment_id, course_id, title, language, due_date, created_at
            """,
            (
                str(body.course_id),
                body.title,
                body.due_date,
                body.language,
            )
        ).fetchone()
        conn.commit()

    return {
        "assignment_id": str(row[0]),
        "course_id": str(row[1]),
        "title": row[2],
        "language": row[3],
        "due_date": row[4].isoformat() if row[4] else None,
        "created_at": row[5].isoformat() if row[5] else None,
        "message": "Assignment created successfully"
    }

@router.get("/{assignment_id}")
def get_assignment(assignment_id: UUID, user: dict = Depends(get_current_user)):
    _require_professor(user)

    with get_db_connection() as conn:
        assignment = conn.execute(
            """
            SELECT assignment_id, course_id, title, language, due_date, created_at
            FROM assignments
            WHERE assignment_id = %s
            """,
            (str(assignment_id),)
        ).fetchone()

        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        submissions = conn.execute(
            """
            SELECT s.submission_id, s.user_id, u.email,
                   s.original_zip_name, s.submitted_at, s.status,
                   a.s3_bucket, a.s3_key
            FROM submissions s
            JOIN users u ON u.user_id = s.user_id
            LEFT JOIN artifacts a ON a.artifact_id = s.artifact_id
            WHERE s.assignment_id = %s
            ORDER BY s.submitted_at DESC
            """,
            (str(assignment_id),)
        ).fetchall()

    return {
        "assignment_id": str(assignment[0]),
        "course_id": str(assignment[1]),
        "title": assignment[2],
        "language": assignment[3],
        "due_date": assignment[4].isoformat() if assignment[4] else None,
        "created_at": assignment[5].isoformat() if assignment[5] else None,
        "submissions": [
            {
                "submission_id": str(s[0]),
                "user_id": str(s[1]),
                "email": s[2],
                "original_zip_name": s[3],
                "submitted_at": s[4].isoformat() if s[4] else None,
                "status": s[5],
                "s3_bucket": s[6],
                "s3_key": s[7],
            }
            for s in submissions
        ]
    }

@router.put("/{assignment_id}")
def edit_assignment(
    assignment_id: UUID,
    body: EditAssignmentRequest,
    user: dict = Depends(get_current_user),
):
    """
    Edit an existing assignment. The professor can update the title, due date,
    and programming language for the assignment.
    """
    _require_professor(user)

    try:
        due_date_parsed = datetime.fromisoformat(body.due_date) if body.due_date else None
    except ValueError:
        raise HTTPException(status_code=400, detail="due_date is not a valid ISO 8601 datetime")

    _check_due_date_not_in_past(due_date_parsed)

    with get_db_connection() as conn:
        # Check if the assignment exists and if the professor is authorized to edit it
        assignment = conn.execute(
            """
            SELECT a.assignment_id
            FROM assignments a
            JOIN courses c ON a.course_id = c.course_id
            JOIN enrollments e ON e.course_id = c.course_id
            WHERE a.assignment_id = %s
              AND e.user_id = %s
            """,
            (str(assignment_id), str(user["user_id"])),
        ).fetchone()

        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found or not authorized")

        # Update the assignment's fields
        conn.execute(
            """
            UPDATE assignments
            SET title = %s,
                due_date = %s,
                language = %s
            WHERE assignment_id = %s
            """,
            (body.title, body.due_date, body.language, str(assignment_id)),
        )

        conn.commit()

    return {"assignment_id": str(assignment_id), "message": "Assignment updated successfully"}

@router.delete("/{assignment_id}")
def delete_assignment(assignment_id: UUID, user: dict = Depends(get_current_user)):
    _require_professor(user)

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT assignment_id FROM assignments WHERE assignment_id = %s",
            (str(assignment_id),)
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Assignment not found")

        conn.execute(
            "DELETE FROM assignments WHERE assignment_id = %s",
            (str(assignment_id),)
        )
        conn.commit()

    return {"message": "Assignment deleted successfully"}