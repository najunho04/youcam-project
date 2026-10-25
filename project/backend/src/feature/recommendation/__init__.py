"""recommendation 슬라이스: 취향 벡터와 퍼스널컬러 점수로 상의를 랭킹해 상위 6개와 추천 이유를 준다. 읽기 전용."""
from feature.recommendation.router import router

__all__ = ["router"]
