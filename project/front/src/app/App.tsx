// 라우터 조립 지점. 슬라이스는 아래 '슬라이스 라우트' 구역에 자기 페이지 한 줄씩만 추가한다.
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { LandingPage, LoginPage, SignupPage } from '../feature/auth'
import { FittingPage } from '../feature/fitting'
import { PersonalColorPage } from '../feature/personal_color'
import { ProfilePage } from '../feature/profile'
import { RecommendationPage } from '../feature/recommendation'
import { SwipePage } from '../feature/swipe'
import { WardrobePage } from '../feature/wardrobe'
import { RequireAuth } from '../shared/auth'
import { useMessages } from '../shared/i18n'
import { ROUTES } from '../shared/navigation'
import { EmptyState, PageLayout } from '../shared/ui'

const NOT_READY_MESSAGES = { en: 'This page is not ready yet.', ko: '준비 중인 화면입니다' }

function NotReadyPage() {
  const message = useMessages(NOT_READY_MESSAGES)
  return (
    <PageLayout title="ColorFit">
      <EmptyState message={message} />
    </PageLayout>
  )
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* ---- 슬라이스 라우트 ---- */}
        <Route path={ROUTES.landing} element={<LandingPage />} />
        <Route path={ROUTES.signup} element={<SignupPage />} />
        <Route path={ROUTES.login} element={<LoginPage />} />
        <Route path={ROUTES.profile} element={<RequireAuth><ProfilePage /></RequireAuth>} />
        <Route path={ROUTES.wardrobe} element={<RequireAuth><WardrobePage /></RequireAuth>} />
        <Route path={ROUTES.personalColor} element={<RequireAuth><PersonalColorPage /></RequireAuth>} />
        <Route path={ROUTES.swipe} element={<RequireAuth><SwipePage /></RequireAuth>} />
        <Route path={ROUTES.recommendation} element={<RequireAuth><RecommendationPage /></RequireAuth>} />
        <Route path={ROUTES.fittingPattern} element={<RequireAuth><FittingPage /></RequireAuth>} />
        {/* ---- 슬라이스 라우트 끝 ---- */}
        <Route path="*" element={<NotReadyPage />} />
      </Routes>
    </BrowserRouter>
  )
}
