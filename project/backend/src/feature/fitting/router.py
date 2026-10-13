"""fitting 슬라이스 HTTP 계층. 요청을 받아 service 로 넘기고, 백그라운드 작업을 등록하기만 한다."""
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from common.dto import FittingCreateRequest, FittingDto
from feature.fitting import service
from shared.database import get_database_session
from shared.security import CurrentUser

router = APIRouter()

DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.post("/api/fittings", response_model=FittingDto, status_code=202)
def create_fitting(
    request: FittingCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    database_session: DatabaseSession,
) -> FittingDto:
    fitting_dto, fitting_job = service.create_fitting(database_session, current_user, request.product_id)
    if fitting_job is not None:
        background_tasks.add_task(service.run_fitting_job, fitting_job)
    return fitting_dto


@router.get("/api/fittings/{fitting_id}", response_model=FittingDto)
def get_fitting(fitting_id: int, current_user: CurrentUser, database_session: DatabaseSession) -> FittingDto:
    return service.get_fitting(database_session, current_user, fitting_id)
