import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { WardrobePage } from '../../../src/feature/wardrobe'
import { tokenStorage } from '../../../src/shared/auth'
import { ROUTES } from '../../../src/shared/navigation'

describe('WardrobePage 영어 화면', () => {
  beforeEach(() => {
    tokenStorage.set('valid-token')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('버튼을 영어로 보여주고, 4장을 넘게 고르면 영어 에러를 보여준다', async () => {
    render(
      <MemoryRouter initialEntries={[ROUTES.wardrobe]}>
        <Routes>
          <Route path={ROUTES.wardrobe} element={<WardrobePage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByRole('button', { name: 'Upload' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Skip' })).toBeEnabled()
    const photos = Array.from({ length: 5 }, (_, index) => new File(['image'], `${index}.jpg`, { type: 'image/jpeg' }))
    await userEvent.upload(screen.getByLabelText('Choose photos'), photos)

    expect(await screen.findByRole('alert')).toHaveTextContent('You can choose up to 4 photos.')
  })
})
