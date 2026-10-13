import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { FittingStatus } from '../../common/type'
import type { FittingDto } from '../../common/type'
import { ApiError } from '../../shared/api'
import { ROUTES } from '../../shared/navigation'
import { Button, EmptyState, ErrorMessage, Loading, PageLayout } from '../../shared/ui'
import { createFitting, fetchFitting } from './api'
import { FittingFailure, FittingResult, ProductSummary } from './FittingResult'

const PAGE_TITLE = '가상 피팅'
const LOADING_MESSAGE = '입혀보는 중'
const TIMED_OUT_MESSAGE = '시간이 오래 걸리고 있어요'
const POLLING_INTERVAL_MILLISECONDS = 2_000
// 서버 YouCam 대기 120초 + 여유 30초
const POLLING_LIMIT_MILLISECONDS = 150_000

/** 폴링 한 회차. 새 객체를 넣을 때마다 회차가 새로 시작된다 (150초 상한도 새로). */
type PollingRound = { fittingId: number; startsImmediately: boolean }

function toErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '요청에 실패했습니다'
}

function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

/**
 * 진입 시 POST → PENDING 이면 GET 을 2초 간격으로 최대 150초 폴링한다. 화면을 떠나면 폴링을 멈춘다.
 * DONE: 원본/결과 비교 · FAILED: 상품 이미지와 다시 시도(POST) · 150초 초과: 다시 확인(GET 후 PENDING 이면 폴링 재개).
 */
export function FittingPage() {
  const navigate = useNavigate()
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

  if (loadError !== null) {
    return (
      <PageLayout title={PAGE_TITLE}>
        <ErrorMessage message={toErrorMessage(loadError)} onRetry={handleCreateAgain} />
      </PageLayout>
    )
  }

  if (fitting === null) {
    return (
      <PageLayout title={PAGE_TITLE}>
        <Loading message={LOADING_MESSAGE} />
      </PageLayout>
    )
  }

  return (
    <PageLayout title={PAGE_TITLE}>
      {fitting.status === FittingStatus.DONE && (
        <FittingResult fitting={fitting} onTryOther={() => navigate(ROUTES.recommendation)} />
      )}
      {fitting.status === FittingStatus.FAILED && (
        <FittingFailure product={fitting.product} onRetry={handleCreateAgain} />
      )}
      {fitting.status === FittingStatus.PENDING && (
        <>
          <ProductSummary product={fitting.product} />
          {isTimedOut ? (
            <>
              <EmptyState message={TIMED_OUT_MESSAGE} />
              <Button variant="secondary" onClick={() => handleCheckAgain(fitting.id)}>
                다시 확인
              </Button>
            </>
          ) : (
            <Loading message={LOADING_MESSAGE} />
          )}
        </>
      )}
    </PageLayout>
  )
}
