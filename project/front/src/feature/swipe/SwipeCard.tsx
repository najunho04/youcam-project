import { useState } from 'react'
import type { PointerEvent } from 'react'
import type { SwipeCardDto } from '../../common/type'

const CONFIRM_DISTANCE_RATIO = 0.3
const ROTATION_DEGREES_PER_PIXEL = 0.05
const MAXIMUM_ROTATION_DEGREES = 15

/**
 * 카드 한 장. pointer events 로 좌우 드래그한다.
 * 가로 이동이 카드 너비의 30% 이상이면 그 방향으로 확정(오른쪽 = 좋아요), 아니면 원위치로 복귀.
 */
export function SwipeCard({ card, onAnswer }: { card: SwipeCardDto; onAnswer: (liked: boolean) => void }) {
  const [dragStartX, setDragStartX] = useState<number | null>(null)
  const [dragOffsetX, setDragOffsetX] = useState(0)
  const isDragging = dragStartX !== null

  function handlePointerDown(event: PointerEvent<HTMLDivElement>) {
    setDragStartX(event.clientX)
    if (typeof event.currentTarget.setPointerCapture === 'function') {
      event.currentTarget.setPointerCapture(event.pointerId)
    }
    setDragOffsetX(0)
  }

  function handlePointerMove(event: PointerEvent<HTMLDivElement>) {
    if (dragStartX === null) return
    setDragOffsetX(event.clientX - dragStartX)
  }

  function handlePointerUp(event: PointerEvent<HTMLDivElement>) {
    if (dragStartX === null) return
    const finalOffsetX = event.clientX - dragStartX
    setDragStartX(null)
    setDragOffsetX(0)
    const cardWidth = event.currentTarget.getBoundingClientRect().width
    if (cardWidth > 0 && Math.abs(finalOffsetX) >= cardWidth * CONFIRM_DISTANCE_RATIO) onAnswer(finalOffsetX > 0)
  }

  function handlePointerCancel() {
    setDragStartX(null)
    setDragOffsetX(0)
  }

  const rotationDegrees = Math.max(
    -MAXIMUM_ROTATION_DEGREES,
    Math.min(MAXIMUM_ROTATION_DEGREES, dragOffsetX * ROTATION_DEGREES_PER_PIXEL),
  )

  return (
    <div
      role="group"
      aria-label="상의 카드"
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerCancel}
      style={{
        transform: `translateX(${dragOffsetX}px) rotate(${rotationDegrees}deg)`,
        transition: isDragging ? 'none' : 'transform 0.2s ease-out',
        touchAction: 'none',
        userSelect: 'none',
        cursor: 'grab',
        borderRadius: 'var(--radius)',
        overflow: 'hidden',
        border: '1px solid var(--color-border)',
        background: 'var(--color-surface)',
      }}
    >
      <img
        src={card.imageUrl}
        alt="상의 이미지"
        draggable={false}
        style={{ display: 'block', width: '100%', aspectRatio: '3 / 4', objectFit: 'cover', pointerEvents: 'none' }}
      />
    </div>
  )
}
