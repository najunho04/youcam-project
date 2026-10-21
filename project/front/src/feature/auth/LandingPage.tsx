import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import type { UserDto } from '../../common/type'
import { ApiError, useDescribeError } from '../../shared/api'
import { tokenStorage } from '../../shared/auth'
import { ROUTES } from '../../shared/navigation'
import { LanguageToggle, useMessages } from '../../shared/i18n'
import './auth.css'
import { fetchMe } from './api'
import { AUTH_MESSAGES } from './messages'

/** 메인 화면 전체를 채우는 3D 갤러리 (design-sample/web-main-sample.html 원본을 그대로 옮긴 정적 페이지) */
const GALLERY_SOURCE = '/landing/gallery.html'

/** 이어하기 이동 규칙: 프로필 → 퍼스널 컬러 → 추천 순으로 비어 있는 단계로 보낸다. */
function getContinueRoute(user: UserDto): string {
  if (user.ageGroup === null || user.gender === null) return ROUTES.profile
  if (user.personalColor === null) return ROUTES.personalColor
  return ROUTES.recommendation
}

export function LandingPage() {
  const messages = useMessages(AUTH_MESSAGES).landing
  const [isLoggedIn, setIsLoggedIn] = useState(() => tokenStorage.get() !== null)

  const handleUnauthorized = useCallback(() => setIsLoggedIn(false), [])

  function handleLogout() {
    tokenStorage.clear()
    setIsLoggedIn(false)
  }

  return (
    <div className="landing">
      <iframe className="landing-gallery" src={GALLERY_SOURCE} title={messages.galleryTitle} />
      <h1 className="visually-hidden">ColorFit</h1>
      <nav className="landing-menu" aria-label={messages.accountMenu}>
        {isLoggedIn ? (
          <LoggedInMenu onLogout={handleLogout} onUnauthorized={handleUnauthorized} />
        ) : (
          <Link to={ROUTES.login} className="landing-menu-link">
            {messages.login}
          </Link>
        )}
      </nav>
      <LanguageToggle className="landing-language" />
    </div>
  )
}

/** 로그인 상태: 비어 있는 단계로 이어가기 · 로그아웃 */
function LoggedInMenu({ onLogout, onUnauthorized }: { onLogout: () => void; onUnauthorized: () => void }) {
  const navigate = useNavigate()
  const messages = useMessages(AUTH_MESSAGES).landing
  const describeError = useDescribeError()
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
        else setErrorMessage(describeError(error))
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
      {errorMessage && (
        <p className="landing-menu-note" role="alert">
          {errorMessage}{' '}
          <button type="button" className="landing-menu-link" onClick={handleRetry}>
            {messages.retry}
          </button>
        </p>
      )}
      <button
        type="button"
        className="landing-menu-link landing-menu-link-small"
        disabled={user === null}
        onClick={() => user && navigate(getContinueRoute(user))}
      >
        {messages.continue}
      </button>
      <button type="button" className="landing-menu-link landing-menu-link-small" onClick={onLogout}>
        {messages.logout}
      </button>
    </>
  )
}
