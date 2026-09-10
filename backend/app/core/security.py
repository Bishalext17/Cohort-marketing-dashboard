import time
import json
import base64
import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.app.core.config import settings
from backend.app.models.auth_schemas import UserProfile
import logging

try:
    import jwt
    HAS_PYJWT = True
except ImportError:
    jwt = None
    HAS_PYJWT = False

logger = logging.getLogger(__name__)

# HTTP Bearer security scheme for OpenAPI docs & token extraction
security_scheme = HTTPBearer(auto_error=False)

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def _b64url_decode(s: str) -> bytes:
    padding = '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + padding)

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
        expire_dt = datetime.now(timezone.utc) + expires_delta
    else:
        expire_dt = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    exp_timestamp = int(expire_dt.timestamp())
    iat_timestamp = int(datetime.now(timezone.utc).timestamp())

    payload = {
        "sub": user.username,
        "name": user.name,
        "role": user.role,
        "exp": exp_timestamp,
        "iat": iat_timestamp
    }

    if HAS_PYJWT and jwt:
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    # Pure Python HS256 Standard JWT Implementation
    header = {"alg": "HS256", "typ": "JWT"}
    header_bytes = json.dumps(header, separators=(',', ':')).encode('utf-8')
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')

    msg = f"{_b64url_encode(header_bytes)}.{_b64url_encode(payload_bytes)}"
    signature = hmac.new(settings.JWT_SECRET_KEY.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).digest()
    
    return f"{msg}.{_b64url_encode(signature)}"

def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and verifies a JWT access token"""
    if HAS_PYJWT and jwt:
        try:
            return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has expired. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token.",
                headers={"WWW-Authenticate": "Bearer"}
            )

    # Pure Python HS256 Verification
    try:
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid token format")
        
        header_b64, payload_b64, sig_b64 = parts
        msg = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(settings.JWT_SECRET_KEY.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).digest()
        actual_sig = _b64url_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            raise ValueError("Signature mismatch")

        payload = json.loads(_b64url_decode(payload_b64).decode('utf-8'))
        exp = payload.get("exp")
        if exp and exp < time.time():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has expired. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return payload
    except HTTPException:
        raise
    except Exception:
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
