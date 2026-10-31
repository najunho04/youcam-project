import { useRef, useState } from 'react'
import type { KeyboardEvent, PointerEvent } from 'react'
import type { FittingDto, ProductDto } from '../../common/type'
import { useMessages } from '../../shared/i18n'
import { FITTING_MESSAGES } from './messages'

const INITIAL_DIVIDER_PERCENT = 50
const KEYBOARD_STEP_PERCENT = 5

/** 상품 썸네일·상품명·쇼핑몰·가격 한 줄. */
export function ProductSummary({ product, caption }: { product: ProductDto; caption?: string }) {
  const messages = useMessages(FITTING_MESSAGES)
  return (
    <section className="fitting-product">
      <img className="fitting-product-thumbnail" src={product.imageUrl} alt="" />
      <div className="fitting-product-text">
        <h2 className="fitting-product-title">{product.title}</h2>
        <p className="footnote">{caption ?? product.mallName}</p>
      </div>
      <p className="fitting-product-price">{messages.price(product.price, product.currency)}</p>
    </section>
  )
}

/** DONE: 원본 위에 결과를 겹치고, 경계선을 끌어 비교한다. */
export function FittingComparison({ fitting }: { fitting: FittingDto }) {
  const messages = useMessages(FITTING_MESSAGES)
  const [dividerPercent, setDividerPercent] = useState(INITIAL_DIVIDER_PERCENT)
  const isDragging = useRef(false)

  function updateFromPointer(event: PointerEvent<HTMLDivElement>) {
    const bounds = event.currentTarget.getBoundingClientRect()
    if (bounds.width <= 0) return
    setDividerPercent(Math.max(0, Math.min(100, ((event.clientX - bounds.left) / bounds.width) * 100)))
  }

  function handlePointerDown(event: PointerEvent<HTMLDivElement>) {
    isDragging.current = true
    if (typeof event.currentTarget.setPointerCapture === 'function') event.currentTarget.setPointerCapture(event.pointerId)
    updateFromPointer(event)
  }

  function handlePointerMove(event: PointerEvent<HTMLDivElement>) {
    if (isDragging.current) updateFromPointer(event)
  }

  function handlePointerEnd() {
    isDragging.current = false
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'ArrowLeft') setDividerPercent((percent) => Math.max(0, percent - KEYBOARD_STEP_PERCENT))
    if (event.key === 'ArrowRight') setDividerPercent((percent) => Math.min(100, percent + KEYBOARD_STEP_PERCENT))
  }

  return (
    <div
      className="fitting-compare"
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerEnd}
      onPointerCancel={handlePointerEnd}
    >
      <img className="fitting-compare-layer" src={fitting.originalImageUrl} alt={messages.original} draggable={false} />
      <img
        className="fitting-compare-layer"
        src={fitting.resultImageUrl ?? ''}
        alt={messages.result}
        draggable={false}
        style={{ clipPath: `inset(0 0 0 ${dividerPercent}%)` }}
      />
      <span className="fitting-compare-tag fitting-compare-tag-left" aria-hidden="true">
        {messages.original}
      </span>
      <span className="fitting-compare-tag fitting-compare-tag-right" aria-hidden="true">
        {messages.result}
      </span>
      <div
        className="fitting-compare-handle"
        role="slider"
        tabIndex={0}
        aria-label={messages.compare}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(dividerPercent)}
        onKeyDown={handleKeyDown}
        style={{ left: `${dividerPercent}%` }}
      >
        <span className="fitting-compare-knob" aria-hidden="true">
          ‹ ›
        </span>
      </div>
    </div>
  )
}

/** PENDING: 내 사진 위에 쉬머와 진행 표시. 시간 초과면 진행 표시 대신 정지 상태. */
export function FittingPendingPreview({
  originalImageUrl,
  isTimedOut,
  loadingMessage,
}: {
  originalImageUrl: string
  isTimedOut: boolean
  loadingMessage: string
}) {
  return (
    <div className={`fitting-compare fitting-pending${isTimedOut ? ' is-timed-out' : ''}`}>
      <img className="fitting-compare-layer" src={originalImageUrl} alt="" draggable={false} />
      {!isTimedOut && (
        <>
          <span className="fitting-shimmer" aria-hidden="true" />
          <div className="fitting-pending-status">
            <span className="fitting-pending-pill" role="status">
              <span className="spinner" aria-hidden="true" />
              {loadingMessage}
            </span>
          </div>
        </>
      )}
    </div>
  )
}

/** FAILED: 상품 이미지만 보여준다. */
export function FittingFailure({ product }: { product: ProductDto }) {
  return <img className="fitting-failure-image" src={product.imageUrl} alt={product.title} />
}
