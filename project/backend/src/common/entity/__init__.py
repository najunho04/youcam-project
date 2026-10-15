"""SQLAlchemy 모델. 스키마 원본은 project-all-docs/erd.md. 응답으로 직접 내보내지 않는다 (DTO 경유)."""
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, BigInteger, Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from common.enums import AgeGroup, Category, EmbeddingDomain, FittingStatus, Gender, Season, Style

EMBEDDING_DIMENSION = 512
WARDROBE_PHOTO_LIMIT = 4


def _enum_column(enum_class):
    # DB enum 타입 대신 varchar 로 저장 (erd.md: 마이그레이션 단순화)
    return Enum(enum_class, native_enum=False, length=20, validate_strings=True)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nickname: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    age_group: Mapped[AgeGroup | None] = mapped_column(_enum_column(AgeGroup), nullable=True)
    gender: Mapped[Gender | None] = mapped_column(_enum_column(Gender), nullable=True)
    season: Mapped[Season | None] = mapped_column(_enum_column(Season), nullable=True)
    selfie_key: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 얼굴 사진 (피부톤 분석)
    body_image_key: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 상반신 사진 (가상 피팅 원본)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (Index("ix_products_filter", "gender", "age_group", "category"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    naver_product_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    mall_name: Mapped[str] = mapped_column(String(100), nullable=False)
    purchase_url: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    gender: Mapped[Gender] = mapped_column(_enum_column(Gender), nullable=False)
    age_group: Mapped[AgeGroup] = mapped_column(_enum_column(AgeGroup), nullable=False)
    style: Mapped[Style] = mapped_column(_enum_column(Style), nullable=False)
    category: Mapped[Category] = mapped_column(_enum_column(Category), nullable=False)
    color_lab: Mapped[list[float]] = mapped_column(ARRAY(Float), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class Pin(Base):
    """스와이프 카드용 코디 사진 (Pinterest). 이미지는 저장하지 않고 원본 URL 과 임베딩만 둔다."""
    __tablename__ = "pins"
    __table_args__ = (Index("ix_pins_filter", "gender", "age_group"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    image_url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    gender: Mapped[Gender] = mapped_column(_enum_column(Gender), nullable=False)
    age_group: Mapped[AgeGroup] = mapped_column(_enum_column(AgeGroup), nullable=False)
    style: Mapped[Style] = mapped_column(_enum_column(Style), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class EmbeddingCentroid(Base):
    """출처별 임베딩 평균. 적재할 때 계산해 둔다 (추천은 읽기만)."""
    __tablename__ = "embedding_centroids"

    domain: Mapped[EmbeddingDomain] = mapped_column(_enum_column(EmbeddingDomain), primary_key=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class Swipe(Base):
    __tablename__ = "swipes"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    pin_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("pins.id", ondelete="CASCADE"), primary_key=True)
    liked: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class WardrobePhoto(Base):
    __tablename__ = "wardrobe_photos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    image_key: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Fitting(Base):
    __tablename__ = "fittings"
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_fittings_user_product"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[FittingStatus] = mapped_column(_enum_column(FittingStatus), nullable=False)
    result_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
