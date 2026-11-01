from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

ALGORITHM = "HS256"
bearer = HTTPBearer(auto_error=False)


def create_access_token(username: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({"sub": username, "exp": expires}, settings.jwt_secret, algorithm=ALGORITHM)


def authenticate_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username != settings.staff_username:
            raise ValueError("Invalid user")
        return username
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
