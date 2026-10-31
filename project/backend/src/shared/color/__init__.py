"""색 변환 (sRGB hex ↔ CIE Lab, D65), 퍼스널컬러 12유형 판정, 유형별 팔레트."""
import math
from dataclasses import dataclass

from common.dto import FaceColorsDto, PersonalColorAnalysisDto
from common.enums import Season, SeasonSubtype

LabColor = tuple[float, float, float]

# 시즌마다 유효한 세부 유형. 순서는 점수가 같을 때의 우선순위
SEASON_SUBTYPES: dict[Season, tuple[SeasonSubtype, SeasonSubtype, SeasonSubtype]] = {
    Season.SPRING_WARM: (SeasonSubtype.TRUE, SeasonSubtype.LIGHT, SeasonSubtype.BRIGHT),
    Season.SUMMER_COOL: (SeasonSubtype.TRUE, SeasonSubtype.LIGHT, SeasonSubtype.SOFT),
    Season.AUTUMN_WARM: (SeasonSubtype.TRUE, SeasonSubtype.DEEP, SeasonSubtype.SOFT),
    Season.WINTER_COOL: (SeasonSubtype.TRUE, SeasonSubtype.DEEP, SeasonSubtype.BRIGHT),
}

# 12유형별 어울리는 색 8개. 추천 컬러 점수와 결과 화면에 쓴다. (기획 조정 대상)
SUBTYPE_PALETTES: dict[tuple[Season, SeasonSubtype], list[str]] = {
    (Season.SPRING_WARM, SeasonSubtype.TRUE): ["#FF7F50", "#FFB38A", "#FFD966", "#E3B778", "#FFF5DC", "#A8D08D", "#40C4B0", "#FA8072"],
    (Season.SPRING_WARM, SeasonSubtype.LIGHT): ["#FFD3B5", "#FFF1A8", "#F7A399", "#BDE8C8", "#A8E6E2", "#FFF8E7", "#E8C9A0", "#B5C7F0"],
    (Season.SPRING_WARM, SeasonSubtype.BRIGHT): ["#FF5A4E", "#F23C2E", "#FFC21A", "#2DBE60", "#00B5AD", "#00C2E0", "#FF6F91", "#2D4E9E"],
    (Season.SUMMER_COOL, SeasonSubtype.TRUE): ["#B7A8D8", "#B0C4DE", "#E8A0B4", "#A9A9B0", "#A8E0D0", "#87CEEB", "#C8A2C8", "#4A5D8A"],
    (Season.SUMMER_COOL, SeasonSubtype.LIGHT): ["#C6DDF0", "#D9CCF0", "#F6C6D6", "#D3D6DB", "#CDEDE4", "#A9D4F2", "#E0C6E6", "#F7F5F7"],
    (Season.SUMMER_COOL, SeasonSubtype.SOFT): ["#C9A0A8", "#A88C9C", "#7088A3", "#9A9CA3", "#A3B5A6", "#4B5A75", "#A39A96", "#A9A3BF"],
    (Season.AUTUMN_WARM, SeasonSubtype.TRUE): ["#C19A6B", "#D8C3A5", "#8F8650", "#6B6B30", "#A0522D", "#D4A017", "#6D2E2E", "#C8643C"],
    (Season.AUTUMN_WARM, SeasonSubtype.DEEP): ["#4E3020", "#4B4A24", "#6D1F24", "#8B3A1E", "#1F4E4A", "#B88A1A", "#2F4A2A", "#3B2A20"],
    (Season.AUTUMN_WARM, SeasonSubtype.SOFT): ["#C8AD8A", "#9CA88A", "#B5A882", "#D9A88C", "#6E9A94", "#A08C7A", "#B9A799", "#8A8A64"],
    (Season.WINTER_COOL, SeasonSubtype.TRUE): ["#111111", "#FFFFFF", "#1F2A55", "#2952C8", "#C2185B", "#800020", "#3A3A3A", "#F2D7E6"],
    (Season.WINTER_COOL, SeasonSubtype.DEEP): ["#111111", "#2E2E33", "#141E3C", "#5C0A1E", "#0B5D45", "#4A1942", "#1D3B33", "#FFFFFF"],
    (Season.WINTER_COOL, SeasonSubtype.BRIGHT): ["#FFFFFF", "#000000", "#1F4BFF", "#E0218A", "#D2042D", "#00A86B", "#F7D1E6", "#6A1BD1"],
}

# 시즌별 피해야 할 색 6개. 결과 화면 표시 + 추천 컬러 점수 감점. (기획 조정 대상)
AVOID_PALETTES: dict[Season, list[str]] = {
    Season.SPRING_WARM: ["#111111", "#3A3A3A", "#5C0A1E", "#141E3C", "#C9CED6", "#A88C9C"],
    Season.SUMMER_COOL: ["#FF7A00", "#D4A017", "#A0522D", "#6B6B30", "#111111", "#C19A6B"],
    Season.AUTUMN_WARM: ["#F7D1E6", "#E0218A", "#1F4BFF", "#FFFFFF", "#C8A2C8", "#C0C0C8"],
    Season.WINTER_COOL: ["#FFB38A", "#C19A6B", "#D4A017", "#FF7A00", "#D8C3A5", "#8F8650"],
}

# 판정 축 기준값 (0 이 경계가 되도록 기준점을 빼고 스케일로 나눈다). 기획 조정 대상
SKIN_HUE_REFERENCE, SKIN_HUE_SCALE = 58.0, 10.0  # 피부 색상각(도). 클수록 노란 쪽 = 웜
LIP_HUE_REFERENCE, LIP_HUE_SCALE = 25.0, 20.0  # 입술 색상각(도). 클수록 코랄 쪽 = 웜
SKIN_LIGHTNESS_REFERENCE, SKIN_LIGHTNESS_SCALE = 72.0, 8.0  # 피부 L*. 낮을수록 딥
CONTRAST_REFERENCE, CONTRAST_SCALE = 50.0, 15.0  # 피부와 가장 어두운 머리·눈썹·눈의 L* 차이. 클수록 딥
SKIN_CHROMA_REFERENCE, SKIN_CHROMA_SCALE = 20.0, 5.0  # 피부 채도. 클수록 선명
LIP_CHROMA_REFERENCE, LIP_CHROMA_SCALE = 45.0, 12.0  # 입술 채도. 클수록 선명
SKIN_HUE_WEIGHT, LIP_HUE_WEIGHT = 0.7, 0.3
SKIN_LIGHTNESS_WEIGHT, CONTRAST_WEIGHT = 0.5, 0.5
SKIN_CHROMA_WEIGHT, LIP_CHROMA_WEIGHT = 0.6, 0.4
ANALYSIS_DECIMAL_PLACES = 2


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    if len(value) != 6:
        raise ValueError(f"invalid hex color: {hex_color}")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def rgb_to_lab(red: int, green: int, blue: int) -> LabColor:
    def to_linear(channel: int) -> float:
        normalized = channel / 255
        return normalized / 12.92 if normalized <= 0.04045 else ((normalized + 0.055) / 1.055) ** 2.4

    linear_red, linear_green, linear_blue = to_linear(red), to_linear(green), to_linear(blue)
    x = (linear_red * 0.4124 + linear_green * 0.3576 + linear_blue * 0.1805) / 0.95047
    y = linear_red * 0.2126 + linear_green * 0.7152 + linear_blue * 0.0722
    z = (linear_red * 0.0193 + linear_green * 0.1192 + linear_blue * 0.9505) / 1.08883

    def pivot(value: float) -> float:
        return value ** (1 / 3) if value > 0.008856 else 7.787 * value + 16 / 116

    pivot_x, pivot_y, pivot_z = pivot(x), pivot(y), pivot(z)
    return 116 * pivot_y - 16, 500 * (pivot_x - pivot_y), 200 * (pivot_y - pivot_z)


def hex_to_lab(hex_color: str) -> LabColor:
    return rgb_to_lab(*hex_to_rgb(hex_color))


def delta_e(first: LabColor, second: LabColor) -> float:
    """CIE76 색차."""
    return math.dist(first, second)


def hue_angle(color: LabColor) -> float:
    """색상각 h = atan2(b*, a*), 도 단위."""
    return math.degrees(math.atan2(color[2], color[1]))


def chroma(color: LabColor) -> float:
    """채도 C = √(a*² + b*²)."""
    return math.hypot(color[1], color[2])


def palette_lab(season: Season, subtype: SeasonSubtype) -> list[LabColor]:
    return [hex_to_lab(hex_color) for hex_color in SUBTYPE_PALETTES[(season, subtype)]]


def avoid_palette_lab(season: Season) -> list[LabColor]:
    return [hex_to_lab(hex_color) for hex_color in AVOID_PALETTES[season]]


@dataclass(frozen=True)
class PersonalColorJudgment:
    season: Season
    subtype: SeasonSubtype
    analysis: PersonalColorAnalysisDto


def _season_of(warmth: float, depth: float) -> Season:
    is_warm, is_deep = warmth >= 0, depth >= 0
    if is_deep:
        return Season.AUTUMN_WARM if is_warm else Season.WINTER_COOL
    return Season.SPRING_WARM if is_warm else Season.SUMMER_COOL


def _subtype_of(season: Season, warmth: float, depth: float, clarity: float) -> SeasonSubtype:
    """시즌 후보 3개 중 점수 최댓값. 같으면 SEASON_SUBTYPES 순서가 앞인 것 (max 는 처음 만난 최댓값을 고른다)."""
    scores = {
        SeasonSubtype.TRUE: abs(warmth),
        SeasonSubtype.LIGHT: -depth,
        SeasonSubtype.DEEP: depth,
        SeasonSubtype.BRIGHT: clarity,
        SeasonSubtype.SOFT: -clarity,
    }
    return max(SEASON_SUBTYPES[season], key=lambda subtype: scores[subtype])


def judge_personal_color(face_colors: FaceColorsDto) -> PersonalColorJudgment:
    """얼굴 색 5개 → 3축(웜/쿨·명도·선명도) → 시즌 + 세부 유형. 판정은 반올림 전 값으로 한다."""
    skin, lip = hex_to_lab(face_colors.skin), hex_to_lab(face_colors.lip)
    darkest_feature_lightness = min(
        hex_to_lab(face_colors.hair)[0], hex_to_lab(face_colors.eyebrow)[0], hex_to_lab(face_colors.eye)[0]
    )
    skin_lightness = skin[0]
    contrast = skin_lightness - darkest_feature_lightness

    warmth = (
        SKIN_HUE_WEIGHT * (hue_angle(skin) - SKIN_HUE_REFERENCE) / SKIN_HUE_SCALE
        + LIP_HUE_WEIGHT * (hue_angle(lip) - LIP_HUE_REFERENCE) / LIP_HUE_SCALE
    )
    depth = (
        SKIN_LIGHTNESS_WEIGHT * (SKIN_LIGHTNESS_REFERENCE - skin_lightness) / SKIN_LIGHTNESS_SCALE
        + CONTRAST_WEIGHT * (contrast - CONTRAST_REFERENCE) / CONTRAST_SCALE
    )
    clarity = (
        SKIN_CHROMA_WEIGHT * (chroma(skin) - SKIN_CHROMA_REFERENCE) / SKIN_CHROMA_SCALE
        + LIP_CHROMA_WEIGHT * (chroma(lip) - LIP_CHROMA_REFERENCE) / LIP_CHROMA_SCALE
    )

    season = _season_of(warmth, depth)
    analysis = PersonalColorAnalysisDto(
        face_colors=face_colors,
        warmth=round(warmth, ANALYSIS_DECIMAL_PLACES),
        depth=round(depth, ANALYSIS_DECIMAL_PLACES),
        clarity=round(clarity, ANALYSIS_DECIMAL_PLACES),
        skin_lightness=round(skin_lightness, ANALYSIS_DECIMAL_PLACES),
        contrast=round(contrast, ANALYSIS_DECIMAL_PLACES),
    )
    return PersonalColorJudgment(
        season=season, subtype=_subtype_of(season, warmth, depth, clarity), analysis=analysis
    )
