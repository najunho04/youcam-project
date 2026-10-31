import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { FittingStatus, Style } from '../../../src/common/type'
import type { FittingDto } from '../../../src/common/type'
import { FittingPage } from '../../../src/feature/fitting'
import { tokenStorage } from '../../../src/shared/auth'
import { ROUTES } from '../../../src/shared/navigation'
import { stubFetch } from './fetchStub'

const PRODUCT_ID = 21

const doneFitting: FittingDto = {
  id: 7,
  productId: PRODUCT_ID,
  product: {
    id: PRODUCT_ID,
    title: 'Test knit 21',
    price: 39.99,
    currency: 'USD',
    mallName: 'Test mall',
    purchaseUrl: 'https://shopping.test/products/21',
    imageUrl: 'https://image.test/products/21.jpg',
    style: Style.MINIMAL,
  },
  status: FittingStatus.DONE,
  originalImageUrl: 'https://storage.test/body-images/1/body.jpg',
  resultImageUrl: 'https://storage.test/fittings/1/7.jpg',
}

describe('FittingPage 영어 화면', () => {
  beforeEach(() => {
    tokenStorage.set('valid-token')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('DONE 이면 비교 이미지·가격·버튼을 영어로 보여준다', async () => {
    stubFetch([{ status: 202, body: doneFitting }])
    render(
      <MemoryRouter initialEntries={[ROUTES.fitting(PRODUCT_ID)]}>
        <Routes>
          <Route path={ROUTES.fittingPattern} element={<FittingPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByRole('img', { name: 'Try-on result' })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Original' })).toBeInTheDocument()
    expect(screen.getByRole('slider', { name: 'Compare original and try-on result' })).toBeInTheDocument()
    expect(screen.getByText('$39.99')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Buy now' })).toHaveAttribute('target', '_blank')
    expect(screen.getByRole('button', { name: 'Try another item' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Recommendations' })).toBeInTheDocument()
  })
})
