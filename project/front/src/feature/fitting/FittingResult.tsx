import type { FittingDto, ProductDto } from '../../common/type'
import { Button } from '../../shared/ui'

const imageStyle = {
  width: '100%',
  aspectRatio: '3 / 4',
  objectFit: 'cover',
  borderRadius: 'var(--radius)',
  background: 'var(--color-surface)',
} as const

/** 상품명·가격·쇼핑몰. */
export function ProductSummary({ product }: { product: ProductDto }) {
  return (
    <section style={{ display: 'grid', gap: 4 }}>
      <h2 style={{ margin: 0, fontSize: 16 }}>{product.title}</h2>
      <p style={{ margin: 0, fontWeight: 700 }}>{`${product.price.toLocaleString('ko-KR')}원`}</p>
      <p style={{ margin: 0, color: 'var(--color-muted)' }}>{product.mallName}</p>
    </section>
  )
}

/** DONE: 원본 / 결과 비교, 구매하러 가기(새 탭), 다른 상품 입어보기. */
export function FittingResult({ fitting, onTryOther }: { fitting: FittingDto; onTryOther: () => void }) {
  return (
    <>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <figure style={{ margin: 0, display: 'grid', gap: 4 }}>
          <img src={fitting.originalImageUrl} alt="원본" style={imageStyle} />
          <figcaption style={{ color: 'var(--color-muted)', textAlign: 'center' }}>원본</figcaption>
        </figure>
        <figure style={{ margin: 0, display: 'grid', gap: 4 }}>
          <img src={fitting.resultImageUrl ?? ''} alt="피팅 결과" style={imageStyle} />
          <figcaption style={{ color: 'var(--color-muted)', textAlign: 'center' }}>피팅 결과</figcaption>
        </figure>
      </div>
      <ProductSummary product={fitting.product} />
      <a
        className="button button-primary"
        href={fitting.product.purchaseUrl}
        target="_blank"
        rel="noopener noreferrer"
        style={{ textAlign: 'center', textDecoration: 'none', boxSizing: 'border-box' }}
      >
        구매하러 가기
      </a>
      <Button variant="secondary" onClick={onTryOther}>
        다른 상품 입어보기
      </Button>
    </>
  )
}

/** FAILED: 상품 이미지만 보여주고 다시 시도. */
export function FittingFailure({ product, onRetry }: { product: ProductDto; onRetry: () => void }) {
  return (
    <>
      <img src={product.imageUrl} alt={product.title} style={{ ...imageStyle, aspectRatio: '1 / 1' }} />
      <ProductSummary product={product} />
      <p role="alert" style={{ margin: 0, color: 'var(--color-error)' }}>
        가상 피팅에 실패했어요
      </p>
      <Button onClick={onRetry}>다시 시도</Button>
    </>
  )
}
