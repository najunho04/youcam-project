"""색 변환 (sRGB hex ↔ CIE Lab, D65) 과 시즌별 팔레트."""
import math

from common.enums import Season

# 시즌별 대표 팔레트. 추천 컬러 점수와 결과 화면에 쓴다. (기획 조정 대상)
SEASON_PALETTES: dict[Season, list[str]] = {
    Season.SPRING_WARM: ["#FF7F50", "#FFB38A", "#FFD966", "#E3B778", "#FFF5DC", "#A8D08D", "#40C4B0", "#FA8072"],
    Season.SUMMER_COOL: ["#B7A8D8", "#B0C4DE", "#E8A0B4", "#A9A9B0", "#A8E0D0", "#87CEEB", "#C8A2C8", "#4A5D8A"],
    Season.AUTUMN_WARM: ["#C19A6B", "#D8C3A5", "#8F8650", "#6B6B30", "#A0522D", "#D4A017", "#6D2E2E", "#C8643C"],
    Season.WINTER_COOL: ["#111111", "#FFFFFF", "#1F2A55", "#2952C8", "#C2185B", "#800020", "#3A3A3A", "#F2D7E6"],
}

LabColor = tuple[float, float, float]


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


def palette_lab(season: Season) -> list[LabColor]:
    return [hex_to_lab(hex_color) for hex_color in SEASON_PALETTES[season]]
