"""personal_color 슬라이스 비즈니스 로직. 실패는 AppError 로만 알린다."""
from fastapi import UploadFile
from sqlalchemy.orm import Session

from common.dto import PersonalColorDto
from common.entity import User
from common.enums import Season
from feature.personal_color import repository
from shared.color import SEASON_PALETTES, hex_to_lab
from shared.image import read_upload_image
from shared.storage import get_storage, new_object_key
from shared.youcam import get_youcam_client

_SELFIE_KEY_PREFIX = "selfies"
_BODY_IMAGE_KEY_PREFIX = "body-images"

# 피부색 Lab 2축 판정 기준값. b* 이상이면 웜, L* 이상이면 밝음 (기획 조정 대상)
WARM_YELLOW_BLUE_THRESHOLD = 18
BRIGHT_LIGHTNESS_THRESHOLD = 70


def determine_season(skin_color_hex: str) -> Season:
    lightness, _, yellow_blue = hex_to_lab(skin_color_hex)
    is_warm = yellow_blue >= WARM_YELLOW_BLUE_THRESHOLD
    is_bright = lightness >= BRIGHT_LIGHTNESS_THRESHOLD
    if is_bright:
        return Season.SPRING_WARM if is_warm else Season.SUMMER_COOL
    return Season.AUTUMN_WARM if is_warm else Season.WINTER_COOL


def analyze_personal_color(
    database_session: Session, user: User, selfie_file: UploadFile, body_image_file: UploadFile
) -> PersonalColorDto:
    """검증 → 두 사진 업로드 → 얼굴 사진 피부톤 분석 → 시즌 판정 → 저장·이전 사진 삭제·피팅 무효화.
    실패하면 이번에 올린 파일만 지우고 users·fittings·기존 파일은 그대로 둔다."""
    selfie_image = read_upload_image(selfie_file)
    body_image = read_upload_image(body_image_file)

    storage = get_storage()
    previous_keys = [key for key in (user.selfie_key, user.body_image_key) if key is not None]
    uploaded_keys: list[str] = []
    try:
        selfie_key = new_object_key(_SELFIE_KEY_PREFIX, user.id, selfie_image.extension)
        storage.upload(selfie_key, selfie_image.data, selfie_image.content_type)
        uploaded_keys.append(selfie_key)
        body_image_key = new_object_key(_BODY_IMAGE_KEY_PREFIX, user.id, body_image.extension)
        storage.upload(body_image_key, body_image.data, body_image.content_type)
        uploaded_keys.append(body_image_key)

        skin_tone = get_youcam_client().analyze_skin_tone(storage.get_url(selfie_key))
        season = determine_season(skin_tone.skin_color_hex)

        repository.update_personal_color(database_session, user, season, selfie_key, body_image_key)
        repository.delete_fittings_by_user(database_session, user.id)
    except Exception:
        for uploaded_key in uploaded_keys:
            storage.delete(uploaded_key)
        raise

    for previous_key in previous_keys:
        storage.delete(previous_key)

    return PersonalColorDto(
        season=season,
        palette=SEASON_PALETTES[season],
        selfie_url=storage.get_url(selfie_key),
        body_image_url=storage.get_url(body_image_key),
    )
