"""swipe 슬라이스 계약 테스트. 컨텍스트 카드(슬라이스: swipe)의 백엔드 API 계약만 검증한다.

GET /api/swipe/cards?count=20
- count 기본 20, 허용 1~50 (밖이면 VALIDATION_ERROR(422))
- Response 200 SwipeCardsResponse { cards: SwipeCardDto { pinId, imageUrl, style }[] }
- 카드는 핀(코디 사진). 성별·나이대 일치, 이미 스와이프한 핀 제외, 스타일별 몫 = count // 5 (+ 나머지 무작위 스타일에 1장씩)
- 후보 부족 시 다른 스타일로 채우지 않음, 후보 없으면 빈 배열
- Error: PROFILE_REQUIRED(409), UNAUTHORIZED(401)

POST /api/swipe/answers
- Request SwipeAnswersRequest { answers: { pinId, liked }[] } 1개 이상
- Response 200 SwipeAnswersResponse { likedCount, totalCount } — 이 사용자의 저장된 전체 swipes 기준
- upsert, 한 요청 안 중복 pinId 는 마지막 값
- Error: PIN_NOT_FOUND(404) 전체 거부, VALIDATION_ERROR(422) 빈 answers, UNAUTHORIZED(401)

카드 선택은 무작위이므로 특정 핀·순서·나머지 스타일은 단정하지 않는다.
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
SWIPE_CARD_DTO_FIELDS = {"pinId", "imageUrl", "style"}
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
        assert isinstance(card["pinId"], int)
        assert isinstance(card["imageUrl"], str)
        assert card["style"] in {style.value for style in Style}
    return body["cards"]


def load_swipes(database_session, user_id: int) -> dict[int, bool]:
    database_session.expire_all()
    swipes = database_session.scalars(select(Swipe).where(Swipe.user_id == user_id)).all()
    return {swipe.pin_id: swipe.liked for swipe in swipes}


def add_swipe(database_session, user_id: int, pin_id: int, liked: bool) -> None:
    database_session.add(Swipe(user_id=user_id, pin_id=pin_id, liked=liked))
    database_session.commit()


def profiled_user(create_user, nickname: str = "swiper"):
    return create_user(nickname=nickname, age_group=AgeGroup.TWENTIES, gender=Gender.FEMALE)


def create_matching_pins(create_pin, style: Style, amount: int) -> list:
    return [create_pin(gender=Gender.FEMALE, age_group=AgeGroup.TWENTIES, style=style) for _ in range(amount)]


# ---- GET /api/swipe/cards 정상 ----
def test_get_cards_returns_unswiped_matching_pins_within_style_quota(
    client, create_user, create_pin, auth_headers, database_session
):
    user = profiled_user(create_user)
    matching_pins = {}
    swiped_pin_ids = set()
    for style in Style:
        pins = create_matching_pins(create_pin, style, 4)
        for swiped_pin in pins[:1]:  # 스타일마다 1개는 이미 스와이프 → 후보 3개
            add_swipe(database_session, user.id, swiped_pin.id, liked=True)
            swiped_pin_ids.add(swiped_pin.id)
        matching_pins.update({pin.id: pin for pin in pins[1:]})
    mismatched_pin_ids = {
        create_pin(gender=Gender.MALE, age_group=AgeGroup.TWENTIES, style=style).id for style in Style
    } | {create_pin(gender=Gender.FEMALE, age_group=AgeGroup.THIRTIES, style=style).id for style in Style}

    response = client.get(CARDS_PATH, params={"count": 7}, headers=auth_headers(user))

    assert response.status_code == 200
    cards = assert_cards_response_shape(response.json())
    pin_ids = [card["pinId"] for card in cards]
    assert len(cards) == 7
    assert len(set(pin_ids)) == len(pin_ids)  # 중복 없음
    assert set(pin_ids) <= set(matching_pins)  # 성별·나이대 일치
    assert not set(pin_ids) & swiped_pin_ids  # 이미 스와이프한 핀 제외
    assert not set(pin_ids) & mismatched_pin_ids
    for card in cards:
        pin = matching_pins[card["pinId"]]
        assert card["style"] == pin.style.value
        assert card["imageUrl"] == pin.image_url
    # count=7 → 몫 1, 나머지 2장은 서로 다른 스타일에 1장씩
    style_counts = Counter(card["style"] for card in cards)
    assert sorted(style_counts[style.value] for style in Style) == [1, 1, 1, 2, 2]


def test_get_cards_with_default_count_does_not_fill_short_styles_from_others(
    client, create_user, create_pin, auth_headers
):
    user = profiled_user(create_user)
    create_matching_pins(create_pin, Style.MINIMAL, 6)  # 몫 4 < 후보 6 → 4장
    create_matching_pins(create_pin, Style.CASUAL, 2)  # 몫 4 > 후보 2 → 2장
    # 나머지 스타일은 후보 0 → 0장. 다른 스타일로 채우지 않으므로 총 6장

    response = client.get(CARDS_PATH, headers=auth_headers(user))  # count 기본 20 → 스타일별 몫 4

    assert response.status_code == 200
    cards = assert_cards_response_shape(response.json())
    style_counts = Counter(card["style"] for card in cards)
    assert style_counts == Counter({Style.MINIMAL.value: 4, Style.CASUAL.value: 2})
    assert len({card["pinId"] for card in cards}) == 6


def test_get_cards_without_candidates_returns_empty_list(client, create_user, create_pin, auth_headers):
    user = profiled_user(create_user)
    for style in Style:
        create_pin(gender=Gender.MALE, age_group=AgeGroup.TWENTIES, style=style)
        create_pin(gender=Gender.FEMALE, age_group=AgeGroup.FORTIES_PLUS, style=style)

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
    client, create_user, create_pin, auth_headers, user_columns, params, status_code, error_code
):
    user = create_user(nickname="member", **user_columns)
    for style in Style:
        create_matching_pins(create_pin, style, 4)

    response = client.get(CARDS_PATH, params=params, headers=auth_headers(user))

    assert_error(response, status_code, error_code)


# ---- POST /api/swipe/answers 정상 ----
def test_submit_answers_upserts_with_last_value_and_counts_all_stored_swipes(
    client, create_user, create_pin, auth_headers, database_session
):
    user = profiled_user(create_user)
    other_user = profiled_user(create_user, nickname="other")
    resubmitted_pin, duplicated_pin, new_pin, untouched_pin = (
        create_pin() for _ in range(4)
    )
    add_swipe(database_session, user.id, resubmitted_pin.id, liked=False)
    add_swipe(database_session, user.id, untouched_pin.id, liked=True)
    add_swipe(database_session, other_user.id, new_pin.id, liked=True)  # 다른 사용자 행은 집계 제외

    response = client.post(
        ANSWERS_PATH,
        json={
            "answers": [
                {"pinId": resubmitted_pin.id, "liked": True},  # 기존 False → True 덮어씀
                {"pinId": duplicated_pin.id, "liked": True},
                {"pinId": duplicated_pin.id, "liked": False},  # 같은 요청 안 마지막 값 사용
                {"pinId": new_pin.id, "liked": False},
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
        resubmitted_pin.id: True,
        duplicated_pin.id: False,
        new_pin.id: False,
        untouched_pin.id: True,
    }
    assert load_swipes(database_session, other_user.id) == {new_pin.id: True}


# ---- POST /api/swipe/answers 거부 ----
@pytest.mark.parametrize(
    ("answers_kind", "status_code", "error_code"),
    [
        ("contains_missing_pin", 404, ErrorCode.PIN_NOT_FOUND),
        ("empty", 422, ErrorCode.VALIDATION_ERROR),
    ],
)
def test_submit_answers_rejects_whole_request_without_partial_save(
    client, create_user, create_pin, auth_headers, database_session, answers_kind, status_code, error_code
):
    user = profiled_user(create_user)
    existing_pin, valid_pin = create_pin(), create_pin()
    add_swipe(database_session, user.id, existing_pin.id, liked=False)
    missing_pin_id = valid_pin.id + 1000
    answers = {
        "contains_missing_pin": [
            {"pinId": existing_pin.id, "liked": True},
            {"pinId": valid_pin.id, "liked": True},
            {"pinId": missing_pin_id, "liked": False},
        ],
        "empty": [],
    }[answers_kind]

    response = client.post(ANSWERS_PATH, json={"answers": answers}, headers=auth_headers(user))

    assert_error(response, status_code, error_code)
    assert load_swipes(database_session, user.id) == {existing_pin.id: False}


# ---- 권한 ----
def _token_with(user_id: int, secret: str, expires_at: datetime) -> str:
    return jwt.encode({"sub": str(user_id), "exp": expires_at}, secret, algorithm="HS256")


@pytest.mark.parametrize("endpoint", ["cards", "answers"])
@pytest.mark.parametrize("token_kind", ["missing", "expired", "forged"])
def test_swipe_endpoints_without_valid_token_return_unauthorized(
    client, create_user, create_pin, database_session, endpoint, token_kind
):
    user = profiled_user(create_user)
    pin = create_pin()
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
            ANSWERS_PATH, json={"answers": [{"pinId": pin.id, "liked": True}]}, headers=headers
        )

    assert_error(response, 401, ErrorCode.UNAUTHORIZED)
    assert load_swipes(database_session, user.id) == {}
