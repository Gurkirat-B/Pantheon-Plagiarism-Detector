from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from database import get_db_connection
from auth import hash_password, verify_password, create_token

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "student" # default role is "student"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/register")
def register(body: RegisterRequest):
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
        row = conn.execute(
            """
            INSERT INTO users (name, email, role, password_hash)
            VALUES (%s, %s, %s, %s)
            RETURNING user_id
            """,
            (body.name, body.email, body.role, hashed_password)
        ).fetchone()
        conn.commit()
    #successfully registered
    return {"user_id": str(row[0]), "message": "User registered successfully"}

@router.post("/login")
def login(body: LoginRequest):
    with get_db_connection() as conn:
        #check if email exists
        row = conn.execute(
            "SELECT user_id, password_hash, role  FROM users WHERE email = %s",
            (body.email,),
        ).fetchone()
    
    if not row:
        raise HTTPException(status_code=401, detail="Invalid email")
    
    if not verify_password(body.password, row[1]):
        raise HTTPException(status_code=401, detail="Invalid password")

    token = create_token(str(row[0]), row[2])
    return {"access_token": token, "token_type": "bearer"}