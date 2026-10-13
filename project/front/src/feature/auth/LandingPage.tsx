import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import type { UserDto } from '../../common/type'
import { ApiError } from '../../shared/api'
import { tokenStorage } from '../../shared/auth'
import { ROUTES } from '../../shared/navigation'
import { Button, ErrorMessage, Loading, PageLayout, buttonClassName } from '../../shared/ui'
import './auth.css'
import { fetchMe } from './api'

const SERVICE_INTRODUCTION = '퍼스널 컬러와 취향으로 나에게 맞는 옷을 추천해 드려요'

const LANDING_STEPS = [
  { icon: '📷', title: '사진 두 장', description: '퍼스널컬러 진단' },
  { icon: '👆', title: '스와이프 20번', description: '내 취향 분석' },
  { icon: '👕', title: '추천 상의 입어보기', description: '바로 구매까지' },
]

/** 이어하기 이동 규칙: 프로필 → 퍼스널 컬러 → 추천 순으로 비어 있는 단계로 보낸다. */
function getContinueRoute(user: UserDto): string {
  if (user.ageGroup === null || user.gender === null) return ROUTES.profile
  if (user.personalColor === null) return ROUTES.personalColor
  return ROUTES.recommendation
}

export function LandingPage() {
  const [isLoggedIn, setIsLoggedIn] = useState(() => tokenStorage.get() !== null)

  const handleUnauthorized = useCallback(() => setIsLoggedIn(false), [])

  function handleLogout() {
    tokenStorage.clear()
    setIsLoggedIn(false)
  }

  return (
    <PageLayout width="wide">
      <div className="landing">
        <div className="landing-hero" aria-hidden="true">
          <span className="landing-orb landing-orb-warm" />
          <span className="landing-orb landing-orb-cool" />
          <span className="landing-orb landing-orb-olive" />
          <span className="landing-orb landing-orb-rose" />
        </div>
        <div className="landing-copy">
          <h1 className="landing-display">
            나에게 어울리고,
            <br />
            내 취향인 옷.
          </h1>
          <p className="page-lede landing-lede">{SERVICE_INTRODUCTION}</p>
          <ol className="landing-steps">
            {LANDING_STEPS.map((step) => (
              <li key={step.title}>
                <span className="landing-step-icon" aria-hidden="true">
                  {step.icon}
                </span>
                <span>
                  {step.title}
                  <small>{step.description}</small>
                </span>
              </li>
            ))}
          </ol>
          <div className="landing-actions">
            {isLoggedIn ? (
              <LoggedInSection onLogout={handleLogout} onUnauthorized={handleUnauthorized} />
            ) : (
              <LoggedOutSection />
            )}
          </div>
        </div>
      </div>
    </PageLayout>
  )
}

function LoggedOutSection() {
  return (
    <>
      <Link to={ROUTES.signup} className={buttonClassName('primary')}>
        시작하기
      </Link>
      <p className="landing-login">
        이미 계정이 있나요? <Link to={ROUTES.login}>로그인</Link>
      </p>
    </>
  )
}

function LoggedInSection({ onLogout, onUnauthorized }: { onLogout: () => void; onUnauthorized: () => void }) {
  const navigate = useNavigate()
  const [user, setUser] = useState<UserDto | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [requestCount, setRequestCount] = useState(0)

  useEffect(() => {
    let isCancelled = false
    fetchMe()
      .then((fetchedUser) => {
        if (!isCancelled) setUser(fetchedUser)
      })
      .catch((error: unknown) => {
        if (isCancelled) return
        // 401 이면 shared/api 가 토큰을 지운다 → 비로그인 화면으로
        if (error instanceof ApiError && error.status === 401) onUnauthorized()
        else setErrorMessage(error instanceof Error ? error.message : '요청에 실패했습니다')
      })
    return () => {
      isCancelled = true
    }
  }, [requestCount, onUnauthorized])

  function handleRetry() {
    setErrorMessage(null)
    setRequestCount((count) => count + 1)
  }

  return (
    <>
      {errorMessage ? (
        <ErrorMessage message={errorMessage} onRetry={handleRetry} />
      ) : user ? (
        <p className="headline landing-greeting">{user.nickname} 님, 반가워요</p>
      ) : (
        <Loading />
      )}
      <Button disabled={user === null} onClick={() => user && navigate(getContinueRoute(user))}>
        이어하기
      </Button>
      <Button variant="secondary" onClick={onLogout}>
        로그아웃
      </Button>
    </>
  )
}
