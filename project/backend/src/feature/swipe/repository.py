"""swipe 슬라이스 DB 접근. swipes 테이블만 쓴다. pins·users 는 읽기만."""
from sqlalchemy import exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from common.entity import Pin, Swipe
from common.enums import AgeGroup, Gender


def find_unswiped_pins(database_session: Session, user_id: int, gender: Gender, age_group: AgeGroup) -> list[Pin]:
    """성별·나이대 일치, 이 사용자가 아직 스와이프하지 않은 핀. id 순."""
    already_swiped = exists().where(Swipe.user_id == user_id, Swipe.pin_id == Pin.id)
    return list(
        database_session.scalars(
            select(Pin)
            .where(Pin.gender == gender, Pin.age_group == age_group, ~already_swiped)
            .order_by(Pin.id)
        ).all()
    )


def find_existing_pin_ids(database_session: Session, pin_ids: set[int]) -> set[int]:
    return set(database_session.scalars(select(Pin.id).where(Pin.id.in_(pin_ids))).all())


def upsert_swipes(database_session: Session, user_id: int, liked_by_pin_id: dict[int, bool]) -> None:
    """(user_id, pin_id) 충돌 시 liked 덮어씀. commit 은 요청 트랜잭션(get_database_session)이 한다."""
    statement = insert(Swipe).values(
        [{"user_id": user_id, "pin_id": pin_id, "liked": liked} for pin_id, liked in liked_by_pin_id.items()]
    )
    database_session.execute(
        statement.on_conflict_do_update(
            index_elements=[Swipe.user_id, Swipe.pin_id], set_={"liked": statement.excluded.liked}
        )
    )


def count_swipes_by_user(database_session: Session, user_id: int) -> tuple[int, int]:
    """(좋아요 수, 전체 수)."""
    liked_count, total_count = database_session.execute(
        select(func.count().filter(Swipe.liked), func.count()).where(Swipe.user_id == user_id)
    ).one()
    return liked_count, total_count
