"""fitting 슬라이스 DB 접근. fittings 만 쓰고, products 는 읽기만 한다."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from common.entity import Fitting, Product
from common.enums import FittingStatus


def find_product(database_session: Session, product_id: int) -> Product | None:
    return database_session.get(Product, product_id)


def find_fitting(database_session: Session, fitting_id: int) -> Fitting | None:
    return database_session.get(Fitting, fitting_id)


def lock_fitting(database_session: Session, fitting_id: int) -> Fitting | None:
    """행 잠금(SELECT ... FOR UPDATE) 후 최신 값으로 읽는다. 없으면 None."""
    return database_session.scalars(
        select(Fitting).where(Fitting.id == fitting_id).with_for_update().execution_options(populate_existing=True)
    ).one_or_none()


def lock_fitting_by_user_and_product(database_session: Session, user_id: int, product_id: int) -> Fitting | None:
    return database_session.scalars(
        select(Fitting)
        .where(Fitting.user_id == user_id, Fitting.product_id == product_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one_or_none()


def add_pending_fitting(database_session: Session, user_id: int, product_id: int, started_at: datetime) -> Fitting | None:
    """PENDING 행 INSERT. 동시 요청이 먼저 만들어 (user_id, product_id) UNIQUE 위반이면 None."""
    fitting = Fitting(user_id=user_id, product_id=product_id, status=FittingStatus.PENDING, created_at=started_at)
    try:
        with database_session.begin_nested():
            database_session.add(fitting)
            database_session.flush()
    except IntegrityError:
        return None
    return fitting


def restart_fitting(database_session: Session, fitting: Fitting, started_at: datetime) -> Fitting:
    """id 를 유지한 채 PENDING 으로 되돌린다. created_at = 마지막으로 작업을 시작한 시각."""
    fitting.status = FittingStatus.PENDING
    fitting.result_key = None
    fitting.created_at = started_at
    database_session.flush()
    return fitting


def complete_fitting(database_session: Session, fitting: Fitting, result_key: str) -> None:
    fitting.status = FittingStatus.DONE
    fitting.result_key = result_key
    database_session.flush()


def fail_fitting(database_session: Session, fitting: Fitting) -> None:
    fitting.status = FittingStatus.FAILED
    fitting.result_key = None
    database_session.flush()
