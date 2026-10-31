"""recommendation 슬라이스 DB 접근. 어떤 테이블에도 쓰지 않는다 (products·pins·swipes·wardrobe_photos·embedding_centroids 읽기만)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from common.entity import EmbeddingCentroid, Pin, Product, Swipe, WardrobePhoto
from common.enums import Category, EmbeddingDomain, Gender, ProductSource, Style


def find_top_products(database_session: Session, gender: Gender) -> list[Product]:
    """후보: eBay 상품 중 성별 일치 + TOP. 상품 나이대는 보지 않는다 (eBay 에는 나이대 정보가 없다). 스와이프는 핀에 하므로 상품을 제외하지 않는다. 쿼리 한 번, id 순.
    한국어 UI용 네이버 상품(source = NAVER)은 최후순위라 지금은 EBAY 고정."""
    return list(
        database_session.scalars(
            select(Product)
            .where(
                Product.source == ProductSource.EBAY,
                Product.gender == gender,
                Product.category == Category.TOP,
            )
            .order_by(Product.id)
        ).all()
    )


def find_swiped_pins(database_session: Session, user_id: int) -> list[tuple[Style, list[float], bool]]:
    """이 사용자가 스와이프한 핀의 (style, embedding, liked). 핀 id 순."""
    rows = database_session.execute(
        select(Pin.style, Pin.embedding, Swipe.liked)
        .join(Swipe, Swipe.pin_id == Pin.id)
        .where(Swipe.user_id == user_id)
        .order_by(Pin.id)
    ).all()
    return [(style, embedding, liked) for style, embedding, liked in rows]


def find_wardrobe_embeddings(database_session: Session, user_id: int) -> list[list[float]]:
    return list(
        database_session.scalars(
            select(WardrobePhoto.embedding).where(WardrobePhoto.user_id == user_id).order_by(WardrobePhoto.id)
        ).all()
    )


def find_centroid(database_session: Session, domain: EmbeddingDomain) -> list[float] | None:
    return database_session.scalars(
        select(EmbeddingCentroid.embedding).where(EmbeddingCentroid.domain == domain)
    ).one_or_none()
