"""auth 슬라이스 HTTP 계층. 요청을 받아 service 로 넘기기만 한다."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from common.dto import AuthRequest, AuthResponse, UserDto
from feature.auth import service
from shared.database import get_database_session
from shared.security import CurrentUser

router = APIRouter()

DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.post("/api/auth/signup", response_model=AuthResponse)
def signup(request: AuthRequest, database_session: DatabaseSession) -> AuthResponse:
    return service.signup(database_session, request)


@router.post("/api/auth/login", response_model=AuthResponse)
def login(request: AuthRequest, database_session: DatabaseSession) -> AuthResponse:
    return service.login(database_session, request)


@router.get("/api/users/me", response_model=UserDto)
def get_me(current_user: CurrentUser) -> UserDto:
    return service.to_user_dto(current_user)
