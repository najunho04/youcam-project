import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ErrorCode, Season, SeasonSubtype } from '../../../src/common/type'
import type { PersonalColorDto } from '../../../src/common/type'
import { PersonalColorPage } from '../../../src/feature/personal_color'
import { tokenStorage } from '../../../src/shared/auth'
import { ROUTES } from '../../../src/shared/navigation'
import { stubFetch } from './fetchStub'

const analyzedResponse: PersonalColorDto = {
  season: Season.SPRING_WARM,
  subtype: SeasonSubtype.TRUE,
  palette: ['#F7C59F'],
  avoidPalette: ['#111111'],
  analysis: {
    faceColors: {
      skin: '#B07B4F', lip: '#B5553A', eye: '#3B2414', eyebrow: '#3A2618', hair: '#2E1C10',
      eyeColorName: 'Brown', hairColorName: null,
    },
    warmth: 1.39,
    depth: -0.83,
    clarity: 0.33,
    skinLightness: 55.96,
    contrast: 43.82,
  },
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
  await screen.findByRole('img', { name: 'Face photo preview' })
  await userEvent.upload(screen.getByLabelText('Choose upper-body photo'), new File(['image'], 'body.png', { type: 'image/png' }))
  await screen.findByRole('img', { name: 'Upper-body photo preview' })
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
    expect(screen.getByText('True Spring')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Why this result' })).toBeInTheDocument()
    expect(screen.getByText(/Spring Warm\. Your undertone stands out most, so you are a True type\./)).toBeInTheDocument()
  })

  it('얼굴을 인식하지 못하면 영어 재촬영 안내를 보여준다', async () => {
    stubFetch([{ status: 422, body: { error: { code: ErrorCode.FACE_NOT_DETECTED, message: 'error_face_position_invalid' } } }])
    renderPersonalColorPage()

    await selectBothPhotosAndAnalyze()

    expect(await screen.findByRole('alert')).toHaveTextContent("We couldn't find your face. Please retake the face photo.")
  })
})
