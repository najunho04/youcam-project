"""profile 슬라이스 HTTP 계층. 요청을 받아 service 로 넘기기만 한다."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from common.dto import ProfileUpdateRequest, UserDto
from feature.profile import service
from shared.database import get_database_session
from shared.security import CurrentUser

router = APIRouter()

DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.put("/api/users/me/profile", response_model=UserDto)
def update_profile(request: ProfileUpdateRequest, current_user: CurrentUser, database_session: DatabaseSession) -> UserDto:
    return service.update_profile(database_session, current_user, request)
