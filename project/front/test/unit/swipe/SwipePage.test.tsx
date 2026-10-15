import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ErrorCode, Style } from '../../../src/common/type'
import type { SwipeAnswersResponse, SwipeCardsResponse } from '../../../src/common/type'
import { SwipePage } from '../../../src/feature/swipe'
import { tokenStorage } from '../../../src/shared/auth'
import { ROUTES } from '../../../src/shared/navigation'
import { stubFetch } from './fetchStub'

const CARD_WIDTH = 300

const cardsResponse: SwipeCardsResponse = {
  cards: [
    { pinId: 11, imageUrl: 'https://image.test/pins/11.jpg', style: Style.MINIMAL },
    { pinId: 12, imageUrl: 'https://image.test/pins/12.jpg', style: Style.STREET },
    { pinId: 13, imageUrl: 'https://image.test/pins/13.jpg', style: Style.LOVELY },
  ],
}

const answersResponse: SwipeAnswersResponse = { likedCount: 2, totalCount: 3 }

function renderSwipePage() {
  render(
    <MemoryRouter initialEntries={[ROUTES.swipe]}>
      <Routes>
        <Route path={ROUTES.swipe} element={<SwipePage />} />
        <Route path={ROUTES.wardrobe} element={<div>옷장 사진 화면</div>} />
        <Route path={ROUTES.profile} element={<div>프로필 화면</div>} />
        <Route path={ROUTES.login} element={<div>로그인 화면</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

function currentCard(): HTMLElement {
  return screen.getByRole('group', { name: '상의 카드' })
}

function currentImageUrl(): string | null {
  return screen.getByRole('img').getAttribute('src')
}

function drag(card: HTMLElement, horizontalDistance: number) {
  fireEvent.pointerDown(card, { pointerId: 1, clientX: 100, clientY: 100 })
  fireEvent.pointerMove(card, { pointerId: 1, clientX: 100 + horizontalDistance, clientY: 110 })
  fireEvent.pointerUp(card, { pointerId: 1, clientX: 100 + horizontalDistance, clientY: 110 })
}

function sentAnswers(fetchMock: ReturnType<typeof stubFetch>['fetchMock'], callIndex: number): unknown {
  const [path, init] = fetchMock.mock.calls[callIndex]
  expect(path).toBe('/api/swipe/answers')
  expect(init?.method).toBe('POST')
  return JSON.parse(String(init?.body))
}

describe('SwipePage', () => {
  beforeEach(() => {
    tokenStorage.set('valid-token')
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue(
      DOMRect.fromRect({ x: 0, y: 0, width: CARD_WIDTH, height: 400 }),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('카드를 불러오는 동안 로딩을 보여주고, 불러오면 첫 카드와 진행률을 보여준다', async () => {
    const { fetchMock, respondPending } = stubFetch(['pending'])
    renderSwipePage()

    expect(screen.getByRole('status')).toBeInTheDocument()
    respondPending(200, cardsResponse)

    expect(await screen.findByText('1 / 3')).toBeInTheDocument()
    expect(currentImageUrl()).toBe('https://image.test/pins/11.jpg')
    expect(screen.getByRole('button', { name: '좋아요' })).toBeEnabled()
    expect(screen.getByRole('button', { name: '싫어요' })).toBeEnabled()
    expect(fetchMock.mock.calls[0][0]).toBe('/api/swipe/cards?count=20')
    expect(fetchMock.mock.calls[0][1]?.method).toBe('GET')
  })

  it('버튼으로 답하면 다음 카드로 넘어가고, 마지막 카드 후 답변을 한 번에 제출하고 옷장 사진 화면으로 이동한다', async () => {
    const { fetchMock } = stubFetch([
      { status: 200, body: cardsResponse },
      { status: 200, body: answersResponse },
    ])
    renderSwipePage()

    await userEvent.click(await screen.findByRole('button', { name: '좋아요' }))
    expect(screen.getByText('2 / 3')).toBeInTheDocument()
    expect(currentImageUrl()).toBe('https://image.test/pins/12.jpg')
    expect(fetchMock).toHaveBeenCalledTimes(1) // 중간에는 제출하지 않는다

    await userEvent.click(screen.getByRole('button', { name: '싫어요' }))
    await userEvent.click(screen.getByRole('button', { name: '좋아요' }))

    expect(await screen.findByText('옷장 사진 화면')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(sentAnswers(fetchMock, 1)).toEqual({
      answers: [
        { pinId: 11, liked: true },
        { pinId: 12, liked: false },
        { pinId: 13, liked: true },
      ],
    })
  })

  it('카드 너비의 30% 이상 오른쪽으로 끌면 좋아요, 왼쪽으로 끌면 싫어요로 확정된다', async () => {
    const { fetchMock } = stubFetch([
      { status: 200, body: cardsResponse },
      { status: 200, body: answersResponse },
    ])
    renderSwipePage()
    await screen.findByText('1 / 3')

    drag(currentCard(), CARD_WIDTH * 0.3)
    expect(screen.getByText('2 / 3')).toBeInTheDocument()
    drag(currentCard(), -CARD_WIDTH * 0.5)
    expect(screen.getByText('3 / 3')).toBeInTheDocument()
    drag(currentCard(), CARD_WIDTH)

    expect(await screen.findByText('옷장 사진 화면')).toBeInTheDocument()
    expect(sentAnswers(fetchMock, 1)).toEqual({
      answers: [
        { pinId: 11, liked: true },
        { pinId: 12, liked: false },
        { pinId: 13, liked: true },
      ],
    })
  })

  it('드래그 중에는 카드가 포인터를 따라 이동·회전하고, 30% 미만이면 원위치로 돌아간다', async () => {
    stubFetch([{ status: 200, body: cardsResponse }])
    renderSwipePage()
    await screen.findByText('1 / 3')
    const card = currentCard()

    fireEvent.pointerDown(card, { pointerId: 1, clientX: 100, clientY: 100 })
    fireEvent.pointerMove(card, { pointerId: 1, clientX: 160, clientY: 100 })
    expect(card.style.transform).toContain('translateX(60px)')
    expect(card.style.transform).toMatch(/rotate\(\d+(\.\d+)?deg\)/)
    fireEvent.pointerUp(card, { pointerId: 1, clientX: 160, clientY: 100 })

    expect(screen.getByText('1 / 3')).toBeInTheDocument()
    expect(currentCard().style.transform).toContain('translateX(0px)')
    expect(currentImageUrl()).toBe('https://image.test/pins/11.jpg')
  })

  it('카드가 0장이면 빈 상태 문구를 보여준다', async () => {
    stubFetch([{ status: 200, body: { cards: [] } }])
    renderSwipePage()

    expect(await screen.findByText('지금 보여줄 카드가 없어요')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '좋아요' })).not.toBeInTheDocument()
  })

  it('PROFILE_REQUIRED 이면 프로필 입력을 안내하고 버튼으로 프로필 화면에 보낸다', async () => {
    stubFetch([
      { status: 409, body: { error: { code: ErrorCode.PROFILE_REQUIRED, message: '나이대와 성별을 먼저 입력해 주세요' } } },
    ])
    renderSwipePage()

    expect(await screen.findByText('나이대와 성별을 먼저 입력해 주세요')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: '프로필 입력하기' }))

    expect(await screen.findByText('프로필 화면')).toBeInTheDocument()
  })

  it('카드 불러오기가 실패하면 에러와 다시 시도를 보여주고, 다시 시도하면 다시 불러온다', async () => {
    const { fetchMock } = stubFetch(['network-failure', { status: 200, body: cardsResponse }])
    renderSwipePage()

    expect(await screen.findByRole('alert')).toHaveTextContent('서버에 연결할 수 없습니다')
    await userEvent.click(screen.getByRole('button', { name: '다시 시도' }))

    expect(await screen.findByText('1 / 3')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('제출하는 동안 로딩을 보여준다', async () => {
    const { respondPending } = stubFetch([{ status: 200, body: { cards: cardsResponse.cards.slice(0, 1) } }, 'pending'])
    renderSwipePage()

    await userEvent.click(await screen.findByRole('button', { name: '좋아요' }))

    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '좋아요' })).not.toBeInTheDocument()
    respondPending(200, { likedCount: 1, totalCount: 1 })
    expect(await screen.findByText('옷장 사진 화면')).toBeInTheDocument()
  })

  it('제출이 실패하면 에러와 다시 시도를 보여주고, 다시 시도하면 같은 답변을 다시 제출한다', async () => {
    const { fetchMock } = stubFetch([
      { status: 200, body: { cards: cardsResponse.cards.slice(0, 2) } },
      { status: 500, body: { error: { code: ErrorCode.INTERNAL_ERROR, message: '서버 오류' } } },
      { status: 200, body: answersResponse },
    ])
    renderSwipePage()

    await userEvent.click(await screen.findByRole('button', { name: '싫어요' }))
    await userEvent.click(screen.getByRole('button', { name: '좋아요' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('서버 오류')
    await userEvent.click(screen.getByRole('button', { name: '다시 시도' }))

    expect(await screen.findByText('옷장 사진 화면')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(3)
    const expectedAnswers = {
      answers: [
        { pinId: 11, liked: false },
        { pinId: 12, liked: true },
      ],
    }
    expect(sentAnswers(fetchMock, 1)).toEqual(expectedAnswers)
    expect(sentAnswers(fetchMock, 2)).toEqual(expectedAnswers)
  })

  it('토큰이 만료되어 401 이면 로그인 화면으로 이동한다', async () => {
    stubFetch([{ status: 401, body: { error: { code: ErrorCode.UNAUTHORIZED, message: 'UNAUTHORIZED' } } }])
    renderSwipePage()

    expect(await screen.findByText('로그인 화면')).toBeInTheDocument()
    expect(tokenStorage.get()).toBeNull()
  })
})
