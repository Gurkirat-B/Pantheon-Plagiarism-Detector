# ========================================
# handle authentication and authorization
# ========================================

from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_MINS
from database import get_db_connection

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

bearer_scheme = HTTPBearer(auto_error=True)

def hash_password(plain: str) -> str:
    """Hash a plaintext password."""
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a hashed password."""
    return pwd_context.verify(plain, hashed)

def create_token(user_id: str, role: str) -> str:
    """Create a JWT token for the given user ID and role."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINS)
    payload = {"sub": user_id, "role": role, "exp": expire}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    """Dependency: extracts + validates JWT from Authorization header."""
    token = creds.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        if user_id is None or role is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return {"user_id": user_id, "role": role}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")