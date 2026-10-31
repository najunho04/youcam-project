"""recommendation 슬라이스 비즈니스 로직. 실패는 AppError 로만 알린다.
점수 계산·정렬·태그 규칙은 DB 없이 쓰는 순수 함수다. 벡터 연산은 numpy 로 한꺼번에 하고, 무작위는 쓰지 않는다.
"""
import math
from collections import Counter

import numpy as np
from sqlalchemy.orm import Session

from common.dto import ProductDto, RecommendationItem, RecommendationResponse
from common.entity import EMBEDDING_DIMENSION, User
from common.enums import EmbeddingDomain, Season, SeasonSubtype, Style
from common.error import AppError, ErrorCode
from feature.recommendation import repository
from shared.color import SUBTYPE_PALETTES, avoid_palette_lab, palette_lab

MAXIMUM_ITEM_COUNT = 6
MINIMUM_LIKED_COUNT = 3
WARDROBE_WEIGHT = 1.5
DISLIKED_WEIGHT = 0.5
TASTE_WEIGHT = 0.7
COLOR_WEIGHT = 0.3
NEUTRAL_TASTE_SCORE = 0.5
COLOR_DISTANCE_SCALE = 50
SEASON_COLOR_THRESHOLD = 0.7
AVOID_DISTANCE_THRESHOLD = 15  # 피해야 할 팔레트와 ΔE 가 이보다 작으면 감점
AVOID_PENALTY_MULTIPLIER = 0.5
MAXIMUM_PREFERRED_STYLE_COUNT = 2

STYLE_KOREAN_NAMES: dict[Style, str] = {
    Style.MINIMAL: "미니멀",
    Style.CASUAL: "캐주얼",
    Style.STREET: "스트릿",
    Style.FORMAL: "포멀",
    Style.LOVELY: "러블리",
}
SEASON_KOREAN_NAMES: dict[Season, str] = {
    Season.SPRING_WARM: "봄 웜톤",
    Season.SUMMER_COOL: "여름 쿨톤",
    Season.AUTUMN_WARM: "가을 웜톤",
    Season.WINTER_COOL: "겨울 쿨톤",
}

_vectorized_erf = np.vectorize(math.erf, otypes=[float])


def to_embedding_matrix(embeddings: list) -> np.ndarray:
    """(n, 512) float 행렬. 비어 있으면 (0, 512)."""
    return np.asarray(embeddings, dtype=float).reshape(len(embeddings), EMBEDDING_DIMENSION)


def to_centroid_vector(centroid: list[float] | None) -> np.ndarray:
    """저장된 평균 벡터. 아직 적재 전이라 없으면 0 벡터 (평균을 빼지 않은 것과 같다)."""
    return np.zeros(EMBEDDING_DIMENSION) if centroid is None else np.asarray(centroid, dtype=float)


def subtract_centroid(embeddings: np.ndarray, centroid: np.ndarray) -> np.ndarray:
    """출처(핀·상품)마다 공유하는 사진 종류 성분을 없애려고 각 행에서 그 출처의 평균을 뺀다."""
    return embeddings - centroid if len(embeddings) else embeddings


def _mean_or_zero(embeddings: np.ndarray) -> np.ndarray:
    return embeddings.mean(axis=0) if len(embeddings) else np.zeros(EMBEDDING_DIMENSION)


def compute_taste_vector(
    liked_embeddings: np.ndarray, wardrobe_embeddings: np.ndarray, disliked_embeddings: np.ndarray
) -> np.ndarray:
    """u = normalize(mean(L) + 1.5 × mean(C) − 0.5 × mean(D)). 비어 있는 항은 0 벡터, 합이 0 이면 0 벡터."""
    combined = (
        _mean_or_zero(liked_embeddings)
        + WARDROBE_WEIGHT * _mean_or_zero(wardrobe_embeddings)
        - DISLIKED_WEIGHT * _mean_or_zero(disliked_embeddings)
    )
    norm = np.linalg.norm(combined)
    return combined if norm == 0 else combined / norm


def compute_taste_scores(taste_vector: np.ndarray, candidate_embeddings: np.ndarray) -> np.ndarray:
    """c_i = cos(u, e_i) 를 후보 안에서 Z-score 정규화한 뒤 Φ. σ = 0 이거나 u 가 0 벡터면 모두 0.5."""
    candidate_count = len(candidate_embeddings)
    neutral_scores = np.full(candidate_count, NEUTRAL_TASTE_SCORE)
    if candidate_count == 0 or np.linalg.norm(taste_vector) == 0:
        return neutral_scores

    embedding_norms = np.linalg.norm(candidate_embeddings, axis=1)
    safe_norms = np.where(embedding_norms == 0, 1.0, embedding_norms)
    similarities = (candidate_embeddings @ taste_vector) / safe_norms
    standard_deviation = similarities.std(ddof=0)
    # 모두 같은 값이면 부동소수 오차와 무관하게 σ = 0 으로 본다
    if standard_deviation == 0 or np.all(similarities == similarities[0]):
        return neutral_scores

    z_scores = (similarities - similarities.mean()) / standard_deviation
    return 0.5 * (1 + _vectorized_erf(z_scores / math.sqrt(2)))


def _nearest_distances(colors: np.ndarray, palette_colors: list) -> np.ndarray:
    palette = np.asarray(palette_colors, dtype=float)
    return np.linalg.norm(colors[:, np.newaxis, :] - palette[np.newaxis, :, :], axis=2).min(axis=1, initial=np.inf)


def compute_color_scores(candidate_colors_lab: np.ndarray, season: Season, subtype: SeasonSubtype) -> np.ndarray:
    """max(0, 1 − ΔE / 50) × 감점. ΔE 는 12유형 팔레트 중 가장 가까운 색까지의 CIE76 거리.
    피해야 할 팔레트 중 가장 가까운 색과 ΔE < 15 이면 × 0.5."""
    colors = np.asarray(candidate_colors_lab, dtype=float).reshape(-1, 3)
    base_scores = np.maximum(0.0, 1 - _nearest_distances(colors, palette_lab(season, subtype)) / COLOR_DISTANCE_SCALE)
    is_close_to_avoid = _nearest_distances(colors, avoid_palette_lab(season)) < AVOID_DISTANCE_THRESHOLD
    return np.where(is_close_to_avoid, base_scores * AVOID_PENALTY_MULTIPLIER, base_scores)


def combine_scores(taste_scores: np.ndarray, color_scores: np.ndarray) -> np.ndarray:
    return TASTE_WEIGHT * taste_scores + COLOR_WEIGHT * color_scores


def rank_top_indices(scores: np.ndarray, product_ids: list[int], limit: int = MAXIMUM_ITEM_COUNT) -> list[int]:
    """score 내림차순, 같으면 product.id 오름차순으로 상위 limit 개의 인덱스."""
    ranked = sorted(range(len(product_ids)), key=lambda index: (-scores[index], product_ids[index]))
    return ranked[:limit]


def select_preferred_styles(liked_styles: list[Style]) -> list[Style]:
    """좋아요 상품 style 빈도순 최대 2개. 빈도가 같으면 Style enum 정의 순서."""
    style_order = list(Style)
    frequencies = Counter(liked_styles)
    ranked = sorted(frequencies, key=lambda style: (-frequencies[style], style_order.index(style)))
    return ranked[:MAXIMUM_PREFERRED_STYLE_COUNT]


def build_style_tags(preferred_styles: list[Style], season: Season) -> list[str]:
    return [STYLE_KOREAN_NAMES[style] for style in preferred_styles] + [SEASON_KOREAN_NAMES[season]]


def build_reason_tags(style: Style, color_score: float, preferred_styles: list[Style], season: Season) -> list[str]:
    """최대 2개: 선호 스타일 → 시즌 컬러. 둘 다 없으면 상품 스타일."""
    tags = []
    if style in preferred_styles:
        tags.append(f"선호하는 {STYLE_KOREAN_NAMES[style]}")
    if color_score >= SEASON_COLOR_THRESHOLD:
        tags.append(f"{SEASON_KOREAN_NAMES[season]} 컬러")
    if not tags:
        tags.append(f"{STYLE_KOREAN_NAMES[style]} 스타일")
    return tags


def get_recommendations(database_session: Session, user: User) -> RecommendationResponse:
    """요청마다 계산하고 저장하지 않는다. 좋아요 < 3 이면 폴백 (tasteScore = 0, score = colorScore)."""
    if user.age_group is None or user.gender is None:
        raise AppError(ErrorCode.PROFILE_REQUIRED, "나이대와 성별을 먼저 입력해 주세요")
    if user.season is None or user.season_subtype is None:
        raise AppError(ErrorCode.PERSONAL_COLOR_REQUIRED, "퍼스널컬러 진단을 먼저 해 주세요")
    season, subtype = user.season, user.season_subtype

    swiped_pins = repository.find_swiped_pins(database_session, user.id)
    liked_styles = [style for style, _, liked in swiped_pins if liked]
    preferred_styles = select_preferred_styles(liked_styles)
    is_fallback = len(liked_styles) < MINIMUM_LIKED_COUNT

    candidates = repository.find_top_products(database_session, user.gender, user.age_group)
    color_scores = compute_color_scores(
        np.asarray([product.color_lab for product in candidates], dtype=float), season, subtype
    )
    if is_fallback:
        taste_scores = np.zeros(len(candidates))
        scores = color_scores
    else:
        # u = mean(L − 핀평균) + 1.5 × mean(C) − 0.5 × mean(D − 핀평균). 옷장 사진은 평균을 빼지 않는다
        pin_centroid = to_centroid_vector(repository.find_centroid(database_session, EmbeddingDomain.PIN))
        product_centroid = to_centroid_vector(repository.find_centroid(database_session, EmbeddingDomain.PRODUCT))
        taste_vector = compute_taste_vector(
            subtract_centroid(to_embedding_matrix([embedding for _, embedding, liked in swiped_pins if liked]), pin_centroid),
            to_embedding_matrix(repository.find_wardrobe_embeddings(database_session, user.id)),
            subtract_centroid(to_embedding_matrix([embedding for _, embedding, liked in swiped_pins if not liked]), pin_centroid),
        )
        taste_scores = compute_taste_scores(
            taste_vector,
            subtract_centroid(to_embedding_matrix([product.embedding for product in candidates]), product_centroid),
        )
        scores = combine_scores(taste_scores, color_scores)

    items = []
    for index in rank_top_indices(scores, [product.id for product in candidates]):
        product = candidates[index]
        color_score = float(color_scores[index])
        items.append(
            RecommendationItem(
                product=ProductDto.model_validate(product),
                score=float(scores[index]),
                taste_score=float(taste_scores[index]),
                color_score=color_score,
                reason_tags=build_reason_tags(product.style, color_score, preferred_styles, season),
            )
        )

    return RecommendationResponse(
        style_tags=build_style_tags(preferred_styles, season),
        season=season,
        subtype=subtype,
        palette=SUBTYPE_PALETTES[(season, subtype)],
        is_fallback=is_fallback,
        items=items,
    )
