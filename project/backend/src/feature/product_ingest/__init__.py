"""product_ingest 슬라이스: eBay 상의 수집(검색어 40개 또는 카테고리 Best Match) → 임베딩·대표색·스타일 → products upsert → 상품 평균 갱신 (오프라인 배치)."""
from feature.product_ingest.service import IngestReport, run_ingest

__all__ = ["IngestReport", "run_ingest"]
