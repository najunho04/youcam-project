"""recommendation 슬라이스 DB 접근. 어떤 테이블에도 쓰지 않는다 (products·swipes·wardrobe_photos 읽기만)."""
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from common.entity import Product, Swipe, WardrobePhoto
from common.enums import AgeGroup, Category, Gender, Style


def find_unswiped_top_products(
    database_session: Session, user_id: int, gender: Gender, age_group: AgeGroup
) -> list[Product]:
    """후보: 성별·나이대 일치 + TOP, 이 사용자가 스와이프하지 않은 상품. 쿼리 한 번, id 순."""
    already_swiped = exists().where(Swipe.user_id == user_id, Swipe.product_id == Product.id)
    return list(
        database_session.scalars(
            select(Product)
            .where(
                Product.gender == gender,
                Product.age_group == age_group,
                Product.category == Category.TOP,
                ~already_swiped,
            )
            .order_by(Product.id)
        ).all()
    )


def find_swiped_products(database_session: Session, user_id: int) -> list[tuple[Style, list[float], bool]]:
    """이 사용자가 스와이프한 상품의 (style, embedding, liked). 상품 id 순."""
    rows = database_session.execute(
        select(Product.style, Product.embedding, Swipe.liked)
        .join(Swipe, Swipe.product_id == Product.id)
        .where(Swipe.user_id == user_id)
        .order_by(Product.id)
    ).all()
    return [(style, embedding, liked) for style, embedding, liked in rows]


def find_wardrobe_embeddings(database_session: Session, user_id: int) -> list[list[float]]:
    return list(
        database_session.scalars(
            select(WardrobePhoto.embedding).where(WardrobePhoto.user_id == user_id).order_by(WardrobePhoto.id)
        ).all()
    )
