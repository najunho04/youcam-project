import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AgeGroup, ErrorCode, Gender, Season } from '../../../src/common/type'
import type { UserDto } from '../../../src/common/type'
import { LandingPage } from '../../../src/feature/auth'
import { tokenStorage } from '../../../src/shared/auth'
import { ROUTES } from '../../../src/shared/navigation'
import { stubFetchResponse, stubNetworkFailure, stubPendingFetch } from './fetchStub'

const newUser: UserDto = { id: 1, nickname: 'member', ageGroup: null, gender: null, personalColor: null }
const profiledUser: UserDto = { ...newUser, ageGroup: AgeGroup.TWENTIES, gender: Gender.FEMALE }
const completeUser: UserDto = {
  ...profiledUser,
  personalColor: {
    season: Season.AUTUMN_WARM,
    palette: ['#C19A6B'],
    selfieUrl: 'https://storage.test/selfie.jpg',
    bodyImageUrl: 'https://storage.test/body.jpg',
  },
}

function renderLandingPage() {
  render(
    <MemoryRouter initialEntries={[ROUTES.landing]}>
      <Routes>
        <Route path={ROUTES.landing} element={<LandingPage />} />
        <Route path={ROUTES.signup} element={<div>가입 화면</div>} />
        <Route path={ROUTES.login} element={<div>로그인 화면</div>} />
        <Route path={ROUTES.profile} element={<div>프로필 화면</div>} />
        <Route path={ROUTES.personalColor} element={<div>퍼스널컬러 화면</div>} />
        <Route path={ROUTES.recommendation} element={<div>추천 화면</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('LandingPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  describe('비로그인', () => {
    it('시작하기는 가입 화면으로 이동하고 users/me 를 호출하지 않는다', async () => {
      const fetchMock = stubFetchResponse(200, newUser)
      renderLandingPage()

      await userEvent.click(screen.getByRole('link', { name: '시작하기' }))

      expect(await screen.findByText('가입 화면')).toBeInTheDocument()
      expect(fetchMock).not.toHaveBeenCalled()
    })

    it('로그인 링크는 로그인 화면으로 이동한다', async () => {
      stubFetchResponse(200, newUser)
      renderLandingPage()

      await userEvent.click(screen.getByRole('link', { name: '로그인' }))

      expect(await screen.findByText('로그인 화면')).toBeInTheDocument()
    })
  })

  describe('로그인', () => {
    it('users/me 로딩 중에는 이어하기가 비활성이고, 완료되면 닉네임 인사를 보여준다', async () => {
      tokenStorage.set('valid-token')
      const { fetchMock, respond } = stubPendingFetch()
      renderLandingPage()

      expect(screen.getByRole('button', { name: '이어하기' })).toBeDisabled()
      respond(200, newUser)

      expect(await screen.findByText('member 님, 반가워요')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: '이어하기' })).toBeEnabled()
      expect(fetchMock).toHaveBeenCalledWith('/api/users/me', expect.objectContaining({ method: 'GET' }))
    })

    it.each([
      ['ageGroup·gender 가 없으면 프로필', newUser, '프로필 화면'],
      ['personalColor 가 없으면 퍼스널컬러', profiledUser, '퍼스널컬러 화면'],
      ['모두 있으면 추천', completeUser, '추천 화면'],
    ])('이어하기: %s 화면으로 이동한다', async (_, user, expectedScreen) => {
      tokenStorage.set('valid-token')
      stubFetchResponse(200, user)
      renderLandingPage()

      await screen.findByText('member 님, 반가워요')
      await userEvent.click(screen.getByRole('button', { name: '이어하기' }))

      expect(await screen.findByText(expectedScreen)).toBeInTheDocument()
    })

    it('ageGroup 만 있고 gender 가 없으면 프로필 화면으로 이동한다', async () => {
      tokenStorage.set('valid-token')
      stubFetchResponse(200, { ...completeUser, gender: null })
      renderLandingPage()

      await screen.findByText('member 님, 반가워요')
      await userEvent.click(screen.getByRole('button', { name: '이어하기' }))

      expect(await screen.findByText('프로필 화면')).toBeInTheDocument()
    })

    it('로그아웃하면 토큰을 지우고 비로그인 화면으로 바뀐다', async () => {
      tokenStorage.set('valid-token')
      const fetchMock = stubFetchResponse(200, newUser)
      renderLandingPage()

      await screen.findByText('member 님, 반가워요')
      await userEvent.click(screen.getByRole('button', { name: '로그아웃' }))

      expect(tokenStorage.get()).toBeNull()
      expect(screen.getByRole('link', { name: '시작하기' })).toBeInTheDocument()
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })

    it('users/me 가 401 이면 비로그인 화면으로 바뀐다', async () => {
      tokenStorage.set('expired-token')
      stubFetchResponse(401, { error: { code: ErrorCode.UNAUTHORIZED, message: 'UNAUTHORIZED' } })
      renderLandingPage()

      expect(await screen.findByRole('link', { name: '시작하기' })).toBeInTheDocument()
      expect(tokenStorage.get()).toBeNull()
    })

    it('네트워크 에러면 에러 메시지를 보여주고 다시 시도할 수 있다', async () => {
      tokenStorage.set('valid-token')
      stubNetworkFailure()
      renderLandingPage()

      expect(await screen.findByRole('alert')).toBeInTheDocument()
      stubFetchResponse(200, newUser)
      await userEvent.click(screen.getByRole('button', { name: '다시 시도' }))

      expect(await screen.findByText('member 님, 반가워요')).toBeInTheDocument()
    })
  })
})
