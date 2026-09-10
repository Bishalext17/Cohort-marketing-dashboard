from fastapi import APIRouter, HTTPException, status, Depends
from datetime import timedelta
from backend.app.models.auth_schemas import LoginRequest, TokenResponse, UserProfile
from backend.app.core.security import authenticate_user, create_access_token, get_current_user
from backend.app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """Authenticates credentials and returns a secure JWT access token"""
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password. Please try again.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    access_token = create_access_token(
        user=user,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        user=user
    )

@router.get("/me", response_model=UserProfile)
async def get_me(current_user: UserProfile = Depends(get_current_user)):
    """Returns currently authenticated user profile"""
    return current_user

@router.post("/logout")
async def logout(current_user: UserProfile = Depends(get_current_user)):
    """Logs out and terminates current session context"""
    return {"message": "Successfully logged out.", "user": current_user.username}
