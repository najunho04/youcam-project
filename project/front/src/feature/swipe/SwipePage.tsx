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
import { SwipeCard } from './SwipeCard'
import { SWIPE_MESSAGES } from './messages'
import './swipe.css'

const CARD_COUNT = 20
/** 가운데에서 양옆 몇 칸까지 그려 둘지. 한 칸 바깥은 투명하게 대기했다가 밀려 들어온다. */
const RENDERED_SLOT_RANGE = 2

type SlotName = 'previous' | 'current' | 'next' | 'waiting'

/** 가운데(0)에서 떨어진 칸 수 → 캐러셀 자리 이름 */
function slotNameOf(offset: number): SlotName {
  if (offset === 0) return 'current'
  if (offset === -1) return 'previous'
  if (offset === 1) return 'next'
  return 'waiting'
}

/** 자리마다 위치·크기·밝기. 바뀔 때 CSS 전환으로 미끄러진다. */
function slotStyleOf(offset: number): CSSProperties {
  const distance = Math.abs(offset)
  return {
    '--slot-position': offset,
    '--slot-scale': distance === 0 ? 1 : distance === 1 ? 0.62 : 0.5,
    '--slot-opacity': distance === 0 ? 1 : distance === 1 ? (offset < 0 ? 0.7 : 0.45) : 0,
    '--slot-brightness': distance === 0 ? 1 : offset < 0 ? 0.8 : 0.55,
  } as CSSProperties
}

function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

function isProfileRequired(error: unknown): boolean {
  return error instanceof ApiError && error.code === ErrorCode.PROFILE_REQUIRED
}

/**
 * 상의 카드를 한 장씩 좋아요/싫어요. 이전 · 현재 · 다음 세 칸 캐러셀로, 답하면 오른쪽 카드가 가운데로 들어오고
 * 답한 카드는 초록(좋아요)·빨강(싫어요) 테두리를 단 채 이전 자리로 간다. 되돌리기로 직전 답을 취소한다.
 * 마지막 카드 후 답변을 한 번에 제출하고 옷장 사진 화면으로 보낸다.
 */
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
  function handleAnswer(liked: boolean) {
    if (cards === null || answers.length >= cards.length) return
    const answeredCard = cards[answers.length]
    const nextAnswers = [...answers, { pinId: answeredCard.pinId, liked }]
    setAnswers(nextAnswers)
    if (nextAnswers.length === cards.length) void submit(nextAnswers)
  }

  function handleUndo() {
    setAnswers((previousAnswers) => previousAnswers.slice(0, -1))
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

  const currentIndex = answers.length
  return (
    <PageLayout
      width="wide"
      align="center"
      title={messages.title}
      lede={messages.lede}
      step={{ current: currentIndex + 1, total: cards.length }}
    >
      <div className="swipe-carousel">
        {cards.map((card, cardIndex) => {
          const offset = cardIndex - currentIndex
          if (Math.abs(offset) > RENDERED_SLOT_RANGE) return null
          const answer = answers[cardIndex]
          return (
            <div
              key={cardIndex}
              className="swipe-slot"
              data-slot={slotNameOf(offset)}
              data-answer={answer === undefined ? undefined : answer.liked ? 'like' : 'dislike'}
              aria-hidden={offset !== 0}
              style={slotStyleOf(offset)}
            >
              {offset === 0 ? (
                <SwipeCard key={card.pinId} card={card} onAnswer={handleAnswer} />
              ) : (
                <div className="swipe-card swipe-card-static">
                  <img src={card.imageUrl} alt="" draggable={false} />
                </div>
              )}
            </div>
          )
        })}
        {currentIndex > 0 && (
          <span className="swipe-slot-label swipe-slot-label-previous" aria-hidden="true">
            ← {messages.previous}
          </span>
        )}
        {currentIndex + 1 < cards.length && (
          <span className="swipe-slot-label swipe-slot-label-next" aria-hidden="true">
            {messages.next} →
          </span>
        )}
      </div>
      <div className="swipe-actions">
        <button
          type="button"
          className="swipe-round-button swipe-round-button-small"
          aria-label={messages.undo}
          disabled={currentIndex === 0}
          onClick={handleUndo}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 14L4 9l5-5" />
            <path d="M4 9h10a6 6 0 0 1 0 12h-3" />
          </svg>
        </button>
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
