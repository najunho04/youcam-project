import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AgeGroup, ErrorCode, Gender } from '../../../src/common/type'
import type { UserDto } from '../../../src/common/type'
import { ProfilePage } from '../../../src/feature/profile'
import { tokenStorage } from '../../../src/shared/auth'
import { ROUTES } from '../../../src/shared/navigation'
import { stubFetchByMethod } from './fetchStub'

const newUser: UserDto = { id: 1, nickname: 'member', ageGroup: null, gender: null, personalColor: null }
const profiledUser: UserDto = { ...newUser, ageGroup: AgeGroup.THIRTIES, gender: Gender.MALE }

function renderProfilePage() {
  render(
    <MemoryRouter initialEntries={[ROUTES.profile]}>
      <Routes>
        <Route path={ROUTES.profile} element={<ProfilePage />} />
        <Route path={ROUTES.personalColor} element={<div>퍼스널컬러 화면</div>} />
        <Route path={ROUTES.login} element={<div>로그인 화면</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProfilePage', () => {
  beforeEach(() => {
    tokenStorage.set('valid-token')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('나이대 4개와 성별 2개 선택지를 보여준다', async () => {
    stubFetchByMethod({ GET: [{ status: 200, body: newUser }] })
    renderProfilePage()

    for (const label of ['10대 후반', '20대', '30대', '40대 이상', '여성', '남성']) {
      expect(await screen.findByRole('radio', { name: label })).not.toBeChecked()
    }
  })

  it('나이대와 성별을 모두 선택해야 다음 버튼이 활성화된다', async () => {
    stubFetchByMethod({ GET: [{ status: 200, body: newUser }] })
    renderProfilePage()

    const nextButton = await screen.findByRole('button', { name: '다음' })
    expect(nextButton).toBeDisabled()
    await userEvent.click(screen.getByRole('radio', { name: '20대' }))
    expect(nextButton).toBeDisabled()
    await userEvent.click(screen.getByRole('radio', { name: '여성' }))
    expect(nextButton).toBeEnabled()
  })

  it('이미 저장된 값이 있으면 선택된 상태로 보여준다', async () => {
    stubFetchByMethod({ GET: [{ status: 200, body: profiledUser }] })
    renderProfilePage()

    expect(await screen.findByRole('radio', { name: '30대' })).toBeChecked()
    expect(screen.getByRole('radio', { name: '남성' })).toBeChecked()
    expect(screen.getByRole('button', { name: '다음' })).toBeEnabled()
  })

  it('다음을 누르면 선택값을 저장하고 퍼스널컬러 화면으로 이동한다', async () => {
    const { fetchMock } = stubFetchByMethod({
      GET: [{ status: 200, body: newUser }],
      PUT: [{ status: 200, body: { ...newUser, ageGroup: AgeGroup.LATE_TEENS, gender: Gender.FEMALE } }],
    })
    renderProfilePage()

    await userEvent.click(await screen.findByRole('radio', { name: '10대 후반' }))
    await userEvent.click(screen.getByRole('radio', { name: '여성' }))
    await userEvent.click(screen.getByRole('button', { name: '다음' }))

    expect(await screen.findByText('퍼스널컬러 화면')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/users/me/profile',
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify({ ageGroup: AgeGroup.LATE_TEENS, gender: Gender.FEMALE }),
      }),
    )
  })

  it('저장 중에는 로딩을 보여주고 다음 버튼이 비활성화된다', async () => {
    const { respondPending } = stubFetchByMethod({
      GET: [{ status: 200, body: profiledUser }],
      PUT: ['pending'],
    })
    renderProfilePage()

    await screen.findByRole('radio', { name: '30대' })
    await userEvent.click(screen.getByRole('button', { name: '다음' }))

    expect(screen.getByRole('button', { name: '다음' })).toBeDisabled()
    expect(screen.getByRole('status')).toBeInTheDocument()
    respondPending(200, profiledUser)
    expect(await screen.findByText('퍼스널컬러 화면')).toBeInTheDocument()
  })

  it('저장에 실패하면 에러 메시지를 보여주고 다시 누를 수 있다', async () => {
    stubFetchByMethod({
      GET: [{ status: 200, body: profiledUser }],
      PUT: [{ status: 422, body: { error: { code: ErrorCode.VALIDATION_ERROR, message: 'VALIDATION_ERROR' } } }],
    })
    renderProfilePage()

    await screen.findByRole('radio', { name: '30대' })
    await userEvent.click(screen.getByRole('button', { name: '다음' }))

    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '다음' })).toBeEnabled()
    expect(screen.queryByText('퍼스널컬러 화면')).not.toBeInTheDocument()
  })

  it('기존 값 조회가 네트워크 에러면 에러 메시지를 보여주고 다시 시도할 수 있다', async () => {
    stubFetchByMethod({ GET: ['network-failure', { status: 200, body: profiledUser }] })
    renderProfilePage()

    expect(await screen.findByRole('alert')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: '다시 시도' }))

    expect(await screen.findByRole('radio', { name: '30대' })).toBeChecked()
  })

  it('토큰이 만료되어 401 이면 로그인 화면으로 이동한다', async () => {
    stubFetchByMethod({ GET: [{ status: 401, body: { error: { code: ErrorCode.UNAUTHORIZED, message: 'UNAUTHORIZED' } } }] })
    renderProfilePage()

    expect(await screen.findByText('로그인 화면')).toBeInTheDocument()
    expect(tokenStorage.get()).toBeNull()
  })
})
