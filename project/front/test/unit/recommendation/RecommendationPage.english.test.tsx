import { render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { Season, Style, SeasonSubtype } from '../../../src/common/type'
import type { RecommendationResponse } from '../../../src/common/type'
import { RecommendationPage } from '../../../src/feature/recommendation'
import { tokenStorage } from '../../../src/shared/auth'
import { ROUTES } from '../../../src/shared/navigation'
import { stubFetch } from './fetchStub'

const recommendationResponse: RecommendationResponse = {
  styleTags: ['미니멀', '가을 웜톤'],
  season: Season.AUTUMN_WARM,
  subtype: SeasonSubtype.DEEP,
  palette: ['#C19A6B'],
  isFallback: false,
  items: [
    {
      product: {
        id: 21,
        title: 'Test knit 21',
        price: 39.99,
        currency: 'USD',
        mallName: 'Test mall',
        purchaseUrl: 'https://shopping.test/products/21',
        imageUrl: 'https://image.test/products/21.jpg',
        style: Style.MINIMAL,
      },
      score: 0.9,
      tasteScore: 0.9,
      colorScore: 0.9,
      reasonTags: ['선호하는 미니멀', '가을 웜톤 컬러', '캐주얼 스타일'],
    },
  ],
}

describe('RecommendationPage 영어 화면', () => {
  beforeEach(() => {
    tokenStorage.set('valid-token')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('서버의 한국어 태그를 영어로 바꾸고, 가격·버튼도 영어로 보여준다', async () => {
    stubFetch([{ status: 200, body: recommendationResponse }])
    render(
      <MemoryRouter initialEntries={[ROUTES.recommendation]}>
        <Routes>
          <Route path={ROUTES.recommendation} element={<RecommendationPage />} />
        </Routes>
      </MemoryRouter>,
    )

    const card = await screen.findByRole('article', { name: 'Test knit 21' })
    const styleSummary = screen.getByRole('list', { name: 'Style summary' })
    expect(within(styleSummary).getAllByRole('listitem').map((item) => item.textContent)).toEqual(['Minimal', 'Autumn Warm'])
    expect(screen.getByRole('list', { name: 'Autumn Warm palette' })).toBeInTheDocument()

    const reasons = within(card).getByRole('list', { name: 'Why we picked this' })
    const reasonItems = within(reasons).getAllByRole('listitem')
    expect(reasonItems.map((item) => item.textContent)).toEqual(['Your Minimal pick', 'Autumn Warm colors', 'Casual style'])
    // 시즌 태그 강조는 화면 언어와 상관없이 유지된다
    expect(reasonItems[1]).toHaveClass('chip-accent')
    expect(within(card).getByText('$39.99')).toBeInTheDocument()
    expect(within(card).getByRole('button', { name: 'Try it on' })).toBeInTheDocument()
    expect(within(card).getByRole('link', { name: 'Buy now' })).toHaveAttribute('href', 'https://shopping.test/products/21')
  })
})
