import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErrorCode } from '../../../src/common/type'
import type { AuthResponse } from '../../../src/common/type'
import { SignupPage } from '../../../src/feature/auth'
import { tokenStorage } from '../../../src/shared/auth'
import { ROUTES } from '../../../src/shared/navigation'
import { stubFetchResponse, stubPendingFetch } from './fetchStub'

const authResponse: AuthResponse = {
  accessToken: 'signup-token',
  user: { id: 1, nickname: 'newbie', ageGroup: null, gender: null, personalColor: null },
}

function renderSignupPage() {
  render(
    <MemoryRouter initialEntries={[ROUTES.signup]}>
      <Routes>
        <Route path={ROUTES.signup} element={<SignupPage />} />
        <Route path={ROUTES.profile} element={<div>프로필 화면</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

async function submitForm(nickname: string, password: string) {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('닉네임'), nickname)
  await user.type(screen.getByLabelText('비밀번호'), password)
  await user.click(screen.getByRole('button', { name: '가입하기' }))
}

describe('SignupPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('가입 성공 시 토큰을 저장하고 프로필 화면으로 이동한다', async () => {
    const fetchMock = stubFetchResponse(200, authResponse)
    renderSignupPage()

    await submitForm('newbie', 'password1234')

    expect(await screen.findByText('프로필 화면')).toBeInTheDocument()
    expect(tokenStorage.get()).toBe('signup-token')
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/signup',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ nickname: 'newbie', password: 'password1234' }) }),
    )
  })

  it('닉네임이 이미 있으면 폼 아래에 에러 메시지를 보여준다', async () => {
    stubFetchResponse(409, { error: { code: ErrorCode.NICKNAME_TAKEN, message: 'NICKNAME_TAKEN' } })
    renderSignupPage()

    await submitForm('duplicate', 'password1234')

    expect(await screen.findByRole('alert')).toHaveTextContent('이미 사용 중인 닉네임입니다')
    expect(tokenStorage.get()).toBeNull()
  })

  it('제출 중에는 버튼이 비활성화된다', async () => {
    const { respond } = stubPendingFetch()
    renderSignupPage()

    await submitForm('newbie', 'password1234')

    expect(screen.getByRole('button', { name: '가입하기' })).toBeDisabled()
    respond(200, authResponse)
    expect(await screen.findByText('프로필 화면')).toBeInTheDocument()
  })
})
