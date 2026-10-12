"""product_ingest 슬라이스 계약 테스트. 컨텍스트 카드(슬라이스: product_ingest)의 배치 입출력만 검증한다.

feature.product_ingest.run_ingest(search, download) -> IngestReport { saved, failed_products, failed_keywords }
- 키워드: Gender × AgeGroup × Style (enum 정의 순서), 검색어 "{성별} {나이대} {스타일} 상의", display=50
- products upsert (naver_product_id 기준). 나중 키워드 값으로 덮어씀. updated_at 갱신
- 상품 단위 실패 → 그 상품만 건너뜀 / 네이버 API 실패 → 그 키워드만 건너뜀
"""
import io
from collections.abc import Callable

import numpy as np
import pytest
from PIL import Image
from sqlalchemy import func, select

from common.entity import EMBEDDING_DIMENSION, Product
from common.enums import AgeGroup, Category, Gender, Style
from common.error import AppError, ErrorCode
from shared.color import rgb_to_lab
from shared.embedding import FakeEmbeddingModel

GENDER_WORDS = {Gender.FEMALE: "여성", Gender.MALE: "남성"}
AGE_GROUP_WORDS = {
    AgeGroup.LATE_TEENS: "10대",
    AgeGroup.TWENTIES: "20대",
    AgeGroup.THIRTIES: "30대",
    AgeGroup.FORTIES_PLUS: "40대",
}
STYLE_WORDS = {
    Style.MINIMAL: "미니멀",
    Style.CASUAL: "캐주얼",
    Style.STREET: "스트릿",
    Style.FORMAL: "포멀",
    Style.LOVELY: "러블리",
}
EXPECTED_QUERIES = [
    f"{GENDER_WORDS[gender]} {AGE_GROUP_WORDS[age_group]} {STYLE_WORDS[style]} 상의"
    for gender in Gender
    for age_group in AgeGroup
    for style in Style
]
KEYWORD_COUNT = len(EXPECTED_QUERIES)  # 40
DISPLAY_COUNT = 50

FEMALE_TWENTIES_MINIMAL = "여성 20대 미니멀 상의"
MALE_THIRTIES_STREET = "남성 30대 스트릿 상의"


def naver_item(product_id: str, **overrides) -> dict:
    item = {
        "productId": product_id,
        "title": f"상품 {product_id}",
        "link": f"https://shopping.test/products/{product_id}",
        "image": f"https://image.test/products/{product_id}.png",
        "lprice": "39000",
        "mallName": "테스트몰",
    }
    item.update(overrides)
    return item


class FakeSearch:
    """검색어별 items 를 돌려준다. 등록되지 않은 검색어는 빈 목록. failing_queries 는 AppError."""

    def __init__(self, items_by_query: dict[str, list[dict]], failing_queries: set[str] | None = None) -> None:
        self.items_by_query = items_by_query
        self.failing_queries = failing_queries or set()
        self.calls: list[tuple[str, int]] = []

    def __call__(self, query: str, display: int) -> list[dict]:
        self.calls.append((query, display))
        if query in self.failing_queries:
            raise AppError(ErrorCode.EXTERNAL_API_FAILED, "네이버 API 실패")
        return [dict(item) for item in self.items_by_query.get(query, [])]


class FakeDownload:
    """URL 별 바이트를 돌려준다. 등록되지 않은 URL 은 AppError(EXTERNAL_API_FAILED)."""

    def __init__(self, bytes_by_url: dict[str, bytes]) -> None:
        self.bytes_by_url = bytes_by_url

    def __call__(self, url: str) -> bytes:
        if url not in self.bytes_by_url:
            raise AppError(ErrorCode.EXTERNAL_API_FAILED, "이미지 다운로드 실패")
        return self.bytes_by_url[url]


def run(search: FakeSearch, download: FakeDownload):
    from feature.product_ingest import run_ingest

    return run_ingest(search, download)


def assert_report(report, saved: int, failed_products: int, failed_keywords: int) -> None:
    assert (report.saved, report.failed_products, report.failed_keywords) == (saved, failed_products, failed_keywords)


def all_products(database_session) -> list[Product]:
    database_session.expire_all()
    return list(database_session.scalars(select(Product).order_by(Product.naver_product_id)))


def test_saves_mapped_product_with_keyword_attributes_color_and_embedding(
    database_session, sample_image_bytes: Callable[..., bytes]
) -> None:
    color_item = naver_item(
        "1001",
        title="<b>여성</b> 미니멀 <b>니트</b> &amp; 가디건 &lt;신상&gt;",
        lprice="39000",
        mallName="컬러몰",
    )
    white_item = naver_item("1002", lprice="15900")
    color_image = sample_image_bytes(color=(200, 160, 130), image_format="PNG")
    white_image = sample_image_bytes(color=(255, 255, 255), image_format="PNG")
    search = FakeSearch({FEMALE_TWENTIES_MINIMAL: [color_item, white_item]})
    download = FakeDownload({color_item["image"]: color_image, white_item["image"]: white_image})

    report = run(search, download)

    assert_report(report, saved=2, failed_products=0, failed_keywords=0)
    assert search.calls == [(query, DISPLAY_COUNT) for query in EXPECTED_QUERIES]

    color_product, white_product = all_products(database_session)
    assert color_product.naver_product_id == "1001"
    assert color_product.title == "여성 미니멀 니트 & 가디건 <신상>"
    assert color_product.price == 39000
    assert color_product.mall_name == "컬러몰"
    assert color_product.purchase_url == color_item["link"]
    assert color_product.image_url == color_item["image"]
    assert (color_product.gender, color_product.age_group, color_product.style, color_product.category) == (
        Gender.FEMALE,
        AgeGroup.TWENTIES,
        Style.MINIMAL,
        Category.TOP,
    )
    assert color_product.updated_at is not None
    # 단색 → 흰 배경 제외 평균 = 그 색
    assert list(color_product.color_lab) == pytest.approx(list(rgb_to_lab(200, 160, 130)), abs=0.01)
    # 전부 흰색 → 제외 후 남는 픽셀 없음 → 가운데 영역 전체 평균 = 흰색
    assert white_product.price == 15900
    assert list(white_product.color_lab) == pytest.approx(list(rgb_to_lab(255, 255, 255)), abs=0.01)

    embedding = np.array(color_product.embedding, dtype=float)
    assert embedding.shape == (EMBEDDING_DIMENSION,)
    assert np.linalg.norm(embedding) == pytest.approx(1.0, abs=1e-4)
    expected_embedding = FakeEmbeddingModel().embed_images([color_image])[0]
    assert embedding.tolist() == pytest.approx(expected_embedding, abs=1e-5)


def test_representative_color_excludes_white_background(database_session) -> None:
    # 흰 배경 400x400, 가운데 100x100 만 색. 가운데 50% 영역(100~300)에서 흰 픽셀을 빼면 그 색만 남는다
    image = Image.new("RGB", (400, 400), (255, 255, 255))
    image.paste((30, 90, 170), (150, 150, 250, 250))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    item = naver_item("1501")
    search = FakeSearch({FEMALE_TWENTIES_MINIMAL: [item]})

    report = run(search, FakeDownload({item["image"]: buffer.getvalue()}))

    assert_report(report, saved=1, failed_products=0, failed_keywords=0)
    (product,) = all_products(database_session)
    assert list(product.color_lab) == pytest.approx(list(rgb_to_lab(30, 90, 170)), abs=0.01)


def test_running_twice_updates_existing_row_without_duplicates(
    database_session, sample_image_bytes: Callable[..., bytes]
) -> None:
    first_item = naver_item("2001", lprice="30000", title="처음 제목")
    image = sample_image_bytes(color=(40, 80, 160), image_format="PNG")
    download = FakeDownload({first_item["image"]: image})

    first_report = run(FakeSearch({FEMALE_TWENTIES_MINIMAL: [first_item]}), download)
    assert_report(first_report, saved=1, failed_products=0, failed_keywords=0)
    (first_product,) = all_products(database_session)
    first_id, first_updated_at = first_product.id, first_product.updated_at

    second_item = naver_item("2001", lprice="25000", title="바뀐 제목")
    second_report = run(FakeSearch({FEMALE_TWENTIES_MINIMAL: [second_item]}), download)

    assert_report(second_report, saved=1, failed_products=0, failed_keywords=0)
    assert database_session.scalar(select(func.count()).select_from(Product)) == 1
    (second_product,) = all_products(database_session)
    assert second_product.id == first_id
    assert second_product.price == 25000
    assert second_product.title == "바뀐 제목"
    assert second_product.updated_at > first_updated_at


def test_same_product_in_multiple_keywords_takes_later_keyword_values(
    database_session, sample_image_bytes: Callable[..., bytes]
) -> None:
    earlier_item = naver_item("3001", title="앞 키워드 제목", lprice="10000")
    later_item = naver_item("3001", title="뒤 키워드 제목", lprice="20000")
    image = sample_image_bytes(color=(90, 120, 60), image_format="PNG")
    search = FakeSearch({FEMALE_TWENTIES_MINIMAL: [earlier_item], MALE_THIRTIES_STREET: [later_item]})

    report = run(search, FakeDownload({earlier_item["image"]: image}))

    assert_report(report, saved=2, failed_products=0, failed_keywords=0)
    (product,) = all_products(database_session)
    assert (product.gender, product.age_group, product.style, product.category) == (
        Gender.MALE,
        AgeGroup.THIRTIES,
        Style.STREET,
        Category.TOP,
    )
    assert product.title == "뒤 키워드 제목"
    assert product.price == 20000


def test_failed_products_are_skipped_and_counted(database_session, sample_image_bytes: Callable[..., bytes]) -> None:
    valid_item = naver_item("4001")
    download_failure_item = naver_item("4002")  # download 에 등록하지 않음 → AppError
    not_image_item = naver_item("4003")
    missing_product_id_item = naver_item("4004")
    del missing_product_id_item["productId"]
    missing_mall_name_item = naver_item("4005")
    del missing_mall_name_item["mallName"]
    invalid_price_item = naver_item("4006", lprice="가격문의")
    image = sample_image_bytes(color=(150, 50, 50), image_format="PNG")
    bytes_by_url = {
        item["image"]: image
        for item in (valid_item, missing_product_id_item, missing_mall_name_item, invalid_price_item)
    }
    bytes_by_url[not_image_item["image"]] = b"this is not an image"
    search = FakeSearch(
        {
            FEMALE_TWENTIES_MINIMAL: [
                valid_item,
                download_failure_item,
                not_image_item,
                missing_product_id_item,
                missing_mall_name_item,
                invalid_price_item,
            ]
        }
    )

    report = run(search, FakeDownload(bytes_by_url))

    assert_report(report, saved=1, failed_products=5, failed_keywords=0)
    assert [product.naver_product_id for product in all_products(database_session)] == ["4001"]


def test_failed_keyword_is_skipped_and_other_keywords_continue(
    database_session, sample_image_bytes: Callable[..., bytes]
) -> None:
    skipped_item = naver_item("5001")
    saved_item = naver_item("5002")
    image = sample_image_bytes(color=(60, 60, 60), image_format="PNG")
    search = FakeSearch(
        {FEMALE_TWENTIES_MINIMAL: [skipped_item], MALE_THIRTIES_STREET: [saved_item]},
        failing_queries={FEMALE_TWENTIES_MINIMAL},
    )

    report = run(search, FakeDownload({skipped_item["image"]: image, saved_item["image"]: image}))

    assert_report(report, saved=1, failed_products=0, failed_keywords=1)
    assert [query for query, _ in search.calls] == EXPECTED_QUERIES
    assert [product.naver_product_id for product in all_products(database_session)] == ["5002"]


def test_all_keywords_failing_saves_nothing(database_session) -> None:
    search = FakeSearch({}, failing_queries=set(EXPECTED_QUERIES))

    report = run(search, FakeDownload({}))

    assert_report(report, saved=0, failed_products=0, failed_keywords=KEYWORD_COUNT)
    assert all_products(database_session) == []
