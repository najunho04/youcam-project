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


class Style(StrEnum):
    MINIMAL = "MINIMAL"
    CASUAL = "CASUAL"
    STREET = "STREET"
    FORMAL = "FORMAL"
    LOVELY = "LOVELY"


class Category(StrEnum):
    TOP = "TOP"


class FittingStatus(StrEnum):
    PENDING = "PENDING"
    DONE = "DONE"
    FAILED = "FAILED"


class EmbeddingDomain(StrEnum):
    """평균 벡터를 따로 두는 임베딩 출처. 핀(코디 사진)과 상품(상품컷)은 사진 종류가 달라 각자 평균을 뺀 뒤 비교한다."""
    PIN = "PIN"
    PRODUCT = "PRODUCT"
