"""swipe 슬라이스 계약 테스트. 컨텍스트 카드(슬라이스: swipe)의 백엔드 API 계약만 검증한다.

GET /api/swipe/cards?count=20
- count 기본 20, 허용 1~50 (밖이면 VALIDATION_ERROR(422))
- Response 200 SwipeCardsResponse { cards: SwipeCardDto { productId, imageUrl, style }[] }
- 성별·나이대 일치 + TOP, 이미 스와이프한 상품 제외, 스타일별 몫 = count // 5 (+ 나머지 무작위 스타일에 1장씩)
- 후보 부족 시 다른 스타일로 채우지 않음, 후보 없으면 빈 배열
- Error: PROFILE_REQUIRED(409), UNAUTHORIZED(401)

POST /api/swipe/answers
- Request SwipeAnswersRequest { answers: { productId, liked }[] } 1개 이상
- Response 200 SwipeAnswersResponse { likedCount, totalCount } — 이 사용자의 저장된 전체 swipes 기준
- upsert, 한 요청 안 중복 productId 는 마지막 값
- Error: PRODUCT_NOT_FOUND(404) 전체 거부, VALIDATION_ERROR(422) 빈 answers, UNAUTHORIZED(401)

카드 선택은 무작위이므로 특정 상품·순서·나머지 스타일은 단정하지 않는다.
"""
from collections import Counter
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select

from common.entity import Swipe
from common.enums import AgeGroup, Gender, Style
from common.error import ErrorCode
from shared.config import get_settings

CARDS_PATH = "/api/swipe/cards"
ANSWERS_PATH = "/api/swipe/answers"
SWIPE_CARDS_RESPONSE_FIELDS = {"cards"}
SWIPE_CARD_DTO_FIELDS = {"productId", "imageUrl", "style"}
SWIPE_ANSWERS_RESPONSE_FIELDS = {"likedCount", "totalCount"}


def assert_error(response, status_code: int, error_code: ErrorCode) -> None:
    assert response.status_code == status_code
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == error_code.value
    assert isinstance(body["error"]["message"], str)


def assert_cards_response_shape(body: dict) -> list[dict]:
    assert set(body) == SWIPE_CARDS_RESPONSE_FIELDS
    assert isinstance(body["cards"], list)
    for card in body["cards"]:
        assert set(card) == SWIPE_CARD_DTO_FIELDS
        assert isinstance(card["productId"], int)
        assert isinstance(card["imageUrl"], str)
        assert card["style"] in {style.value for style in Style}
    return body["cards"]


def load_swipes(database_session, user_id: int) -> dict[int, bool]:
    database_session.expire_all()
    swipes = database_session.scalars(select(Swipe).where(Swipe.user_id == user_id)).all()
    return {swipe.product_id: swipe.liked for swipe in swipes}


def add_swipe(database_session, user_id: int, product_id: int, liked: bool) -> None:
    database_session.add(Swipe(user_id=user_id, product_id=product_id, liked=liked))
    database_session.commit()


def profiled_user(create_user, nickname: str = "swiper"):
    return create_user(nickname=nickname, age_group=AgeGroup.TWENTIES, gender=Gender.FEMALE)


def create_matching_products(create_product, style: Style, amount: int) -> list:
    return [create_product(gender=Gender.FEMALE, age_group=AgeGroup.TWENTIES, style=style) for _ in range(amount)]


# ---- GET /api/swipe/cards 정상 ----
def test_get_cards_returns_unswiped_matching_products_within_style_quota(
    client, create_user, create_product, auth_headers, database_session
):
    user = profiled_user(create_user)
    matching_products = {}
    swiped_product_ids = set()
    for style in Style:
        products = create_matching_products(create_product, style, 4)
        for swiped_product in products[:1]:  # 스타일마다 1개는 이미 스와이프 → 후보 3개
            add_swipe(database_session, user.id, swiped_product.id, liked=True)
            swiped_product_ids.add(swiped_product.id)
        matching_products.update({product.id: product for product in products[1:]})
    mismatched_product_ids = {
        create_product(gender=Gender.MALE, age_group=AgeGroup.TWENTIES, style=style).id for style in Style
    } | {create_product(gender=Gender.FEMALE, age_group=AgeGroup.THIRTIES, style=style).id for style in Style}

    response = client.get(CARDS_PATH, params={"count": 7}, headers=auth_headers(user))

    assert response.status_code == 200
    cards = assert_cards_response_shape(response.json())
    product_ids = [card["productId"] for card in cards]
    assert len(cards) == 7
    assert len(set(product_ids)) == len(product_ids)  # 중복 없음
    assert set(product_ids) <= set(matching_products)  # 성별·나이대 일치
    assert not set(product_ids) & swiped_product_ids  # 이미 스와이프한 상품 제외
    assert not set(product_ids) & mismatched_product_ids
    for card in cards:
        product = matching_products[card["productId"]]
        assert card["style"] == product.style.value
        assert card["imageUrl"] == product.image_url
    # count=7 → 몫 1, 나머지 2장은 서로 다른 스타일에 1장씩
    style_counts = Counter(card["style"] for card in cards)
    assert sorted(style_counts[style.value] for style in Style) == [1, 1, 1, 2, 2]


def test_get_cards_with_default_count_does_not_fill_short_styles_from_others(
    client, create_user, create_product, auth_headers
):
    user = profiled_user(create_user)
    create_matching_products(create_product, Style.MINIMAL, 6)  # 몫 4 < 후보 6 → 4장
    create_matching_products(create_product, Style.CASUAL, 2)  # 몫 4 > 후보 2 → 2장
    # 나머지 스타일은 후보 0 → 0장. 다른 스타일로 채우지 않으므로 총 6장

    response = client.get(CARDS_PATH, headers=auth_headers(user))  # count 기본 20 → 스타일별 몫 4

    assert response.status_code == 200
    cards = assert_cards_response_shape(response.json())
    style_counts = Counter(card["style"] for card in cards)
    assert style_counts == Counter({Style.MINIMAL.value: 4, Style.CASUAL.value: 2})
    assert len({card["productId"] for card in cards}) == 6


def test_get_cards_without_candidates_returns_empty_list(client, create_user, create_product, auth_headers):
    user = profiled_user(create_user)
    for style in Style:
        create_product(gender=Gender.MALE, age_group=AgeGroup.TWENTIES, style=style)
        create_product(gender=Gender.FEMALE, age_group=AgeGroup.FORTIES_PLUS, style=style)

    response = client.get(CARDS_PATH, params={"count": 20}, headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json() == {"cards": []}


# ---- GET /api/swipe/cards 거부 ----
@pytest.mark.parametrize(
    ("user_columns", "params", "status_code", "error_code"),
    [
        ({"age_group": AgeGroup.TWENTIES, "gender": Gender.FEMALE}, {"count": 0}, 422, ErrorCode.VALIDATION_ERROR),
        ({"age_group": AgeGroup.TWENTIES, "gender": Gender.FEMALE}, {"count": 51}, 422, ErrorCode.VALIDATION_ERROR),
        ({"age_group": None, "gender": Gender.FEMALE}, {"count": 20}, 409, ErrorCode.PROFILE_REQUIRED),
        ({"age_group": AgeGroup.TWENTIES, "gender": None}, {"count": 20}, 409, ErrorCode.PROFILE_REQUIRED),
        ({}, {}, 409, ErrorCode.PROFILE_REQUIRED),  # 프로필 미설정 (둘 다 NULL)
    ],
)
def test_get_cards_rejects_invalid_count_or_missing_profile(
    client, create_user, create_product, auth_headers, user_columns, params, status_code, error_code
):
    user = create_user(nickname="member", **user_columns)
    for style in Style:
        create_matching_products(create_product, style, 4)

    response = client.get(CARDS_PATH, params=params, headers=auth_headers(user))

    assert_error(response, status_code, error_code)


# ---- POST /api/swipe/answers 정상 ----
def test_submit_answers_upserts_with_last_value_and_counts_all_stored_swipes(
    client, create_user, create_product, auth_headers, database_session
):
    user = profiled_user(create_user)
    other_user = profiled_user(create_user, nickname="other")
    resubmitted_product, duplicated_product, new_product, untouched_product = (
        create_product() for _ in range(4)
    )
    add_swipe(database_session, user.id, resubmitted_product.id, liked=False)
    add_swipe(database_session, user.id, untouched_product.id, liked=True)
    add_swipe(database_session, other_user.id, new_product.id, liked=True)  # 다른 사용자 행은 집계 제외

    response = client.post(
        ANSWERS_PATH,
        json={
            "answers": [
                {"productId": resubmitted_product.id, "liked": True},  # 기존 False → True 덮어씀
                {"productId": duplicated_product.id, "liked": True},
                {"productId": duplicated_product.id, "liked": False},  # 같은 요청 안 마지막 값 사용
                {"productId": new_product.id, "liked": False},
            ]
        },
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == SWIPE_ANSWERS_RESPONSE_FIELDS
    assert isinstance(body["likedCount"], int)
    assert isinstance(body["totalCount"], int)
    assert body == {"likedCount": 2, "totalCount": 4}
    assert load_swipes(database_session, user.id) == {
        resubmitted_product.id: True,
        duplicated_product.id: False,
        new_product.id: False,
        untouched_product.id: True,
    }
    assert load_swipes(database_session, other_user.id) == {new_product.id: True}


# ---- POST /api/swipe/answers 거부 ----
@pytest.mark.parametrize(
    ("answers_kind", "status_code", "error_code"),
    [
        ("contains_missing_product", 404, ErrorCode.PRODUCT_NOT_FOUND),
        ("empty", 422, ErrorCode.VALIDATION_ERROR),
    ],
)
def test_submit_answers_rejects_whole_request_without_partial_save(
    client, create_user, create_product, auth_headers, database_session, answers_kind, status_code, error_code
):
    user = profiled_user(create_user)
    existing_product, valid_product = create_product(), create_product()
    add_swipe(database_session, user.id, existing_product.id, liked=False)
    missing_product_id = valid_product.id + 1000
    answers = {
        "contains_missing_product": [
            {"productId": existing_product.id, "liked": True},
            {"productId": valid_product.id, "liked": True},
            {"productId": missing_product_id, "liked": False},
        ],
        "empty": [],
    }[answers_kind]

    response = client.post(ANSWERS_PATH, json={"answers": answers}, headers=auth_headers(user))

    assert_error(response, status_code, error_code)
    assert load_swipes(database_session, user.id) == {existing_product.id: False}


# ---- 권한 ----
def _token_with(user_id: int, secret: str, expires_at: datetime) -> str:
    return jwt.encode({"sub": str(user_id), "exp": expires_at}, secret, algorithm="HS256")


@pytest.mark.parametrize("endpoint", ["cards", "answers"])
@pytest.mark.parametrize("token_kind", ["missing", "expired", "forged"])
def test_swipe_endpoints_without_valid_token_return_unauthorized(
    client, create_user, create_product, database_session, endpoint, token_kind
):
    user = profiled_user(create_user)
    product = create_product()
    secret = get_settings().jwt_secret
    headers = {
        "missing": {},
        "expired": {"Authorization": f"Bearer {_token_with(user.id, secret, datetime.now(UTC) - timedelta(minutes=1))}"},
        "forged": {"Authorization": f"Bearer {_token_with(user.id, 'forged-secret-key-0123456789abcdef', datetime.now(UTC) + timedelta(days=1))}"},
    }[token_kind]

    if endpoint == "cards":
        response = client.get(CARDS_PATH, params={"count": 20}, headers=headers)
    else:
        response = client.post(
            ANSWERS_PATH, json={"answers": [{"productId": product.id, "liked": True}]}, headers=headers
        )

    assert_error(response, 401, ErrorCode.UNAUTHORIZED)
    assert load_swipes(database_session, user.id) == {}
