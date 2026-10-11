// 라우터 조립 지점. 슬라이스는 아래 '슬라이스 라우트' 구역에 자기 페이지 한 줄씩만 추가한다.
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { EmptyState, PageLayout } from '../shared/ui'

function NotReadyPage() {
  return (
    <PageLayout title="ColorFit">
      <EmptyState message="준비 중인 화면입니다" />
    </PageLayout>
  )
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* ---- 슬라이스 라우트 ---- */}
        {/* ---- 슬라이스 라우트 끝 ---- */}
        <Route path="*" element={<NotReadyPage />} />
      </Routes>
    </BrowserRouter>
  )
}
