from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from psycopg.types.json import Jsonb

from database import get_db_connection
from auth import get_current_user

router = APIRouter(prefix="/assignments", tags=["assignments"])


def _require_professor(user: dict):
    if user["role"] != "professor":
        raise HTTPException(status_code=403, detail="Professor role required")


class CreateAssignmentRequest(BaseModel):
    course_id: UUID
    title: str
    language: str
    due_date: datetime | None = None
    settings: dict = {}


@router.post("/")
def create_assignment(body: CreateAssignmentRequest, user: dict = Depends(get_current_user)):
    _require_professor(user)

    allowed_languages = {"java", "c", "cpp"}
    if body.language not in allowed_languages:
        raise HTTPException(
            status_code=400,
            detail=f"language must be one of {sorted(allowed_languages)}"
        )

    with get_db_connection() as conn:
        course = conn.execute(
            "SELECT course_id FROM courses WHERE course_id = %s",
            (str(body.course_id),)
        ).fetchone()

        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        row = conn.execute(
            """
            INSERT INTO assignments (course_id, title, due_date, language, settings)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING assignment_id, course_id, title, language, due_date, created_at
            """,
            (
                str(body.course_id),
                body.title,
                body.due_date,
                body.language,
                Jsonb(body.settings),
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


@router.get("/")
def list_assignments(user: dict = Depends(get_current_user)):
    _require_professor(user)

    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT assignment_id, course_id, title, language, due_date, created_at
            FROM assignments
            ORDER BY created_at DESC
            """
        ).fetchall()

    return {
        "assignments": [
            {
                "assignment_id": str(r[0]),
                "course_id": str(r[1]),
                "title": r[2],
                "language": r[3],
                "due_date": r[4].isoformat() if r[4] else None,
                "created_at": r[5].isoformat() if r[5] else None,
            }
            for r in rows
        ]
    }


@router.get("/{assignment_id}")
def get_assignment(assignment_id: UUID, user: dict = Depends(get_current_user)):
    _require_professor(user)

    with get_db_connection() as conn:
        assignment = conn.execute(
            """
            SELECT assignment_id, course_id, title, language, due_date, settings, created_at
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
        "settings": assignment[5],
        "created_at": assignment[6].isoformat() if assignment[6] else None,
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