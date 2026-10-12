"""swipe service 단위 테스트. 무작위 선택은 난수 생성기를 주입해 결과를 고정한다."""
import random
from collections import Counter

import pytest
from sqlalchemy import select

from common.dto import SwipeAnswer, SwipeAnswersRequest
from common.entity import Swipe
from common.enums import AgeGroup, Gender, Style
from common.error import AppError, ErrorCode
from feature.swipe import service

STYLE_COUNT = len(Style)


class FirstPickRandom(random.Random):
    """고정 난수 생성기: sample 은 앞에서부터 k 개, shuffle 은 순서를 바꾸지 않는다."""

    def sample(self, population, k, *, counts=None):
        return list(population)[:k]

    def shuffle(self, x) -> None:
        return None


class ReversingRandom(FirstPickRandom):
    """shuffle 만 순서를 뒤집는다 (최종 순서 섞기 확인용)."""

    def shuffle(self, x) -> None:
        x.reverse()


def load_swipes(database_session, user_id: int) -> dict[int, bool]:
    database_session.expire_all()
    swipes = database_session.scalars(select(Swipe).where(Swipe.user_id == user_id)).all()
    return {swipe.product_id: swipe.liked for swipe in swipes}


def add_swipe(database_session, user_id: int, product_id: int, liked: bool) -> None:
    database_session.add(Swipe(user_id=user_id, product_id=product_id, liked=liked))
    database_session.commit()


def profiled_user(create_user, nickname: str = "swiper"):
    return create_user(nickname=nickname, age_group=AgeGroup.TWENTIES, gender=Gender.FEMALE)


def create_matching_products(create_product, style: Style, amount: int) -> list:
    return [create_product(gender=Gender.FEMALE, age_group=AgeGroup.TWENTIES, style=style) for _ in range(amount)]


# ---- allocate_style_quotas ----
@pytest.mark.parametrize("count", [1, 4, 5, 7, 13, 20, 50])
def test_allocate_style_quotas_gives_base_share_and_one_extra_to_distinct_random_styles(count):
    quotas = service.allocate_style_quotas(count, random.Random(count))

    assert set(quotas) == set(Style)
    assert sum(quotas.values()) == count
    base_share, remainder = divmod(count, STYLE_COUNT)
    assert Counter(quotas.values()) == Counter({base_share + 1: remainder, base_share: STYLE_COUNT - remainder})


def test_allocate_style_quotas_gives_remainder_to_styles_chosen_by_random_generator():
    quotas = service.allocate_style_quotas(7, FirstPickRandom())

    first_two_styles = list(Style)[:2]
    assert quotas == {style: (2 if style in first_two_styles else 1) for style in Style}


def test_allocate_style_quotas_is_reproducible_with_same_seed():
    assert service.allocate_style_quotas(13, random.Random(42)) == service.allocate_style_quotas(13, random.Random(42))


# ---- get_swipe_cards: 정상 ----
def test_get_swipe_cards_picks_quota_per_style_from_unswiped_matching_top_products(
    database_session, create_user, create_product
):
    user = profiled_user(create_user)
    candidates_by_style = {}
    for style in Style:
        products = create_matching_products(create_product, style, 4)
        add_swipe(database_session, user.id, products[0].id, liked=True)  # 이미 스와이프 → 제외
        candidates_by_style[style] = products[1:]
    create_product(gender=Gender.MALE, age_group=AgeGroup.TWENTIES, style=Style.MINIMAL)
    create_product(gender=Gender.FEMALE, age_group=AgeGroup.THIRTIES, style=Style.MINIMAL)

    response = service.get_swipe_cards(database_session, user, 7, FirstPickRandom())

    # FirstPickRandom: 나머지 2장은 앞 두 스타일, 스타일 안에서는 id 순 앞에서부터, 순서는 스타일 순
    expected_products = [
        product
        for index, style in enumerate(Style)
        for product in candidates_by_style[style][: 2 if index < 2 else 1]
    ]
    assert [card.product_id for card in response.cards] == [product.id for product in expected_products]
    assert [card.image_url for card in response.cards] == [product.image_url for product in expected_products]
    assert [card.style for card in response.cards] == [product.style for product in expected_products]


def test_get_swipe_cards_shuffles_final_order_with_random_generator(database_session, create_user, create_product):
    user = profiled_user(create_user)
    for style in Style:
        create_matching_products(create_product, style, 1)

    in_style_order = service.get_swipe_cards(database_session, user, 5, FirstPickRandom())
    reversed_order = service.get_swipe_cards(database_session, user, 5, ReversingRandom())

    assert [card.product_id for card in reversed_order.cards] == [
        card.product_id for card in reversed(in_style_order.cards)
    ]


def test_get_swipe_cards_does_not_fill_short_styles_from_other_styles(database_session, create_user, create_product):
    user = profiled_user(create_user)
    create_matching_products(create_product, Style.STREET, 6)
    create_matching_products(create_product, Style.LOVELY, 1)

    response = service.get_swipe_cards(database_session, user, 20, random.Random(7))

    assert Counter(card.style for card in response.cards) == Counter({Style.STREET: 4, Style.LOVELY: 1})
    assert len({card.product_id for card in response.cards}) == 5


def test_get_swipe_cards_returns_empty_list_without_candidates(database_session, create_user, create_product):
    user = profiled_user(create_user)
    product = create_product(gender=Gender.FEMALE, age_group=AgeGroup.TWENTIES, style=Style.CASUAL)
    add_swipe(database_session, user.id, product.id, liked=False)
    create_product(gender=Gender.MALE, age_group=AgeGroup.TWENTIES, style=Style.CASUAL)

    response = service.get_swipe_cards(database_session, user, 20, random.Random(1))

    assert response.cards == []


def test_get_swipe_cards_ignores_other_users_swipes(database_session, create_user, create_product):
    user = profiled_user(create_user)
    other_user = profiled_user(create_user, nickname="other")
    product = create_product(gender=Gender.FEMALE, age_group=AgeGroup.TWENTIES, style=Style.FORMAL)
    add_swipe(database_session, other_user.id, product.id, liked=True)

    response = service.get_swipe_cards(database_session, user, 5, FirstPickRandom())

    assert [card.product_id for card in response.cards] == [product.id]


# ---- get_swipe_cards: 거부 ----
@pytest.mark.parametrize(
    "user_columns",
    [{"age_group": None, "gender": Gender.FEMALE}, {"age_group": AgeGroup.TWENTIES, "gender": None}, {}],
)
def test_get_swipe_cards_without_profile_raises_profile_required(database_session, create_user, user_columns):
    user = create_user(nickname="member", **user_columns)

    with pytest.raises(AppError) as raised:
        service.get_swipe_cards(database_session, user, 20, random.Random(1))

    assert raised.value.error_code == ErrorCode.PROFILE_REQUIRED


# ---- submit_swipe_answers ----
def test_submit_swipe_answers_upserts_last_value_and_counts_all_stored_swipes(
    database_session, create_user, create_product
):
    user = profiled_user(create_user)
    resubmitted_product, duplicated_product, untouched_product = (create_product() for _ in range(3))
    add_swipe(database_session, user.id, resubmitted_product.id, liked=False)
    add_swipe(database_session, user.id, untouched_product.id, liked=True)

    response = service.submit_swipe_answers(
        database_session,
        user,
        SwipeAnswersRequest(
            answers=[
                SwipeAnswer(product_id=resubmitted_product.id, liked=True),
                SwipeAnswer(product_id=duplicated_product.id, liked=True),
                SwipeAnswer(product_id=duplicated_product.id, liked=False),
            ]
        ),
    )
    database_session.commit()

    assert (response.liked_count, response.total_count) == (2, 3)
    assert load_swipes(database_session, user.id) == {
        resubmitted_product.id: True,
        duplicated_product.id: False,
        untouched_product.id: True,
    }


def test_submit_swipe_answers_with_missing_product_raises_and_writes_nothing(
    database_session, create_user, create_product
):
    user = profiled_user(create_user)
    valid_product = create_product()

    with pytest.raises(AppError) as raised:
        service.submit_swipe_answers(
            database_session,
            user,
            SwipeAnswersRequest(
                answers=[
                    SwipeAnswer(product_id=valid_product.id, liked=True),
                    SwipeAnswer(product_id=valid_product.id + 1000, liked=False),
                ]
            ),
        )
    database_session.rollback()

    assert raised.value.error_code == ErrorCode.PRODUCT_NOT_FOUND
    assert load_swipes(database_session, user.id) == {}
