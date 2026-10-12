"""wardrobe 슬라이스 DB 접근. wardrobe_photos 테이블만 쓴다."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from common.entity import WardrobePhoto


def count_photos_by_user(database_session: Session, user_id: int) -> int:
    return database_session.scalar(
        select(func.count()).select_from(WardrobePhoto).where(WardrobePhoto.user_id == user_id)
    ) or 0


def find_photos_by_user(database_session: Session, user_id: int) -> list[WardrobePhoto]:
    return list(
        database_session.scalars(
            select(WardrobePhoto).where(WardrobePhoto.user_id == user_id).order_by(WardrobePhoto.id)
        ).all()
    )


def add_photos(database_session: Session, user_id: int, image_keys: list[str], embeddings: list[list[float]]) -> None:
    """INSERT 후 flush. commit 은 요청 트랜잭션(get_database_session)이 한다."""
    database_session.add_all(
        WardrobePhoto(user_id=user_id, image_key=image_key, embedding=embedding)
        for image_key, embedding in zip(image_keys, embeddings, strict=True)
    )
    database_session.flush()
