import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ErrorCode } from '../../common/type'
import type { SwipeAnswer, SwipeCardDto } from '../../common/type'
import { ApiError } from '../../shared/api'
import { ROUTES } from '../../shared/navigation'
import { Button, EmptyState, ErrorMessage, Loading, PageLayout } from '../../shared/ui'
import { fetchSwipeCards, submitSwipeAnswers } from './api'
import { SwipeCard } from './SwipeCard'

const CARD_COUNT = 20
const PAGE_TITLE = '취향 스와이프'

function toErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '요청에 실패했습니다'
}

function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

function isProfileRequired(error: unknown): boolean {
  return error instanceof ApiError && error.code === ErrorCode.PROFILE_REQUIRED
}

/** 상의 카드를 한 장씩 좋아요/싫어요. 마지막 카드 후 답변을 한 번에 제출하고 옷장 사진 화면으로 보낸다. */
export function SwipePage() {
  const navigate = useNavigate()
  const [cards, setCards] = useState<SwipeCardDto[] | null>(null)
  const [loadError, setLoadError] = useState<unknown>(null)
  const [requestCount, setRequestCount] = useState(0)
  const [answers, setAnswers] = useState<SwipeAnswer[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitErrorMessage, setSubmitErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    let isCancelled = false
    fetchSwipeCards(CARD_COUNT)
      .then((response) => {
        if (!isCancelled) setCards(response.cards)
      })
      .catch((error: unknown) => {
        if (isCancelled) return
        // 401 이면 shared/api 가 토큰을 지운다 → 로그인 화면으로
        if (isUnauthorized(error)) navigate(ROUTES.login, { replace: true })
        else setLoadError(error)
      })
    return () => {
      isCancelled = true
    }
  }, [requestCount, navigate])

  function handleRetryLoad() {
    setLoadError(null)
    setRequestCount((count) => count + 1)
  }

  async function submit(completedAnswers: SwipeAnswer[]) {
    setIsSubmitting(true)
    setSubmitErrorMessage(null)
    try {
      await submitSwipeAnswers({ answers: completedAnswers })
      navigate(ROUTES.wardrobe)
    } catch (error) {
      if (isUnauthorized(error)) {
        navigate(ROUTES.login, { replace: true })
        return
      }
      setSubmitErrorMessage(toErrorMessage(error))
      setIsSubmitting(false)
    }
  }

  /** 버튼과 드래그가 함께 쓰는 답변 처리. 마지막 카드면 자동 제출한다. */
  function handleAnswer(liked: boolean) {
    if (cards === null || answers.length >= cards.length) return
    const nextAnswers = [...answers, { productId: cards[answers.length].productId, liked }]
    setAnswers(nextAnswers)
    if (nextAnswers.length === cards.length) void submit(nextAnswers)
  }

  if (loadError !== null) {
    return (
      <PageLayout title={PAGE_TITLE}>
        {isProfileRequired(loadError) ? (
          <>
            <EmptyState message={toErrorMessage(loadError)} />
            <Button onClick={() => navigate(ROUTES.profile)}>프로필 입력하기</Button>
          </>
        ) : (
          <ErrorMessage message={toErrorMessage(loadError)} onRetry={handleRetryLoad} />
        )}
      </PageLayout>
    )
  }

  if (cards === null) {
    return (
      <PageLayout title={PAGE_TITLE}>
        <Loading />
      </PageLayout>
    )
  }

  if (cards.length === 0) {
    return (
      <PageLayout title={PAGE_TITLE}>
        <EmptyState message="지금 보여줄 카드가 없어요" />
      </PageLayout>
    )
  }

  if (answers.length === cards.length) {
    return (
      <PageLayout title={PAGE_TITLE}>
        {isSubmitting && <Loading message="저장 중…" />}
        {submitErrorMessage && <ErrorMessage message={submitErrorMessage} onRetry={() => void submit(answers)} />}
      </PageLayout>
    )
  }

  const currentCard = cards[answers.length]
  return (
    <PageLayout title={PAGE_TITLE}>
      <p style={{ margin: 0, textAlign: 'center', color: 'var(--color-muted)' }}>
        {`${answers.length + 1} / ${cards.length}`}
      </p>
      <SwipeCard key={currentCard.productId} card={currentCard} onAnswer={handleAnswer} />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <Button variant="secondary" onClick={() => handleAnswer(false)}>
          싫어요
        </Button>
        <Button onClick={() => handleAnswer(true)}>좋아요</Button>
      </div>
    </PageLayout>
  )
}
