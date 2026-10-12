"""product_ingest 슬라이스 비즈니스 로직. 키워드 1개 = 트랜잭션 1개."""
import html
import io
import re
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from PIL import Image, UnidentifiedImageError
from sqlalchemy.exc import SQLAlchemyError

from common.enums import AgeGroup, Category, Gender, Style
from common.error import AppError, ErrorCode
from feature.product_ingest import repository
from shared.color import LabColor, rgb_to_lab
from shared.database import session_scope
from shared.embedding import get_embedding_model

SearchFunction = Callable[[str, int], list[dict]]
DownloadFunction = Callable[[str], bytes]

DISPLAY_COUNT = 50
WHITE_THRESHOLD = 240

_GENDER_WORDS = {Gender.FEMALE: "여성", Gender.MALE: "남성"}
_AGE_GROUP_WORDS = {
    AgeGroup.LATE_TEENS: "10대",
    AgeGroup.TWENTIES: "20대",
    AgeGroup.THIRTIES: "30대",
    AgeGroup.FORTIES_PLUS: "40대",
}
_STYLE_WORDS = {
    Style.MINIMAL: "미니멀",
    Style.CASUAL: "캐주얼",
    Style.STREET: "스트릿",
    Style.FORMAL: "포멀",
    Style.LOVELY: "러블리",
}
_CATEGORY_WORDS = {Category.TOP: "상의"}
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class IngestReport:
    saved: int
    failed_products: int
    failed_keywords: int


@dataclass(frozen=True)
class IngestKeyword:
    gender: Gender
    age_group: AgeGroup
    style: Style
    category: Category

    @property
    def search_query(self) -> str:
        return (
            f"{_GENDER_WORDS[self.gender]} {_AGE_GROUP_WORDS[self.age_group]} "
            f"{_STYLE_WORDS[self.style]} {_CATEGORY_WORDS[self.category]}"
        )


@dataclass(frozen=True)
class NaverProductFields:
    naver_product_id: str
    title: str
    price: int
    mall_name: str
    purchase_url: str
    image_url: str


@dataclass(frozen=True)
class _PreparedProduct:
    fields: NaverProductFields
    image_bytes: bytes
    color_lab: LabColor


def build_keywords() -> list[IngestKeyword]:
    """Gender → AgeGroup → Style enum 정의 순서. 카테고리는 TOP 만."""
    return [
        IngestKeyword(gender=gender, age_group=age_group, style=style, category=Category.TOP)
        for gender in Gender
        for age_group in AgeGroup
        for style in Style
    ]


def clean_title(raw_title: str) -> str:
    """HTML 태그 제거 후 엔티티 복원 (복원된 '<신상>' 같은 문자열은 남긴다)."""
    return html.unescape(_HTML_TAG_PATTERN.sub("", raw_title)).strip()


def map_naver_item(item: dict) -> NaverProductFields:
    """필수 필드 누락·변환 실패 시 VALIDATION_ERROR."""
    try:
        return NaverProductFields(
            naver_product_id=_required_text(item, "productId"),
            title=clean_title(_required_text(item, "title")),
            price=int(_required_text(item, "lprice")),
            mall_name=_required_text(item, "mallName"),
            purchase_url=_required_text(item, "link"),
            image_url=_required_text(item, "image"),
        )
    except ValueError as error:
        raise AppError(ErrorCode.VALIDATION_ERROR, f"상품 필드 오류: {error}") from error


def _required_text(item: dict, key: str) -> str:
    value = item.get(key)
    if value is None:
        raise ValueError(f"{key} 누락")
    return str(value)


def representative_color_lab(image_bytes: bytes) -> LabColor:
    """RGB 변환 → 가운데 50% 영역 → 흰 배경(R·G·B 모두 240 이상) 제외 평균. 남는 픽셀이 없으면 영역 전체 평균."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            rgb_image = image.convert("RGB")
    except (UnidentifiedImageError, OSError) as error:
        raise AppError(ErrorCode.INVALID_IMAGE, "이미지로 열 수 없습니다") from error

    width, height = rgb_image.size
    left, upper = width // 4, height // 4
    center_region = rgb_image.crop((left, upper, left + max(width // 2, 1), upper + max(height // 2, 1)))
    pixels = np.asarray(center_region, dtype=float).reshape(-1, 3)
    non_white_pixels = pixels[~np.all(pixels >= WHITE_THRESHOLD, axis=1)]
    average_red, average_green, average_blue = (non_white_pixels if len(non_white_pixels) else pixels).mean(axis=0)
    return rgb_to_lab(average_red, average_green, average_blue)


def run_ingest(search: SearchFunction, download: DownloadFunction) -> IngestReport:
    """키워드별로 검색 → 상품 준비(다운로드·대표색) → 임베딩 → upsert. 실패는 건너뛰고 계속한다."""
    saved = failed_products = failed_keywords = 0
    for keyword in build_keywords():
        query = keyword.search_query
        try:
            items = search(query, DISPLAY_COUNT)
        except AppError as error:
            failed_keywords += 1
            print(f"[{query}] 키워드 실패: {error.message}")
            continue

        prepared_products: list[_PreparedProduct] = []
        for item in items:
            try:
                prepared_products.append(_prepare_product(item, download))
            except AppError:
                failed_products += 1
        keyword_failed_products = len(items) - len(prepared_products)

        try:
            keyword_saved = _save_products(keyword, prepared_products)
        except SQLAlchemyError as error:
            failed_keywords += 1
            print(f"[{query}] 키워드 실패: 저장 중 DB 오류로 롤백 ({type(error).__name__})")
            continue
        saved += keyword_saved
        print(f"[{query}] 수집 {len(items)} · 저장 {keyword_saved} · 실패 {keyword_failed_products}")

    report = IngestReport(saved=saved, failed_products=failed_products, failed_keywords=failed_keywords)
    print(f"완료: 저장 {report.saved} · 실패 상품 {report.failed_products} · 실패 키워드 {report.failed_keywords}")
    return report


def _prepare_product(item: dict, download: DownloadFunction) -> _PreparedProduct:
    fields = map_naver_item(item)
    image_bytes = download(fields.image_url)
    return _PreparedProduct(fields=fields, image_bytes=image_bytes, color_lab=representative_color_lab(image_bytes))


def _save_products(keyword: IngestKeyword, prepared_products: list[_PreparedProduct]) -> int:
    if not prepared_products:
        return 0
    embeddings = get_embedding_model().embed_images(
        [prepared_product.image_bytes for prepared_product in prepared_products]
    )
    with session_scope() as database_session:
        for prepared_product, embedding in zip(prepared_products, embeddings, strict=True):
            fields = prepared_product.fields
            repository.upsert_product(
                database_session,
                fields.naver_product_id,
                title=fields.title,
                price=fields.price,
                mall_name=fields.mall_name,
                purchase_url=fields.purchase_url,
                image_url=fields.image_url,
                gender=keyword.gender,
                age_group=keyword.age_group,
                style=keyword.style,
                category=keyword.category,
                color_lab=list(prepared_product.color_lab),
                embedding=embedding,
            )
    return len(prepared_products)


def exit_code(report: IngestReport) -> int:
    """키워드가 전부 실패하면 1, 그 외 0."""
    return 1 if report.failed_keywords == len(build_keywords()) else 0
