"""recommendation 슬라이스 계약 테스트. 컨텍스트 카드(슬라이스: recommendation)의 백엔드 API 계약만 검증한다.

GET /api/recommendations (인증 필요)
- Response 200 RecommendationResponse { styleTags, season, palette, isFallback, items: RecommendationItem[] }
- RecommendationItem { product: ProductDto, score, tasteScore, colorScore, reasonTags }
- ProductDto { id, title, price, mallName, purchaseUrl, imageUrl, style }
- 스와이프는 핀(코디 사진)에 한다. 후보: gender·age_group 일치 + TOP 상품 전체 (스와이프와 무관)
- 핀평균 P·상품평균 Q 는 embedding_centroids 에 미리 적재 (없으면 0 벡터)
- u = normalize(mean(L − P) + 1.5 × mean(C) − 0.5 × mean(D − P)), c_i = cos(u, e_i − Q)
- tasteScore = Φ((c_i − μ) / σ) (σ = 0 이면 0.5)
- colorScore = max(0, 1 − ΔE / 50), score = 0.7 × tasteScore + 0.3 × colorScore
- 정렬 score 내림차순 → product.id 오름차순, 최대 5개
- 폴백(좋아요 < 3): tasteScore = 0, score = colorScore, isFallback = true
- Error: PROFILE_REQUIRED(409), PERSONAL_COLOR_REQUIRED(409), UNAUTHORIZED(401)

기대값은 DB 에서 다시 읽은 embedding·color_lab 으로 카드의 식을 그대로 계산한다.
"""
import math
from collections import Counter
from datetime import UTC, datetime, timedelta

import jwt
import numpy as np
import pytest

from common.entity import EMBEDDING_DIMENSION, EmbeddingCentroid, Swipe, WardrobePhoto
from common.enums import AgeGroup, EmbeddingDomain, Gender, Season, Style
from common.error import ErrorCode
from shared.color import SEASON_PALETTES, delta_e, palette_lab
from shared.config import get_settings

RECOMMENDATIONS_PATH = "/api/recommendations"
RECOMMENDATION_RESPONSE_FIELDS = {"styleTags", "season", "palette", "isFallback", "items"}
RECOMMENDATION_ITEM_FIELDS = {"product", "score", "tasteScore", "colorScore", "reasonTags"}
PRODUCT_DTO_FIELDS = {"id", "title", "price", "mallName", "purchaseUrl", "imageUrl", "style"}
MAXIMUM_ITEM_COUNT = 5
TOLERANCE = 1e-6

STYLE_KOREAN_NAMES = {
    Style.MINIMAL: "미니멀",
    Style.CASUAL: "캐주얼",
    Style.STREET: "스트릿",
    Style.FORMAL: "포멀",
    Style.LOVELY: "러블리",
}
SEASON_KOREAN_NAMES = {
    Season.SPRING_WARM: "봄 웜톤",
    Season.SUMMER_COOL: "여름 쿨톤",
    Season.AUTUMN_WARM: "가을 웜톤",
    Season.WINTER_COOL: "겨울 쿨톤",
}


# ---- 입력 통제 ----
def axis_vector(*weights_by_axis: tuple[int, float]) -> list[float]:
    """지정한 축에만 값이 있는 L2 정규화 512차원 벡터."""
    vector = np.zeros(EMBEDDING_DIMENSION)
    for axis, weight in weights_by_axis:
        vector[axis] = weight
    return (vector / np.linalg.norm(vector)).tolist()


def shifted_lab(base: tuple[float, float, float], lightness_offset: float) -> list[float]:
    return [base[0] + lightness_offset, base[1], base[2]]


def matching_user(create_user, season: Season, nickname: str = "recommendee"):
    return create_user(nickname=nickname, age_group=AgeGroup.TWENTIES, gender=Gender.FEMALE, season=season)


def matching_product(create_product, **columns):
    return create_product(gender=Gender.FEMALE, age_group=AgeGroup.TWENTIES, **columns)


def matching_pin(create_pin, **columns):
    return create_pin(gender=Gender.FEMALE, age_group=AgeGroup.TWENTIES, **columns)


def add_swipe(database_session, user_id: int, pin_id: int, liked: bool) -> None:
    database_session.add(Swipe(user_id=user_id, pin_id=pin_id, liked=liked))
    database_session.commit()


def add_centroid(database_session, domain: EmbeddingDomain, embedding: list[float]) -> EmbeddingCentroid:
    centroid = EmbeddingCentroid(domain=domain, embedding=embedding)
    database_session.add(centroid)
    database_session.commit()
    return centroid


def add_wardrobe_photo(database_session, user_id: int, embedding: list[float]) -> WardrobePhoto:
    photo = WardrobePhoto(user_id=user_id, image_key=f"wardrobe/{user_id}/photo.jpg", embedding=embedding)
    database_session.add(photo)
    database_session.commit()
    return photo


def stored_vector(entity) -> np.ndarray:
    """DB 에 저장된 값(pgvector 정밀도)으로 다시 읽는다."""
    return np.asarray(entity.embedding, dtype=float)


# ---- 카드의 식으로 기대값 계산 ----
def mean_or_zero(vectors: list[np.ndarray]) -> np.ndarray:
    return np.mean(vectors, axis=0) if vectors else np.zeros(EMBEDDING_DIMENSION)


def expected_taste_vector(liked_pins, wardrobe_photos, disliked_pins, pin_centroid: np.ndarray) -> np.ndarray:
    combined = (
        mean_or_zero([stored_vector(pin) - pin_centroid for pin in liked_pins])
        + 1.5 * mean_or_zero([stored_vector(photo) for photo in wardrobe_photos])
        - 0.5 * mean_or_zero([stored_vector(pin) - pin_centroid for pin in disliked_pins])
    )
    norm = np.linalg.norm(combined)
    return combined if norm == 0 else combined / norm


def expected_taste_scores(taste_vector: np.ndarray, candidates, product_centroid: np.ndarray) -> dict[int, float]:
    similarities = {}
    for product in candidates:
        embedding = stored_vector(product) - product_centroid
        similarities[product.id] = float(np.dot(taste_vector, embedding) / np.linalg.norm(embedding))
    values = np.array(list(similarities.values()))
    mean, standard_deviation = values.mean(), values.std(ddof=0)
    if np.linalg.norm(taste_vector) == 0 or standard_deviation == 0:
        return {product_id: 0.5 for product_id in similarities}
    return {
        product_id: 0.5 * (1 + math.erf(((similarity - mean) / standard_deviation) / math.sqrt(2)))
        for product_id, similarity in similarities.items()
    }


def expected_color_score(product, season: Season) -> float:
    nearest_distance = min(delta_e(tuple(product.color_lab), palette_color) for palette_color in palette_lab(season))
    return max(0.0, 1 - nearest_distance / 50)


def expected_preferred_styles(liked_pins) -> list[Style]:
    style_order = list(Style)
    frequencies = Counter(pin.style for pin in liked_pins)
    ranked = sorted(frequencies, key=lambda style: (-frequencies[style], style_order.index(style)))
    return ranked[:2]


def expected_reason_tags(product, color_score: float, preferred_styles: list[Style], season: Season) -> list[str]:
    tags = []
    if product.style in preferred_styles:
        tags.append(f"선호하는 {STYLE_KOREAN_NAMES[product.style]}")
    if color_score >= 0.7:
        tags.append(f"{SEASON_KOREAN_NAMES[season]} 컬러")
    if not tags:
        tags.append(f"{STYLE_KOREAN_NAMES[product.style]} 스타일")
    return tags


def expected_items(candidates, season: Season, preferred_styles: list[Style], taste_scores: dict[int, float] | None):
    """taste_scores 가 None 이면 폴백 (tasteScore = 0, score = colorScore)."""
    rows = []
    for product in candidates:
        color_score = expected_color_score(product, season)
        if taste_scores is None:
            taste_score, score = 0.0, color_score
        else:
            taste_score = taste_scores[product.id]
            score = 0.7 * taste_score + 0.3 * color_score
        rows.append(
            {
                "productId": product.id,
                "score": score,
                "tasteScore": taste_score,
                "colorScore": color_score,
                "reasonTags": expected_reason_tags(product, color_score, preferred_styles, season),
            }
        )
    rows.sort(key=lambda row: (-row["score"], row["productId"]))
    return rows[:MAXIMUM_ITEM_COUNT]


# ---- 응답 검증 ----
def assert_error(response, status_code: int, error_code: ErrorCode) -> None:
    assert response.status_code == status_code
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == error_code.value
    assert isinstance(body["error"]["message"], str)


def assert_response_shape(body: dict) -> None:
    assert set(body) == RECOMMENDATION_RESPONSE_FIELDS
    assert isinstance(body["styleTags"], list) and all(isinstance(tag, str) for tag in body["styleTags"])
    assert body["season"] in {season.value for season in Season}
    assert isinstance(body["palette"], list) and all(isinstance(color, str) for color in body["palette"])
    assert isinstance(body["isFallback"], bool)
    assert isinstance(body["items"], list)
    assert len(body["items"]) <= MAXIMUM_ITEM_COUNT
    for item in body["items"]:
        assert set(item) == RECOMMENDATION_ITEM_FIELDS
        for score_field in ("score", "tasteScore", "colorScore"):
            assert isinstance(item[score_field], int | float) and not isinstance(item[score_field], bool)
            assert 0 <= item[score_field] <= 1
        assert isinstance(item["reasonTags"], list) and 1 <= len(item["reasonTags"]) <= 2
        assert all(isinstance(tag, str) for tag in item["reasonTags"])
        product = item["product"]
        assert set(product) == PRODUCT_DTO_FIELDS
        assert isinstance(product["id"], int)
        assert isinstance(product["title"], str)
        assert isinstance(product["price"], int)
        assert isinstance(product["mallName"], str)
        assert isinstance(product["purchaseUrl"], str)
        assert isinstance(product["imageUrl"], str)
        assert product["style"] in {style.value for style in Style}
    scores = [item["score"] for item in body["items"]]
    assert scores == sorted(scores, reverse=True)


def assert_items_match(actual_items: list[dict], expected_rows: list[dict], products_by_id: dict) -> None:
    assert [item["product"]["id"] for item in actual_items] == [row["productId"] for row in expected_rows]
    for item, row in zip(actual_items, expected_rows, strict=True):
        assert item["tasteScore"] == pytest.approx(row["tasteScore"], abs=TOLERANCE)
        assert item["colorScore"] == pytest.approx(row["colorScore"], abs=TOLERANCE)
        assert item["score"] == pytest.approx(row["score"], abs=TOLERANCE)
        assert item["reasonTags"] == row["reasonTags"]
        product = products_by_id[row["productId"]]
        assert item["product"] == {
            "id": product.id,
            "title": product.title,
            "price": product.price,
            "mallName": product.mall_name,
            "purchaseUrl": product.purchase_url,
            "imageUrl": product.image_url,
            "style": product.style.value,
        }


# ---- 정상: 취향 + 컬러 ----
def test_recommendations_rank_all_candidates_by_centered_taste_and_color(
    client, create_user, create_product, create_pin, auth_headers, database_session
):
    season = Season.AUTUMN_WARM
    base_color = palette_lab(season)[0]
    user = matching_user(create_user, season)
    other_user = matching_user(create_user, Season.WINTER_COOL, nickname="other")

    # 핀평균·상품평균 (축9 = 핀 사진 종류 성분, 축3 = 상품 사진 종류 성분)
    pin_centroid = add_centroid(database_session, EmbeddingDomain.PIN, axis_vector((9, 1.0), (0, 0.2)))
    product_centroid = add_centroid(database_session, EmbeddingDomain.PRODUCT, axis_vector((3, 0.3), (8, 1.0)))

    # 핀 좋아요 4개 (LOVELY 2, CASUAL 1, MINIMAL 1) · 핀 싫어요 1개 · 옷장 사진 1장
    liked_pins = [
        matching_pin(create_pin, style=style, embedding=axis_vector((0, 1.0), (9, 1.0)))
        for style in (Style.LOVELY, Style.LOVELY, Style.CASUAL, Style.MINIMAL)
    ]
    disliked_pins = [matching_pin(create_pin, style=Style.STREET, embedding=axis_vector((1, 1.0), (9, 1.0)))]
    for pin in liked_pins:
        add_swipe(database_session, user.id, pin.id, liked=True)
    for pin in disliked_pins:
        add_swipe(database_session, user.id, pin.id, liked=False)
    wardrobe_photos = [add_wardrobe_photo(database_session, user.id, axis_vector((2, 1.0)))]

    candidates = [
        matching_product(create_product, style=Style.MINIMAL, embedding=axis_vector((0, 1.0)), color_lab=list(base_color)),
        matching_product(create_product, style=Style.FORMAL, embedding=axis_vector((2, 1.0)), color_lab=shifted_lab(base_color, 10)),
        matching_product(create_product, style=Style.STREET, embedding=axis_vector((0, 1.0), (1, 1.0)), color_lab=shifted_lab(base_color, -20)),
        matching_product(create_product, style=Style.CASUAL, embedding=axis_vector((1, 1.0)), color_lab=list(base_color)),
        matching_product(create_product, style=Style.LOVELY, embedding=axis_vector((3, 1.0)), color_lab=[100.0, -100.0, -100.0]),
        # 완전히 같은 두 상품 → 같은 score, id 오름차순
        matching_product(create_product, style=Style.FORMAL, embedding=axis_vector((0, 1.0), (3, 1.0)), color_lab=shifted_lab(base_color, 5)),
        matching_product(create_product, style=Style.FORMAL, embedding=axis_vector((0, 1.0), (3, 1.0)), color_lab=shifted_lab(base_color, 5)),
        matching_product(create_product, style=Style.STREET, embedding=axis_vector((3, 1.0)), color_lab=shifted_lab(base_color, -30)),
    ]
    # 후보가 아닌 상품: 성별·나이대 불일치 (취향·컬러 모두 최고점이어도 제외)
    excluded_products = [
        create_product(gender=Gender.MALE, age_group=AgeGroup.TWENTIES, embedding=axis_vector((0, 1.0)), color_lab=list(base_color)),
        create_product(gender=Gender.FEMALE, age_group=AgeGroup.THIRTIES, embedding=axis_vector((0, 1.0)), color_lab=list(base_color)),
    ]
    # 다른 사용자의 스와이프·옷장은 이 사용자의 취향에 영향 없음
    other_pin = matching_pin(create_pin, style=Style.FORMAL, embedding=axis_vector((2, 1.0)))
    add_swipe(database_session, other_user.id, other_pin.id, liked=True)
    add_wardrobe_photo(database_session, other_user.id, axis_vector((1, 1.0)))

    preferred_styles = expected_preferred_styles(liked_pins)
    taste_vector = expected_taste_vector(liked_pins, wardrobe_photos, disliked_pins, stored_vector(pin_centroid))
    taste_scores = expected_taste_scores(taste_vector, candidates, stored_vector(product_centroid))
    expected_rows = expected_items(candidates, season, preferred_styles, taste_scores)

    response = client.get(RECOMMENDATIONS_PATH, headers=auth_headers(user))

    assert response.status_code == 200
    body = response.json()
    assert_response_shape(body)
    assert body["styleTags"] == ["러블리", "미니멀", "가을 웜톤"]  # 빈도순, 동률은 Style 정의 순서
    assert body["season"] == season.value
    assert body["palette"] == SEASON_PALETTES[season]
    assert body["isFallback"] is False
    assert len(body["items"]) == MAXIMUM_ITEM_COUNT
    assert not {item["product"]["id"] for item in body["items"]} & {product.id for product in excluded_products}
    assert_items_match(body["items"], expected_rows, {product.id: product for product in candidates})

    # 같은 입력이면 같은 결과
    assert client.get(RECOMMENDATIONS_PATH, headers=auth_headers(user)).json() == body


def test_recommendations_without_centroids_use_uncentered_embeddings(
    client, create_user, create_product, create_pin, auth_headers, database_session
):
    season = Season.AUTUMN_WARM
    base_color = palette_lab(season)[0]
    user = matching_user(create_user, season)
    liked_pins = [matching_pin(create_pin, style=Style.CASUAL, embedding=axis_vector((0, 1.0), (4, 0.5))) for _ in range(3)]
    for pin in liked_pins:
        add_swipe(database_session, user.id, pin.id, liked=True)
    candidates = [
        matching_product(create_product, style=Style.CASUAL, embedding=axis_vector((0, 1.0)), color_lab=list(base_color)),
        matching_product(create_product, style=Style.MINIMAL, embedding=axis_vector((1, 1.0)), color_lab=list(base_color)),
        matching_product(create_product, style=Style.STREET, embedding=axis_vector((0, 1.0), (1, 1.0)), color_lab=list(base_color)),
    ]
    zero_vector = np.zeros(EMBEDDING_DIMENSION)
    taste_vector = expected_taste_vector(liked_pins, [], [], zero_vector)
    expected_rows = expected_items(
        candidates, season, [Style.CASUAL], expected_taste_scores(taste_vector, candidates, zero_vector)
    )

    response = client.get(RECOMMENDATIONS_PATH, headers=auth_headers(user))

    assert response.status_code == 200
    body = response.json()
    assert_response_shape(body)
    assert_items_match(body["items"], expected_rows, {product.id: product for product in candidates})


def test_recommendations_keep_candidates_regardless_of_swipes(
    client, create_user, create_product, create_pin, auth_headers, database_session
):
    season = Season.SPRING_WARM
    user = matching_user(create_user, season)
    for style in (Style.CASUAL, Style.CASUAL, Style.MINIMAL):
        add_swipe(database_session, user.id, matching_pin(create_pin, style=style).id, liked=True)
    candidates = [matching_product(create_product, style=Style.CASUAL) for _ in range(3)]

    response = client.get(RECOMMENDATIONS_PATH, headers=auth_headers(user))

    assert response.status_code == 200
    assert {item["product"]["id"] for item in response.json()["items"]} == {product.id for product in candidates}


def test_recommendations_give_neutral_taste_score_when_candidate_similarities_are_equal(
    client, create_user, create_product, create_pin, auth_headers, database_session
):
    season = Season.SPRING_WARM
    base_color = palette_lab(season)[2]
    user = matching_user(create_user, season)
    liked_pins = [matching_pin(create_pin, style=Style.CASUAL, embedding=axis_vector((0, 1.0))) for _ in range(3)]
    for pin in liked_pins:
        add_swipe(database_session, user.id, pin.id, liked=True)
    # 모든 후보의 cos 값이 같음 → σ = 0 → tasteScore 0.5
    candidates = [
        matching_product(create_product, style=Style.FORMAL, embedding=axis_vector((5, 1.0)), color_lab=shifted_lab(base_color, -40)),
        matching_product(create_product, style=Style.CASUAL, embedding=axis_vector((5, 1.0)), color_lab=list(base_color)),
    ]
    expected_rows = expected_items(candidates, season, [Style.CASUAL], {product.id: 0.5 for product in candidates})

    response = client.get(RECOMMENDATIONS_PATH, headers=auth_headers(user))

    assert response.status_code == 200
    body = response.json()
    assert_response_shape(body)
    assert body["styleTags"] == ["캐주얼", "봄 웜톤"]
    assert body["isFallback"] is False
    assert [item["tasteScore"] for item in body["items"]] == pytest.approx([0.5, 0.5], abs=TOLERANCE)
    assert_items_match(body["items"], expected_rows, {product.id: product for product in candidates})


# ---- 정상: 폴백 ----
def test_recommendations_fall_back_to_color_score_when_likes_are_fewer_than_three(
    client, create_user, create_product, create_pin, auth_headers, database_session
):
    season = Season.SUMMER_COOL
    palette_colors = palette_lab(season)
    user = matching_user(create_user, season)
    # 핀 좋아요 2개 (< 3) + 싫어요·옷장 사진이 있어도 폴백
    liked_pins = [matching_pin(create_pin, style=Style.STREET, embedding=axis_vector((0, 1.0))) for _ in range(2)]
    disliked_pin = matching_pin(create_pin, style=Style.MINIMAL, embedding=axis_vector((1, 1.0)))
    for pin in liked_pins:
        add_swipe(database_session, user.id, pin.id, liked=True)
    add_swipe(database_session, user.id, disliked_pin.id, liked=False)
    add_wardrobe_photo(database_session, user.id, axis_vector((0, 1.0)))

    candidates = [
        matching_product(create_product, style=Style.STREET, embedding=axis_vector((0, 1.0)), color_lab=shifted_lab(palette_colors[1], -25)),
        matching_product(create_product, style=Style.MINIMAL, embedding=axis_vector((1, 1.0)), color_lab=list(palette_colors[3])),
        matching_product(create_product, style=Style.STREET, embedding=axis_vector((2, 1.0)), color_lab=shifted_lab(palette_colors[4], 8)),
        matching_product(create_product, style=Style.LOVELY, embedding=axis_vector((3, 1.0)), color_lab=shifted_lab(palette_colors[5], -25)),
        matching_product(create_product, style=Style.CASUAL, embedding=axis_vector((4, 1.0)), color_lab=list(palette_colors[6])),
        matching_product(create_product, style=Style.FORMAL, embedding=axis_vector((5, 1.0)), color_lab=shifted_lab(palette_colors[7], -12)),
        matching_product(create_product, style=Style.STREET, embedding=axis_vector((6, 1.0)), color_lab=[100.0, 100.0, 100.0]),
    ]
    expected_rows = expected_items(candidates, season, [Style.STREET], taste_scores=None)

    response = client.get(RECOMMENDATIONS_PATH, headers=auth_headers(user))

    assert response.status_code == 200
    body = response.json()
    assert_response_shape(body)
    assert body["styleTags"] == ["스트릿", "여름 쿨톤"]
    assert body["season"] == season.value
    assert body["palette"] == SEASON_PALETTES[season]
    assert body["isFallback"] is True
    assert len(body["items"]) == MAXIMUM_ITEM_COUNT
    for item in body["items"]:
        assert item["tasteScore"] == 0
        assert item["score"] == pytest.approx(item["colorScore"], abs=TOLERANCE)
    assert_items_match(body["items"], expected_rows, {product.id: product for product in candidates})


def test_recommendations_without_swipes_or_candidates_return_season_tag_and_empty_items(
    client, create_user, create_product, auth_headers
):
    season = Season.WINTER_COOL
    user = matching_user(create_user, season)
    create_product(gender=Gender.MALE, age_group=AgeGroup.TWENTIES)
    create_product(gender=Gender.FEMALE, age_group=AgeGroup.FORTIES_PLUS)

    response = client.get(RECOMMENDATIONS_PATH, headers=auth_headers(user))

    assert response.status_code == 200
    body = response.json()
    assert_response_shape(body)
    assert body == {
        "styleTags": ["겨울 쿨톤"],
        "season": season.value,
        "palette": SEASON_PALETTES[season],
        "isFallback": True,
        "items": [],
    }


# ---- 거부: 사전 조건 ----
@pytest.mark.parametrize(
    ("user_columns", "error_code"),
    [
        ({"age_group": None, "gender": Gender.FEMALE, "season": Season.AUTUMN_WARM}, ErrorCode.PROFILE_REQUIRED),
        ({"age_group": AgeGroup.TWENTIES, "gender": None, "season": Season.AUTUMN_WARM}, ErrorCode.PROFILE_REQUIRED),
        ({"age_group": AgeGroup.TWENTIES, "gender": Gender.FEMALE, "season": None}, ErrorCode.PERSONAL_COLOR_REQUIRED),
    ],
)
def test_recommendations_reject_missing_profile_or_personal_color(
    client, create_user, create_product, auth_headers, user_columns, error_code
):
    user = create_user(nickname="member", **user_columns)
    create_product(gender=Gender.FEMALE, age_group=AgeGroup.TWENTIES)

    response = client.get(RECOMMENDATIONS_PATH, headers=auth_headers(user))

    assert_error(response, 409, error_code)


# ---- 권한 ----
def _token_with(user_id: int, secret: str, expires_at: datetime) -> str:
    return jwt.encode({"sub": str(user_id), "exp": expires_at}, secret, algorithm="HS256")


@pytest.mark.parametrize("token_kind", ["missing", "expired", "forged"])
def test_recommendations_without_valid_token_return_unauthorized(client, create_user, create_product, token_kind):
    user = matching_user(create_user, Season.AUTUMN_WARM)
    create_product(gender=Gender.FEMALE, age_group=AgeGroup.TWENTIES)
    secret = get_settings().jwt_secret
    headers = {
        "missing": {},
        "expired": {"Authorization": f"Bearer {_token_with(user.id, secret, datetime.now(UTC) - timedelta(minutes=1))}"},
        "forged": {"Authorization": f"Bearer {_token_with(user.id, 'forged-secret-key-0123456789abcdef', datetime.now(UTC) + timedelta(days=1))}"},
    }[token_kind]

    response = client.get(RECOMMENDATIONS_PATH, headers=headers)

    assert_error(response, 401, ErrorCode.UNAUTHORIZED)
