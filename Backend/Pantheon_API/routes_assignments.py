from fastapi import APIRouter, Depends, HTTPException

from database import get_db_connection
from auth import get_current_user

router = APIRouter(prefix="/assignments", tags=["assignments"])

@router.get("/")
def list_assignments(user: dict = Depends(get_current_user)):
    if user["role"] != "professor":
        raise HTTPException(status_code=403, detail="Professor role required")
    
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