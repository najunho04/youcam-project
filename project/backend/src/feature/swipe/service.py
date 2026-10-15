"""swipe 슬라이스 비즈니스 로직. 실패는 AppError 로만 알린다. 무작위 선택은 난수 생성기를 주입받는다."""
import random
from collections import defaultdict

from sqlalchemy.orm import Session

from common.dto import SwipeAnswersRequest, SwipeAnswersResponse, SwipeCardDto, SwipeCardsResponse
from common.entity import Pin, User
from common.enums import Gender, Style
from common.error import AppError, ErrorCode
from feature.swipe import repository


# 남자 핀은 러블리를 빼고 포멀을 미니멀에 합쳐 적재했다 (Pinterest 남성 결과 부족)
SWIPE_STYLES_BY_GENDER: dict[Gender, list[Style]] = {
    Gender.FEMALE: list(Style),
    Gender.MALE: [Style.MINIMAL, Style.CASUAL, Style.STREET],
}


def allocate_style_quotas(
    count: int, random_generator: random.Random, styles: list[Style] | None = None
) -> dict[Style, int]:
    """스타일별 몫 = count // 스타일 수. 나머지 장은 무작위로 고른 서로 다른 스타일에 1장씩 더한다."""
    styles = styles or list(Style)
    base_share, remainder = divmod(count, len(styles))
    quotas = dict.fromkeys(styles, base_share)
    for style in random_generator.sample(styles, remainder):
        quotas[style] += 1
    return quotas


def get_swipe_cards(
    database_session: Session, user: User, count: int, random_generator: random.Random | None = None
) -> SwipeCardsResponse:
    """스타일별로 몫과 후보 수 중 작은 만큼 무작위로 담고 순서를 섞는다. 부족한 스타일을 다른 스타일로 채우지 않는다."""
    if user.age_group is None or user.gender is None:
        raise AppError(ErrorCode.PROFILE_REQUIRED, "나이대와 성별을 먼저 입력해 주세요")
    random_generator = random_generator or random.Random()

    candidates_by_style: dict[Style, list[Pin]] = defaultdict(list)
    for pin in repository.find_unswiped_pins(database_session, user.id, user.gender, user.age_group):
        candidates_by_style[pin.style].append(pin)

    selected_pins: list[Pin] = []
    for style, quota in allocate_style_quotas(count, random_generator, SWIPE_STYLES_BY_GENDER[user.gender]).items():
        candidates = candidates_by_style[style]
        selected_pins.extend(random_generator.sample(candidates, min(quota, len(candidates))))
    random_generator.shuffle(selected_pins)

    return SwipeCardsResponse(
        cards=[SwipeCardDto(pin_id=pin.id, image_url=pin.image_url, style=pin.style) for pin in selected_pins]
    )


def submit_swipe_answers(database_session: Session, user: User, request: SwipeAnswersRequest) -> SwipeAnswersResponse:
    """없는 핀이 하나라도 있으면 전체 거부. 같은 pinId 는 마지막 값으로 upsert."""
    liked_by_pin_id = {answer.pin_id: answer.liked for answer in request.answers}
    missing_pin_ids = set(liked_by_pin_id) - repository.find_existing_pin_ids(database_session, set(liked_by_pin_id))
    if missing_pin_ids:
        raise AppError(ErrorCode.PIN_NOT_FOUND, f"없는 코디입니다: {sorted(missing_pin_ids)}")

    repository.upsert_swipes(database_session, user.id, liked_by_pin_id)
    liked_count, total_count = repository.count_swipes_by_user(database_session, user.id)
    return SwipeAnswersResponse(liked_count=liked_count, total_count=total_count)
