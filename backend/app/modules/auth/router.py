import os
from typing import Annotated
from fastapi import APIRouter, Depends, Response, Cookie, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.schema import (
    RegisterRequest, 
    LoginRequest, 
    TokenResponse, 
    UserResponse,
    MessageResponse
)
from app.modules.auth import service
from app.modules.auth.dependencies import get_current_user, verify_origin
from app.modules.users.model import User
from app.modules.auth.exceptions import (
    AuthenticationError,
    InvalidSessionError,
    DuplicateEmailError,
    PasswordPolicyError
)

router = APIRouter(prefix="/auth", tags=["auth"])

from app.core.config import settings

def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=raw_token,
        httponly=True,
        samesite="strict",
        secure=settings.cookie_secure,
        path="/api/v1/auth"
    )

def _clear_refresh_cookie(response: Response) -> None:
    response.set_cookie(
        key="refresh_token",
        value="",
        httponly=True,
        samesite="strict",
        secure=settings.cookie_secure,
        path="/api/v1/auth",
        max_age=0
    )

@router.post(
    "/register", 
    status_code=201, 
    response_model=TokenResponse,
    dependencies=[Depends(verify_origin)]
)
async def register(
    data: RegisterRequest, 
    response: Response, 
    db: Annotated[AsyncSession, Depends(get_db_session)]
):
    try:
        user, access_token, refresh_token = await service.register_user(db, data)
    except DuplicateEmailError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except PasswordPolicyError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    
    _set_refresh_cookie(response, refresh_token)
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )

@router.post(
    "/login", 
    response_model=TokenResponse,
    dependencies=[Depends(verify_origin)]
)
async def login(
    data: LoginRequest, 
    response: Response, 
    db: Annotated[AsyncSession, Depends(get_db_session)]
):
    try:
        user, access_token, refresh_token = await service.login_user(db, data)
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
    
    _set_refresh_cookie(response, refresh_token)
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )

@router.post(
    "/refresh", 
    response_model=TokenResponse,
    dependencies=[Depends(verify_origin)]
)
async def refresh(
    response: Response, 
    db: Annotated[AsyncSession, Depends(get_db_session)],
    refresh_token: Annotated[str | None, Cookie()] = None
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session."
        )
        
    try:
        access_token, new_refresh_token = await service.refresh_session(db, refresh_token)
    except InvalidSessionError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session."
        )
    
    _set_refresh_cookie(response, new_refresh_token)
    
    return TokenResponse(access_token=access_token)

@router.post(
    "/logout", 
    response_model=MessageResponse,
    dependencies=[Depends(verify_origin)]
)
async def logout(
    response: Response, 
    db: Annotated[AsyncSession, Depends(get_db_session)],
    refresh_token: Annotated[str | None, Cookie()] = None
):
    if refresh_token:
        await service.logout_session(db, refresh_token)
        
    _clear_refresh_cookie(response)
    
    return MessageResponse(message="Logged out")

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    return UserResponse.model_validate(current_user)
