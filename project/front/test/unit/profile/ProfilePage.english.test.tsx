import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { UserDto } from '../../../src/common/type'
import { ProfilePage } from '../../../src/feature/profile'
import { tokenStorage } from '../../../src/shared/auth'
import { ROUTES } from '../../../src/shared/navigation'
import { stubFetchByMethod } from './fetchStub'

const newUser: UserDto = { id: 1, nickname: 'member', ageGroup: null, gender: null, personalColor: null }

describe('ProfilePage 영어 화면', () => {
  beforeEach(() => {
    tokenStorage.set('valid-token')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('제목·선택지·다음 버튼을 영어로 보여준다', async () => {
    stubFetchByMethod({ GET: [{ status: 200, body: newUser }] })
    render(
      <MemoryRouter initialEntries={[ROUTES.profile]}>
        <Routes>
          <Route path={ROUTES.profile} element={<ProfilePage />} />
        </Routes>
      </MemoryRouter>,
    )

    for (const label of ['Late teens', '20s', '30s', '40s+', 'Women', 'Men']) {
      expect(await screen.findByRole('radio', { name: label })).not.toBeChecked()
    }
    expect(screen.getByRole('heading', { name: 'Tell us about you' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Back' })).toBeInTheDocument()
  })
})
