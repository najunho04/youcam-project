import { act, render, screen, waitFor, within } from '@testing-library/react'
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
    it('START 는 로그인 화면으로 이동하고 users/me 를 호출하지 않는다', async () => {
      const fetchMock = stubFetchResponse(200, newUser)
      renderLandingPage()

      await userEvent.click(screen.getByRole('link', { name: 'START' }))

      expect(await screen.findByText('로그인 화면')).toBeInTheDocument()
      expect(fetchMock).not.toHaveBeenCalled()
    })
  })

  describe('로그인', () => {
    it('users/me 로딩 중에는 CONTINUE 가 비활성이고, 완료되면 닉네임 인사를 보여준다', async () => {
      tokenStorage.set('valid-token')
      const { fetchMock, respond } = stubPendingFetch()
      renderLandingPage()

      expect(screen.getByRole('button', { name: 'CONTINUE' })).toBeDisabled()
      respond(200, newUser)

      await waitFor(() => expect(screen.getByRole('button', { name: 'CONTINUE' })).toBeEnabled())
      expect(fetchMock).toHaveBeenCalledWith('/api/users/me', expect.objectContaining({ method: 'GET' }))
    })

    it.each([
      ['ageGroup·gender 가 없으면 프로필', newUser, '프로필 화면'],
      ['personalColor 가 없으면 퍼스널컬러', profiledUser, '퍼스널컬러 화면'],
      ['모두 있으면 추천', completeUser, '추천 화면'],
    ])('CONTINUE: %s 화면으로 이동한다', async (_, user, expectedScreen) => {
      tokenStorage.set('valid-token')
      stubFetchResponse(200, user)
      renderLandingPage()

      await waitFor(() => expect(screen.getByRole('button', { name: 'CONTINUE' })).toBeEnabled())
      await userEvent.click(screen.getByRole('button', { name: 'CONTINUE' }))

      expect(await screen.findByText(expectedScreen)).toBeInTheDocument()
    })

    it('ageGroup 만 있고 gender 가 없으면 프로필 화면으로 이동한다', async () => {
      tokenStorage.set('valid-token')
      stubFetchResponse(200, { ...completeUser, gender: null })
      renderLandingPage()

      await waitFor(() => expect(screen.getByRole('button', { name: 'CONTINUE' })).toBeEnabled())
      await userEvent.click(screen.getByRole('button', { name: 'CONTINUE' }))

      expect(await screen.findByText('프로필 화면')).toBeInTheDocument()
    })

    it('로그아웃하면 토큰을 지우고 비로그인 화면으로 바뀐다', async () => {
      tokenStorage.set('valid-token')
      const fetchMock = stubFetchResponse(200, newUser)
      renderLandingPage()

      await waitFor(() => expect(screen.getByRole('button', { name: 'CONTINUE' })).toBeEnabled())
      await userEvent.click(screen.getByRole('button', { name: 'LOGOUT' }))

      expect(tokenStorage.get()).toBeNull()
      expect(screen.getByRole('link', { name: 'START' })).toBeInTheDocument()
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })

    it('users/me 가 401 이면 비로그인 화면으로 바뀐다', async () => {
      tokenStorage.set('expired-token')
      stubFetchResponse(401, { error: { code: ErrorCode.UNAUTHORIZED, message: 'UNAUTHORIZED' } })
      renderLandingPage()

      expect(await screen.findByRole('link', { name: 'START' })).toBeInTheDocument()
      expect(tokenStorage.get()).toBeNull()
    })

    it('네트워크 에러면 에러 메시지를 보여주고 다시 시도할 수 있다', async () => {
      tokenStorage.set('valid-token')
      stubNetworkFailure()
      renderLandingPage()

      expect(await screen.findByRole('alert')).toBeInTheDocument()
      stubFetchResponse(200, newUser)
      await userEvent.click(screen.getByRole('button', { name: 'RETRY' }))

      await waitFor(() => expect(screen.getByRole('button', { name: 'CONTINUE' })).toBeEnabled())
    })
  })

  describe('반원 코디 카드', () => {
    function startButton() {
      return screen.getByRole('button', { name: 'Get started with ColorFit looks' })
    }

    function cardCount() {
      return within(screen.getByRole('region', { name: 'ColorFit looks' })).getByText(/\d{2} \/ 05/)
    }

    afterEach(() => {
      vi.useRealTimers()
    })

    it('갤러리 대신 코디 일러스트 5장을 반원으로 펼쳐 보여주고, 첫 장이 메인이다', () => {
      stubFetchResponse(200, newUser)
      renderLandingPage()

      const wheel = screen.getByRole('region', { name: 'ColorFit looks' })
      expect(within(wheel).getAllByRole('img')).toHaveLength(5)
      expect(cardCount()).toHaveTextContent('01 / 05')
    })

    it('시간이 지나면 다음 카드가 돌아서 메인이 된다', () => {
      vi.useFakeTimers()
      stubFetchResponse(200, newUser)
      renderLandingPage()

      act(() => {
        vi.advanceTimersByTime(3500)
      })

      expect(cardCount()).toHaveTextContent('02 / 05')
    })

    it('옆 카드를 누르면 그 카드가 메인으로 돌아온다', async () => {
      stubFetchResponse(200, newUser)
      renderLandingPage()

      await userEvent.click(screen.getByRole('button', { name: 'Bring Blue gingham shirt with brown trousers to the front' }))

      expect(cardCount()).toHaveTextContent('02 / 05')
    })

    it('비로그인이면 메인 카드를 눌러 로그인 화면으로 이동한다', async () => {
      const fetchMock = stubFetchResponse(200, newUser)
      renderLandingPage()

      await userEvent.click(startButton())

      expect(await screen.findByText('로그인 화면')).toBeInTheDocument()
      expect(fetchMock).not.toHaveBeenCalled()
    })

    it.each([
      ['ageGroup·gender 가 없으면 프로필', newUser, '프로필 화면'],
      ['personalColor 가 없으면 퍼스널컬러', profiledUser, '퍼스널컬러 화면'],
      ['모두 있으면 추천', completeUser, '추천 화면'],
    ])('로그인 상태면 메인 카드를 눌러 CONTINUE 와 같은 곳으로 간다: %s', async (_, user, expectedScreen) => {
      tokenStorage.set('valid-token')
      stubFetchResponse(200, user)
      renderLandingPage()

      await userEvent.click(startButton())

      expect(await screen.findByText(expectedScreen)).toBeInTheDocument()
    })

    it('토큰이 만료되어 401 이면 메인 카드를 눌렀을 때 로그인 화면으로 이동한다', async () => {
      tokenStorage.set('expired-token')
      renderLandingPage()
      await screen.findByRole('button', { name: 'CONTINUE' })
      stubFetchResponse(401, { error: { code: ErrorCode.UNAUTHORIZED, message: 'UNAUTHORIZED' } })

      await userEvent.click(startButton())

      expect(await screen.findByText('로그인 화면')).toBeInTheDocument()
    })
  })
})
