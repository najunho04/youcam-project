"""personal_color 슬라이스 HTTP 계층. 요청을 받아 service 로 넘기기만 한다."""
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from common.dto import PersonalColorDto
from feature.personal_color import service
from shared.database import get_database_session
from shared.security import CurrentUser

router = APIRouter()

DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.post("/api/personal-color", response_model=PersonalColorDto)
def analyze_personal_color(
    selfie: Annotated[UploadFile, File()],
    body_image: Annotated[UploadFile, File(alias="bodyImage")],
    current_user: CurrentUser,
    database_session: DatabaseSession,
) -> PersonalColorDto:
    return service.analyze_personal_color(database_session, current_user, selfie, body_image)
