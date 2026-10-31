import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ErrorCode, Season, Style, SeasonSubtype } from '../../../src/common/type'
import type { RecommendationItem, RecommendationResponse } from '../../../src/common/type'
import { RecommendationPage } from '../../../src/feature/recommendation'
import { tokenStorage } from '../../../src/shared/auth'
import { setLanguage } from '../../../src/shared/i18n'
import { ROUTES } from '../../../src/shared/navigation'
import { stubFetch } from './fetchStub'

// 이 파일의 명세는 한국어 화면 기준이다. 영어 화면은 *.english.test.tsx 에서 확인한다.
beforeEach(() => setLanguage('ko'))
afterEach(() => setLanguage('en'))

function recommendationItem(productId: number, reasonTags: string[]): RecommendationItem {
  return {
    product: {
      id: productId,
      title: `테스트 니트 ${productId}`,
      price: 39000 + productId,
      currency: 'KRW',
      mallName: `테스트몰 ${productId}`,
      purchaseUrl: `https://shopping.test/products/${productId}`,
      imageUrl: `https://image.test/products/${productId}.jpg`,
      style: Style.MINIMAL,
    },
    score: 0.9,
    tasteScore: 0.9,
    colorScore: 0.9,
    reasonTags,
  }
}

const recommendationResponse: RecommendationResponse = {
  styleTags: ['러블리', '미니멀', '가을 웜톤'],
  season: Season.AUTUMN_WARM,
  subtype: SeasonSubtype.DEEP,
  palette: ['#C19A6B', '#D8C3A5'],
  isFallback: false,
  items: [
    recommendationItem(21, ['선호하는 미니멀', '가을 웜톤 컬러']),
    recommendationItem(22, ['캐주얼 스타일']),
    recommendationItem(23, ['가을 웜톤 컬러']),
    recommendationItem(24, ['미니멀 스타일']),
    recommendationItem(25, ['선호하는 미니멀']),
  ],
}

const FALLBACK_NOTICE = '취향 데이터가 적어 퍼스널컬러에 어울리는 상품을 보여드려요'

function renderRecommendationPage() {
  render(
    <MemoryRouter initialEntries={[ROUTES.recommendation]}>
      <Routes>
        <Route path={ROUTES.recommendation} element={<RecommendationPage />} />
        <Route path={ROUTES.fittingPattern} element={<div>가상 피팅 화면</div>} />
        <Route path={ROUTES.profile} element={<div>프로필 화면</div>} />
        <Route path={ROUTES.personalColor} element={<div>퍼스널컬러 화면</div>} />
        <Route path={ROUTES.login} element={<div>로그인 화면</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

function errorBody(code: ErrorCode, message: string) {
  return { error: { code, message } }
}

describe('RecommendationPage', () => {
  beforeEach(() => {
    tokenStorage.set('valid-token')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('불러오는 동안 로딩을 보여주고, 불러오면 취향 요약·팔레트·상품 카드 5개를 보여준다', async () => {
    const { fetchMock, respondPending } = stubFetch(['pending'])
    renderRecommendationPage()

    expect(screen.getByRole('status')).toBeInTheDocument()
    respondPending(200, recommendationResponse)

    const cards = await screen.findAllByRole('article')
    expect(cards).toHaveLength(5)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/recommendations')
    expect(fetchMock.mock.calls[0][1]?.method).toBe('GET')

    const styleTagList = screen.getByRole('list', { name: '취향 요약' })
    expect(within(styleTagList).getAllByRole('listitem').map((item) => item.textContent)).toEqual([
      '러블리',
      '미니멀',
      '가을 웜톤',
    ])
    const paletteList = screen.getByRole('list', { name: '가을 웜톤 팔레트' })
    expect(within(paletteList).getAllByRole('listitem').map((item) => item.getAttribute('title'))).toEqual([
      '#C19A6B',
      '#D8C3A5',
    ])
    expect(screen.queryByText(FALLBACK_NOTICE)).not.toBeInTheDocument()
  })

  it('카드에 이미지·상품명·가격(원)·쇼핑몰·추천 이유·구매 링크(새 탭)를 보여준다', async () => {
    stubFetch([{ status: 200, body: recommendationResponse }])
    renderRecommendationPage()

    const firstCard = (await screen.findAllByRole('article'))[0]
    expect(within(firstCard).getByRole('img', { name: '테스트 니트 21' })).toHaveAttribute(
      'src',
      'https://image.test/products/21.jpg',
    )
    expect(within(firstCard).getByText('테스트 니트 21')).toBeInTheDocument()
    expect(within(firstCard).getByText('39,021원')).toBeInTheDocument()
    expect(within(firstCard).getByText('테스트몰 21')).toBeInTheDocument()
    expect(within(firstCard).getByText('선호하는 미니멀')).toBeInTheDocument()
    expect(within(firstCard).getByText('가을 웜톤 컬러')).toBeInTheDocument()

    const purchaseLink = within(firstCard).getByRole('link', { name: '구매하러 가기' })
    expect(purchaseLink).toHaveAttribute('href', 'https://shopping.test/products/21')
    expect(purchaseLink).toHaveAttribute('target', '_blank')
    expect(purchaseLink).toHaveAttribute('rel', expect.stringContaining('noopener'))
  })

  it('입어보기를 누르면 해당 상품의 가상 피팅 화면으로 이동한다', async () => {
    stubFetch([{ status: 200, body: recommendationResponse }])
    renderRecommendationPage()

    const secondCard = (await screen.findAllByRole('article'))[1]
    await userEvent.click(within(secondCard).getByRole('button', { name: '입어보기' }))

    expect(await screen.findByText('가상 피팅 화면')).toBeInTheDocument()
  })

  it('isFallback 이면 퍼스널컬러 기반 안내 문구를 보여준다', async () => {
    stubFetch([{ status: 200, body: { ...recommendationResponse, isFallback: true } }])
    renderRecommendationPage()

    expect(await screen.findByText(FALLBACK_NOTICE)).toBeInTheDocument()
  })

  it('추천 상품이 0개면 빈 상태 문구를 보여준다', async () => {
    stubFetch([{ status: 200, body: { ...recommendationResponse, styleTags: ['가을 웜톤'], items: [] } }])
    renderRecommendationPage()

    expect(await screen.findByText('추천할 상품이 아직 없어요')).toBeInTheDocument()
    expect(screen.queryByRole('article')).not.toBeInTheDocument()
  })

  it('PROFILE_REQUIRED 이면 프로필 입력을 안내하고 버튼으로 프로필 화면에 보낸다', async () => {
    stubFetch([{ status: 409, body: errorBody(ErrorCode.PROFILE_REQUIRED, '나이대와 성별을 먼저 입력해 주세요') }])
    renderRecommendationPage()

    expect(await screen.findByText('나이대와 성별을 먼저 입력해 주세요')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: '프로필 입력하기' }))

    expect(await screen.findByText('프로필 화면')).toBeInTheDocument()
  })

  it('PERSONAL_COLOR_REQUIRED 이면 진단을 안내하고 버튼으로 퍼스널컬러 화면에 보낸다', async () => {
    stubFetch([
      { status: 409, body: errorBody(ErrorCode.PERSONAL_COLOR_REQUIRED, '퍼스널컬러 진단을 먼저 해 주세요') },
    ])
    renderRecommendationPage()

    expect(await screen.findByText('퍼스널컬러 진단을 먼저 해 주세요')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: '퍼스널컬러 진단하기' }))

    expect(await screen.findByText('퍼스널컬러 화면')).toBeInTheDocument()
  })

  it('401 이면 로그인 화면으로 보낸다', async () => {
    stubFetch([{ status: 401, body: errorBody(ErrorCode.UNAUTHORIZED, '로그인이 필요합니다') }])
    renderRecommendationPage()

    expect(await screen.findByText('로그인 화면')).toBeInTheDocument()
  })

  it('불러오기가 실패하면 에러와 다시 시도를 보여주고, 다시 시도하면 다시 불러온다', async () => {
    const { fetchMock } = stubFetch(['network-failure', { status: 200, body: recommendationResponse }])
    renderRecommendationPage()

    expect(await screen.findByRole('alert')).toHaveTextContent('서버에 연결할 수 없습니다')
    await userEvent.click(screen.getByRole('button', { name: '다시 시도' }))

    expect(await screen.findAllByRole('article')).toHaveLength(5)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})
