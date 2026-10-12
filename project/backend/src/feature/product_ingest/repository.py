"""product_ingest 슬라이스 DB 접근. products 테이블만 쓴다 (삭제하지 않는다)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from common.entity import Product


def find_product_by_naver_product_id(database_session: Session, naver_product_id: str) -> Product | None:
    return database_session.scalars(
        select(Product).where(Product.naver_product_id == naver_product_id)
    ).one_or_none()


def upsert_product(database_session: Session, naver_product_id: str, **columns) -> Product:
    """naver_product_id 기준으로 있으면 갱신(updated_at 포함), 없으면 삽입. flush 까지만 한다."""
    product = find_product_by_naver_product_id(database_session, naver_product_id)
    if product is None:
        product = Product(naver_product_id=naver_product_id, **columns)
        database_session.add(product)
    else:
        for column_name, value in columns.items():
            setattr(product, column_name, value)
        product.updated_at = func.now()
    database_session.flush()
    return product
