"""배치 진입점: python -m feature.product_ingest (make ingest). 실제 네이버 API·이미지 다운로드로 run_ingest 실행."""
import sys

from feature.product_ingest.naver_client import search_products
from feature.product_ingest.service import exit_code, run_ingest
from shared.image import download_image


def main() -> int:
    return exit_code(run_ingest(search_products, download_image))


if __name__ == "__main__":
    sys.exit(main())
