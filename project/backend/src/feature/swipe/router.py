"""swipe 슬라이스 HTTP 계층. 요청을 받아 service 로 넘기기만 한다."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from common.dto import SwipeAnswersRequest, SwipeAnswersResponse, SwipeCardsResponse
from feature.swipe import service
from shared.database import get_database_session
from shared.security import CurrentUser

router = APIRouter()

DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.get("/api/swipe/cards", response_model=SwipeCardsResponse)
def get_swipe_cards(
    current_user: CurrentUser, database_session: DatabaseSession, count: Annotated[int, Query(ge=1, le=50)] = 20
) -> SwipeCardsResponse:
    return service.get_swipe_cards(database_session, current_user, count)


@router.post("/api/swipe/answers", response_model=SwipeAnswersResponse)
def submit_swipe_answers(
    request: SwipeAnswersRequest, current_user: CurrentUser, database_session: DatabaseSession
) -> SwipeAnswersResponse:
    return service.submit_swipe_answers(database_session, current_user, request)
