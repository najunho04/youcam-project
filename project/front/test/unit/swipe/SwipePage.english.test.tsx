import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ErrorCode, Style } from '../../../src/common/type'
import { SwipePage } from '../../../src/feature/swipe'
import { tokenStorage } from '../../../src/shared/auth'
import { ROUTES } from '../../../src/shared/navigation'
import { stubFetch } from './fetchStub'

function renderSwipePage() {
  render(
    <MemoryRouter initialEntries={[ROUTES.swipe]}>
      <Routes>
        <Route path={ROUTES.swipe} element={<SwipePage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('SwipePage 영어 화면', () => {
  beforeEach(() => {
    tokenStorage.set('valid-token')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('카드와 좋아요·싫어요 버튼을 영어 이름으로 보여준다', async () => {
    stubFetch([{ status: 200, body: { cards: [{ pinId: 11, imageUrl: 'https://image.test/pins/11.jpg', style: Style.MINIMAL }] } }])
    renderSwipePage()

    expect(await screen.findByRole('group', { name: 'Outfit card' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Like' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Dislike' })).toBeInTheDocument()
  })

  it('PROFILE_REQUIRED 이면 서버 한국어 문구 대신 영어 안내와 버튼을 보여준다', async () => {
    stubFetch([{ status: 409, body: { error: { code: ErrorCode.PROFILE_REQUIRED, message: '나이대와 성별을 먼저 입력해 주세요' } } }])
    renderSwipePage()

    expect(await screen.findByText('Please tell us your age group and gender first.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Fill in your profile' })).toBeInTheDocument()
  })
})
