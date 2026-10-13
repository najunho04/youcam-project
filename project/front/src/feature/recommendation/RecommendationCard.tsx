import type { RecommendationItem } from '../../common/type'
import { Button, buttonClassName } from '../../shared/ui'

/**
 * 추천 상품 카드: 이미지·상품명·가격·쇼핑몰·추천 이유, 입어보기·구매하러 가기(새 탭).
 * 1위는 큰 카드(featured), 나머지는 가로형 카드. highlightedReason 이 들어간 추천 이유는 강조 칩.
 */
export function RecommendationCard({
  item,
  rank,
  isFeatured,
  highlightedReason,
  onTryOn,
}: {
  item: RecommendationItem
  rank: number
  isFeatured: boolean
  highlightedReason: string
  onTryOn: () => void
}) {
  const { product, reasonTags } = item
  return (
    <article aria-label={product.title} className={`recommendation-card${isFeatured ? ' is-featured' : ''}`}>
      <div className="recommendation-card-image">
        <img src={product.imageUrl} alt={product.title} loading={isFeatured ? 'eager' : 'lazy'} />
        <span className="recommendation-card-rank" aria-hidden="true">{`${rank}위`}</span>
      </div>
      <div className="recommendation-card-body">
        <div>
          <p className="recommendation-card-mall">{product.mallName}</p>
          <h2 className="recommendation-card-title">{product.title}</h2>
        </div>
        <p className="price">{`${product.price.toLocaleString('ko-KR')}원`}</p>
        <ul aria-label="추천 이유" className="chip-list">
          {reasonTags.map((reasonTag) => (
            <li key={reasonTag} className={`chip${reasonTag.includes(highlightedReason) ? ' chip-accent' : ''}`}>
              {reasonTag}
            </li>
          ))}
        </ul>
        <div className="button-row">
          <Button size="small" onClick={onTryOn}>
            입어보기
          </Button>
          <a
            className={buttonClassName('secondary', 'small')}
            href={product.purchaseUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            구매하러 가기
          </a>
        </div>
      </div>
    </article>
  )
}
