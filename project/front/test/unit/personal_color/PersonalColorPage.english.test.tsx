import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ErrorCode, Season } from '../../../src/common/type'
import type { PersonalColorDto } from '../../../src/common/type'
import { PersonalColorPage } from '../../../src/feature/personal_color'
import { tokenStorage } from '../../../src/shared/auth'
import { ROUTES } from '../../../src/shared/navigation'
import { stubFetch } from './fetchStub'

const analyzedResponse: PersonalColorDto = {
  season: Season.SPRING_WARM,
  palette: ['#F7C59F'],
  selfieUrl: 'https://storage.test/selfies/1/face.jpg',
  bodyImageUrl: 'https://storage.test/body-images/1/body.jpg',
}

function renderPersonalColorPage() {
  render(
    <MemoryRouter initialEntries={[ROUTES.personalColor]}>
      <Routes>
        <Route path={ROUTES.personalColor} element={<PersonalColorPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

async function selectBothPhotosAndAnalyze() {
  await userEvent.upload(screen.getByLabelText('Choose face photo'), new File(['image'], 'face.jpg', { type: 'image/jpeg' }))
  await userEvent.upload(screen.getByLabelText('Choose upper-body photo'), new File(['image'], 'body.png', { type: 'image/png' }))
  await userEvent.click(screen.getByRole('button', { name: 'Analyze' }))
}

describe('PersonalColorPage 영어 화면', () => {
  beforeEach(() => {
    tokenStorage.set('valid-token')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('결과 시즌 이름과 설명을 영어로 보여준다', async () => {
    stubFetch([{ status: 200, body: analyzedResponse }])
    renderPersonalColorPage()

    await selectBothPhotosAndAnalyze()

    expect(await screen.findByRole('heading', { name: 'Spring Warm' })).toBeInTheDocument()
    expect(screen.getByText('Bright, warm colors bring your face to life.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next' })).toBeInTheDocument()
  })

  it('얼굴을 인식하지 못하면 영어 재촬영 안내를 보여준다', async () => {
    stubFetch([{ status: 422, body: { error: { code: ErrorCode.FACE_NOT_DETECTED, message: 'error_face_position_invalid' } } }])
    renderPersonalColorPage()

    await selectBothPhotosAndAnalyze()

    expect(await screen.findByRole('alert')).toHaveTextContent("We couldn't find your face. Please retake the face photo.")
  })
})
