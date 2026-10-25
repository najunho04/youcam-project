import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ErrorCode } from '../../../src/common/type'
import type { AuthResponse } from '../../../src/common/type'
import { LoginPage } from '../../../src/feature/auth'
import { tokenStorage } from '../../../src/shared/auth'
import { setLanguage } from '../../../src/shared/i18n'
import { ROUTES } from '../../../src/shared/navigation'
import { stubFetchResponse, stubPendingFetch } from './fetchStub'

// 이 파일의 명세는 한국어 화면 기준이다. 영어 화면은 *.english.test.tsx 에서 확인한다.
beforeEach(() => setLanguage('ko'))
afterEach(() => setLanguage('en'))

const authResponse: AuthResponse = {
  accessToken: 'login-token',
  user: { id: 1, nickname: 'member', ageGroup: null, gender: null, personalColor: null },
}

function renderLoginPage() {
  render(
    <MemoryRouter initialEntries={[ROUTES.login]}>
      <Routes>
        <Route path={ROUTES.login} element={<LoginPage />} />
        <Route path={ROUTES.landing} element={<div>메인 화면</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

async function submitForm(nickname: string, password: string) {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('닉네임'), nickname)
  await user.type(screen.getByLabelText('비밀번호'), password)
  await user.click(screen.getByRole('button', { name: '로그인' }))
}

describe('LoginPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('로그인 성공 시 토큰을 저장하고 메인 화면으로 이동한다', async () => {
    const fetchMock = stubFetchResponse(200, authResponse)
    renderLoginPage()

    await submitForm('member', 'password1234')

    expect(await screen.findByText('메인 화면')).toBeInTheDocument()
    expect(tokenStorage.get()).toBe('login-token')
    expect(fetchMock).toHaveBeenCalledWith('/api/auth/login', expect.objectContaining({ method: 'POST' }))
  })

  it('자격 증명이 틀리면 폼 아래에 에러 메시지를 보여준다', async () => {
    stubFetchResponse(401, { error: { code: ErrorCode.INVALID_CREDENTIALS, message: 'INVALID_CREDENTIALS' } })
    renderLoginPage()

    await submitForm('member', 'wrong-password')

    expect(await screen.findByRole('alert')).toHaveTextContent('닉네임 또는 비밀번호가 올바르지 않습니다')
    expect(tokenStorage.get()).toBeNull()
  })

  it('제출 중에는 버튼이 비활성화된다', async () => {
    const { respond } = stubPendingFetch()
    renderLoginPage()

    await submitForm('member', 'password1234')

    expect(screen.getByRole('button', { name: '로그인' })).toBeDisabled()
    respond(200, authResponse)
    expect(await screen.findByText('메인 화면')).toBeInTheDocument()
  })

  it('코디 카드 없이 가운데 정렬된 로그인 폼만 보여준다', () => {
    renderLoginPage()

    expect(screen.queryByRole('region', { name: 'ColorFit 코디' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '로그인' })).toBeInTheDocument()
  })
})
