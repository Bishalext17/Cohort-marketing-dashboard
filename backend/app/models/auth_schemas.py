from typing import Optional
from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    username: str = Field(..., description="Admin username or email")
    password: str = Field(..., description="Account password")

class UserProfile(BaseModel):
    username: str
    name: str
    role: str
    avatar: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: UserProfile
