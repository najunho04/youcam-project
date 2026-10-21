import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ErrorCode, FittingStatus, Style } from '../../../src/common/type'
import type { FittingDto } from '../../../src/common/type'
import { FittingPage } from '../../../src/feature/fitting'
import { tokenStorage } from '../../../src/shared/auth'
import { setLanguage } from '../../../src/shared/i18n'
import { ROUTES } from '../../../src/shared/navigation'
import { stubFetch } from './fetchStub'

// 이 파일의 명세는 한국어 화면 기준이다. 영어 화면은 *.english.test.tsx 에서 확인한다.
beforeEach(() => setLanguage('ko'))
afterEach(() => setLanguage('en'))

const PRODUCT_ID = 21
const FITTING_ID = 7
const POLLING_INTERVAL_MILLISECONDS = 2_000
const POLLING_LIMIT_MILLISECONDS = 150_000
const LOADING_MESSAGE = '입혀보는 중'
const TIMED_OUT_MESSAGE = '시간이 오래 걸리고 있어요'

function fittingOf(status: FittingStatus): FittingDto {
  return {
    id: FITTING_ID,
    productId: PRODUCT_ID,
    product: {
      id: PRODUCT_ID,
      title: '테스트 니트 21',
      price: 39000,
      mallName: '테스트몰',
      purchaseUrl: 'https://shopping.test/products/21',
      imageUrl: 'https://image.test/products/21.jpg',
      style: Style.MINIMAL,
    },
    status,
    originalImageUrl: 'https://storage.test/body-images/1/body.jpg',
    resultImageUrl: status === FittingStatus.DONE ? `https://storage.test/fittings/1/${FITTING_ID}.jpg` : null,
  }
}

const created = { status: 202, body: fittingOf(FittingStatus.PENDING) }
const createdDone = { status: 202, body: fittingOf(FittingStatus.DONE) }
const fetchedPending = { status: 200, body: fittingOf(FittingStatus.PENDING) }
const fetchedDone = { status: 200, body: fittingOf(FittingStatus.DONE) }
const fetchedFailed = { status: 200, body: fittingOf(FittingStatus.FAILED) }

function errorBody(code: ErrorCode, message: string) {
  return { error: { code, message } }
}

function renderFittingPage() {
  return render(
    <MemoryRouter initialEntries={[ROUTES.fitting(PRODUCT_ID)]}>
      <Routes>
        <Route path={ROUTES.fittingPattern} element={<FittingPage />} />
        <Route path={ROUTES.recommendation} element={<div>추천 화면</div>} />
        <Route path={ROUTES.login} element={<div>로그인 화면</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

/** 가짜 타이머를 진행시키고 그 사이의 fetch·상태 갱신을 모두 반영한다. */
async function advance(milliseconds: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(milliseconds)
  })
}

const settle = () => advance(0)

async function click(name: string) {
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name }))
  })
  await settle()
}

function requestsOf(fetchMock: ReturnType<typeof stubFetch>['fetchMock']) {
  return fetchMock.mock.calls.map(([path, init]) => `${init?.method} ${path}`)
}

describe('FittingPage', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    tokenStorage.set('valid-token')
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('진입하면 상품 id 로 피팅을 요청하고, 그동안 "입혀보는 중" 을 보여준다', async () => {
    const { fetchMock } = stubFetch([created])
    renderFittingPage()

    expect(screen.getByRole('status')).toHaveTextContent(LOADING_MESSAGE)
    await settle()

    expect(requestsOf(fetchMock)).toEqual(['POST /api/fittings'])
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({ productId: PRODUCT_ID })
    expect(screen.getByRole('status')).toHaveTextContent(LOADING_MESSAGE)
  })

  it('DONE 이면 원본·결과 비교, 상품 정보, 구매 링크(새 탭), 다른 상품 입어보기를 보여준다', async () => {
    const { fetchMock } = stubFetch([createdDone])
    renderFittingPage()
    await settle()

    expect(screen.getByRole('img', { name: '원본' })).toHaveAttribute('src', 'https://storage.test/body-images/1/body.jpg')
    expect(screen.getByRole('img', { name: '피팅 결과' })).toHaveAttribute(
      'src',
      `https://storage.test/fittings/1/${FITTING_ID}.jpg`,
    )
    expect(screen.getByText('테스트 니트 21')).toBeInTheDocument()
    expect(screen.getByText('39,000원')).toBeInTheDocument()
    expect(screen.getByText('테스트몰')).toBeInTheDocument()
    const purchaseLink = screen.getByRole('link', { name: '구매하러 가기' })
    expect(purchaseLink).toHaveAttribute('href', 'https://shopping.test/products/21')
    expect(purchaseLink).toHaveAttribute('target', '_blank')
    expect(purchaseLink).toHaveAttribute('rel', expect.stringContaining('noopener'))

    await advance(POLLING_INTERVAL_MILLISECONDS * 3)
    expect(fetchMock).toHaveBeenCalledTimes(1) // DONE 이면 폴링하지 않는다

    await click('다른 상품 입어보기')
    expect(screen.getByText('추천 화면')).toBeInTheDocument()
  })

  it('PENDING 이면 2초 간격으로 GET 폴링하고, DONE 이 되면 멈추고 결과를 보여준다', async () => {
    const { fetchMock } = stubFetch([created, fetchedPending, fetchedDone])
    renderFittingPage()
    await settle()

    await advance(POLLING_INTERVAL_MILLISECONDS - 1)
    expect(fetchMock).toHaveBeenCalledTimes(1)

    await advance(1)
    expect(requestsOf(fetchMock)).toEqual(['POST /api/fittings', `GET /api/fittings/${FITTING_ID}`])
    expect(screen.getByRole('status')).toHaveTextContent(LOADING_MESSAGE)

    await advance(POLLING_INTERVAL_MILLISECONDS)
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(screen.getByRole('img', { name: '피팅 결과' })).toBeInTheDocument()

    await advance(POLLING_INTERVAL_MILLISECONDS * 5)
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('150초가 지나도 PENDING 이면 폴링을 멈추고 "시간이 오래 걸리고 있어요" 와 다시 확인을 보여준다', async () => {
    const { fetchMock } = stubFetch([created, fetchedPending])
    renderFittingPage()
    await settle()

    await advance(POLLING_LIMIT_MILLISECONDS - 1)
    expect(screen.queryByText(TIMED_OUT_MESSAGE)).not.toBeInTheDocument()

    await advance(1)
    expect(screen.getByText(TIMED_OUT_MESSAGE)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '다시 확인' })).toBeInTheDocument()

    const callCountAtTimeout = fetchMock.mock.calls.length
    await advance(POLLING_INTERVAL_MILLISECONDS * 10)
    expect(fetchMock).toHaveBeenCalledTimes(callCountAtTimeout)
  })

  it('다시 확인은 GET 을 다시 부르고, 여전히 PENDING 이면 폴링을 재개한다', async () => {
    const { fetchMock } = stubFetch([created, fetchedPending])
    renderFittingPage()
    await settle()
    await advance(POLLING_LIMIT_MILLISECONDS)
    const callCountAtTimeout = fetchMock.mock.calls.length

    await click('다시 확인')

    expect(fetchMock).toHaveBeenCalledTimes(callCountAtTimeout + 1)
    expect(requestsOf(fetchMock).at(-1)).toBe(`GET /api/fittings/${FITTING_ID}`)
    expect(screen.queryByText(TIMED_OUT_MESSAGE)).not.toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent(LOADING_MESSAGE)

    await advance(POLLING_INTERVAL_MILLISECONDS)
    expect(fetchMock).toHaveBeenCalledTimes(callCountAtTimeout + 2)

    // 재개한 폴링도 150초 상한을 다시 적용한다
    await advance(POLLING_LIMIT_MILLISECONDS)
    expect(screen.getByText(TIMED_OUT_MESSAGE)).toBeInTheDocument()
  })

  it('다시 확인에서 DONE 이면 결과를 보여준다', async () => {
    stubFetch([created, fetchedPending])
    renderFittingPage()
    await settle()
    await advance(POLLING_LIMIT_MILLISECONDS)
    expect(screen.getByText(TIMED_OUT_MESSAGE)).toBeInTheDocument()
    const { fetchMock: recheckFetchMock } = stubFetch([fetchedDone])

    await click('다시 확인')

    expect(requestsOf(recheckFetchMock)).toEqual([`GET /api/fittings/${FITTING_ID}`])
    expect(screen.getByRole('img', { name: '피팅 결과' })).toBeInTheDocument()
    await advance(POLLING_INTERVAL_MILLISECONDS * 3)
    expect(recheckFetchMock).toHaveBeenCalledTimes(1)
  })

  it('화면을 떠나면 폴링을 멈춘다', async () => {
    const { fetchMock } = stubFetch([created, fetchedPending])
    const { unmount } = renderFittingPage()
    await settle()
    await advance(POLLING_INTERVAL_MILLISECONDS)
    expect(fetchMock).toHaveBeenCalledTimes(2)

    unmount()
    await advance(POLLING_INTERVAL_MILLISECONDS * 10)

    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('FAILED 면 상품 이미지만 보여주고, 다시 시도하면 POST 를 다시 부른다', async () => {
    const { fetchMock } = stubFetch([created, fetchedFailed, createdDone])
    renderFittingPage()
    await settle()
    await advance(POLLING_INTERVAL_MILLISECONDS)

    expect(screen.getByRole('img', { name: '테스트 니트 21' })).toHaveAttribute(
      'src',
      'https://image.test/products/21.jpg',
    )
    expect(screen.queryByRole('img', { name: '원본' })).not.toBeInTheDocument()
    expect(screen.queryByRole('img', { name: '피팅 결과' })).not.toBeInTheDocument()

    await click('다시 시도')

    expect(requestsOf(fetchMock)).toEqual([
      'POST /api/fittings',
      `GET /api/fittings/${FITTING_ID}`,
      'POST /api/fittings',
    ])
    expect(screen.getByRole('img', { name: '피팅 결과' })).toBeInTheDocument()
  })

  it('요청이 실패하면 에러와 다시 시도를 보여주고, 다시 시도하면 POST 를 다시 부른다', async () => {
    const { fetchMock } = stubFetch([
      { status: 404, body: errorBody(ErrorCode.PRODUCT_NOT_FOUND, '상품을 찾을 수 없습니다') },
      createdDone,
    ])
    renderFittingPage()
    await settle()

    expect(screen.getByRole('alert')).toHaveTextContent('상품을 찾을 수 없습니다')

    await click('다시 시도')

    expect(requestsOf(fetchMock)).toEqual(['POST /api/fittings', 'POST /api/fittings'])
    expect(screen.getByRole('img', { name: '피팅 결과' })).toBeInTheDocument()
  })

  it('폴링 중 요청이 실패하면 폴링을 멈추고 에러를 보여준다', async () => {
    const { fetchMock } = stubFetch([created, 'network-failure'])
    renderFittingPage()
    await settle()
    await advance(POLLING_INTERVAL_MILLISECONDS)

    expect(screen.getByRole('alert')).toHaveTextContent('서버에 연결할 수 없습니다')
    await advance(POLLING_INTERVAL_MILLISECONDS * 5)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('401 이면 로그인 화면으로 보낸다', async () => {
    stubFetch([{ status: 401, body: errorBody(ErrorCode.UNAUTHORIZED, '로그인이 필요합니다') }])
    renderFittingPage()
    await settle()

    expect(screen.getByText('로그인 화면')).toBeInTheDocument()
  })
})
