"""product_ingest 슬라이스 계약 테스트. 컨텍스트 카드(슬라이스: product_ingest)의 배치 입출력만 검증한다.

feature.product_ingest.run_ingest(search, download) -> IngestReport { saved, failed_products, failed_keywords }
- search(query, limit, offset, category_id)
- 키워드: Gender × AgeGroup × Style (enum 정의 순서). eBay 는 나이대 검색을 모르므로 나이대 단어를 쓰지 않는다
  - 10·20대: "{성별} trendy {스타일} top", 30·40대: "{성별} {스타일} top"
  - 같은 검색어의 두 나이대는 페이지로 나눈다: 10·30대 offset 0, 20·40대 offset 50. limit=50
  - 카테고리: 여성 53159(Tops), 남성 185100(Shirts)
- eBay itemSummaries[] → products upsert ((source=EBAY, external_id) 기준). 나중 키워드 값으로 덮어씀. updated_at 갱신
- 대표색: 테두리 배경색 제거 → K-means(k=3) 가장 큰 묶음의 중심
- 배치가 끝나면 embedding_centroids(PRODUCT) = products 전체 embedding 평균
- 상품 단위 실패 → 그 상품만 건너뜀 / eBay API 실패 → 그 키워드만 건너뜀
"""
import io
from collections.abc import Callable
from decimal import Decimal

import numpy as np
import pytest
from PIL import Image
from sqlalchemy import func, select

from common.entity import EMBEDDING_DIMENSION, EmbeddingCentroid, Product
from common.enums import AgeGroup, Category, EmbeddingDomain, Gender, ProductSource, Style
from common.error import AppError, ErrorCode
from shared.color import rgb_to_lab
from shared.embedding import FakeEmbeddingModel

GENDER_WORDS = {Gender.FEMALE: "women", Gender.MALE: "men"}
TRENDY_WORDS = {AgeGroup.LATE_TEENS: " trendy", AgeGroup.TWENTIES: " trendy", AgeGroup.THIRTIES: "", AgeGroup.FORTIES_PLUS: ""}
OFFSETS = {AgeGroup.LATE_TEENS: 0, AgeGroup.TWENTIES: 50, AgeGroup.THIRTIES: 0, AgeGroup.FORTIES_PLUS: 50}
CATEGORY_IDS = {Gender.FEMALE: "53159", Gender.MALE: "185100"}
STYLE_WORDS = {
    Style.MINIMAL: "minimal",
    Style.CASUAL: "casual",
    Style.STREET: "streetwear",
    Style.FORMAL: "formal",
    Style.LOVELY: "feminine",
}
LIMIT_COUNT = 50
# (query, limit, offset, category_id)
EXPECTED_CALLS = [
    (f"{GENDER_WORDS[gender]}{TRENDY_WORDS[age_group]} {STYLE_WORDS[style]} top", LIMIT_COUNT, OFFSETS[age_group], CATEGORY_IDS[gender])
    for gender in Gender
    for age_group in AgeGroup
    for style in Style
]
KEYWORD_COUNT = len(EXPECTED_CALLS)  # 40

# FakeSearch 키: (query, offset)
FEMALE_TWENTIES_MINIMAL = ("women trendy minimal top", 50)
MALE_THIRTIES_STREET = ("men streetwear top", 0)


def ebay_item(item_id: str, **overrides) -> dict:
    """eBay Browse item_summary/search 응답의 itemSummaries[] 한 개."""
    item = {
        "itemId": item_id,
        "title": f"Item {item_id}",
        "price": {"value": "39.99", "currency": "USD"},
        "image": {"imageUrl": f"https://image.test/items/{item_id}.png"},
        "itemWebUrl": f"https://www.ebay.test/itm/{item_id}",
        "seller": {"username": "test-seller"},
    }
    item.update(overrides)
    return item


def image_url_of(item: dict) -> str:
    return item["image"]["imageUrl"]


def png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class FakeSearch:
    """(검색어, offset) 별 items 를 돌려준다. 등록되지 않은 것은 빈 목록. failing_queries 는 AppError."""

    def __init__(
        self, items_by_query: dict[tuple[str, int], list[dict]], failing_queries: set[tuple[str, int]] | None = None
    ) -> None:
        self.items_by_query = items_by_query
        self.failing_queries = failing_queries or set()
        self.calls: list[tuple[str, int, int, str]] = []

    def __call__(self, query: str, limit: int, offset: int, category_id: str) -> list[dict]:
        self.calls.append((query, limit, offset, category_id))
        if (query, offset) in self.failing_queries:
            raise AppError(ErrorCode.EXTERNAL_API_FAILED, "eBay API 실패")
        return [dict(item) for item in self.items_by_query.get((query, offset), [])]


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
    return list(database_session.scalars(select(Product).order_by(Product.external_id)))


def product_centroid(database_session) -> EmbeddingCentroid | None:
    database_session.expire_all()
    return database_session.get(EmbeddingCentroid, EmbeddingDomain.PRODUCT)


def test_saves_mapped_product_with_keyword_attributes_color_and_embedding(
    database_session, sample_image_bytes: Callable[..., bytes]
) -> None:
    color_item = ebay_item(
        "v1|1001|0",
        title="Women's Minimal Knit Top & Cardigan",
        price={"value": "39.99", "currency": "USD"},
        seller={"username": "color-shop"},
    )
    no_seller_item = ebay_item("v1|1002|0", price={"value": "15.50", "currency": "USD"})
    del no_seller_item["seller"]
    color_image = sample_image_bytes(color=(200, 160, 130), image_format="PNG")
    white_image = sample_image_bytes(color=(255, 255, 255), image_format="PNG")
    search = FakeSearch({FEMALE_TWENTIES_MINIMAL: [color_item, no_seller_item]})
    download = FakeDownload({image_url_of(color_item): color_image, image_url_of(no_seller_item): white_image})

    report = run(search, download)

    assert_report(report, saved=2, failed_products=0, failed_keywords=0)
    assert search.calls == EXPECTED_CALLS

    color_product, no_seller_product = all_products(database_session)
    assert (color_product.source, color_product.external_id) == (ProductSource.EBAY, "v1|1001|0")
    assert color_product.title == "Women's Minimal Knit Top & Cardigan"
    assert color_product.price == Decimal("39.99")
    assert color_product.currency == "USD"
    # 판매자 아이디(eBay 사용자 정보)는 저장하지 않는다 → 판매처는 항상 "eBay"
    assert color_product.mall_name == "eBay"
    assert color_product.purchase_url == color_item["itemWebUrl"]
    assert color_product.image_url == image_url_of(color_item)
    assert (color_product.gender, color_product.age_group, color_product.style, color_product.category) == (
        Gender.FEMALE,
        AgeGroup.TWENTIES,
        Style.MINIMAL,
        Category.TOP,
    )
    assert color_product.updated_at is not None
    # 단색 → 배경 제거 후 남는 픽셀이 5% 미만이라 영역 전체 → K-means 중심 = 그 색
    assert list(color_product.color_lab) == pytest.approx(list(rgb_to_lab(200, 160, 130)), abs=0.01)
    # 판매자가 없어도 "eBay"
    assert no_seller_product.mall_name == "eBay"
    assert no_seller_product.price == Decimal("15.50")
    assert list(no_seller_product.color_lab) == pytest.approx(list(rgb_to_lab(255, 255, 255)), abs=0.01)

    embedding = np.array(color_product.embedding, dtype=float)
    assert embedding.shape == (EMBEDDING_DIMENSION,)
    assert np.linalg.norm(embedding) == pytest.approx(1.0, abs=1e-4)
    expected_embedding = FakeEmbeddingModel().embed_images([color_image])[0]
    assert embedding.tolist() == pytest.approx(expected_embedding, abs=1e-5)


def test_representative_color_removes_border_background_and_takes_largest_cluster(database_session) -> None:
    # 회색 배경 400x400. 가운데 80% 영역(40~360) 안에 큰 파란 사각형(160x160)과 작은 빨간 사각형(40x40)
    # 테두리 색(회색)과 비슷한 픽셀을 빼면 파랑·빨강만 남고, 픽셀이 더 많은 파랑이 대표색
    image = Image.new("RGB", (400, 400), (180, 180, 180))
    image.paste((30, 90, 170), (120, 120, 280, 280))
    image.paste((200, 30, 30), (290, 290, 330, 330))
    item = ebay_item("v1|1501|0")
    search = FakeSearch({FEMALE_TWENTIES_MINIMAL: [item]})

    report = run(search, FakeDownload({image_url_of(item): png_bytes(image)}))

    assert_report(report, saved=1, failed_products=0, failed_keywords=0)
    (product,) = all_products(database_session)
    assert list(product.color_lab) == pytest.approx(list(rgb_to_lab(30, 90, 170)), abs=0.01)


def test_running_twice_updates_existing_row_without_duplicates(
    database_session, sample_image_bytes: Callable[..., bytes]
) -> None:
    first_item = ebay_item("v1|2001|0", price={"value": "30.00", "currency": "USD"}, title="First Title")
    image = sample_image_bytes(color=(40, 80, 160), image_format="PNG")
    download = FakeDownload({image_url_of(first_item): image})

    first_report = run(FakeSearch({FEMALE_TWENTIES_MINIMAL: [first_item]}), download)
    assert_report(first_report, saved=1, failed_products=0, failed_keywords=0)
    (first_product,) = all_products(database_session)
    first_id, first_updated_at = first_product.id, first_product.updated_at

    second_item = ebay_item("v1|2001|0", price={"value": "25.00", "currency": "USD"}, title="Changed Title")
    second_report = run(FakeSearch({FEMALE_TWENTIES_MINIMAL: [second_item]}), download)

    assert_report(second_report, saved=1, failed_products=0, failed_keywords=0)
    assert database_session.scalar(select(func.count()).select_from(Product)) == 1
    (second_product,) = all_products(database_session)
    assert second_product.id == first_id
    assert second_product.price == Decimal("25.00")
    assert second_product.title == "Changed Title"
    assert second_product.updated_at > first_updated_at


def test_same_product_in_multiple_keywords_takes_later_keyword_values(
    database_session, sample_image_bytes: Callable[..., bytes]
) -> None:
    earlier_item = ebay_item("v1|3001|0", title="Earlier Title", price={"value": "10.00", "currency": "USD"})
    later_item = ebay_item("v1|3001|0", title="Later Title", price={"value": "20.00", "currency": "USD"})
    image = sample_image_bytes(color=(90, 120, 60), image_format="PNG")
    search = FakeSearch({FEMALE_TWENTIES_MINIMAL: [earlier_item], MALE_THIRTIES_STREET: [later_item]})

    report = run(search, FakeDownload({image_url_of(earlier_item): image}))

    assert_report(report, saved=2, failed_products=0, failed_keywords=0)
    (product,) = all_products(database_session)
    assert (product.gender, product.age_group, product.style, product.category) == (
        Gender.MALE,
        AgeGroup.THIRTIES,
        Style.STREET,
        Category.TOP,
    )
    assert product.title == "Later Title"
    assert product.price == Decimal("20.00")


def test_failed_products_are_skipped_and_counted(database_session, sample_image_bytes: Callable[..., bytes]) -> None:
    valid_item = ebay_item("v1|4001|0")
    download_failure_item = ebay_item("v1|4002|0")  # download 에 등록하지 않음 → AppError
    not_image_item = ebay_item("v1|4003|0")
    missing_item_id_item = ebay_item("v1|4004|0")
    del missing_item_id_item["itemId"]
    missing_image_item = ebay_item("v1|4005|0")
    del missing_image_item["image"]
    invalid_price_item = ebay_item("v1|4006|0", price={"value": "see description", "currency": "USD"})
    image = sample_image_bytes(color=(150, 50, 50), image_format="PNG")
    bytes_by_url = {image_url_of(item): image for item in (valid_item, missing_item_id_item, invalid_price_item)}
    bytes_by_url[image_url_of(not_image_item)] = b"this is not an image"
    search = FakeSearch(
        {
            FEMALE_TWENTIES_MINIMAL: [
                valid_item,
                download_failure_item,
                not_image_item,
                missing_item_id_item,
                missing_image_item,
                invalid_price_item,
            ]
        }
    )

    report = run(search, FakeDownload(bytes_by_url))

    assert_report(report, saved=1, failed_products=5, failed_keywords=0)
    assert [product.external_id for product in all_products(database_session)] == ["v1|4001|0"]


def test_failed_keyword_is_skipped_and_other_keywords_continue(
    database_session, sample_image_bytes: Callable[..., bytes]
) -> None:
    skipped_item = ebay_item("v1|5001|0")
    saved_item = ebay_item("v1|5002|0")
    image = sample_image_bytes(color=(60, 60, 60), image_format="PNG")
    search = FakeSearch(
        {FEMALE_TWENTIES_MINIMAL: [skipped_item], MALE_THIRTIES_STREET: [saved_item]},
        failing_queries={FEMALE_TWENTIES_MINIMAL},
    )

    report = run(search, FakeDownload({image_url_of(skipped_item): image, image_url_of(saved_item): image}))

    assert_report(report, saved=1, failed_products=0, failed_keywords=1)
    assert search.calls == EXPECTED_CALLS
    assert [product.external_id for product in all_products(database_session)] == ["v1|5002|0"]


def test_all_keywords_failing_saves_nothing(database_session) -> None:
    search = FakeSearch({}, failing_queries={(query, offset) for query, _, offset, _ in EXPECTED_CALLS})

    report = run(search, FakeDownload({}))

    assert_report(report, saved=0, failed_products=0, failed_keywords=KEYWORD_COUNT)
    assert all_products(database_session) == []


def test_product_centroid_is_mean_of_all_product_embeddings_after_ingest(
    database_session, create_product, sample_image_bytes: Callable[..., bytes]
) -> None:
    # 이번 배치에서 빠진 기존 상품도 평균에 들어간다 (products 전체 평균)
    existing_product = create_product(external_id="existing")
    first_item, second_item = ebay_item("v1|6001|0"), ebay_item("v1|6002|0")
    search = FakeSearch({FEMALE_TWENTIES_MINIMAL: [first_item], MALE_THIRTIES_STREET: [second_item]})
    download = FakeDownload(
        {
            image_url_of(first_item): sample_image_bytes(color=(10, 20, 30), image_format="PNG"),
            image_url_of(second_item): sample_image_bytes(color=(200, 100, 50), image_format="PNG"),
        }
    )

    report = run(search, download)

    assert_report(report, saved=2, failed_products=0, failed_keywords=0)
    products = all_products(database_session)
    assert {product.id for product in products} >= {existing_product.id}
    expected_centroid = np.mean([np.array(product.embedding, dtype=float) for product in products], axis=0)
    centroid = product_centroid(database_session)
    assert centroid is not None
    assert np.array(centroid.embedding, dtype=float).tolist() == pytest.approx(expected_centroid.tolist(), abs=1e-5)
