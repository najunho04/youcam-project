import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ErrorCode, Season } from '../../common/type'
import type { RecommendationResponse } from '../../common/type'
import { ApiError } from '../../shared/api'
import { ROUTES } from '../../shared/navigation'
import { Button, EmptyState, ErrorMessage, Loading, Notice, PageLayout } from '../../shared/ui'
import { fetchRecommendations } from './api'
import { RecommendationCard } from './RecommendationCard'
import './recommendation.css'

const PAGE_TITLE = '추천 상의'
const PAGE_LEDE = '취향과 퍼스널컬러를 함께 봤어요.'
const FALLBACK_NOTICE = '취향 데이터가 적어 퍼스널컬러에 어울리는 상품을 보여드려요'

const SEASON_NAMES: Record<Season, string> = {
  [Season.SPRING_WARM]: '봄 웜톤',
  [Season.SUMMER_COOL]: '여름 쿨톤',
  [Season.AUTUMN_WARM]: '가을 웜톤',
  [Season.WINTER_COOL]: '겨울 쿨톤',
}

/** 사전 조건 에러별로 이동할 화면과 버튼 문구. */
const REQUIRED_STEP_BY_ERROR_CODE: Partial<Record<ErrorCode, { route: string; label: string }>> = {
  [ErrorCode.PROFILE_REQUIRED]: { route: ROUTES.profile, label: '프로필 입력하기' },
  [ErrorCode.PERSONAL_COLOR_REQUIRED]: { route: ROUTES.personalColor, label: '퍼스널컬러 진단하기' },
}

function toErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '요청에 실패했습니다'
}

function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

function requiredStepOf(error: unknown) {
  return error instanceof ApiError ? REQUIRED_STEP_BY_ERROR_CODE[error.code] : undefined
}

function RecommendationSummary({ recommendation }: { recommendation: RecommendationResponse }) {
  const seasonName = SEASON_NAMES[recommendation.season]
  return (
    <>
      <section className="recommendation-summary">
        <div className="recommendation-summary-row">
          <p className="eyebrow">선호 스타일</p>
          <ul aria-label="취향 요약" className="chip-list">
            {recommendation.styleTags.map((styleTag) => (
              <li key={styleTag} className="chip">
                {styleTag}
              </li>
            ))}
          </ul>
        </div>
        <div className="recommendation-summary-row">
          <p className="eyebrow">{seasonName}</p>
          <ul aria-label={`${seasonName} 팔레트`} className="recommendation-palette">
            {recommendation.palette.map((hexColor) => (
              <li key={hexColor} title={hexColor} style={{ background: hexColor }} />
            ))}
          </ul>
        </div>
      </section>
      {recommendation.isFallback && <Notice>{FALLBACK_NOTICE}</Notice>}
    </>
  )
}

/** 취향·퍼스널컬러로 고른 상의 상위 5개. 입어보기는 가상 피팅 화면, 구매하러 가기는 쇼핑몰(새 탭). */
export function RecommendationPage() {
  const navigate = useNavigate()
  const [recommendation, setRecommendation] = useState<RecommendationResponse | null>(null)
  const [loadError, setLoadError] = useState<unknown>(null)
  const [requestCount, setRequestCount] = useState(0)

  useEffect(() => {
    let isCancelled = false
    fetchRecommendations()
      .then((response) => {
        if (!isCancelled) setRecommendation(response)
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

  if (loadError !== null) {
    const requiredStep = requiredStepOf(loadError)
    return (
      <PageLayout width="wide" title={PAGE_TITLE} lede={PAGE_LEDE}>
        {requiredStep ? (
          <>
            <EmptyState message={toErrorMessage(loadError)} />
            <Button onClick={() => navigate(requiredStep.route)}>{requiredStep.label}</Button>
          </>
        ) : (
          <ErrorMessage message={toErrorMessage(loadError)} onRetry={handleRetryLoad} />
        )}
      </PageLayout>
    )
  }

  if (recommendation === null) {
    return (
      <PageLayout width="wide" title={PAGE_TITLE} lede={PAGE_LEDE}>
        <Loading />
      </PageLayout>
    )
  }

  return (
    <PageLayout width="wide" title={PAGE_TITLE} lede={PAGE_LEDE}>
      <RecommendationSummary recommendation={recommendation} />
      {recommendation.items.length === 0 ? (
        <EmptyState message="추천할 상품이 아직 없어요" />
      ) : (
        <div className="recommendation-list">
          {recommendation.items.map((item, index) => (
            <RecommendationCard
              key={item.product.id}
              item={item}
              rank={index + 1}
              isFeatured={index === 0}
              highlightedReason={SEASON_NAMES[recommendation.season]}
              onTryOn={() => navigate(ROUTES.fitting(item.product.id))}
            />
          ))}
        </div>
      )}
    </PageLayout>
  )
}
