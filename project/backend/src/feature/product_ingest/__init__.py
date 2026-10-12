"""product_ingest 슬라이스: 네이버 쇼핑 상의 수집 → 임베딩·대표색 계산 → products upsert (오프라인 배치)."""
from feature.product_ingest.service import IngestReport, run_ingest

__all__ = ["IngestReport", "run_ingest"]
