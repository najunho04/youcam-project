"""shared.color.judge_personal_color — personal_color 카드의 판정 예시 그대로."""
import pytest

from common.dto import FaceColorsDto
from common.enums import Season, SeasonSubtype
from shared.color import AVOID_PALETTES, SEASON_SUBTYPES, SUBTYPE_PALETTES, judge_personal_color


def face_colors_of(skin: str, lip: str, eye: str, eyebrow: str, hair: str) -> FaceColorsDto:
    return FaceColorsDto(
        skin=skin, lip=lip, eye=eye, eyebrow=eyebrow, hair=hair, eye_color_name=None, hair_color_name=None
    )


@pytest.mark.parametrize(
    ("colors", "expected_season", "expected_subtype", "expected_axes"),
    [
        (("#F6DCC2", "#E8907A", "#8A6A4A", "#A08060", "#B08A60"), Season.SPRING_WARM, SeasonSubtype.LIGHT, (1.26, -1.34, -0.54)),
        (("#F2D3B1", "#E07A5F", "#6B4A2B", "#7A5A3A", "#8B6A45"), Season.SPRING_WARM, SeasonSubtype.TRUE, (1.39, -0.83, 0.33)),
        (("#D8C0B8", "#B88890", "#5A5048", "#6A605A", "#5A524C"), Season.SUMMER_COOL, SeasonSubtype.SOFT, (-1.17, -0.64, -2.03)),
        (("#B07B4F", "#B5553A", "#3B2414", "#3A2618", "#2E1C10"), Season.AUTUMN_WARM, SeasonSubtype.DEEP, (0.68, 0.79, 2.06)),
        (("#E3C0A6", "#C8646E", "#3A2A22", "#3B2E28", "#231C19"), Season.AUTUMN_WARM, SeasonSubtype.TRUE, (0.32, 0.13, -0.11)),
        (("#C9A79A", "#A8354F", "#1E1714", "#1A1514", "#141212"), Season.WINTER_COOL, SeasonSubtype.TRUE, (-0.92, 0.57, -0.38)),
    ],
)
def test_judgment_matches_card_examples(colors, expected_season, expected_subtype, expected_axes):
    judgment = judge_personal_color(face_colors_of(*colors))

    assert (judgment.season, judgment.subtype) == (expected_season, expected_subtype)
    assert (judgment.analysis.warmth, judgment.analysis.depth, judgment.analysis.clarity) == expected_axes


def test_analysis_keeps_face_colors_and_rounds_to_two_decimals():
    face_colors = face_colors_of("#E3C0A6", "#C8646E", "#3A2A22", "#3B2E28", "#231C19")

    analysis = judge_personal_color(face_colors).analysis

    assert analysis.face_colors == face_colors
    for value in (analysis.warmth, analysis.depth, analysis.clarity, analysis.skin_lightness, analysis.contrast):
        assert round(value, 2) == value


def test_every_valid_subtype_has_palettes():
    for season, subtypes in SEASON_SUBTYPES.items():
        assert len(AVOID_PALETTES[season]) == 6
        for subtype in subtypes:
            assert len(SUBTYPE_PALETTES[(season, subtype)]) == 8
    assert len(SUBTYPE_PALETTES) == 12
