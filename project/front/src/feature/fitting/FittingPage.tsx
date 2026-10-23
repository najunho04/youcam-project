import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { FittingStatus } from '../../common/type'
import type { FittingDto } from '../../common/type'
import { ApiError, useDescribeError } from '../../shared/api'
import { useMessages } from '../../shared/i18n'
import { ROUTES } from '../../shared/navigation'
import { Button, ErrorMessage, Loading, Notice, PageActions, PageLayout, buttonClassName } from '../../shared/ui'
import { createFitting, fetchFitting } from './api'
import { FittingComparison, FittingFailure, FittingPendingPreview, ProductSummary } from './FittingResult'
import { FITTING_MESSAGES } from './messages'
import './fitting.css'

const POLLING_INTERVAL_MILLISECONDS = 2_000
// 서버 YouCam 대기 120초 + 여유 30초
// 서버가 YouCam 을 최대 165초 기다린 뒤 결과(DONE/FAILED)를 기록하므로 그보다 넉넉히 기다린다
const POLLING_LIMIT_MILLISECONDS = 200_000

/** 폴링 한 회차. 새 객체를 넣을 때마다 회차가 새로 시작된다 (200초 상한도 새로). */
type PollingRound = { fittingId: number; startsImmediately: boolean }

function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

/**
 * 진입 시 POST → PENDING 이면 GET 을 2초 간격으로 최대 200초 폴링한다. 화면을 떠나면 폴링을 멈춘다.
 * DONE: 원본/결과 비교 · FAILED: 상품 이미지와 다시 시도(POST) · 200초 초과: 다시 확인(GET 후 PENDING 이면 폴링 재개).
 */
export function FittingPage() {
  const navigate = useNavigate()
  const messages = useMessages(FITTING_MESSAGES)
  const describeError = useDescribeError()
  const { productId } = useParams()
  const [fitting, setFitting] = useState<FittingDto | null>(null)
  const [loadError, setLoadError] = useState<unknown>(null)
  const [isTimedOut, setIsTimedOut] = useState(false)
  const [pollingRound, setPollingRound] = useState<PollingRound | null>(null)
  const [createRequestCount, setCreateRequestCount] = useState(0)

  const handleLoadError = useCallback(
    (error: unknown) => {
      // 401 이면 shared/api 가 토큰을 지운다 → 로그인 화면으로
      if (isUnauthorized(error)) navigate(ROUTES.login, { replace: true })
      else setLoadError(error)
    },
    [navigate],
  )

  useEffect(() => {
    let isCancelled = false
    createFitting({ productId: Number(productId) })
      .then((response) => {
        if (isCancelled) return
        setFitting(response)
        if (response.status === FittingStatus.PENDING) {
          setPollingRound({ fittingId: response.id, startsImmediately: false })
        }
      })
      .catch((error: unknown) => {
        if (!isCancelled) handleLoadError(error)
      })
    return () => {
      isCancelled = true
    }
  }, [productId, createRequestCount, handleLoadError])

  useEffect(() => {
    if (pollingRound === null) return
    const { fittingId, startsImmediately } = pollingRound
    let isStopped = false
    let pollTimeoutId: ReturnType<typeof setTimeout> | undefined

    function stopPolling() {
      isStopped = true
      clearTimeout(pollTimeoutId)
      clearTimeout(limitTimeoutId)
    }

    const limitTimeoutId = setTimeout(() => {
      stopPolling()
      setIsTimedOut(true)
    }, POLLING_LIMIT_MILLISECONDS)

    async function poll() {
      try {
        const response = await fetchFitting(fittingId)
        if (isStopped) return
        setFitting(response)
        if (response.status === FittingStatus.PENDING) scheduleNextPoll()
        else stopPolling()
      } catch (error) {
        if (isStopped) return
        stopPolling()
        handleLoadError(error)
      }
    }

    function scheduleNextPoll() {
      pollTimeoutId = setTimeout(() => void poll(), POLLING_INTERVAL_MILLISECONDS)
    }

    if (startsImmediately) void poll()
    else scheduleNextPoll()
    return stopPolling
  }, [pollingRound, handleLoadError])

  function handleCreateAgain() {
    setLoadError(null)
    setFitting(null)
    setIsTimedOut(false)
    setPollingRound(null)
    setCreateRequestCount((count) => count + 1)
  }

  function handleCheckAgain(fittingId: number) {
    setIsTimedOut(false)
    setPollingRound({ fittingId, startsImmediately: true })
  }

  const layoutProps = {
    navigationTitle: messages.title,
    width: 'regular' as const,
    onBack: () => navigate(ROUTES.recommendation),
    backLabel: messages.backLabel,
  }
  const tryOtherButton = (
    <Button variant="plain" onClick={() => navigate(ROUTES.recommendation)}>
      {messages.tryOther}
    </Button>
  )

  if (loadError !== null) {
    return (
      <PageLayout {...layoutProps}>
        <h1 className="visually-hidden">{messages.title}</h1>
        <ErrorMessage message={describeError(loadError)} onRetry={handleCreateAgain} />
      </PageLayout>
    )
  }

  if (fitting === null) {
    return (
      <PageLayout {...layoutProps}>
        <h1 className="visually-hidden">{messages.title}</h1>
        <Loading message={messages.loading} />
      </PageLayout>
    )
  }

  if (fitting.status === FittingStatus.DONE) {
    return (
      <PageLayout {...layoutProps}>
        <h1 className="visually-hidden">{messages.title}</h1>
        <div className="fitting-layout">
          <FittingComparison fitting={fitting} />
          <div className="fitting-side">
            <ProductSummary product={fitting.product} />
            <p className="footnote">{messages.compareHint}</p>
            <PageActions>
              <a className={buttonClassName('primary')} href={fitting.product.purchaseUrl} target="_blank" rel="noopener noreferrer">
                {messages.buy}
              </a>
              {tryOtherButton}
            </PageActions>
          </div>
        </div>
      </PageLayout>
    )
  }

  if (fitting.status === FittingStatus.FAILED) {
    return (
      <PageLayout {...layoutProps}>
        <h1 className="visually-hidden">{messages.title}</h1>
        <div className="fitting-layout">
          <FittingFailure product={fitting.product} />
          <div className="fitting-side">
            <p role="alert" className="state state-banner state-error">
              {messages.failed}
            </p>
            <ProductSummary product={fitting.product} />
            <PageActions>
              <Button onClick={handleCreateAgain}>{messages.retry}</Button>
              {tryOtherButton}
            </PageActions>
          </div>
        </div>
      </PageLayout>
    )
  }

  return (
    <PageLayout {...layoutProps}>
      <h1 className="visually-hidden">{messages.title}</h1>
      <div className="fitting-layout">
        <FittingPendingPreview originalImageUrl={fitting.originalImageUrl} isTimedOut={isTimedOut} loadingMessage={messages.loading} />
        <div className="fitting-side">
          {isTimedOut && (
            <Notice>
              <p>{messages.timedOut}</p>
              <Button variant="plain" size="small" onClick={() => handleCheckAgain(fitting.id)}>
                {messages.checkAgain}
              </Button>
            </Notice>
          )}
          <ProductSummary product={fitting.product} caption={isTimedOut ? undefined : messages.pendingCaption} />
          <PageActions>{tryOtherButton}</PageActions>
        </div>
      </div>
    </PageLayout>
  )
}
