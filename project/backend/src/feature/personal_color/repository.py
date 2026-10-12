"""personal_color 슬라이스 DB 접근. users 테이블은 season·selfie_key·body_image_key 만 쓰고, fittings 는 사용자 행 삭제만 한다."""
from sqlalchemy import delete
from sqlalchemy.orm import Session

from common.entity import Fitting, User
from common.enums import Season


def update_personal_color(
    database_session: Session, user: User, season: Season, selfie_key: str, body_image_key: str
) -> User:
    user.season = season
    user.selfie_key = selfie_key
    user.body_image_key = body_image_key
    database_session.flush()
    return user


def delete_fittings_by_user(database_session: Session, user_id: int) -> None:
    """사진이 바뀌면 피팅 결과가 무효가 되므로 해당 사용자의 행을 모두 지운다."""
    database_session.execute(delete(Fitting).where(Fitting.user_id == user_id))
    database_session.flush()
