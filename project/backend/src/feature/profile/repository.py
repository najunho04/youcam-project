"""profile 슬라이스 DB 접근. users 테이블은 age_group·gender 만 쓴다."""
from sqlalchemy.orm import Session

from common.entity import User
from common.enums import AgeGroup, Gender


def update_age_group_and_gender(database_session: Session, user: User, age_group: AgeGroup, gender: Gender) -> User:
    user.age_group = age_group
    user.gender = gender
    database_session.flush()
    return user
