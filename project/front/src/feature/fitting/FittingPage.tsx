import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { FittingStatus } from '../../common/type'
import type { FittingDto } from '../../common/type'
import { ApiError } from '../../shared/api'
import { ROUTES } from '../../shared/navigation'
import { Button, ErrorMessage, Loading, Notice, PageActions, PageLayout, buttonClassName } from '../../shared/ui'
import { createFitting, fetchFitting } from './api'
import { FittingComparison, FittingFailure, FittingPendingPreview, ProductSummary } from './FittingResult'
import './fitting.css'

const PAGE_TITLE = '가상 피팅'
const LOADING_MESSAGE = '입혀보는 중'
const TIMED_OUT_MESSAGE = '시간이 오래 걸리고 있어요'
const PENDING_CAPTION = '보통 20~40초 걸려요'
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

  const layoutProps = {
    navigationTitle: PAGE_TITLE,
    width: 'regular' as const,
    onBack: () => navigate(ROUTES.recommendation),
    backLabel: '추천',
  }
  const tryOtherButton = (
    <Button variant="plain" onClick={() => navigate(ROUTES.recommendation)}>
      다른 상품 입어보기
    </Button>
  )

  if (loadError !== null) {
    return (
      <PageLayout {...layoutProps}>
        <h1 className="visually-hidden">{PAGE_TITLE}</h1>
        <ErrorMessage message={toErrorMessage(loadError)} onRetry={handleCreateAgain} />
      </PageLayout>
    )
  }

  if (fitting === null) {
    return (
      <PageLayout {...layoutProps}>
        <h1 className="visually-hidden">{PAGE_TITLE}</h1>
        <Loading message={LOADING_MESSAGE} />
      </PageLayout>
    )
  }

  if (fitting.status === FittingStatus.DONE) {
    return (
      <PageLayout {...layoutProps}>
        <h1 className="visually-hidden">{PAGE_TITLE}</h1>
        <div className="fitting-layout">
          <FittingComparison fitting={fitting} />
          <div className="fitting-side">
            <ProductSummary product={fitting.product} />
            <p className="footnote">경계선을 좌우로 끌어 원본과 비교해 보세요.</p>
            <PageActions>
              <a className={buttonClassName('primary')} href={fitting.product.purchaseUrl} target="_blank" rel="noopener noreferrer">
                구매하러 가기
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
        <h1 className="visually-hidden">{PAGE_TITLE}</h1>
        <div className="fitting-layout">
          <FittingFailure product={fitting.product} />
          <div className="fitting-side">
            <p role="alert" className="state state-banner state-error">
              가상 피팅에 실패했어요
            </p>
            <ProductSummary product={fitting.product} />
            <PageActions>
              <Button onClick={handleCreateAgain}>다시 시도</Button>
              {tryOtherButton}
            </PageActions>
          </div>
        </div>
      </PageLayout>
    )
  }

  return (
    <PageLayout {...layoutProps}>
      <h1 className="visually-hidden">{PAGE_TITLE}</h1>
      <div className="fitting-layout">
        <FittingPendingPreview originalImageUrl={fitting.originalImageUrl} isTimedOut={isTimedOut} loadingMessage={LOADING_MESSAGE} />
        <div className="fitting-side">
          {isTimedOut && (
            <Notice>
              <p>{TIMED_OUT_MESSAGE}</p>
              <Button variant="plain" size="small" onClick={() => handleCheckAgain(fitting.id)}>
                다시 확인
              </Button>
            </Notice>
          )}
          <ProductSummary product={fitting.product} caption={isTimedOut ? undefined : PENDING_CAPTION} />
          <PageActions>{tryOtherButton}</PageActions>
        </div>
      </div>
    </PageLayout>
  )
}
