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
