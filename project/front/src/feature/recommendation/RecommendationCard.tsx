import type { RecommendationItem } from '../../common/type'
import { Button } from '../../shared/ui'

const tagStyle = {
  padding: '4px 10px',
  borderRadius: 999,
  background: 'var(--color-surface)',
  border: '1px solid var(--color-border)',
  fontSize: 13,
} as const

/** 추천 상품 카드: 이미지·상품명·가격·쇼핑몰·추천 이유, 입어보기·구매하러 가기(새 탭). */
export function RecommendationCard({ item, onTryOn }: { item: RecommendationItem; onTryOn: () => void }) {
  const { product, reasonTags } = item
  return (
    <article
      aria-label={product.title}
      style={{ display: 'grid', gap: 8, padding: 12, border: '1px solid var(--color-border)', borderRadius: 'var(--radius)' }}
    >
      <img
        src={product.imageUrl}
        alt={product.title}
        style={{ width: '100%', aspectRatio: '1 / 1', objectFit: 'cover', borderRadius: 'var(--radius)' }}
      />
      <h2 style={{ margin: 0, fontSize: 16 }}>{product.title}</h2>
      <p style={{ margin: 0, fontWeight: 700 }}>{`${product.price.toLocaleString('ko-KR')}원`}</p>
      <p style={{ margin: 0, color: 'var(--color-muted)' }}>{product.mallName}</p>
      <ul aria-label="추천 이유" style={{ display: 'flex', flexWrap: 'wrap', gap: 6, padding: 0, margin: 0, listStyle: 'none' }}>
        {reasonTags.map((reasonTag) => (
          <li key={reasonTag} style={tagStyle}>
            {reasonTag}
          </li>
        ))}
      </ul>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <Button variant="secondary" onClick={onTryOn}>
          입어보기
        </Button>
        <a
          className="button button-primary"
          href={product.purchaseUrl}
          target="_blank"
          rel="noopener noreferrer"
          style={{ textAlign: 'center', textDecoration: 'none', boxSizing: 'border-box' }}
        >
          구매하러 가기
        </a>
      </div>
    </article>
  )
}
