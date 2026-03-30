from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from database import get_db_connection
from auth import hash_password, verify_password, create_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "student"  # default role is student


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    assignment_id: UUID | None = None  # required only for students


class GetUserResponse(BaseModel):
    user_id: UUID
    name: str
    email: EmailStr
    role: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest):
    hashed_password = hash_password(body.password)

    with get_db_connection() as conn:
        # Check if email already exists
        existing = conn.execute(
            "SELECT user_id FROM users WHERE email = %s",
            (body.email,)
        ).fetchone()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

        allowed_roles = {"student", "professor"}
        if body.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role must be one of {allowed_roles}"
            )

        # Insert new user
        row = conn.execute(
            """
            INSERT INTO users (name, email, role, password_hash)
            VALUES (%s, %s, %s, %s)
            RETURNING user_id
            """,
            (body.name, body.email, body.role, hashed_password)
        ).fetchone()

        conn.commit()

    return {
        "user_id": str(row[0]),
        "message": "User registered successfully"
    }


@router.post("/login")
def login(body: LoginRequest):
    with get_db_connection() as conn:
        # Check if email exists
        row = conn.execute(
            """
            SELECT user_id, password_hash, role
            FROM users
            WHERE email = %s
            """,
            (body.email,)
        ).fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email"
            )

        if not verify_password(body.password, row[1]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password"
            )

        user_id = str(row[0])
        role = row[2]

        # Student-only assignment existence check
        if role == "student":
            if body.assignment_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="assignment_id is required for student login"
                )

            assignment = conn.execute(
                "SELECT assignment_id FROM assignments WHERE assignment_id = %s",
                (str(body.assignment_id),)
            ).fetchone()

            if not assignment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Assignment not found"
                )

    token = create_token(user_id, role)

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@router.get("/role")
def get_role(user: dict = Depends(get_current_user)):
    """
    Provide Authorization: Bearer <token>
    Returns the role associated with that token.
    """
    return {"role": user["role"]}


@router.get("/me", response_model=GetUserResponse)
def get_my_account(user: dict = Depends(get_current_user)):
    """
    Professor My Account API.
    Provide Authorization: Bearer <token>
    Returns the logged-in professor's account details.
    """
    if user["role"] != "professor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only professors can access this endpoint"
        )

    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT user_id, name, email, role
            FROM users
            WHERE user_id = %s
            """,
            (user["user_id"],)
        ).fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

    return {
        "user_id": row[0],
        "name": row[1],
        "email": row[2],
        "role": row[3]
    }