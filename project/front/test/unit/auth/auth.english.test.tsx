import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErrorCode } from '../../../src/common/type'
import { LandingPage, LoginPage } from '../../../src/feature/auth'
import { setLanguage } from '../../../src/shared/i18n'
import { ROUTES } from '../../../src/shared/navigation'
import { stubFetchResponse } from './fetchStub'

function renderAt(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path={ROUTES.landing} element={<LandingPage />} />
        <Route path={ROUTES.login} element={<LoginPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('auth 영어 화면', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    setLanguage('en')
  })

  it('기본 언어는 영어다: 로그인 화면 제목·입력칸·버튼이 영어로 보인다', () => {
    renderAt(ROUTES.login)

    expect(screen.getByRole('heading', { name: 'Log in' })).toBeInTheDocument()
    expect(screen.getByLabelText('Nickname')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Log in' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Sign up' })).toBeInTheDocument()
  })

  it('자격 증명이 틀리면 영어 에러 문구를 보여준다', async () => {
    stubFetchResponse(401, { error: { code: ErrorCode.INVALID_CREDENTIALS, message: '닉네임 또는 비밀번호가 올바르지 않습니다' } })
    renderAt(ROUTES.login)

    await userEvent.type(screen.getByLabelText('Nickname'), 'member')
    await userEvent.type(screen.getByLabelText('Password'), 'wrong-password')
    await userEvent.click(screen.getByRole('button', { name: 'Log in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Wrong nickname or password.')
  })

  it('KO 를 누르면 한국어로 바뀌고, 고른 언어를 기억한다', async () => {
    renderAt(ROUTES.login)

    await userEvent.click(screen.getByRole('button', { name: 'KO' }))

    expect(screen.getByRole('heading', { name: '로그인' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'KO' })).toHaveAttribute('aria-pressed', 'true')
    expect(localStorage.getItem('colorfit.language')).toBe('ko')
    expect(document.documentElement.lang).toBe('ko')
  })

  it('메인 화면도 언어 전환을 따른다: LOGIN ↔ 로그인', async () => {
    renderAt(ROUTES.landing)

    expect(screen.getByRole('link', { name: 'LOGIN' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'KO' }))
    expect(screen.getByRole('link', { name: '로그인' })).toBeInTheDocument()
  })
})
