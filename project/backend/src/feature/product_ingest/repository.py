"""product_ingest 슬라이스 DB 접근. products 와 embedding_centroids(PRODUCT 행)만 쓴다 (상품은 삭제하지 않는다)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from common.entity import EmbeddingCentroid, Product
from common.enums import EmbeddingDomain, ProductSource


def find_product(database_session: Session, source: ProductSource, external_id: str) -> Product | None:
    return database_session.scalars(
        select(Product).where(Product.source == source, Product.external_id == external_id)
    ).one_or_none()


def upsert_product(database_session: Session, source: ProductSource, external_id: str, **columns) -> Product:
    """(source, external_id) 기준으로 있으면 갱신(updated_at 포함), 없으면 삽입. flush 까지만 한다."""
    product = find_product(database_session, source, external_id)
    if product is None:
        product = Product(source=source, external_id=external_id, **columns)
        database_session.add(product)
    else:
        for column_name, value in columns.items():
            setattr(product, column_name, value)
        product.updated_at = func.now()
    database_session.flush()
    return product


def find_all_product_embeddings(database_session: Session) -> list[list[float]]:
    return [list(embedding) for embedding in database_session.scalars(select(Product.embedding))]


def upsert_product_centroid(database_session: Session, embedding: list[float]) -> None:
    centroid = database_session.get(EmbeddingCentroid, EmbeddingDomain.PRODUCT)
    if centroid is None:
        database_session.add(EmbeddingCentroid(domain=EmbeddingDomain.PRODUCT, embedding=embedding))
    else:
        centroid.embedding = embedding
        centroid.updated_at = func.now()
    database_session.flush()
