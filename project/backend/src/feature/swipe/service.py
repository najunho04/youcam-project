"""swipe 슬라이스 비즈니스 로직. 실패는 AppError 로만 알린다. 무작위 선택은 난수 생성기를 주입받는다."""
import random
from collections import defaultdict

from sqlalchemy.orm import Session

from common.dto import SwipeAnswersRequest, SwipeAnswersResponse, SwipeCardDto, SwipeCardsResponse
from common.entity import Product, User
from common.enums import Style
from common.error import AppError, ErrorCode
from feature.swipe import repository


def allocate_style_quotas(count: int, random_generator: random.Random) -> dict[Style, int]:
    """스타일별 몫 = count // 5. 나머지 count % 5 장은 무작위로 고른 서로 다른 스타일에 1장씩 더한다."""
    styles = list(Style)
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

    candidates_by_style: dict[Style, list[Product]] = defaultdict(list)
    for product in repository.find_unswiped_top_products(database_session, user.id, user.gender, user.age_group):
        candidates_by_style[product.style].append(product)

    selected_products: list[Product] = []
    for style, quota in allocate_style_quotas(count, random_generator).items():
        candidates = candidates_by_style[style]
        selected_products.extend(random_generator.sample(candidates, min(quota, len(candidates))))
    random_generator.shuffle(selected_products)

    return SwipeCardsResponse(
        cards=[
            SwipeCardDto(product_id=product.id, image_url=product.image_url, style=product.style)
            for product in selected_products
        ]
    )


def submit_swipe_answers(database_session: Session, user: User, request: SwipeAnswersRequest) -> SwipeAnswersResponse:
    """없는 상품이 하나라도 있으면 전체 거부. 같은 productId 는 마지막 값으로 upsert."""
    liked_by_product_id = {answer.product_id: answer.liked for answer in request.answers}
    missing_product_ids = set(liked_by_product_id) - repository.find_existing_product_ids(
        database_session, set(liked_by_product_id)
    )
    if missing_product_ids:
        raise AppError(ErrorCode.PRODUCT_NOT_FOUND, f"없는 상품입니다: {sorted(missing_product_ids)}")

    repository.upsert_swipes(database_session, user.id, liked_by_product_id)
    liked_count, total_count = repository.count_swipes_by_user(database_session, user.id)
    return SwipeAnswersResponse(liked_count=liked_count, total_count=total_count)
