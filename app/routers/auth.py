from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.dependencies import get_auth_service, rate_limit_auth
from app.schemas.user import UserCreate, UserResponse, Token
from app.services.auth_service import AuthService, create_access_token
from app.services.rate_limit_service import RateLimitResult

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    _rate_limit: Annotated[RateLimitResult, Depends(rate_limit_auth)],
):
    """Register a new user."""
    # Check if email already exists
    existing_user = await auth_service.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    
    user = await auth_service.create_user(user_data)
    return UserResponse(
        id=user.id,
        email=user.email,
        created_at=user.created_at,
    )


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    _rate_limit: Annotated[RateLimitResult, Depends(rate_limit_auth)],
):
    """Login and get access token."""
    user = await auth_service.authenticate(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    access_token = create_access_token(user.id)
    return Token(access_token=access_token)
