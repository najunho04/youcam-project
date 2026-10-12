import { render, screen, within } from '@testing-library/react'
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
  season: Season.AUTUMN_WARM,
  palette: ['#C19A6B', '#D8C3A5', '#8F8650'],
  selfieUrl: 'https://storage.test/selfies/1/face.jpg',
  bodyImageUrl: 'https://storage.test/body-images/1/body.jpg',
}

function imageFile(name: string, type = 'image/jpeg'): File {
  return new File(['image-bytes'], name, { type })
}

function renderPersonalColorPage() {
  render(
    <MemoryRouter initialEntries={[ROUTES.personalColor]}>
      <Routes>
        <Route path={ROUTES.personalColor} element={<PersonalColorPage />} />
        <Route path={ROUTES.swipe} element={<div>스와이프 화면</div>} />
        <Route path={ROUTES.login} element={<div>로그인 화면</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

function selfieInput(): HTMLInputElement {
  return screen.getByLabelText('얼굴 사진 선택')
}

function bodyImageInput(): HTMLInputElement {
  return screen.getByLabelText('상반신 사진 선택')
}

function analyzeButton(): HTMLElement {
  return screen.getByRole('button', { name: '분석하기' })
}

async function selectBothPhotos() {
  await userEvent.upload(selfieInput(), imageFile('face.jpg'))
  await userEvent.upload(bodyImageInput(), imageFile('body.png', 'image/png'))
}

describe('PersonalColorPage', () => {
  beforeEach(() => {
    tokenStorage.set('valid-token')
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: vi.fn((file: File) => `blob:${file.name}`),
    })
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('사진 2칸에 각각 가이드와 카메라 촬영 가능한 파일 선택을 보여준다', () => {
    renderPersonalColorPage()

    for (const input of [selfieInput(), bodyImageInput()]) {
      expect(input).toHaveAttribute('type', 'file')
      expect(input).toHaveAttribute('accept', 'image/*')
      expect(input).toHaveAttribute('capture', 'user')
    }
    expect(screen.getByText(/정면, 자연광, 화장 최소화, 얼굴이 화면을 가득 채우게/)).toBeInTheDocument()
    expect(screen.getByText(/정면으로 서서, 가슴 위 상반신과 어깨가 보이게, 혼자 나오게/)).toBeInTheDocument()
  })

  it('두 장을 모두 선택해야 분석하기가 활성화되고 각 칸에 미리보기를 보여준다', async () => {
    renderPersonalColorPage()

    expect(analyzeButton()).toBeDisabled()
    await userEvent.upload(selfieInput(), imageFile('face.jpg'))
    expect(screen.getByRole('img', { name: '얼굴 사진 미리보기' })).toHaveAttribute('src', 'blob:face.jpg')
    expect(analyzeButton()).toBeDisabled()
    await userEvent.upload(bodyImageInput(), imageFile('body.png', 'image/png'))
    expect(screen.getByRole('img', { name: '상반신 사진 미리보기' })).toHaveAttribute('src', 'blob:body.png')
    expect(analyzeButton()).toBeEnabled()
  })

  it('분석하기를 누르면 selfie·bodyImage 필드로 보낸다', async () => {
    const { fetchMock } = stubFetch([{ status: 200, body: analyzedResponse }])
    renderPersonalColorPage()

    await selectBothPhotos()
    await userEvent.click(analyzeButton())

    await screen.findByText('가을 웜톤')
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [path, init] = fetchMock.mock.calls[0]
    expect(path).toBe('/api/personal-color')
    expect(init?.method).toBe('POST')
    const formData = init?.body as FormData
    expect((formData.get('selfie') as File).name).toBe('face.jpg')
    expect((formData.get('bodyImage') as File).name).toBe('body.png')
  })

  it('분석 중에는 로딩을 보여주고 분석하기가 비활성화된다', async () => {
    const { respondPending } = stubFetch(['pending'])
    renderPersonalColorPage()

    await selectBothPhotos()
    await userEvent.click(analyzeButton())

    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(analyzeButton()).toBeDisabled()
    respondPending(200, analyzedResponse)
    expect(await screen.findByText('가을 웜톤')).toBeInTheDocument()
  })

  it.each([
    [Season.SPRING_WARM, '봄 웜톤'],
    [Season.SUMMER_COOL, '여름 쿨톤'],
    [Season.AUTUMN_WARM, '가을 웜톤'],
    [Season.WINTER_COOL, '겨울 쿨톤'],
  ])('결과 시즌 %s 를 한글 %s 로 보여준다', async (season, seasonName) => {
    stubFetch([{ status: 200, body: { ...analyzedResponse, season } }])
    renderPersonalColorPage()

    await selectBothPhotos()
    await userEvent.click(analyzeButton())

    expect(await screen.findByText(seasonName)).toBeInTheDocument()
  })

  it('결과로 팔레트 색 칩과 얼굴 사진을 보여주고 다음을 누르면 스와이프 화면으로 이동한다', async () => {
    stubFetch([{ status: 200, body: analyzedResponse }])
    renderPersonalColorPage()

    await selectBothPhotos()
    await userEvent.click(analyzeButton())

    const palette = await screen.findByRole('list', { name: '팔레트' })
    const chips = within(palette).getAllByRole('listitem')
    expect(chips.map((chip) => chip.getAttribute('title'))).toEqual(analyzedResponse.palette)
    expect(screen.getByRole('img', { name: '얼굴 사진' })).toHaveAttribute('src', analyzedResponse.selfieUrl)

    await userEvent.click(screen.getByRole('button', { name: '다음' }))
    expect(await screen.findByText('스와이프 화면')).toBeInTheDocument()
  })

  it('얼굴을 인식하지 못하면 얼굴 사진 재촬영 안내와 가이드를 다시 보여준다', async () => {
    stubFetch([
      { status: 422, body: { error: { code: ErrorCode.FACE_NOT_DETECTED, message: 'error_face_position_invalid' } } },
    ])
    renderPersonalColorPage()

    await selectBothPhotos()
    await userEvent.click(analyzeButton())

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('얼굴 사진을 다시 찍어')
    expect(alert).toHaveTextContent('정면, 자연광, 화장 최소화, 얼굴이 화면을 가득 채우게')
    expect(selfieInput()).toBeEnabled()
    expect(analyzeButton()).toBeEnabled()
  })

  it('기타 에러는 서버 메시지를 보여주고 화면에 남는다', async () => {
    stubFetch([{ status: 502, body: { error: { code: ErrorCode.EXTERNAL_API_FAILED, message: 'YouCam 분석 실패' } } }])
    renderPersonalColorPage()

    await selectBothPhotos()
    await userEvent.click(analyzeButton())

    expect(await screen.findByRole('alert')).toHaveTextContent('YouCam 분석 실패')
    expect(analyzeButton()).toBeEnabled()
  })

  it('토큰이 만료되어 401 이면 로그인 화면으로 이동한다', async () => {
    stubFetch([{ status: 401, body: { error: { code: ErrorCode.UNAUTHORIZED, message: 'UNAUTHORIZED' } } }])
    renderPersonalColorPage()

    await selectBothPhotos()
    await userEvent.click(analyzeButton())

    expect(await screen.findByText('로그인 화면')).toBeInTheDocument()
    expect(tokenStorage.get()).toBeNull()
  })
})
