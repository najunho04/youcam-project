"""product_ingest service 단위 테스트. 네이버 API·이미지 다운로드는 가짜 함수로 대체한다."""
import io

import pytest
from PIL import Image
from sqlalchemy import select

from common.entity import Product
from common.enums import AgeGroup, Category, Gender, Style
from common.error import AppError, ErrorCode
from feature.product_ingest import service
from shared.color import rgb_to_lab

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


def png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def search_returning(items_by_query: dict[str, list[dict]]):
    return lambda query, display: [dict(item) for item in items_by_query.get(query, [])]


def download_returning(image_bytes: bytes):
    return lambda url: image_bytes


def all_products(database_session) -> list[Product]:
    database_session.expire_all()
    return list(database_session.scalars(select(Product).order_by(Product.naver_product_id)))


# ---- 키워드 ----
def test_build_keywords_follows_gender_age_group_style_enum_order():
    keywords = service.build_keywords()

    assert len(keywords) == len(Gender) * len(AgeGroup) * len(Style)
    assert [(keyword.gender, keyword.age_group, keyword.style) for keyword in keywords] == [
        (gender, age_group, style) for gender in Gender for age_group in AgeGroup for style in Style
    ]
    assert all(keyword.category == Category.TOP for keyword in keywords)
    assert keywords[0].search_query == "여성 10대 미니멀 상의"
    assert keywords[-1].search_query == "남성 40대 러블리 상의"


# ---- 제목 정리 ----
@pytest.mark.parametrize(
    ("raw_title", "expected_title"),
    [
        ("<b>여성</b> 니트", "여성 니트"),
        ("A &amp; B &lt;신상&gt; &quot;특가&quot;", 'A & B <신상> "특가"'),
        ("  공백 <b>정리</b>  ", "공백 정리"),
    ],
)
def test_clean_title_removes_html_tags_and_unescapes_entities(raw_title, expected_title):
    assert service.clean_title(raw_title) == expected_title


# ---- 상품 매핑 ----
def test_map_naver_item_maps_fields():
    item = naver_item("77", title="<b>니트</b>", lprice="15900", mallName="몰")

    fields = service.map_naver_item(item)

    assert fields.naver_product_id == "77"
    assert fields.title == "니트"
    assert fields.price == 15900
    assert fields.mall_name == "몰"
    assert fields.purchase_url == item["link"]
    assert fields.image_url == item["image"]


@pytest.mark.parametrize("missing_key", ["productId", "title", "link", "image", "lprice", "mallName"])
def test_map_naver_item_with_missing_field_raises_validation_error(missing_key):
    item = naver_item("77")
    del item[missing_key]

    with pytest.raises(AppError) as raised:
        service.map_naver_item(item)

    assert raised.value.error_code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("missing_key", ["productId", "mallName"])
def test_map_naver_item_with_null_field_raises_validation_error(missing_key):
    with pytest.raises(AppError) as raised:
        service.map_naver_item(naver_item("77", **{missing_key: None}))

    assert raised.value.error_code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("invalid_price", ["가격문의", "12.5", ""])
def test_map_naver_item_with_invalid_price_raises_validation_error(invalid_price):
    with pytest.raises(AppError) as raised:
        service.map_naver_item(naver_item("77", lprice=invalid_price))

    assert raised.value.error_code == ErrorCode.VALIDATION_ERROR


# ---- 대표색 ----
def test_representative_color_uses_only_center_half_region():
    # 가장자리(가운데 50% 밖)는 빨강, 가운데 50% 는 파랑 → 파랑만 반영
    image = Image.new("RGB", (200, 100), (255, 0, 0))
    image.paste((0, 0, 255), (50, 25, 150, 75))

    assert service.representative_color_lab(png_bytes(image)) == pytest.approx(rgb_to_lab(0, 0, 255), abs=0.01)


def test_representative_color_averages_non_white_pixels():
    # 가운데 영역: 왼쪽 절반 (100, 0, 0), 오른쪽 절반 (0, 0, 100) → 평균 (50, 0, 50)
    image = Image.new("RGB", (100, 100), (255, 255, 255))
    image.paste((100, 0, 0), (25, 25, 50, 75))
    image.paste((0, 0, 100), (50, 25, 75, 75))

    assert service.representative_color_lab(png_bytes(image)) == pytest.approx(rgb_to_lab(50, 0, 50), abs=0.01)


def test_representative_color_keeps_pixels_with_any_channel_below_240():
    # (240, 240, 239) 는 흰 배경이 아니다 → 제외되지 않음
    image = Image.new("RGB", (100, 100), (240, 240, 239))

    assert service.representative_color_lab(png_bytes(image)) == pytest.approx(rgb_to_lab(240, 240, 239), abs=0.01)


def test_representative_color_with_only_white_pixels_averages_whole_center_region():
    image = Image.new("RGB", (100, 100), (0, 0, 0))
    image.paste((250, 245, 240), (25, 25, 75, 75))

    assert service.representative_color_lab(png_bytes(image)) == pytest.approx(rgb_to_lab(250, 245, 240), abs=0.01)


def test_representative_color_converts_non_rgb_image_to_rgb():
    image = Image.new("RGBA", (40, 40), (10, 120, 200, 255))

    assert service.representative_color_lab(png_bytes(image)) == pytest.approx(rgb_to_lab(10, 120, 200), abs=0.01)


def test_representative_color_with_non_image_bytes_raises_invalid_image():
    with pytest.raises(AppError) as raised:
        service.representative_color_lab(b"not an image")

    assert raised.value.error_code == ErrorCode.INVALID_IMAGE


# ---- run_ingest ----
def test_run_ingest_same_product_twice_in_one_keyword_keeps_single_row(database_session, sample_image_bytes):
    search = search_returning(
        {FEMALE_TWENTIES_MINIMAL: [naver_item("10", lprice="1000"), naver_item("10", lprice="2000")]}
    )

    report = service.run_ingest(search, download_returning(sample_image_bytes(image_format="PNG", size=32)))

    assert (report.saved, report.failed_products, report.failed_keywords) == (2, 0, 0)
    (product,) = all_products(database_session)
    assert product.price == 2000


def test_run_ingest_database_error_rolls_back_only_that_keyword(database_session, sample_image_bytes):
    # title varchar(255) 초과 → DB 오류 → 그 키워드 전체 롤백, 다른 키워드는 저장
    search = search_returning(
        {
            FEMALE_TWENTIES_MINIMAL: [naver_item("20"), naver_item("21", title="가" * 300)],
            MALE_THIRTIES_STREET: [naver_item("22")],
        }
    )

    report = service.run_ingest(search, download_returning(sample_image_bytes(image_format="PNG", size=32)))

    assert (report.saved, report.failed_products, report.failed_keywords) == (1, 0, 1)
    assert [product.naver_product_id for product in all_products(database_session)] == ["22"]


def test_run_ingest_does_not_delete_products_missing_from_search(database_session, create_product, sample_image_bytes):
    create_product(naver_product_id="old-product")

    service.run_ingest(
        search_returning({FEMALE_TWENTIES_MINIMAL: [naver_item("30")]}),
        download_returning(sample_image_bytes(image_format="PNG", size=32)),
    )

    assert [product.naver_product_id for product in all_products(database_session)] == ["30", "old-product"]


def test_run_ingest_prints_counts_per_keyword(database_session, sample_image_bytes, capsys):
    def search(query: str, display: int) -> list[dict]:
        if query == MALE_THIRTIES_STREET:
            raise AppError(ErrorCode.EXTERNAL_API_FAILED, "네이버 API 실패")
        return [naver_item("40"), naver_item("41", lprice="가격문의")] if query == FEMALE_TWENTIES_MINIMAL else []

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
