"""recommendation service 단위 테스트. 점수 계산·정렬·태그 규칙은 DB 없이 순수 함수로 검증한다."""
import math

import numpy as np
import pytest

from common.entity import EMBEDDING_DIMENSION
from common.enums import AgeGroup, Gender, Season, SeasonSubtype, Style
from common.error import AppError, ErrorCode
from feature.recommendation import service
from shared.color import avoid_palette_lab, delta_e, hex_to_lab, palette_lab

TOLERANCE = 1e-9


def axis_vector(*weights_by_axis: tuple[int, float]) -> np.ndarray:
    vector = np.zeros(EMBEDDING_DIMENSION)
    for axis, weight in weights_by_axis:
        vector[axis] = weight
    return vector / np.linalg.norm(vector)


def stack(*vectors: np.ndarray) -> np.ndarray:
    return np.array(vectors, dtype=float).reshape(len(vectors), EMBEDDING_DIMENSION)


def standard_normal_cdf(value: float) -> float:
    return 0.5 * (1 + math.erf(value / math.sqrt(2)))


# ---- compute_taste_vector ----
def test_compute_taste_vector_weights_likes_wardrobe_and_dislikes_then_normalizes():
    liked = stack(axis_vector((0, 1.0)), axis_vector((1, 1.0)))
    wardrobe = stack(axis_vector((2, 1.0)))
    disliked = stack(axis_vector((3, 1.0)))

    taste_vector = service.compute_taste_vector(liked, wardrobe, disliked)

    combined = np.zeros(EMBEDDING_DIMENSION)
    combined[0], combined[1], combined[2], combined[3] = 0.5, 0.5, 1.5, -0.5
    assert taste_vector == pytest.approx(combined / np.linalg.norm(combined), abs=TOLERANCE)
    assert np.linalg.norm(taste_vector) == pytest.approx(1.0, abs=TOLERANCE)


def test_compute_taste_vector_treats_empty_groups_as_zero_vectors():
    empty = stack()
    wardrobe = stack(axis_vector((4, 1.0)), axis_vector((5, 1.0)))

    taste_vector = service.compute_taste_vector(empty, wardrobe, empty)

    assert taste_vector == pytest.approx(axis_vector((4, 1.0), (5, 1.0)), abs=TOLERANCE)


def test_compute_taste_vector_returns_zero_vector_when_everything_is_empty_or_cancels():
    empty = stack()
    assert np.all(service.compute_taste_vector(empty, empty, empty) == 0)

    # 상쇄: mean(L) = 축0, mean(D) = 2×축0 → 축0 − 0.5 × 2×축0 = 0
    liked = stack(axis_vector((0, 1.0)))
    disliked = stack(2 * axis_vector((0, 1.0)))
    assert np.all(service.compute_taste_vector(liked, empty, disliked) == 0)


# ---- subtract_centroid / to_centroid_vector ----
def test_subtract_centroid_subtracts_domain_mean_from_every_row():
    centroid = axis_vector((0, 1.0))
    embeddings = stack(axis_vector((0, 1.0), (1, 1.0)), axis_vector((2, 1.0)))

    centered = service.subtract_centroid(embeddings, centroid)

    assert centered == pytest.approx(embeddings - centroid, abs=TOLERANCE)


def test_subtract_centroid_keeps_empty_matrix_empty():
    centered = service.subtract_centroid(stack(), axis_vector((0, 1.0)))

    assert centered.shape == (0, EMBEDDING_DIMENSION)


def test_to_centroid_vector_returns_zero_vector_when_centroid_is_missing():
    assert np.all(service.to_centroid_vector(None) == 0)
    assert service.to_centroid_vector(axis_vector((3, 1.0)).tolist()) == pytest.approx(axis_vector((3, 1.0)), abs=TOLERANCE)


def test_centering_removes_shared_domain_component_from_taste_ranking():
    # 핀은 모두 축9(사진 종류) 성분을 공유한다. 평균을 빼면 축9 가 사라지고 스타일 축(0/1)만 남는다.
    liked_pins = stack(axis_vector((0, 1.0), (9, 3.0)), axis_vector((0, 1.0), (9, 3.0)))
    disliked_pins = stack(axis_vector((1, 1.0), (9, 3.0)))
    pin_centroid = np.mean(np.vstack([liked_pins, disliked_pins]), axis=0)
    # 상품: 축9 성분이 큰 상품(착용컷)은 스타일이 반대(축1)
    products = stack(axis_vector((0, 1.0), (8, 1.0)), axis_vector((1, 1.0), (9, 2.0)))
    product_centroid = products.mean(axis=0)

    raw_taste = service.compute_taste_vector(liked_pins, stack(), disliked_pins)
    raw_scores = service.compute_taste_scores(raw_taste, products)
    centered_taste = service.compute_taste_vector(
        service.subtract_centroid(liked_pins, pin_centroid), stack(), service.subtract_centroid(disliked_pins, pin_centroid)
    )
    centered_scores = service.compute_taste_scores(centered_taste, service.subtract_centroid(products, product_centroid))

    assert raw_scores[1] > raw_scores[0]  # 평균을 빼지 않으면 사진 종류 성분 때문에 반대 스타일이 위
    assert centered_scores[0] > centered_scores[1]  # 평균을 빼면 좋아요 스타일(축0)이 위


# ---- compute_taste_scores ----
def test_compute_taste_scores_applies_z_score_then_standard_normal_cdf():
    taste_vector = axis_vector((0, 1.0))
    candidates = stack(axis_vector((0, 1.0)), axis_vector((0, 1.0), (1, 1.0)), axis_vector((1, 1.0)))

    taste_scores = service.compute_taste_scores(taste_vector, candidates)

    similarities = np.array([1.0, 1 / math.sqrt(2), 0.0])
    mean, standard_deviation = similarities.mean(), similarities.std(ddof=0)
    expected = [standard_normal_cdf((value - mean) / standard_deviation) for value in similarities]
    assert taste_scores == pytest.approx(expected, abs=TOLERANCE)


def test_compute_taste_scores_uses_cosine_so_embedding_length_does_not_matter():
    taste_vector = axis_vector((0, 1.0))
    candidates = stack(3 * axis_vector((0, 1.0)), axis_vector((1, 1.0)))

    taste_scores = service.compute_taste_scores(taste_vector, candidates)

    assert taste_scores == pytest.approx(service.compute_taste_scores(taste_vector, stack(axis_vector((0, 1.0)), axis_vector((1, 1.0)))))


@pytest.mark.parametrize(
    "candidates",
    [
        stack(axis_vector((0, 1.0))),  # 후보 1개
        stack(axis_vector((5, 1.0)), axis_vector((5, 1.0)), axis_vector((5, 1.0))),  # 모두 같은 값
    ],
)
def test_compute_taste_scores_are_neutral_when_standard_deviation_is_zero(candidates):
    taste_scores = service.compute_taste_scores(axis_vector((0, 1.0)), candidates)

    assert taste_scores == pytest.approx([0.5] * len(candidates), abs=TOLERANCE)


def test_compute_taste_scores_are_neutral_when_taste_vector_is_zero():
    candidates = stack(axis_vector((0, 1.0)), axis_vector((1, 1.0)))

    taste_scores = service.compute_taste_scores(np.zeros(EMBEDDING_DIMENSION), candidates)

    assert taste_scores == pytest.approx([0.5, 0.5], abs=TOLERANCE)


def test_compute_taste_scores_return_empty_for_no_candidates():
    assert len(service.compute_taste_scores(axis_vector((0, 1.0)), stack())) == 0


# ---- compute_color_scores ----
def test_compute_color_scores_use_nearest_palette_color_and_clip_at_zero():
    season, subtype = Season.AUTUMN_WARM, SeasonSubtype.DEEP
    palette = palette_lab(season, subtype)
    near_color = [palette[3][0] + 10, palette[3][1], palette[3][2]]
    candidate_colors = np.array([list(palette[0]), near_color, [100.0, -100.0, -100.0]])

    color_scores = service.compute_color_scores(candidate_colors, season, subtype)

    near_distance = min(delta_e(tuple(near_color), color) for color in palette)
    far_distance = min(delta_e((100.0, -100.0, -100.0), color) for color in palette)
    assert near_distance <= 10
    assert far_distance > 50
    assert color_scores == pytest.approx([1.0, 1 - near_distance / 50, 0.0], abs=TOLERANCE)


def test_compute_color_scores_use_subtype_palette():
    # 같은 가을이라도 세부 유형마다 팔레트가 달라 점수가 다르다
    deep_color = list(palette_lab(Season.AUTUMN_WARM, SeasonSubtype.DEEP)[0])

    deep_score = service.compute_color_scores(np.array([deep_color]), Season.AUTUMN_WARM, SeasonSubtype.DEEP)[0]
    soft_score = service.compute_color_scores(np.array([deep_color]), Season.AUTUMN_WARM, SeasonSubtype.SOFT)[0]

    assert deep_score == pytest.approx(1.0, abs=TOLERANCE)
    assert soft_score < deep_score


@pytest.mark.parametrize(("avoid_offset", "expected_penalty"), [(0.0, 0.5), (14.9, 0.5), (15.0, 1.0), (30.0, 1.0)])
def test_compute_color_scores_halve_score_when_avoid_color_is_closer_than_15(avoid_offset, expected_penalty):
    season, subtype = Season.AUTUMN_WARM, SeasonSubtype.TRUE
    fuchsia = hex_to_lab("#E0218A")  # 가을 피해야 할 색
    candidate = [fuchsia[0] + avoid_offset, fuchsia[1], fuchsia[2]]
    nearest_palette_distance = min(delta_e(tuple(candidate), color) for color in palette_lab(season, subtype))
    nearest_avoid_distance = min(delta_e(tuple(candidate), color) for color in avoid_palette_lab(season))
    assert nearest_avoid_distance == pytest.approx(avoid_offset, abs=1e-9)

    (color_score,) = service.compute_color_scores(np.array([candidate]), season, subtype)

    assert color_score == pytest.approx(max(0.0, 1 - nearest_palette_distance / 50) * expected_penalty, abs=TOLERANCE)


def test_compute_color_scores_return_empty_for_no_candidates():
    assert len(service.compute_color_scores(np.empty((0, 3)), Season.SPRING_WARM, SeasonSubtype.TRUE)) == 0


# ---- combine_scores ----
def test_combine_scores_weights_taste_and_color():
    scores = service.combine_scores(np.array([1.0, 0.0, 0.5]), np.array([0.0, 1.0, 0.5]))

    assert scores == pytest.approx([0.7, 0.3, 0.5], abs=TOLERANCE)


# ---- rank_top_indices ----
def test_rank_top_indices_orders_by_score_descending_then_product_id_ascending():
    scores = np.array([0.4, 0.9, 0.4, 0.1, 0.9])
    product_ids = [30, 20, 10, 50, 40]

    assert service.rank_top_indices(scores, product_ids, limit=5) == [1, 4, 2, 0, 3]


def test_rank_top_indices_keeps_at_most_limit():
    scores = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7])

    assert service.rank_top_indices(scores, list(range(1, 8)), limit=5) == [6, 5, 4, 3, 2]
    assert service.rank_top_indices(np.array([]), [], limit=5) == []


# ---- select_preferred_styles ----
def test_select_preferred_styles_by_frequency_breaking_ties_by_enum_order():
    liked_styles = [Style.LOVELY, Style.CASUAL, Style.LOVELY, Style.MINIMAL]

    assert service.select_preferred_styles(liked_styles) == [Style.LOVELY, Style.MINIMAL]


def test_select_preferred_styles_returns_fewer_when_few_styles():
    assert service.select_preferred_styles([Style.STREET, Style.STREET]) == [Style.STREET]
    assert service.select_preferred_styles([]) == []


# ---- build_style_tags ----
def test_build_style_tags_puts_season_name_last():
    assert service.build_style_tags([Style.LOVELY, Style.MINIMAL], Season.AUTUMN_WARM) == ["러블리", "미니멀", "가을 웜톤"]
    assert service.build_style_tags([], Season.WINTER_COOL) == ["겨울 쿨톤"]


# ---- build_reason_tags ----
def test_build_reason_tags_lists_preferred_style_then_season_color():
    tags = service.build_reason_tags(Style.MINIMAL, 0.7, [Style.MINIMAL], Season.AUTUMN_WARM)

    assert tags == ["선호하는 미니멀", "가을 웜톤 컬러"]


def test_build_reason_tags_with_only_one_rule_matching():
    assert service.build_reason_tags(Style.MINIMAL, 0.69, [Style.MINIMAL], Season.SPRING_WARM) == ["선호하는 미니멀"]
    assert service.build_reason_tags(Style.FORMAL, 0.9, [Style.MINIMAL], Season.SUMMER_COOL) == ["여름 쿨톤 컬러"]


def test_build_reason_tags_fall_back_to_product_style():
    assert service.build_reason_tags(Style.CASUAL, 0.2, [], Season.WINTER_COOL) == ["캐주얼 스타일"]


# ---- 사전 조건 ----
class StubUser:
    def __init__(self, age_group, gender, season, season_subtype=SeasonSubtype.TRUE) -> None:
        self.id = 1
        self.age_group = age_group
        self.gender = gender
        self.season = season
        self.season_subtype = season_subtype if season is not None else None


@pytest.mark.parametrize(
    ("user", "error_code"),
    [
        (StubUser(None, Gender.FEMALE, Season.AUTUMN_WARM), ErrorCode.PROFILE_REQUIRED),
        (StubUser(AgeGroup.TWENTIES, None, None), ErrorCode.PROFILE_REQUIRED),
        (StubUser(AgeGroup.TWENTIES, Gender.FEMALE, None), ErrorCode.PERSONAL_COLOR_REQUIRED),
        (StubUser(AgeGroup.TWENTIES, Gender.FEMALE, Season.AUTUMN_WARM, None), ErrorCode.PERSONAL_COLOR_REQUIRED),
    ],
)
def test_get_recommendations_rejects_missing_profile_before_personal_color(user, error_code):
    with pytest.raises(AppError) as raised:
        service.get_recommendations(None, user)

    assert raised.value.error_code == error_code
