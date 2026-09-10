import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.app.core.config import settings
from backend.app.models.auth_schemas import UserProfile
import logging
import hmac
import hashlib

logger = logging.getLogger(__name__)

# HTTP Bearer security scheme for OpenAPI docs & token extraction
security_scheme = HTTPBearer(auto_error=False)

def verify_password(plain_password: str, expected_password: str) -> bool:
    """Timing-attack safe comparison for credentials"""
    return hmac.compare_digest(plain_password.encode("utf-8"), expected_password.encode("utf-8"))

def authenticate_user(username: str, password: str) -> Optional[UserProfile]:
    """Authenticates username & password against configured admin credentials"""
    if username.strip().lower() == settings.ADMIN_USERNAME.strip().lower() and verify_password(password, settings.ADMIN_PASSWORD):
        return UserProfile(
            username=settings.ADMIN_USERNAME,
            name=settings.ADMIN_NAME,
            role=settings.ADMIN_ROLE,
            avatar="👨‍💼"
        )
    return None

def create_access_token(user: UserProfile, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a cryptographically signed JWT access token"""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "sub": user.username,
        "name": user.name,
        "role": user.role,
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    
    encoded_jwt = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and verifies a JWT access token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)) -> UserProfile:
    """FastAPI route dependency that validates bearer token and returns UserProfile"""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access marketing analytics.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    payload = decode_access_token(credentials.credentials)
    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return UserProfile(
        username=username,
        name=payload.get("name", settings.ADMIN_NAME),
        role=payload.get("role", settings.ADMIN_ROLE),
        avatar="👨‍💼"
    )
