"""fitting 슬라이스 계약 테스트. 컨텍스트 카드(슬라이스: fitting)의 백엔드 API 계약만 검증한다.

POST /api/fittings (인증 필요)
- Request FittingCreateRequest { productId }
- Response 202 FittingDto { id, productId, product: ProductDto, status, originalImageUrl, resultImageUrl }
- DONE → 그대로 반환(YouCam 호출 없음), 3분 이내 PENDING → 그대로 반환
- 없음 / FAILED / 3분 넘은 PENDING → PENDING·result_key NULL·created_at 현재로 생성/갱신 후 백그라운드 작업
- Error: PRODUCT_NOT_FOUND(404), PERSONAL_COLOR_REQUIRED(409, body_image_key 없음), UNAUTHORIZED(401)

GET /api/fittings/{fittingId} (인증 필요)
- Response 200 FittingDto
- Error: FITTING_NOT_FOUND(404, 없음 또는 다른 사용자), UNAUTHORIZED(401)

백그라운드 작업: start_cloth_fitting → wait_cloth_fitting → SUCCESS 면 결과 다운로드 →
fittings/{userId}/{fittingId}.jpg 업로드 → DONE / ERROR·예외 → FAILED

작업이 끝났을 때 행이 없으면(personal_color 사진 변경으로 삭제) 아무것도 하지 않는다 — 행 재생성·결과 업로드 없음.
재시작(FAILED / 3분 넘은 PENDING) 시 기존 행을 갱신하며 id 를 유지한다.

TestClient 에서는 BackgroundTasks 가 응답 직후 동기로 실행되므로 POST 응답(PENDING)과 이후 GET 결과를 나눠 검증한다.
"""
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import delete, select

from common.entity import Fitting
from common.enums import FittingStatus, Style
from common.error import ErrorCode
from shared.database import get_session_factory

FITTINGS_PATH = "/api/fittings"
FITTING_DTO_FIELDS = {"id", "productId", "product", "status", "originalImageUrl", "resultImageUrl"}
PRODUCT_DTO_FIELDS = {"id", "title", "price", "currency", "mallName", "purchaseUrl", "imageUrl", "style"}
STALE_PENDING_AGE = timedelta(minutes=4)  # 슬라이스 상수 3분 초과
FRESH_PENDING_AGE = timedelta(minutes=1)  # 슬라이스 상수 3분 이내


# ---- 입력 통제 ----
def body_image_key_of(user_id: int) -> str:
    return f"body-images/{user_id}/body.jpg"


def create_user_with_body_image(create_user, nickname: str = "fitter"):
    user = create_user(nickname=nickname)
    user.body_image_key = body_image_key_of(user.id)
    return user


@pytest.fixture
def fitting_user(create_user, database_session):
    user = create_user_with_body_image(create_user)
    database_session.commit()
    return user


@pytest.fixture
def result_image_bytes(sample_image_bytes) -> bytes:
    return sample_image_bytes(color=(10, 120, 200))


@pytest.fixture
def downloaded_urls(monkeypatch, result_image_bytes) -> list[str]:
    """download_image 내부의 httpx.get 을 대체. 호출된 URL 을 기록한다."""
    urls: list[str] = []

    def fake_get(url, *arguments, **keyword_arguments):
        urls.append(str(url))
        return httpx.Response(200, content=result_image_bytes, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    return urls


@pytest.fixture
def cloth_fitting_calls(monkeypatch, youcam_client) -> list[dict]:
    """youcam_client.start_cloth_fitting 호출 인자를 기록한다."""
    calls: list[dict] = []
    original_start = youcam_client.start_cloth_fitting

    def counting_start(user_image_url: str, garment_image_url: str) -> str:
        calls.append({"user_image_url": user_image_url, "garment_image_url": garment_image_url})
        return original_start(user_image_url=user_image_url, garment_image_url=garment_image_url)

    monkeypatch.setattr(youcam_client, "start_cloth_fitting", counting_start)
    return calls


def insert_fitting(database_session, user_id: int, product_id: int, status: FittingStatus, created_at: datetime,
                   result_key: str | None = None) -> Fitting:
    fitting = Fitting(user_id=user_id, product_id=product_id, status=status, result_key=result_key, created_at=created_at)
    database_session.add(fitting)
    database_session.commit()
    return fitting


def fittings_of(database_session, user_id: int, product_id: int) -> list[Fitting]:
    database_session.expire_all()
    return list(
        database_session.scalars(
            select(Fitting).where(Fitting.user_id == user_id, Fitting.product_id == product_id)
        ).all()
    )


# ---- 검증 헬퍼 ----
def assert_product_dto(product_body: dict, product) -> None:
    assert set(product_body) == PRODUCT_DTO_FIELDS
    assert product_body == {
        "id": product.id,
        "title": product.title,
        "price": float(product.price),
        "currency": product.currency,
        "mallName": product.mall_name,
        "purchaseUrl": product.purchase_url,
        "imageUrl": product.image_url,
        "style": Style(product.style).value,
    }
    assert isinstance(product_body["id"], int)
    assert isinstance(product_body["price"], int | float) and not isinstance(product_body["price"], bool)


def assert_fitting_dto(body: dict, user, product, storage, status: FittingStatus) -> None:
    assert set(body) == FITTING_DTO_FIELDS
    assert isinstance(body["id"], int)
    assert body["productId"] == product.id
    assert_product_dto(body["product"], product)
    assert body["status"] == status.value
    assert body["originalImageUrl"] == storage.get_url(body_image_key_of(user.id))
    if status == FittingStatus.DONE:
        assert body["resultImageUrl"] == storage.get_url(f"fittings/{user.id}/{body['id']}.jpg")
    else:
        assert body["resultImageUrl"] is None


def assert_error(response, status_code: int, error_code: ErrorCode) -> None:
    assert response.status_code == status_code
    body = response.json()
    assert body["error"]["code"] == error_code.value
    assert isinstance(body["error"]["message"], str)


# ---- 정상 ----
def test_create_fitting_returns_pending_then_stores_result_as_done(
    client, auth_headers, fitting_user, create_product, storage, database_session,
    downloaded_urls, cloth_fitting_calls, result_image_bytes,
):
    product = create_product()

    create_response = client.post(FITTINGS_PATH, json={"productId": product.id}, headers=auth_headers(fitting_user))

    assert create_response.status_code == 202
    created = create_response.json()
    assert_fitting_dto(created, fitting_user, product, storage, FittingStatus.PENDING)

    # 백그라운드 작업: 사용자 상반신 URL + 상품 이미지 URL 로 1회 호출, 결과 다운로드 후 저장
    assert cloth_fitting_calls == [
        {"user_image_url": storage.get_url(body_image_key_of(fitting_user.id)), "garment_image_url": product.image_url}
    ]
    assert downloaded_urls == [product.image_url]  # Mock 결과 URL = 상품 이미지 URL
    result_key = f"fittings/{fitting_user.id}/{created['id']}.jpg"
    assert storage.objects[result_key] == result_image_bytes

    get_response = client.get(f"{FITTINGS_PATH}/{created['id']}", headers=auth_headers(fitting_user))

    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched["id"] == created["id"]
    assert_fitting_dto(fetched, fitting_user, product, storage, FittingStatus.DONE)

    rows = fittings_of(database_session, fitting_user.id, product.id)
    assert len(rows) == 1
    assert rows[0].status == FittingStatus.DONE
    assert rows[0].result_key == result_key


def test_create_fitting_marks_failed_when_youcam_returns_error(
    client, auth_headers, fitting_user, create_product, storage, database_session, youcam_client, downloaded_urls,
):
    youcam_client.cloth_fitting_succeeds = False
    product = create_product()

    create_response = client.post(FITTINGS_PATH, json={"productId": product.id}, headers=auth_headers(fitting_user))

    assert create_response.status_code == 202
    created = create_response.json()
    assert_fitting_dto(created, fitting_user, product, storage, FittingStatus.PENDING)

    get_response = client.get(f"{FITTINGS_PATH}/{created['id']}", headers=auth_headers(fitting_user))

    assert get_response.status_code == 200
    assert_fitting_dto(get_response.json(), fitting_user, product, storage, FittingStatus.FAILED)
    assert downloaded_urls == []
    assert not any(key.startswith("fittings/") for key in storage.objects)
    rows = fittings_of(database_session, fitting_user.id, product.id)
    assert len(rows) == 1
    assert rows[0].status == FittingStatus.FAILED
    assert rows[0].result_key is None


# ---- 불변조건: 재사용 (YouCam 재호출 없음) ----
@pytest.mark.parametrize("existing_status", [FittingStatus.DONE, FittingStatus.PENDING])
def test_create_fitting_reuses_done_or_recent_pending_without_calling_youcam(
    client, auth_headers, fitting_user, create_product, storage, database_session,
    downloaded_urls, cloth_fitting_calls, existing_status,
):
    product = create_product()
    existing = insert_fitting(
        database_session, fitting_user.id, product.id, existing_status,
        created_at=datetime.now(UTC) - FRESH_PENDING_AGE,
    )
    if existing_status == FittingStatus.DONE:
        existing.result_key = f"fittings/{fitting_user.id}/{existing.id}.jpg"
        database_session.commit()

    response = client.post(FITTINGS_PATH, json={"productId": product.id}, headers=auth_headers(fitting_user))

    assert response.status_code == 202
    body = response.json()
    assert body["id"] == existing.id
    assert_fitting_dto(body, fitting_user, product, storage, existing_status)
    assert cloth_fitting_calls == []
    assert downloaded_urls == []
    rows = fittings_of(database_session, fitting_user.id, product.id)
    assert len(rows) == 1
    assert rows[0].status == existing_status


# ---- 불변조건: 재시작 (행 1개 유지) ----
@pytest.mark.parametrize(
    ("existing_status", "existing_age"),
    [(FittingStatus.FAILED, FRESH_PENDING_AGE), (FittingStatus.PENDING, STALE_PENDING_AGE)],
    ids=["failed", "stale-pending"],
)
def test_create_fitting_restarts_failed_or_stale_pending_in_single_row(
    client, auth_headers, fitting_user, create_product, storage, database_session,
    downloaded_urls, cloth_fitting_calls, existing_status, existing_age,
):
    product = create_product()
    previous_created_at = datetime.now(UTC) - existing_age
    existing = insert_fitting(database_session, fitting_user.id, product.id, existing_status, created_at=previous_created_at)

    response = client.post(FITTINGS_PATH, json={"productId": product.id}, headers=auth_headers(fitting_user))

    assert response.status_code == 202
    body = response.json()
    assert body["id"] == existing.id  # 갱신 시 id 유지
    assert_fitting_dto(body, fitting_user, product, storage, FittingStatus.PENDING)
    assert len(cloth_fitting_calls) == 1

    rows = fittings_of(database_session, fitting_user.id, product.id)
    assert len(rows) == 1
    assert rows[0].id == existing.id
    assert rows[0].created_at > previous_created_at  # 마지막으로 작업을 시작한 시각
    assert rows[0].status == FittingStatus.DONE  # 백그라운드 작업이 응답 직후 실행됨
    assert rows[0].result_key == f"fittings/{fitting_user.id}/{body['id']}.jpg"


# ---- 공유 상태: 작업 중 행 삭제 (personal_color 사진 변경) ----
def test_background_task_does_nothing_when_fitting_row_was_deleted(
    client, auth_headers, fitting_user, create_product, storage, database_session, youcam_client,
    downloaded_urls, monkeypatch,
):
    product = create_product()
    original_wait = youcam_client.wait_cloth_fitting

    def wait_after_row_deleted(task_id: str):
        with get_session_factory()() as other_session:  # 작업 도중 다른 요청이 이 사용자의 fittings 를 삭제
            other_session.execute(delete(Fitting).where(Fitting.user_id == fitting_user.id))
            other_session.commit()
        return original_wait(task_id)

    monkeypatch.setattr(youcam_client, "wait_cloth_fitting", wait_after_row_deleted)

    response = client.post(FITTINGS_PATH, json={"productId": product.id}, headers=auth_headers(fitting_user))

    assert response.status_code == 202
    assert fittings_of(database_session, fitting_user.id, product.id) == []  # 행을 다시 만들지 않는다
    assert not any(key.startswith("fittings/") for key in storage.objects)  # 결과 업로드도 하지 않는다


# ---- 에러 ----
@pytest.mark.parametrize("case", ["product-not-found", "body-image-missing"])
def test_create_fitting_rejects_missing_product_or_body_image(
    client, auth_headers, create_user, create_product, database_session, cloth_fitting_calls, case,
):
    product = create_product()
    if case == "product-not-found":
        user = create_user_with_body_image(create_user)
        database_session.commit()
        product_id, expected = product.id + 1000, (404, ErrorCode.PRODUCT_NOT_FOUND)
    else:
        user = create_user(nickname="no-body-image")
        product_id, expected = product.id, (409, ErrorCode.PERSONAL_COLOR_REQUIRED)

    response = client.post(FITTINGS_PATH, json={"productId": product_id}, headers=auth_headers(user))

    assert_error(response, *expected)
    assert cloth_fitting_calls == []
    database_session.expire_all()
    assert database_session.scalars(select(Fitting)).all() == []


@pytest.mark.parametrize("case", ["other-user", "missing"])
def test_get_fitting_returns_not_found_for_other_user_or_missing(
    client, auth_headers, create_user, create_product, database_session, case,
):
    owner = create_user_with_body_image(create_user, nickname="owner")
    requester = create_user_with_body_image(create_user, nickname="requester")
    database_session.commit()
    product = create_product()
    fitting = insert_fitting(
        database_session, owner.id, product.id, FittingStatus.DONE,
        created_at=datetime.now(UTC), result_key=f"fittings/{owner.id}/1.jpg",
    )
    fitting_id = fitting.id if case == "other-user" else fitting.id + 1000

    response = client.get(f"{FITTINGS_PATH}/{fitting_id}", headers=auth_headers(requester))

    assert_error(response, 404, ErrorCode.FITTING_NOT_FOUND)


# ---- 인증 ----
@pytest.mark.parametrize("method", ["post", "get"])
def test_fitting_endpoints_without_token_return_unauthorized(
    client, fitting_user, create_product, database_session, cloth_fitting_calls, method,
):
    product = create_product()
    if method == "post":
        response = client.post(FITTINGS_PATH, json={"productId": product.id})
    else:
        fitting = insert_fitting(database_session, fitting_user.id, product.id, FittingStatus.PENDING, datetime.now(UTC))
        response = client.get(f"{FITTINGS_PATH}/{fitting.id}")

    assert_error(response, 401, ErrorCode.UNAUTHORIZED)
    assert cloth_fitting_calls == []
