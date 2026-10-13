"""fitting service 단위 테스트."""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select

from common.entity import Fitting, User
from common.enums import FittingStatus, Style
from common.error import AppError, ErrorCode
from feature.fitting import service
from shared.database import session_scope

RESULT_IMAGE_BYTES = b"fitted-result-image"


def body_image_key_of(user_id: int) -> str:
    return f"body-images/{user_id}/body.jpg"


@pytest.fixture
def fitting_user(create_user, database_session) -> User:
    user = create_user(nickname="fitter")
    user.body_image_key = body_image_key_of(user.id)
    database_session.commit()
    return user


@pytest.fixture
def downloaded_urls(monkeypatch) -> list[str]:
    urls: list[str] = []

    def fake_download_image(url: str) -> bytes:
        urls.append(url)
        return RESULT_IMAGE_BYTES

    monkeypatch.setattr(service, "download_image", fake_download_image)
    return urls


def insert_fitting(database_session, user_id: int, product_id: int, status: FittingStatus, created_at: datetime,
                   result_key: str | None = None) -> Fitting:
    fitting = Fitting(user_id=user_id, product_id=product_id, status=status, result_key=result_key, created_at=created_at)
    database_session.add(fitting)
    database_session.commit()
    return fitting


def load_fitting(database_session, fitting_id: int) -> Fitting | None:
    database_session.expire_all()
    return database_session.scalars(select(Fitting).where(Fitting.id == fitting_id)).one_or_none()


def fitting_of(fitting_id: int, status: FittingStatus, created_at: datetime, result_key: str | None = None) -> Fitting:
    return Fitting(id=fitting_id, user_id=1, product_id=1, status=status, result_key=result_key, created_at=created_at)


# ---- 상수·순수 함수 ----
def test_restart_threshold_is_three_minutes():
    assert service.PENDING_RESTART_THRESHOLD == timedelta(minutes=3)


def test_result_key_follows_storage_key_rule():
    assert service.result_key_of(user_id=7, fitting_id=42) == "fittings/7/42.jpg"


@pytest.mark.parametrize(
    ("status", "age", "expected"),
    [
        (FittingStatus.DONE, timedelta(days=30), True),
        (FittingStatus.PENDING, timedelta(minutes=1), True),
        (FittingStatus.PENDING, timedelta(minutes=3), True),  # 경계 포함 (3분 이내)
        (FittingStatus.PENDING, timedelta(minutes=3, seconds=1), False),
        (FittingStatus.FAILED, timedelta(seconds=1), False),
    ],
)
def test_is_reusable_decides_by_status_and_started_time(status, age, expected):
    now = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)

    assert service.is_reusable(fitting_of(1, status, created_at=now - age), now) is expected


def test_to_fitting_dto_sets_result_url_only_when_done(create_product, fitting_user, storage):
    product = create_product(style=Style.LOVELY)
    now = datetime.now(UTC)
    done = fitting_of(5, FittingStatus.DONE, now, result_key="fittings/1/5.jpg")
    done.product_id = product.id
    pending = fitting_of(6, FittingStatus.PENDING, now, result_key="fittings/1/6.jpg")
    pending.product_id = product.id

    done_dto = service.to_fitting_dto(done, product, fitting_user)
    pending_dto = service.to_fitting_dto(pending, product, fitting_user)

    assert done_dto.id == 5
    assert done_dto.product_id == product.id
    assert done_dto.product.style == Style.LOVELY
    assert done_dto.product.purchase_url == product.purchase_url
    assert done_dto.original_image_url == storage.get_url(body_image_key_of(fitting_user.id))
    assert done_dto.result_image_url == storage.get_url("fittings/1/5.jpg")
    assert pending_dto.result_image_url is None


# ---- create_fitting ----
def test_create_fitting_inserts_pending_row_and_returns_job(database_session, fitting_user, create_product, storage):
    product = create_product()

    fitting_dto, fitting_job = service.create_fitting(database_session, fitting_user, product.id)

    row = load_fitting(database_session, fitting_dto.id)
    assert row is not None  # 백그라운드 세션이 읽을 수 있도록 커밋되어 있다
    assert row.status == FittingStatus.PENDING
    assert row.result_key is None
    assert fitting_dto.status == FittingStatus.PENDING
    assert fitting_job == service.FittingJob(
        fitting_id=row.id,
        user_id=fitting_user.id,
        started_at=row.created_at,
        user_image_url=storage.get_url(body_image_key_of(fitting_user.id)),
        garment_image_url=product.image_url,
    )


@pytest.mark.parametrize(
    ("status", "age"),
    [(FittingStatus.DONE, timedelta(days=1)), (FittingStatus.PENDING, timedelta(minutes=1))],
)
def test_create_fitting_reuses_row_without_job(database_session, fitting_user, create_product, status, age):
    product = create_product()
    created_at = datetime.now(UTC) - age
    existing = insert_fitting(
        database_session, fitting_user.id, product.id, status, created_at,
        result_key="fittings/x.jpg" if status == FittingStatus.DONE else None,
    )

    fitting_dto, fitting_job = service.create_fitting(database_session, fitting_user, product.id)

    assert fitting_job is None
    assert fitting_dto.id == existing.id
    assert fitting_dto.status == status
    assert load_fitting(database_session, existing.id).created_at == created_at


@pytest.mark.parametrize(
    ("status", "age"),
    [(FittingStatus.FAILED, timedelta(seconds=10)), (FittingStatus.PENDING, timedelta(minutes=4))],
)
def test_create_fitting_restarts_row_keeping_id(database_session, fitting_user, create_product, status, age):
    product = create_product()
    previous_created_at = datetime.now(UTC) - age
    existing = insert_fitting(database_session, fitting_user.id, product.id, status, previous_created_at)

    fitting_dto, fitting_job = service.create_fitting(database_session, fitting_user, product.id)

    row = load_fitting(database_session, existing.id)
    assert fitting_dto.id == existing.id
    assert fitting_dto.status == FittingStatus.PENDING
    assert row.status == FittingStatus.PENDING
    assert row.result_key is None
    assert row.created_at > previous_created_at
    assert fitting_job is not None
    assert fitting_job.fitting_id == existing.id
    assert fitting_job.started_at == row.created_at


def test_create_fitting_rejects_missing_product(database_session, fitting_user, create_product):
    product = create_product()

    with pytest.raises(AppError) as error:
        service.create_fitting(database_session, fitting_user, product.id + 1000)

    assert error.value.error_code == ErrorCode.PRODUCT_NOT_FOUND


def test_create_fitting_requires_body_image(database_session, create_user, create_product):
    user = create_user(nickname="no-body")
    product = create_product()

    with pytest.raises(AppError) as error:
        service.create_fitting(database_session, user, product.id)

    assert error.value.error_code == ErrorCode.PERSONAL_COLOR_REQUIRED


# ---- get_fitting ----
def test_get_fitting_returns_own_fitting(database_session, fitting_user, create_product, storage):
    product = create_product()
    fitting = insert_fitting(
        database_session, fitting_user.id, product.id, FittingStatus.DONE, datetime.now(UTC),
        result_key=f"fittings/{fitting_user.id}/1.jpg",
    )

    fitting_dto = service.get_fitting(database_session, fitting_user, fitting.id)

    assert fitting_dto.id == fitting.id
    assert fitting_dto.product.id == product.id
    assert fitting_dto.result_image_url == storage.get_url(f"fittings/{fitting_user.id}/1.jpg")


def test_get_fitting_hides_other_users_fitting(database_session, fitting_user, create_user, create_product):
    other_user = create_user(nickname="other")
    product = create_product()
    fitting = insert_fitting(database_session, other_user.id, product.id, FittingStatus.PENDING, datetime.now(UTC))

    with pytest.raises(AppError) as error:
        service.get_fitting(database_session, fitting_user, fitting.id)

    assert error.value.error_code == ErrorCode.FITTING_NOT_FOUND


# ---- run_fitting_job (백그라운드) ----
def start_job(database_session, fitting_user, create_product) -> service.FittingJob:
    product = create_product()
    _, fitting_job = service.create_fitting(database_session, fitting_user, product.id)
    assert fitting_job is not None
    return fitting_job


def test_run_fitting_job_stores_result_and_marks_done(
    database_session, fitting_user, create_product, storage, youcam_client, downloaded_urls,
):
    fitting_job = start_job(database_session, fitting_user, create_product)

    service.run_fitting_job(fitting_job)

    result_key = f"fittings/{fitting_user.id}/{fitting_job.fitting_id}.jpg"
    row = load_fitting(database_session, fitting_job.fitting_id)
    assert row.status == FittingStatus.DONE
    assert row.result_key == result_key
    assert storage.objects[result_key] == RESULT_IMAGE_BYTES
    assert downloaded_urls == [fitting_job.garment_image_url]  # Mock 결과 URL = 상품 이미지 URL


def test_run_fitting_job_marks_failed_when_youcam_returns_error(
    database_session, fitting_user, create_product, storage, youcam_client, downloaded_urls,
):
    youcam_client.cloth_fitting_succeeds = False
    fitting_job = start_job(database_session, fitting_user, create_product)

    service.run_fitting_job(fitting_job)

    row = load_fitting(database_session, fitting_job.fitting_id)
    assert row.status == FittingStatus.FAILED
    assert row.result_key is None
    assert downloaded_urls == []


def test_run_fitting_job_marks_failed_when_start_raises(
    database_session, fitting_user, create_product, youcam_client, monkeypatch, downloaded_urls,
):
    def failing_start(user_image_url: str, garment_image_url: str) -> str:
        raise AppError(ErrorCode.EXTERNAL_API_FAILED)

    monkeypatch.setattr(youcam_client, "start_cloth_fitting", failing_start)
    fitting_job = start_job(database_session, fitting_user, create_product)

    service.run_fitting_job(fitting_job)

    assert load_fitting(database_session, fitting_job.fitting_id).status == FittingStatus.FAILED


def test_run_fitting_job_marks_failed_when_download_raises(
    database_session, fitting_user, create_product, storage, youcam_client, monkeypatch,
):
    def failing_download(url: str) -> bytes:
        raise AppError(ErrorCode.EXTERNAL_API_FAILED)

    monkeypatch.setattr(service, "download_image", failing_download)
    fitting_job = start_job(database_session, fitting_user, create_product)

    service.run_fitting_job(fitting_job)

    assert load_fitting(database_session, fitting_job.fitting_id).status == FittingStatus.FAILED
    assert not any(key.startswith("fittings/") for key in storage.objects)


def test_run_fitting_job_waits_for_started_task_until_end(
    database_session, fitting_user, create_product, youcam_client, monkeypatch, downloaded_urls,
):
    started_task_ids: list[str] = []
    waited_task_ids: list[str] = []
    original_start = youcam_client.start_cloth_fitting
    original_wait = youcam_client.wait_cloth_fitting

    def recording_start(user_image_url: str, garment_image_url: str) -> str:
        task_id = original_start(user_image_url=user_image_url, garment_image_url=garment_image_url)
        started_task_ids.append(task_id)
        return task_id

    def recording_wait(task_id: str):
        waited_task_ids.append(task_id)
        return original_wait(task_id)

    monkeypatch.setattr(youcam_client, "start_cloth_fitting", recording_start)
    monkeypatch.setattr(youcam_client, "wait_cloth_fitting", recording_wait)
    fitting_job = start_job(database_session, fitting_user, create_product)

    service.run_fitting_job(fitting_job)

    assert len(started_task_ids) == 1
    assert waited_task_ids == started_task_ids


@pytest.mark.parametrize("cloth_fitting_succeeds", [True, False])
def test_run_fitting_job_writes_nothing_when_row_was_deleted(
    database_session, fitting_user, create_product, storage, youcam_client, downloaded_urls, cloth_fitting_succeeds,
):
    youcam_client.cloth_fitting_succeeds = cloth_fitting_succeeds
    fitting_job = start_job(database_session, fitting_user, create_product)
    with session_scope() as other_session:
        other_session.execute(delete(Fitting).where(Fitting.user_id == fitting_user.id))

    service.run_fitting_job(fitting_job)

    assert load_fitting(database_session, fitting_job.fitting_id) is None
    assert not any(key.startswith("fittings/") for key in storage.objects)


@pytest.mark.parametrize("cloth_fitting_succeeds", [True, False])
def test_run_fitting_job_writes_nothing_when_restarted_by_other_job(
    database_session, fitting_user, create_product, storage, youcam_client, downloaded_urls, cloth_fitting_succeeds,
):
    youcam_client.cloth_fitting_succeeds = cloth_fitting_succeeds
    fitting_job = start_job(database_session, fitting_user, create_product)
    restarted_at = fitting_job.started_at + timedelta(minutes=4)
    with session_scope() as other_session:
        other_session.get(Fitting, fitting_job.fitting_id).created_at = restarted_at

    service.run_fitting_job(fitting_job)

    row = load_fitting(database_session, fitting_job.fitting_id)
    assert row.status == FittingStatus.PENDING
    assert row.result_key is None
    assert row.created_at == restarted_at
    assert not any(key.startswith("fittings/") for key in storage.objects)
