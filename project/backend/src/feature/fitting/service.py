"""fitting 슬라이스 비즈니스 로직. 실패는 AppError 로만 알린다.
POST 는 행을 PENDING 으로 만들고 커밋한 뒤 FittingJob 을 돌려준다. 실제 YouCam 호출은 백그라운드 작업(run_fitting_job)이
session_scope() 로 연 별도 세션에서 한다.
"""
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from common.dto import FittingDto, ProductDto
from common.entity import Fitting, Product, User
from common.enums import FittingStatus
from common.error import AppError, ErrorCode
from feature.fitting import repository
from shared.database import session_scope
from shared.image import download_image
from shared.storage import get_storage
from shared.youcam import YouCamTaskStatus, get_youcam_client

logger = logging.getLogger(__name__)

# 이보다 오래된 PENDING 은 멈춘 작업으로 보고 다시 시작한다 (계약 고정값).
# 서버의 YouCam 대기(YOUCAM_POLL_TIMEOUT_SECONDS=165)는 반드시 이보다 짧아야 한다. 길면 아직 기다리는 작업을 또 시작해 두 번 과금된다
PENDING_RESTART_THRESHOLD = timedelta(minutes=3)
_RESULT_KEY_PREFIX = "fittings"
_RESULT_CONTENT_TYPE = "image/jpeg"


@dataclass(frozen=True)
class FittingJob:
    """백그라운드 작업 입력. started_at 이 행의 created_at 과 다르면 다른 작업으로 다시 시작된 것이다."""

    fitting_id: int
    user_id: int
    started_at: datetime
    user_image_url: str
    garment_image_url: str


def result_key_of(user_id: int, fitting_id: int) -> str:
    return f"{_RESULT_KEY_PREFIX}/{user_id}/{fitting_id}.jpg"


def is_reusable(fitting: Fitting, now: datetime) -> bool:
    """DONE 이거나 PENDING 이고 시작한 지 3분 이내면 그대로 반환한다."""
    if fitting.status == FittingStatus.DONE:
        return True
    return fitting.status == FittingStatus.PENDING and now - fitting.created_at <= PENDING_RESTART_THRESHOLD


def to_product_dto(product: Product) -> ProductDto:
    return ProductDto.model_validate(product)


def to_fitting_dto(fitting: Fitting, product: Product, user: User) -> FittingDto:
    """resultImageUrl 은 DONE 일 때만 채운다."""
    storage = get_storage()
    return FittingDto(
        id=fitting.id,
        product_id=fitting.product_id,
        product=to_product_dto(product),
        status=fitting.status,
        original_image_url=storage.get_url(user.body_image_key) if user.body_image_key else "",
        result_image_url=(
            storage.get_url(fitting.result_key)
            if fitting.status == FittingStatus.DONE and fitting.result_key is not None
            else None
        ),
    )


def _find_product_or_raise(database_session: Session, product_id: int) -> Product:
    product = repository.find_product(database_session, product_id)
    if product is None:
        raise AppError(ErrorCode.PRODUCT_NOT_FOUND, "상품을 찾을 수 없습니다")
    return product


def create_fitting(database_session: Session, user: User, product_id: int) -> tuple[FittingDto, FittingJob | None]:
    """(user, product) 행을 재사용하거나 PENDING 으로 생성/갱신한다. 작업을 시작해야 하면 FittingJob 도 돌려준다."""
    product = _find_product_or_raise(database_session, product_id)
    if user.body_image_key is None:
        raise AppError(ErrorCode.PERSONAL_COLOR_REQUIRED, "퍼스널컬러 진단에서 상반신 사진을 먼저 올려 주세요")

    started_at = datetime.now(UTC)
    fitting = repository.lock_fitting_by_user_and_product(database_session, user.id, product.id)
    if fitting is None:
        added_fitting = repository.add_pending_fitting(database_session, user.id, product.id, started_at)
        if added_fitting is not None:
            return _start(database_session, added_fitting, product, user)
        # 동시 요청이 먼저 만들었다 → 그 행 기준으로 다시 판단
        fitting = repository.lock_fitting_by_user_and_product(database_session, user.id, product.id)
        if fitting is None:
            raise AppError(ErrorCode.INTERNAL_ERROR)

    if is_reusable(fitting, started_at):
        return to_fitting_dto(fitting, product, user), None
    return _start(database_session, repository.restart_fitting(database_session, fitting, started_at), product, user)


def _start(database_session: Session, fitting: Fitting, product: Product, user: User) -> tuple[FittingDto, FittingJob]:
    # 응답 직후 실행되는 백그라운드 작업은 별도 세션이므로, 그 전에 PENDING 행을 커밋해 보이게 한다
    database_session.commit()
    storage = get_storage()
    fitting_job = FittingJob(
        fitting_id=fitting.id,
        user_id=user.id,
        started_at=fitting.created_at,
        user_image_url=storage.get_url(user.body_image_key) if user.body_image_key else "",
        garment_image_url=product.image_url,
    )
    return to_fitting_dto(fitting, product, user), fitting_job


def get_fitting(database_session: Session, user: User, fitting_id: int) -> FittingDto:
    """본인 피팅만 조회. 없거나 다른 사용자의 피팅이면 FITTING_NOT_FOUND."""
    fitting = repository.find_fitting(database_session, fitting_id)
    if fitting is None or fitting.user_id != user.id:
        raise AppError(ErrorCode.FITTING_NOT_FOUND, "피팅을 찾을 수 없습니다")
    return to_fitting_dto(fitting, _find_product_or_raise(database_session, fitting.product_id), user)


def _lock_current_fitting(database_session: Session, fitting_job: FittingJob) -> Fitting | None:
    """이 작업이 아직 유효한 행만 돌려준다. 행이 삭제됐거나(사진 재업로드) 다른 작업으로 다시 시작됐으면 None."""
    fitting = repository.lock_fitting(database_session, fitting_job.fitting_id)
    if fitting is None or fitting.status != FittingStatus.PENDING or fitting.created_at != fitting_job.started_at:
        return None
    return fitting


def run_fitting_job(fitting_job: FittingJob) -> None:
    """백그라운드 작업. YouCam 작업을 시작하면 끝까지 기다린 뒤 결과를 저장한다 (DONE / FAILED)."""
    try:
        youcam_client = get_youcam_client()
        task_id = youcam_client.start_cloth_fitting(
            user_image_url=fitting_job.user_image_url, garment_image_url=fitting_job.garment_image_url
        )
        cloth_fitting_task = youcam_client.wait_cloth_fitting(task_id)
        if cloth_fitting_task.status != YouCamTaskStatus.SUCCESS or cloth_fitting_task.result_image_url is None:
            raise AppError(ErrorCode.EXTERNAL_API_FAILED, cloth_fitting_task.error_code or "가상 피팅 실패")
        result_image = download_image(cloth_fitting_task.result_image_url)
    except Exception:
        logger.exception("cloth fitting failed: fitting_id=%s", fitting_job.fitting_id)
        _mark_failed(fitting_job)
        return

    try:
        with session_scope() as database_session:
            fitting = _lock_current_fitting(database_session, fitting_job)
            if fitting is None:
                return
            result_key = result_key_of(fitting_job.user_id, fitting_job.fitting_id)
            get_storage().upload(result_key, result_image, _RESULT_CONTENT_TYPE)
            repository.complete_fitting(database_session, fitting, result_key)
    except Exception:
        logger.exception("cloth fitting result save failed: fitting_id=%s", fitting_job.fitting_id)
        _mark_failed(fitting_job)


def _mark_failed(fitting_job: FittingJob) -> None:
    with session_scope() as database_session:
        fitting = _lock_current_fitting(database_session, fitting_job)
        if fitting is not None:
            repository.fail_fitting(database_session, fitting)
