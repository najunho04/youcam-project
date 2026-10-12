"""auth 슬라이스 DB 접근. users 테이블은 nickname·password_hash 만 쓴다."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from common.entity import User


def find_user_by_nickname(database_session: Session, nickname: str) -> User | None:
    return database_session.scalars(select(User).where(User.nickname == nickname)).one_or_none()


def add_user(database_session: Session, nickname: str, password_hash: str) -> User:
    """INSERT 후 flush 해 id 를 채운다. 닉네임 UNIQUE 위반 시 IntegrityError."""
    user = User(nickname=nickname, password_hash=password_hash)
    database_session.add(user)
    database_session.flush()
    return user
