import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ErrorCode } from '../../../src/common/type'
import type { WardrobePhotosResponse } from '../../../src/common/type'
import { WardrobePage } from '../../../src/feature/wardrobe'
import { tokenStorage } from '../../../src/shared/auth'
import { setLanguage } from '../../../src/shared/i18n'
import { ROUTES } from '../../../src/shared/navigation'
import { stubFetch } from './fetchStub'

// 이 파일의 명세는 한국어 화면 기준이다. 영어 화면은 *.english.test.tsx 에서 확인한다.
beforeEach(() => setLanguage('ko'))
afterEach(() => setLanguage('en'))

const uploadedResponse: WardrobePhotosResponse = {
  photos: [
    { id: 1, imageUrl: 'https://storage.test/wardrobe/1/a.jpg' },
    { id: 2, imageUrl: 'https://storage.test/wardrobe/1/b.png' },
  ],
}

function imageFile(name: string, type = 'image/jpeg'): File {
  return new File(['image-bytes'], name, { type })
}

function renderWardrobePage() {
  render(
    <MemoryRouter initialEntries={[ROUTES.wardrobe]}>
      <Routes>
        <Route path={ROUTES.wardrobe} element={<WardrobePage />} />
        <Route path={ROUTES.recommendation} element={<div>추천 화면</div>} />
        <Route path={ROUTES.login} element={<div>로그인 화면</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

function photoInput(): HTMLInputElement {
  return screen.getByLabelText('사진 선택')
}

describe('WardrobePage', () => {
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

  it('안내 문구와 사진 선택, 업로드·건너뛰기 버튼을 보여주고 0장이면 업로드가 비활성화된다', () => {
    renderWardrobePage()

    expect(screen.getByText(/좋아하는 착용 사진이나 옷 사진/)).toBeInTheDocument()
    expect(photoInput()).toHaveAttribute('accept', 'image/jpeg,image/png')
    expect(photoInput()).toHaveAttribute('multiple')
    expect(screen.getByRole('button', { name: '업로드' })).toBeDisabled()
    expect(screen.getByRole('button', { name: '건너뛰기' })).toBeEnabled()
  })

  it('사진을 고르면 미리보기를 보여주고 업로드가 활성화된다', async () => {
    renderWardrobePage()

    await userEvent.upload(photoInput(), [imageFile('a.jpg'), imageFile('b.png', 'image/png')])

    const previews = screen.getAllByRole('img')
    expect(previews.map((preview) => preview.getAttribute('src'))).toEqual(['blob:a.jpg', 'blob:b.png'])
    expect(screen.getByRole('button', { name: '업로드' })).toBeEnabled()
  })

  it('4장을 넘게 고르면 에러를 보여주고 선택을 받지 않는다', async () => {
    renderWardrobePage()

    await userEvent.upload(
      photoInput(),
      ['1.jpg', '2.jpg', '3.jpg', '4.jpg', '5.jpg'].map((name) => imageFile(name)),
    )

    expect(screen.getByRole('alert')).toHaveTextContent('최대 4장')
    expect(screen.queryAllByRole('img')).toHaveLength(0)
    expect(screen.getByRole('button', { name: '업로드' })).toBeDisabled()
  })

  it('jpg·png 가 아닌 파일이 섞여 있으면 에러를 보여주고 선택을 받지 않는다', async () => {
    const user = userEvent.setup({ applyAccept: false })
    renderWardrobePage()

    await user.upload(photoInput(), [imageFile('a.jpg'), imageFile('c.gif', 'image/gif')])

    expect(screen.getByRole('alert')).toHaveTextContent('jpg 또는 png')
    expect(screen.queryAllByRole('img')).toHaveLength(0)
    expect(screen.getByRole('button', { name: '업로드' })).toBeDisabled()
  })

  it('업로드하면 선택한 사진을 images 필드로 보내고 추천 화면으로 이동한다', async () => {
    const { fetchMock } = stubFetch([{ status: 200, body: uploadedResponse }])
    renderWardrobePage()

    await userEvent.upload(photoInput(), [imageFile('a.jpg'), imageFile('b.png', 'image/png')])
    await userEvent.click(screen.getByRole('button', { name: '업로드' }))

    expect(await screen.findByText('추천 화면')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [path, init] = fetchMock.mock.calls[0]
    expect(path).toBe('/api/wardrobe-photos')
    expect(init?.method).toBe('POST')
    expect(init?.body).toBeInstanceOf(FormData)
    const sentFileNames = (init?.body as FormData).getAll('images').map((file) => (file as File).name)
    expect(sentFileNames).toEqual(['a.jpg', 'b.png'])
  })

  it('업로드 중에는 로딩을 보여주고 버튼이 비활성화된다', async () => {
    const { respondPending } = stubFetch(['pending'])
    renderWardrobePage()

    await userEvent.upload(photoInput(), [imageFile('a.jpg')])
    await userEvent.click(screen.getByRole('button', { name: '업로드' }))

    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '업로드' })).toBeDisabled()
    expect(screen.getByRole('button', { name: '건너뛰기' })).toBeDisabled()
    respondPending(200, uploadedResponse)
    expect(await screen.findByText('추천 화면')).toBeInTheDocument()
  })

  it('서버가 개수 초과로 거부하면 에러를 보여주고 화면에 남는다', async () => {
    stubFetch([
      {
        status: 409,
        body: { error: { code: ErrorCode.WARDROBE_LIMIT_EXCEEDED, message: '사진은 최대 4장까지 저장할 수 있습니다' } },
      },
    ])
    renderWardrobePage()

    await userEvent.upload(photoInput(), [imageFile('a.jpg')])
    await userEvent.click(screen.getByRole('button', { name: '업로드' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('사진은 최대 4장까지 저장할 수 있습니다')
    expect(screen.getByRole('button', { name: '업로드' })).toBeEnabled()
    expect(screen.queryByText('추천 화면')).not.toBeInTheDocument()
  })

  it('서버가 이미지 형식으로 거부하면 에러를 보여준다', async () => {
    stubFetch([{ status: 400, body: { error: { code: ErrorCode.INVALID_IMAGE, message: '이미지 파일이 아닙니다' } } }])
    renderWardrobePage()

    await userEvent.upload(photoInput(), [imageFile('a.jpg')])
    await userEvent.click(screen.getByRole('button', { name: '업로드' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('이미지 파일이 아닙니다')
  })

  it('건너뛰기를 누르면 요청 없이 추천 화면으로 이동한다', async () => {
    const { fetchMock } = stubFetch([{ status: 200, body: uploadedResponse }])
    renderWardrobePage()

    await userEvent.click(screen.getByRole('button', { name: '건너뛰기' }))

    expect(await screen.findByText('추천 화면')).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('토큰이 만료되어 401 이면 로그인 화면으로 이동한다', async () => {
    stubFetch([{ status: 401, body: { error: { code: ErrorCode.UNAUTHORIZED, message: 'UNAUTHORIZED' } } }])
    renderWardrobePage()

    await userEvent.upload(photoInput(), [imageFile('a.jpg')])
    await userEvent.click(screen.getByRole('button', { name: '업로드' }))

    expect(await screen.findByText('로그인 화면')).toBeInTheDocument()
    expect(tokenStorage.get()).toBeNull()
  })
})
