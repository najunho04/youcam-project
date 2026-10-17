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

/** 이미지 배경색 이름. 메인 화면 배경이 같은 색으로 함께 바뀐다 (색 값은 auth.css). */
type HeroBackdrop = 'cream' | 'brown' | 'sky'

/** 대표 화면에서 번갈아 보여 줄 이미지. 스케치 → 실사 순서로 짝지어 둔다. */
const HERO_SLIDES: { source: string; backdrop: HeroBackdrop }[] = [
  { source: '/landing/hero-man-sketch.webp', backdrop: 'cream' },
  { source: '/landing/hero-man-photo.webp', backdrop: 'brown' },
  { source: '/landing/hero-woman-sketch.webp', backdrop: 'cream' },
  { source: '/landing/hero-woman-photo.webp', backdrop: 'sky' },
]
const HERO_IMAGE_INTERVAL_MILLISECONDS = 1750

/** 이어하기 이동 규칙: 프로필 → 퍼스널 컬러 → 추천 순으로 비어 있는 단계로 보낸다. */
function getContinueRoute(user: UserDto): string {
  if (user.ageGroup === null || user.gender === null) return ROUTES.profile
  if (user.personalColor === null) return ROUTES.personalColor
  return ROUTES.recommendation
}

/** 대표 이미지 순번을 일정 간격으로 넘긴다. */
function useHeroSlideIndex(): number {
  const [activeIndex, setActiveIndex] = useState(0)

  useEffect(() => {
    const intervalId = window.setInterval(
      () => setActiveIndex((index) => (index + 1) % HERO_SLIDES.length),
      HERO_IMAGE_INTERVAL_MILLISECONDS,
    )
    return () => window.clearInterval(intervalId)
  }, [])

  return activeIndex
}

/** 겹쳐 둔 대표 이미지 중 activeIndex 만 서서히 드러낸다 (스케치가 실사로 번지듯 전환). */
function LandingHero({ activeIndex }: { activeIndex: number }) {
  return (
    <div className="landing-hero" aria-hidden="true">
      {HERO_SLIDES.map((slide, index) => (
        <img
          key={slide.source}
          className={`landing-hero-image${index === activeIndex ? ' landing-hero-image-active' : ''}`}
          src={slide.source}
          alt=""
        />
      ))}
    </div>
  )
}

export function LandingPage() {
  const [isLoggedIn, setIsLoggedIn] = useState(() => tokenStorage.get() !== null)

  const heroSlideIndex = useHeroSlideIndex()

  const handleUnauthorized = useCallback(() => setIsLoggedIn(false), [])

  function handleLogout() {
    tokenStorage.clear()
    setIsLoggedIn(false)
  }

  return (
    <PageLayout width="wide">
      <div className="landing" data-hero-backdrop={HERO_SLIDES[heroSlideIndex].backdrop}>
        <div className="landing-copy">
          <p className="landing-eyebrow">사진 한 장에서 피팅까지</p>
          <h1 className="landing-display">
            나에게 어울리고,
            <br />
            내 취향인 옷.
          </h1>
          <p className="page-lede landing-lede">{SERVICE_INTRODUCTION}</p>
          <div className="landing-actions">
            {isLoggedIn ? (
              <LoggedInSection onLogout={handleLogout} onUnauthorized={handleUnauthorized} />
            ) : (
              <LoggedOutSection />
            )}
          </div>
        </div>

        <LandingHero activeIndex={heroSlideIndex} />
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
