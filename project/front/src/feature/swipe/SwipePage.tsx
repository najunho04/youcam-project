import { useEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import { ErrorCode } from '../../common/type'
import type { SwipeAnswer, SwipeCardDto } from '../../common/type'
import { ApiError, useDescribeError } from '../../shared/api'
import { useMessages } from '../../shared/i18n'
import { ROUTES } from '../../shared/navigation'
import { Button, EmptyState, ErrorMessage, Loading, PageLayout } from '../../shared/ui'
import { fetchSwipeCards, submitSwipeAnswers } from './api'
import { SwipeCard, rotationOf } from './SwipeCard'
import { SWIPE_MESSAGES } from './messages'
import './swipe.css'

const CARD_COUNT = 20

/** 답한 뒤 화면 밖으로 날아가는 직전 카드 (장식용, 보조기술에서 숨김). */
type ExitingCard = { card: SwipeCardDto; liked: boolean; releaseOffsetX: number; sequence: number }

function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

function isProfileRequired(error: unknown): boolean {
  return error instanceof ApiError && error.code === ErrorCode.PROFILE_REQUIRED
}

/** 상의 카드를 한 장씩 좋아요/싫어요. 마지막 카드 후 답변을 한 번에 제출하고 옷장 사진 화면으로 보낸다. */
export function SwipePage() {
  const navigate = useNavigate()
  const messages = useMessages(SWIPE_MESSAGES)
  const describeError = useDescribeError()
  const [cards, setCards] = useState<SwipeCardDto[] | null>(null)
  const [loadError, setLoadError] = useState<unknown>(null)
  const [requestCount, setRequestCount] = useState(0)
  const [answers, setAnswers] = useState<SwipeAnswer[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitErrorMessage, setSubmitErrorMessage] = useState<string | null>(null)
  const [exitingCard, setExitingCard] = useState<ExitingCard | null>(null)
  const [dragProgress, setDragProgress] = useState(0)

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
      setSubmitErrorMessage(describeError(error))
      setIsSubmitting(false)
    }
  }

  // 데스크톱: ← 싫어요 · → 좋아요
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return
      if (event.key === 'ArrowLeft') handleAnswerRef.current(false)
      if (event.key === 'ArrowRight') handleAnswerRef.current(true)
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  /** 버튼과 드래그가 함께 쓰는 답변 처리. 마지막 카드면 자동 제출한다. */
  function handleAnswer(liked: boolean, releaseOffsetX = 0) {
    if (cards === null || answers.length >= cards.length) return
    const answeredCard = cards[answers.length]
    const nextAnswers = [...answers, { pinId: answeredCard.pinId, liked }]
    setAnswers(nextAnswers)
    setDragProgress(0)
    setExitingCard({ card: answeredCard, liked, releaseOffsetX, sequence: nextAnswers.length })
    if (nextAnswers.length === cards.length) void submit(nextAnswers)
  }
  const handleAnswerRef = useRef(handleAnswer)
  useEffect(() => {
    handleAnswerRef.current = handleAnswer
  })

  if (loadError !== null) {
    return (
      <PageLayout title={messages.title}>
        {isProfileRequired(loadError) ? (
          <>
            <EmptyState message={describeError(loadError)} />
            <Button onClick={() => navigate(ROUTES.profile)}>{messages.goToProfile}</Button>
          </>
        ) : (
          <ErrorMessage message={describeError(loadError)} onRetry={handleRetryLoad} />
        )}
      </PageLayout>
    )
  }

  if (cards === null) {
    return (
      <PageLayout title={messages.title}>
        <Loading />
      </PageLayout>
    )
  }

  if (cards.length === 0) {
    return (
      <PageLayout title={messages.title}>
        <EmptyState message={messages.noCards} />
      </PageLayout>
    )
  }

  if (answers.length === cards.length) {
    return (
      <PageLayout title={messages.title}>
        {isSubmitting && <Loading message={messages.saving} />}
        {submitErrorMessage && <ErrorMessage message={submitErrorMessage} onRetry={() => void submit(answers)} />}
      </PageLayout>
    )
  }

  const currentCard = cards[answers.length]
  const nextCard = cards[answers.length + 1]
  const underCardScale = 0.94 + 0.06 * dragProgress
  return (
    <PageLayout step={{ current: answers.length + 1, total: cards.length }}>
      <h1 className="visually-hidden">{messages.title}</h1>
      <div className="swipe-deck">
        {nextCard && (
          <div
            className="swipe-card swipe-card-under"
            aria-hidden="true"
            style={{ transform: `translateY(${14 * (1 - dragProgress)}px) scale(${underCardScale})` }}
          >
            <img src={nextCard.imageUrl} alt="" draggable={false} />
          </div>
        )}
        <SwipeCard key={currentCard.pinId} card={currentCard} onAnswer={handleAnswer} onDragProgress={setDragProgress} />
        {exitingCard && (
          <div
            key={exitingCard.sequence}
            className="swipe-card swipe-card-exiting"
            aria-hidden="true"
            onAnimationEnd={() => setExitingCard(null)}
            style={
              {
                '--exit-from-x': `${exitingCard.releaseOffsetX}px`,
                '--exit-from-rotation': `${rotationOf(exitingCard.releaseOffsetX)}deg`,
                '--exit-direction': exitingCard.liked ? 1 : -1,
              } as CSSProperties
            }
          >
            <img src={exitingCard.card.imageUrl} alt="" draggable={false} />
          </div>
        )}
      </div>
      <div className="swipe-actions">
        <button type="button" className="swipe-round-button" aria-label={messages.dislike} onClick={() => handleAnswer(false)}>
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="var(--color-nope)" strokeWidth="2.6" strokeLinecap="round">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
        <button type="button" className="swipe-round-button" aria-label={messages.like} onClick={() => handleAnswer(true)}>
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="var(--color-like)">
            <path d="M12 21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.7 4.5c2.1 0 3.6 1.2 4.3 2.4h2c.7-1.2 2.2-2.4 4.3-2.4 3.7 0 5.8 3.9 4.3 7.3C19.5 16.4 12 21 12 21z" />
          </svg>
        </button>
      </div>
      <p className="footnote swipe-hint">
        {messages.hint}
        <span className="swipe-hint-keyboard">
          {messages.keyboard}
          <kbd>←</kbd>
          <kbd>→</kbd>
        </span>
      </p>
    </PageLayout>
  )
}
