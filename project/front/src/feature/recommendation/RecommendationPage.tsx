import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ErrorCode } from '../../common/type'
import type { RecommendationResponse } from '../../common/type'
import { ApiError, useDescribeError } from '../../shared/api'
import { useMessages } from '../../shared/i18n'
import { ROUTES } from '../../shared/navigation'
import { Button, EmptyState, ErrorMessage, Loading, Notice, PageLayout } from '../../shared/ui'
import { fetchRecommendations } from './api'
import { RecommendationCard } from './RecommendationCard'
import { RECOMMENDATION_MESSAGES, SERVER_SEASON_NAMES } from './messages'
import './recommendation.css'

/** 사전 조건 에러별로 이동할 화면 */
const REQUIRED_ROUTE_BY_ERROR_CODE: Partial<Record<ErrorCode, string>> = {
  [ErrorCode.PROFILE_REQUIRED]: ROUTES.profile,
  [ErrorCode.PERSONAL_COLOR_REQUIRED]: ROUTES.personalColor,
}

function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

function requiredRouteOf(error: unknown): string | undefined {
  return error instanceof ApiError ? REQUIRED_ROUTE_BY_ERROR_CODE[error.code] : undefined
}

function RecommendationSummary({ recommendation }: { recommendation: RecommendationResponse }) {
  const messages = useMessages(RECOMMENDATION_MESSAGES)
  const seasonName = messages.seasonNames[recommendation.season]
  return (
    <>
      <section className="recommendation-summary">
        <div className="recommendation-summary-row">
          <p className="eyebrow">{messages.preferredStyle}</p>
          <ul aria-label={messages.styleSummary} className="chip-list">
            {recommendation.styleTags.map((styleTag) => (
              <li key={styleTag} className="chip">
                {messages.tag(styleTag)}
              </li>
            ))}
          </ul>
        </div>
        <div className="recommendation-summary-row">
          <p className="eyebrow">{seasonName}</p>
          <ul aria-label={messages.palette(seasonName)} className="recommendation-palette">
            {recommendation.palette.map((hexColor) => (
              <li key={hexColor} title={hexColor} style={{ background: hexColor }} />
            ))}
          </ul>
        </div>
      </section>
      {recommendation.isFallback && <Notice>{messages.fallbackNotice}</Notice>}
    </>
  )
}

/** 취향·퍼스널컬러로 고른 상의 상위 6개 (3열 두 줄, 모자라면 마지막 줄을 가운데로). 입어보기는 가상 피팅 화면, 구매하러 가기는 쇼핑몰(새 탭). */
export function RecommendationPage() {
  const navigate = useNavigate()
  const messages = useMessages(RECOMMENDATION_MESSAGES)
  const describeError = useDescribeError()
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
    const requiredRoute = requiredRouteOf(loadError)
    return (
      <PageLayout width="wide" align="center" title={messages.title} lede={messages.lede}>
        {requiredRoute ? (
          <>
            <EmptyState message={describeError(loadError)} />
            <Button onClick={() => navigate(requiredRoute)}>
              {requiredRoute === ROUTES.profile ? messages.goToProfile : messages.goToPersonalColor}
            </Button>
          </>
        ) : (
          <ErrorMessage message={describeError(loadError)} onRetry={handleRetryLoad} />
        )}
      </PageLayout>
    )
  }

  if (recommendation === null) {
    return (
      <PageLayout width="wide" align="center" title={messages.title} lede={messages.lede}>
        <Loading />
      </PageLayout>
    )
  }

  return (
    <PageLayout width="wide" align="center" title={messages.title} lede={messages.lede}>
      <RecommendationSummary recommendation={recommendation} />
      {recommendation.items.length === 0 ? (
        <EmptyState message={messages.noItems} />
      ) : (
        <div className="recommendation-list">
          {recommendation.items.map((item, index) => (
            <RecommendationCard
              key={item.product.id}
              item={item}
              rank={index + 1}
              highlightedReason={SERVER_SEASON_NAMES[recommendation.season]}
              onTryOn={() => navigate(ROUTES.fitting(item.product.id))}
            />
          ))}
        </div>
      )}
    </PageLayout>
  )
}
