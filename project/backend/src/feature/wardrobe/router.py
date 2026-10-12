"""wardrobe 슬라이스 HTTP 계층. 요청을 받아 service 로 넘기기만 한다."""
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from common.dto import WardrobePhotosResponse
from feature.wardrobe import service
from shared.database import get_database_session
from shared.security import CurrentUser

router = APIRouter()

DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.post("/api/wardrobe-photos", response_model=WardrobePhotosResponse)
def upload_wardrobe_photos(
    images: Annotated[list[UploadFile], File()], current_user: CurrentUser, database_session: DatabaseSession
) -> WardrobePhotosResponse:
    return service.upload_wardrobe_photos(database_session, current_user, images)
