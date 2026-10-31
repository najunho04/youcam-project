"""product_ingest service 단위 테스트. eBay API·이미지 다운로드는 가짜 함수로 대체한다."""
import io
from decimal import Decimal

import numpy as np
import pytest
from PIL import Image
from sqlalchemy import select

from common.entity import EmbeddingCentroid, Product
from common.enums import AgeGroup, Category, EmbeddingDomain, Gender, ProductSource, Style
from common.error import AppError, ErrorCode
from feature.product_ingest import service
from shared.color import rgb_to_lab

FEMALE_TWENTIES_MINIMAL = "women 20s minimal top"
MALE_THIRTIES_STREET = "men 30s streetwear top"


def ebay_item(item_id: str, **overrides) -> dict:
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


def png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def search_returning(items_by_query: dict[str, list[dict]]):
    return lambda query, limit: [dict(item) for item in items_by_query.get(query, [])]


def download_returning(image_bytes: bytes):
    return lambda url: image_bytes


def all_products(database_session) -> list[Product]:
    database_session.expire_all()
    return list(database_session.scalars(select(Product).order_by(Product.external_id)))


# ---- 키워드 ----
def test_build_keywords_follows_gender_age_group_style_enum_order():
    keywords = service.build_keywords()

    assert len(keywords) == len(Gender) * len(AgeGroup) * len(Style)
    assert [(keyword.gender, keyword.age_group, keyword.style) for keyword in keywords] == [
        (gender, age_group, style) for gender in Gender for age_group in AgeGroup for style in Style
    ]
    assert all(keyword.category == Category.TOP for keyword in keywords)
    assert keywords[0].search_query == "women teen minimal top"
    assert keywords[-1].search_query == "men 40s feminine top"


# ---- eBay 항목 매핑 ----
def test_map_ebay_item_maps_fields():
    fields = service.map_ebay_item(ebay_item("v1|77|0", title="Knit Top", price={"value": "15.90", "currency": "USD"}))

    assert fields.external_id == "v1|77|0"
    assert fields.title == "Knit Top"
    assert fields.price == Decimal("15.90")
    assert fields.currency == "USD"
    assert fields.mall_name == "eBay"
    assert fields.purchase_url == "https://www.ebay.test/itm/v1|77|0"
    assert fields.image_url == "https://image.test/items/v1|77|0.png"


@pytest.mark.parametrize("seller", [None, {}, {"username": ""}, {"username": "some-seller"}])
def test_map_ebay_item_never_stores_seller_username(seller):
    item = ebay_item("v1|77|0")
    if seller is None:
        del item["seller"]
    else:
        item["seller"] = seller

    assert service.map_ebay_item(item).mall_name == "eBay"


@pytest.mark.parametrize("missing_key", ["itemId", "title", "price", "image", "itemWebUrl"])
def test_map_ebay_item_with_missing_field_raises_validation_error(missing_key):
    item = ebay_item("v1|77|0")
    del item[missing_key]

    with pytest.raises(AppError) as error:
        service.map_ebay_item(item)
    assert error.value.error_code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize(
    "price", [{"value": "see description", "currency": "USD"}, {"value": "1.00"}, {"currency": "USD"}, "39.99"]
)
def test_map_ebay_item_with_invalid_price_raises_validation_error(price):
    with pytest.raises(AppError) as error:
        service.map_ebay_item(ebay_item("v1|77|0", price=price))
    assert error.value.error_code == ErrorCode.VALIDATION_ERROR


# ---- 대표색 ----
def test_representative_color_of_single_color_image_is_that_color():
    image = Image.new("RGB", (300, 300), (90, 120, 60))

    assert service.representative_color_lab(png_bytes(image)) == pytest.approx(rgb_to_lab(90, 120, 60), abs=0.01)


def test_representative_color_removes_border_colored_background():
    # 배경(회색)과 같은 색을 빼면 가운데 초록만 남는다
    image = Image.new("RGB", (300, 300), (200, 200, 200))
    image.paste((20, 140, 60), (60, 60, 240, 240))

    assert service.representative_color_lab(png_bytes(image)) == pytest.approx(rgb_to_lab(20, 140, 60), abs=0.01)


def test_representative_color_ignores_pixels_outside_center_eighty_percent():
    # 가운데 80% 밖(가장자리 10%)의 빨강은 영역에 들어오지 않는다
    image = Image.new("RGB", (300, 300), (255, 255, 255))
    image.paste((200, 20, 20), (0, 0, 300, 25))
    image.paste((30, 60, 160), (100, 100, 200, 200))

    assert service.representative_color_lab(png_bytes(image)) == pytest.approx(rgb_to_lab(30, 60, 160), abs=0.01)


def test_representative_color_takes_largest_cluster_not_average():
    # 파랑 큰 면 + 노랑 작은 면 → 평균(섞인 색)이 아니라 파랑
    image = Image.new("RGB", (300, 300), (255, 255, 255))
    image.paste((30, 60, 160), (40, 40, 260, 200))
    image.paste((240, 220, 40), (40, 200, 260, 260))

    assert service.representative_color_lab(png_bytes(image)) == pytest.approx(rgb_to_lab(30, 60, 160), abs=0.01)


def test_representative_color_is_deterministic():
    image = Image.new("RGB", (300, 300), (250, 250, 250))
    image.paste((120, 80, 50), (50, 50, 250, 250))
    image.paste((20, 20, 20), (100, 100, 150, 150))
    data = png_bytes(image)

    assert service.representative_color_lab(data) == service.representative_color_lab(data)


def test_representative_color_converts_non_rgb_image_to_rgb():
    image = Image.new("RGBA", (64, 64), (10, 120, 200, 255))

    assert service.representative_color_lab(png_bytes(image)) == pytest.approx(rgb_to_lab(10, 120, 200), abs=0.01)


def test_representative_color_with_non_image_bytes_raises_invalid_image():
    with pytest.raises(AppError) as error:
        service.representative_color_lab(b"not an image")
    assert error.value.error_code == ErrorCode.INVALID_IMAGE


def test_rgb_pixels_to_lab_matches_shared_scalar_conversion():
    pixels = np.array([[0, 0, 0], [255, 255, 255], [200, 160, 130], [10, 120, 200]], dtype=float)

    expected = [rgb_to_lab(*map(int, pixel)) for pixel in pixels]
    for actual_color, expected_color in zip(service.rgb_pixels_to_lab(pixels).tolist(), expected, strict=True):
        assert actual_color == pytest.approx(list(expected_color), abs=1e-9)


# ---- run_ingest ----
def test_run_ingest_same_product_twice_in_one_keyword_keeps_single_row(database_session, sample_image_bytes):
    search = search_returning(
        {
            FEMALE_TWENTIES_MINIMAL: [
                ebay_item("v1|10|0", price={"value": "10.00", "currency": "USD"}),
                ebay_item("v1|10|0", price={"value": "20.00", "currency": "USD"}),
            ]
        }
    )

    report = service.run_ingest(search, download_returning(sample_image_bytes(image_format="PNG", size=32)))

    assert (report.saved, report.failed_products, report.failed_keywords) == (2, 0, 0)
    (product,) = all_products(database_session)
    assert product.price == Decimal("20.00")
    assert product.source == ProductSource.EBAY


def test_run_ingest_database_error_rolls_back_only_that_keyword(database_session, sample_image_bytes):
    # title varchar(255) 초과 → DB 오류 → 그 키워드 전체 롤백, 다른 키워드는 저장
    search = search_returning(
        {
            FEMALE_TWENTIES_MINIMAL: [ebay_item("v1|20|0"), ebay_item("v1|21|0", title="a" * 300)],
            MALE_THIRTIES_STREET: [ebay_item("v1|22|0")],
        }
    )

    report = service.run_ingest(search, download_returning(sample_image_bytes(image_format="PNG", size=32)))

    assert (report.saved, report.failed_products, report.failed_keywords) == (1, 0, 1)
    assert [product.external_id for product in all_products(database_session)] == ["v1|22|0"]


def test_run_ingest_does_not_delete_products_missing_from_search(database_session, create_product, sample_image_bytes):
    create_product(external_id="old-product")

    service.run_ingest(
        search_returning({FEMALE_TWENTIES_MINIMAL: [ebay_item("v1|30|0")]}),
        download_returning(sample_image_bytes(image_format="PNG", size=32)),
    )

    assert [product.external_id for product in all_products(database_session)] == ["old-product", "v1|30|0"]


def test_run_ingest_without_any_product_saves_no_centroid(database_session):
    service.run_ingest(search_returning({}), download_returning(b""))

    database_session.expire_all()
    assert database_session.get(EmbeddingCentroid, EmbeddingDomain.PRODUCT) is None


def test_run_ingest_updates_existing_product_centroid(database_session, create_product, sample_image_bytes):
    database_session.add(EmbeddingCentroid(domain=EmbeddingDomain.PRODUCT, embedding=[0.0] * 512))
    database_session.commit()
    create_product(external_id="existing")

    service.run_ingest(
        search_returning({FEMALE_TWENTIES_MINIMAL: [ebay_item("v1|50|0")]}),
        download_returning(sample_image_bytes(image_format="PNG", size=32)),
    )

    database_session.expire_all()
    expected = np.mean([np.array(product.embedding, dtype=float) for product in all_products(database_session)], axis=0)
    centroid = database_session.get(EmbeddingCentroid, EmbeddingDomain.PRODUCT)
    assert np.array(centroid.embedding, dtype=float).tolist() == pytest.approx(expected.tolist(), abs=1e-5)


def test_run_ingest_prints_counts_per_keyword(database_session, sample_image_bytes, capsys):
    def search(query: str, limit: int) -> list[dict]:
        if query == MALE_THIRTIES_STREET:
            raise AppError(ErrorCode.EXTERNAL_API_FAILED, "eBay API 실패")
        if query == FEMALE_TWENTIES_MINIMAL:
            return [ebay_item("v1|40|0"), ebay_item("v1|41|0", price={"value": "ask", "currency": "USD"})]
        return []

    service.run_ingest(search, download_returning(sample_image_bytes(image_format="PNG", size=32)))

    output_lines = capsys.readouterr().out.splitlines()
    assert any(FEMALE_TWENTIES_MINIMAL in line and "수집 2" in line and "저장 1" in line and "실패 1" in line for line in output_lines)
    assert any(MALE_THIRTIES_STREET in line and "키워드 실패" in line for line in output_lines)


# ---- 종료 코드 ----
@pytest.mark.parametrize(
    ("report", "expected_exit_code"),
    [
        (service.IngestReport(saved=0, failed_products=0, failed_keywords=40), 1),
        (service.IngestReport(saved=0, failed_products=0, failed_keywords=39), 0),
        (service.IngestReport(saved=5, failed_products=3, failed_keywords=0), 0),
    ],
)
def test_exit_code_is_one_only_when_all_keywords_failed(report, expected_exit_code):
    assert service.exit_code(report) == expected_exit_code
