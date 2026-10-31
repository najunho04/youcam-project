"""배치 진입점 (실제 eBay API·이미지 다운로드).
- python -m feature.product_ingest            검색어 40개로 수집 (make ingest)
- python -m feature.product_ingest category   상의 카테고리 Best Match 상위 100개씩 + 스타일 자동 분류
"""
import sys

from feature.product_ingest.ebay_client import EbayClient
from feature.product_ingest.service import exit_code, run_category_ingest, run_ingest
from shared.image import download_image


def main() -> int:
    ebay_client = EbayClient()
    try:
        if sys.argv[1:] == ["category"]:
            report = run_category_ingest(ebay_client.search_items, download_image)
            return 1 if report.failed_categories == 2 else 0
        return exit_code(run_ingest(ebay_client.search_items, download_image))
    finally:
        ebay_client.close()


if __name__ == "__main__":
    sys.exit(main())
