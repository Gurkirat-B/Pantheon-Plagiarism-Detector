from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from database import get_db_connection
from auth import (
    hash_password,
    verify_password,
    create_token,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "professor"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str | None = None # required for professors only
    assignment_id: UUID | None = None   # required only for students
    role: str

    
class GetUserResponse(BaseModel):
    name: str
    email: EmailStr


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class DeleteAccountRequest(BaseModel):
    password: str


def register_user(conn, name, email, role, password=None):
    """
    Helper method to register a user
    """
    hashed_password = hash_password(password) if password else None
    row = conn.execute(
        """
        INSERT INTO users (name, email, role, password_hash)
        VALUES (%s, %s, %s, %s)
        RETURNING user_id
        """,
        (name, email, role, hashed_password)
    ).fetchone()
    conn.commit()
    return row

@router.post("/register")
def register(body: RegisterRequest):
    """
    Registers a professor based on a JSON request
    Hashes password before storing in database
    """
    hashed_password = hash_password(body.password)
    with get_db_connection() as conn:
        # Check if email already exists
        existing = conn.execute("SELECT user_id FROM users WHERE email = %s", (body.email,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")
        
        roles = {"student", "professor"}
        if body.role not in roles:
            raise HTTPException(status_code=400, detail=f"Role must be one of {roles}")

        # Insert new user
        row = register_user(conn, body.name, body.email, body.role, body.password)

        # Create a default repository for professors
        if body.role == "professor":
            conn.execute(
                """
                INSERT INTO repositories (owner_id, name)
                VALUES (%s, %s)
                """,
                (str(row[0]), f"{body.name}'s Repository")
            )
            conn.commit()

    #successfully registered
    return {"user_id": str(row[0]), "message": "User registered successfully"}

@router.post("/login")
def login(body: LoginRequest):
    """
    Login for existing users based on JSON request
    Students are automatically registered if there is no existing user for that student
    """
    with get_db_connection() as conn:
        #check if email exists
        row = conn.execute(
            "SELECT user_id, password_hash, role  FROM users WHERE email = %s",
            (body.email,),
        ).fetchone()

        if body.role == "professor":
            if body.password is None:
                raise HTTPException(status_code=400, detail="Password is required for professor login")
            if not row:
                raise HTTPException(status_code=400, detail="Professor not registered")   
            if not verify_password(body.password, row[1]):
                raise HTTPException(status_code=401, detail="Invalid password")
        # Student-only assignment existence check and add student to db if they don't exist (first-time login)
        elif body.role == "student":
            assignment = conn.execute(
                "SELECT assignment_id FROM assignments WHERE assignment_id = %s",
                (str(body.assignment_id),),
            ).fetchone()
            if not assignment:
                raise HTTPException(status_code=404, detail="Assignment not found")
            
            if not row:
                user_row = register_user(conn, name = None, email = body.email, role = "student", password = None)
                token = create_token(str(user_row[0]), "student")
                return {"access_token": token, "token_type": "bearer", "message": "Student registered and logged in"}
            # Student exists, proceed with login (no password required)
            token = create_token(str(row[0]), row[2])
            return {"access_token": token, "token_type": "bearer", "message": "Student logged in"}
        else:
            raise HTTPException(status_code=400, detail="Invalid role specified")

    token = create_token(str(row[0]), row[2])
    return {"access_token": token, "token_type": "bearer"}

@router.get("/role")
def get_role(user: dict = Depends(get_current_user)):
    """
    Provide Authorization: Bearer <token>
    Returns the role associated with that token (as validated by get_current_user).
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
            SELECT name, email
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
        "name": row[0],
        "email": row[1],
    }


@router.post("/change-password")
def change_password(body: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    """
    Allow a logged-in professor to change their password.
    Requires the current password for verification.
    """
    if user["role"] != "professor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only professors can change their password"
        )

    if not body.new_password:
        raise HTTPException(status_code=400, detail="New password cannot be empty")

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE user_id = %s",
            (user["user_id"],)
        ).fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        if not verify_password(body.current_password, row[0]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )

        new_hash = hash_password(body.new_password)
        conn.execute(
            "UPDATE users SET password_hash = %s WHERE user_id = %s",
            (new_hash, user["user_id"])
        )
        conn.commit()

    return {"message": "Password changed successfully"}


@router.delete("/delete-account")
def delete_account(body: DeleteAccountRequest, user: dict = Depends(get_current_user)):
    """
    Allow a logged-in professor to permanently delete their account.
    Requires the current password for verification.
    Cascades to related rows via ON DELETE CASCADE in the schema.
    """
    if user["role"] != "professor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only professors can delete their account"
        )

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE user_id = %s",
            (user["user_id"],)
        ).fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        if not verify_password(body.password, row[0]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Password is incorrect"
            )

        conn.execute(
            "DELETE FROM users WHERE user_id = %s",
            (user["user_id"],)
        )
        conn.commit()

    return {"message": "Account deleted successfully"}
