"""recommendation 슬라이스 HTTP 계층. 요청을 받아 service 로 넘기기만 한다."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from common.dto import RecommendationResponse
from feature.recommendation import service
from shared.database import get_database_session
from shared.security import CurrentUser

router = APIRouter()

DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.get("/api/recommendations", response_model=RecommendationResponse)
def get_recommendations(current_user: CurrentUser, database_session: DatabaseSession) -> RecommendationResponse:
    return service.get_recommendations(database_session, current_user)
