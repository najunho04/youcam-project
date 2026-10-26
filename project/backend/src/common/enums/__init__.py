from enum import StrEnum


class AgeGroup(StrEnum):
    LATE_TEENS = "LATE_TEENS"
    TWENTIES = "TWENTIES"
    THIRTIES = "THIRTIES"
    FORTIES_PLUS = "FORTIES_PLUS"


class Gender(StrEnum):
    FEMALE = "FEMALE"
    MALE = "MALE"


class Season(StrEnum):
    SPRING_WARM = "SPRING_WARM"
    SUMMER_COOL = "SUMMER_COOL"
    AUTUMN_WARM = "AUTUMN_WARM"
    WINTER_COOL = "WINTER_COOL"


class SeasonSubtype(StrEnum):
    """퍼스널컬러 12유형의 세부 유형. 시즌마다 3개만 유효하다 (shared.color.SEASON_SUBTYPES)."""
    TRUE = "TRUE"
    LIGHT = "LIGHT"
    DEEP = "DEEP"
    BRIGHT = "BRIGHT"
    SOFT = "SOFT"


class Style(StrEnum):
    MINIMAL = "MINIMAL"
    CASUAL = "CASUAL"
    STREET = "STREET"
    FORMAL = "FORMAL"
    LOVELY = "LOVELY"


class Category(StrEnum):
    TOP = "TOP"


class ProductSource(StrEnum):
    """상품 출처. NAVER 는 한국어 UI용 (최후순위)."""
    EBAY = "EBAY"
    NAVER = "NAVER"


class FittingStatus(StrEnum):
    PENDING = "PENDING"
    DONE = "DONE"
    FAILED = "FAILED"


class EmbeddingDomain(StrEnum):
    """평균 벡터를 따로 두는 임베딩 출처. 핀(코디 사진)과 상품(상품컷)은 사진 종류가 달라 각자 평균을 뺀 뒤 비교한다."""
    PIN = "PIN"
    PRODUCT = "PRODUCT"
