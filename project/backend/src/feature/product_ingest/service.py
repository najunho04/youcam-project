"""product_ingest 슬라이스 비즈니스 로직. 키워드 1개 = 트랜잭션 1개."""
import io
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import numpy as np
from PIL import Image, UnidentifiedImageError
from sqlalchemy.exc import SQLAlchemyError

from common.enums import AgeGroup, Category, Gender, ProductSource, Style
from common.error import AppError, ErrorCode
from feature.product_ingest import repository
from shared.color import LabColor
from shared.database import session_scope
from shared.embedding import get_embedding_model

SearchFunction = Callable[[str, int], list[dict]]
DownloadFunction = Callable[[str], bytes]

LIMIT_COUNT = 50
DEFAULT_MALL_NAME = "eBay"

# 대표색 추출 기준값
CENTER_REGION_RATIO = 0.8  # 가로·세로 가운데 80% 영역
BACKGROUND_DELTA_E_THRESHOLD = 12.0  # 테두리 배경색과 이보다 가까우면 배경
MINIMUM_FOREGROUND_RATIO = 0.05  # 배경을 빼고 남은 픽셀이 영역의 5% 미만이면 영역 전체를 쓴다
CLUSTER_COUNT = 3
MAXIMUM_CLUSTER_ITERATIONS = 10
ANALYSIS_MAXIMUM_SIDE = 200  # 계산량을 줄이려고 긴 변을 이 크기로 줄인다 (가까운 픽셀 보간이라 색이 섞이지 않는다)

_GENDER_WORDS = {Gender.FEMALE: "women", Gender.MALE: "men"}
_AGE_GROUP_WORDS = {
    AgeGroup.LATE_TEENS: "teen",
    AgeGroup.TWENTIES: "20s",
    AgeGroup.THIRTIES: "30s",
    AgeGroup.FORTIES_PLUS: "40s",
}
_STYLE_WORDS = {
    Style.MINIMAL: "minimal",
    Style.CASUAL: "casual",
    Style.STREET: "streetwear",
    Style.FORMAL: "formal",
    Style.LOVELY: "feminine",
}
_CATEGORY_WORDS = {Category.TOP: "top"}


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
class EbayProductFields:
    external_id: str
    title: str
    price: Decimal
    currency: str
    mall_name: str
    purchase_url: str
    image_url: str


@dataclass(frozen=True)
class _PreparedProduct:
    fields: EbayProductFields
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


def map_ebay_item(item: dict) -> EbayProductFields:
    """eBay itemSummaries[] 한 개 → 저장할 필드. 필수 필드 누락·변환 실패 시 VALIDATION_ERROR. 판매자가 없으면 "eBay"."""
    try:
        price = item["price"]
        seller = item.get("seller") or {}
        return EbayProductFields(
            external_id=_required_text(item.get("itemId"), "itemId"),
            title=_required_text(item.get("title"), "title"),
            price=Decimal(_required_text(price.get("value"), "price.value")),
            currency=_required_text(price.get("currency"), "price.currency"),
            mall_name=str(seller.get("username") or DEFAULT_MALL_NAME),
            purchase_url=_required_text(item.get("itemWebUrl"), "itemWebUrl"),
            image_url=_required_text((item.get("image") or {}).get("imageUrl"), "image.imageUrl"),
        )
    except (KeyError, TypeError, AttributeError, ValueError, InvalidOperation) as error:
        raise AppError(ErrorCode.VALIDATION_ERROR, f"상품 필드 오류: {error}") from error


def _required_text(value: object, field_name: str) -> str:
    if value is None or value == "":
        raise ValueError(f"{field_name} 누락")
    return str(value)


def rgb_pixels_to_lab(pixels: np.ndarray) -> np.ndarray:
    """(n, 3) sRGB 0~255 → (n, 3) CIE Lab (D65). shared.color.rgb_to_lab 과 같은 식을 벡터로 계산한다."""
    normalized = pixels / 255.0
    linear = np.where(normalized <= 0.04045, normalized / 12.92, ((normalized + 0.055) / 1.055) ** 2.4)
    x = (linear @ np.array([0.4124, 0.3576, 0.1805])) / 0.95047
    y = linear @ np.array([0.2126, 0.7152, 0.0722])
    z = (linear @ np.array([0.0193, 0.1192, 0.9505])) / 1.08883

    def pivot(values: np.ndarray) -> np.ndarray:
        return np.where(values > 0.008856, np.cbrt(values), 7.787 * values + 16 / 116)

    pivot_x, pivot_y, pivot_z = pivot(x), pivot(y), pivot(z)
    return np.stack([116 * pivot_y - 16, 500 * (pivot_x - pivot_y), 200 * (pivot_y - pivot_z)], axis=1)


def largest_cluster_center(lab_pixels: np.ndarray) -> np.ndarray:
    """K-means(k=3). 초기 중심은 L* 하위·중간·상위 분위수 픽셀, 최대 10회. 비는 묶음은 중심을 그대로 둔다.
    무작위를 쓰지 않으므로 같은 입력이면 같은 결과. 픽셀이 가장 많은 묶음의 중심을 돌려준다."""
    sorted_by_lightness = lab_pixels[np.argsort(lab_pixels[:, 0], kind="stable")]
    pixel_count = len(sorted_by_lightness)
    initial_indices = [pixel_count // 6, pixel_count // 2, (5 * pixel_count) // 6]
    centers = sorted_by_lightness[initial_indices].astype(float)

    labels = np.zeros(pixel_count, dtype=int)
    for _ in range(MAXIMUM_CLUSTER_ITERATIONS):
        distances = np.linalg.norm(lab_pixels[:, np.newaxis, :] - centers[np.newaxis, :, :], axis=2)
        labels = distances.argmin(axis=1)  # 같으면 앞 묶음
        new_centers = centers.copy()
        for cluster_index in range(CLUSTER_COUNT):
            members = lab_pixels[labels == cluster_index]
            if len(members):
                new_centers[cluster_index] = members.mean(axis=0)
        if np.allclose(new_centers, centers):
            break
        centers = new_centers

    cluster_sizes = np.bincount(labels, minlength=CLUSTER_COUNT)
    return centers[int(cluster_sizes.argmax())]


def representative_color_lab(image_bytes: bytes) -> LabColor:
    """테두리 1px 중앙값 = 배경색 → 가운데 80% 영역에서 배경과 ΔE < 12 인 픽셀 제거
    (남은 픽셀이 5% 미만이면 영역 전체) → K-means 가장 큰 묶음의 중심."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            rgb_image = image.convert("RGB")
    except (UnidentifiedImageError, OSError) as error:
        raise AppError(ErrorCode.INVALID_IMAGE, "이미지로 열 수 없습니다") from error

    rgb_image.thumbnail((ANALYSIS_MAXIMUM_SIDE, ANALYSIS_MAXIMUM_SIDE), Image.Resampling.NEAREST)
    image_array = np.asarray(rgb_image, dtype=float)
    height, width, _ = image_array.shape

    border_pixels = np.concatenate(
        [image_array[0, :], image_array[-1, :], image_array[:, 0], image_array[:, -1]], axis=0
    )
    background_lab = rgb_pixels_to_lab(np.median(border_pixels, axis=0)[np.newaxis, :])[0]

    margin_x = int(round(width * (1 - CENTER_REGION_RATIO) / 2))
    margin_y = int(round(height * (1 - CENTER_REGION_RATIO) / 2))
    center_region = image_array[margin_y : height - margin_y or height, margin_x : width - margin_x or width]
    region_lab = rgb_pixels_to_lab(center_region.reshape(-1, 3))

    is_foreground = np.linalg.norm(region_lab - background_lab, axis=1) >= BACKGROUND_DELTA_E_THRESHOLD
    foreground_lab = region_lab[is_foreground]
    if len(foreground_lab) < MINIMUM_FOREGROUND_RATIO * len(region_lab):
        foreground_lab = region_lab

    lightness, green_red, blue_yellow = largest_cluster_center(foreground_lab)
    return float(lightness), float(green_red), float(blue_yellow)


def run_ingest(search: SearchFunction, download: DownloadFunction) -> IngestReport:
    """키워드별로 검색 → 상품 준비(다운로드·대표색) → 임베딩 → upsert. 실패는 건너뛰고 계속한다.
    끝나면 products 전체 embedding 평균을 embedding_centroids(PRODUCT) 에 저장한다."""
    saved = failed_products = failed_keywords = 0
    for keyword in build_keywords():
        query = keyword.search_query
        try:
            items = search(query, LIMIT_COUNT)
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

    _save_product_centroid()
    report = IngestReport(saved=saved, failed_products=failed_products, failed_keywords=failed_keywords)
    print(f"완료: 저장 {report.saved} · 실패 상품 {report.failed_products} · 실패 키워드 {report.failed_keywords}")
    return report


def _prepare_product(item: dict, download: DownloadFunction) -> _PreparedProduct:
    fields = map_ebay_item(item)
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
                ProductSource.EBAY,
                fields.external_id,
                title=fields.title,
                price=fields.price,
                currency=fields.currency,
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


def _save_product_centroid() -> None:
    """products 전체 embedding 평균. 상품이 없으면 저장하지 않는다."""
    with session_scope() as database_session:
        embeddings = repository.find_all_product_embeddings(database_session)
        if not embeddings:
            return
        centroid = np.asarray(embeddings, dtype=float).mean(axis=0)
        repository.upsert_product_centroid(database_session, centroid.tolist())


def exit_code(report: IngestReport) -> int:
    """키워드가 전부 실패하면 1, 그 외 0."""
    return 1 if report.failed_keywords == len(build_keywords()) else 0
