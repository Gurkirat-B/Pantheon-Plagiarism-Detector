# ========================================
# handle authentication and authorization
# ========================================

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_MINS
from database import get_db_connection

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

bearer_scheme = HTTPBearer(auto_error=True)


def _unauthorized(detail: str = "Invalid token") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def ensure_professor_session_support(conn) -> None:
    """Ensure the users table can track the current professor session."""
    conn.execute(
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS active_session_id TEXT
        """
    )
    conn.commit()


def issue_professor_session(conn, user_id: str) -> str:
    """Rotate the active professor session and return the new session ID."""
    ensure_professor_session_support(conn)
    session_id = str(uuid4())
    conn.execute(
        """
        UPDATE users
        SET active_session_id = %s
        WHERE user_id = %s
        """,
        (session_id, user_id),
    )
    conn.commit()
    return session_id

def hash_password(plain: str) -> str:
    """Hash a plaintext password."""
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a hashed password."""
    return pwd_context.verify(plain, hashed)

def create_token(user_id: str, role: str, session_id: str | None = None) -> str:
    """Create a JWT token for the given user ID and role."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINS)
    payload = {"sub": user_id, "role": role, "exp": expire}
    if session_id is not None:
        payload["sid"] = session_id
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    """Dependency: extracts + validates JWT from Authorization header."""
    token = creds.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        if user_id is None or role is None:
            raise _unauthorized()

        if role == "professor":
            session_id: str | None = payload.get("sid")
            if session_id is None:
                raise _unauthorized("Session expired")

            with get_db_connection() as conn:
                ensure_professor_session_support(conn)
                row = conn.execute(
                    """
                    SELECT active_session_id
                    FROM users
                    WHERE user_id = %s
                    """,
                    (user_id,),
                ).fetchone()

            if not row or row[0] != session_id:
                raise _unauthorized("Session expired")

            return {"user_id": user_id, "role": role, "session_id": session_id}

        return {"user_id": user_id, "role": role}
    except JWTError:
        raise _unauthorized()
