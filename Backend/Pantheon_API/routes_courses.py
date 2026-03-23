from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database import get_db_connection
from auth import get_current_user

router = APIRouter(prefix="/courses", tags=["courses"])


def _require_professor(user: dict):
    if user["role"] != "professor":
        raise HTTPException(status_code=403, detail="Professor role required")


class CreateCourseRequest(BaseModel):
    code: str
    name: str


@router.post("/")
def create_course(body: CreateCourseRequest, user: dict = Depends(get_current_user)):
    _require_professor(user)

    with get_db_connection() as conn:
        existing = conn.execute(
            "SELECT course_id FROM courses WHERE code = %s",
            (body.code,)
        ).fetchone()

        if existing:
            raise HTTPException(status_code=409, detail="Course code already exists")

        row = conn.execute(
            """
            INSERT INTO courses (code, name)
            VALUES (%s, %s)
            RETURNING course_id, code, name
            """,
            (body.code, body.name)
        ).fetchone()
        
        course_id = row[0]  # Extract course_id from returned row

        # Add record to enrollments table to track professor-course relationship
        conn.execute(
            """
            INSERT INTO enrollments (user_id, course_id)
            VALUES (%s, %s)
            """,
            (str(user["user_id"]), str(course_id)),
        )

        conn.commit()

    return {
        "course_id": str(course_id),
        "code": row[1],
        "name": row[2],
        "message": "Course created successfully"
    }


@router.get("/")
def list_courses(user: dict = Depends(get_current_user)):
    _require_professor(user)

    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.course_id, c.code, c.name, c.created_at
            FROM courses c
            JOIN enrollments e ON c.course_id = e.course_id
            WHERE e.user_id = %s
            ORDER BY c.created_at DESC
            """,
            (str(user["user_id"]),),
        ).fetchall()

    return {
        "courses": [
            {
                "course_id": str(r[0]),
                "code": r[1],
                "name": r[2],
            }
            for r in rows
        ]
    }


@router.get("/{course_id}")
def get_course(course_id: UUID, user: dict = Depends(get_current_user)):
    _require_professor(user)

    with get_db_connection() as conn:
        course = conn.execute(
            """
            SELECT course_id, code, name
            FROM courses
            WHERE course_id = %s
            """,
            (str(course_id),)
        ).fetchone()

        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        assignments = conn.execute(
            """
            SELECT assignment_id, title, language, due_date, created_at
            FROM assignments
            WHERE course_id = %s
            ORDER BY created_at DESC
            """,
            (str(course_id),)
        ).fetchall()

    return {
        "course_id": str(course[0]),
        "code": course[1],
        "name": course[2],
        "assignments": [
            {
                "assignment_id": str(a[0]),
                "title": a[1],
                "language": a[2],
                "due_date": a[3].isoformat() if a[3] else None,
                "created_at": a[4].isoformat() if a[4] else None,
            }
            for a in assignments
        ]
    }


@router.delete("/{course_id}")
def delete_course(course_id: UUID, user: dict = Depends(get_current_user)):
    _require_professor(user)

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT course_id FROM courses WHERE course_id = %s",
            (str(course_id),)
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Course not found")

        conn.execute(
            "DELETE FROM courses WHERE course_id = %s",
            (str(course_id),)
        )
        conn.commit()

    return {"message": "Course deleted successfully"}