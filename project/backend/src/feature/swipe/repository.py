"""swipe 슬라이스 DB 접근. swipes 테이블만 쓴다. products·users 는 읽기만."""
from sqlalchemy import exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from common.entity import Product, Swipe
from common.enums import AgeGroup, Category, Gender


def find_unswiped_top_products(
    database_session: Session, user_id: int, gender: Gender, age_group: AgeGroup
) -> list[Product]:
    """성별·나이대 일치 + TOP, 이 사용자가 아직 스와이프하지 않은 상품. id 순."""
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


def find_existing_product_ids(database_session: Session, product_ids: set[int]) -> set[int]:
    return set(database_session.scalars(select(Product.id).where(Product.id.in_(product_ids))).all())


def upsert_swipes(database_session: Session, user_id: int, liked_by_product_id: dict[int, bool]) -> None:
    """(user_id, product_id) 충돌 시 liked 덮어씀. commit 은 요청 트랜잭션(get_database_session)이 한다."""
    statement = insert(Swipe).values(
        [
            {"user_id": user_id, "product_id": product_id, "liked": liked}
            for product_id, liked in liked_by_product_id.items()
        ]
    )
    database_session.execute(
        statement.on_conflict_do_update(
            index_elements=[Swipe.user_id, Swipe.product_id], set_={"liked": statement.excluded.liked}
        )
    )


def count_swipes_by_user(database_session: Session, user_id: int) -> tuple[int, int]:
    """(좋아요 수, 전체 수)."""
    liked_count, total_count = database_session.execute(
        select(func.count().filter(Swipe.liked), func.count()).where(Swipe.user_id == user_id)
    ).one()
    return liked_count, total_count
