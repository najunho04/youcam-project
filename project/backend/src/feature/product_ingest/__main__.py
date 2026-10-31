"""배치 진입점: python -m feature.product_ingest (make ingest). 실제 eBay API·이미지 다운로드로 run_ingest 실행."""
import sys

from feature.product_ingest.ebay_client import EbayClient
from feature.product_ingest.service import exit_code, run_ingest
from shared.image import download_image


def main() -> int:
    ebay_client = EbayClient()
    try:
        return exit_code(run_ingest(ebay_client.search_items, download_image))
    finally:
        ebay_client.close()


if __name__ == "__main__":
    sys.exit(main())
