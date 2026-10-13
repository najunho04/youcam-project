import { useRef, useState } from 'react'
import type { PointerEvent } from 'react'
import type { SwipeCardDto } from '../../common/type'

const CONFIRM_DISTANCE_RATIO = 0.3
const ROTATION_DEGREES_PER_PIXEL = 0.05
const MAXIMUM_ROTATION_DEGREES = 15
const VERTICAL_FOLLOW_RATIO = 0.3
// 놓을 때 속도 계산에 쓰는 최근 구간. 이보다 짧은 기록은 속도 0 으로 본다
const VELOCITY_WINDOW_MILLISECONDS = 100
const MINIMUM_VELOCITY_SAMPLE_MILLISECONDS = 16
// 카드용 감속률 (Apple 투영식, 스크롤보다 빠르게 멈춘다)
const DECELERATION_RATE = 0.99

type PointerSample = { x: number; time: number }

export function rotationOf(offsetX: number): number {
  return Math.max(-MAXIMUM_ROTATION_DEGREES, Math.min(MAXIMUM_ROTATION_DEGREES, offsetX * ROTATION_DEGREES_PER_PIXEL))
}

/** 놓은 속도로 카드가 멈출 지점까지의 추가 이동 거리 (Apple 'Designing Fluid Interfaces' 투영식). */
function projectDistance(velocityPixelsPerSecond: number): number {
  return ((velocityPixelsPerSecond / 1000) * DECELERATION_RATE) / (1 - DECELERATION_RATE)
}

function velocityOf(samples: PointerSample[]): number {
  if (samples.length < 2) return 0
  const first = samples[0]
  const last = samples[samples.length - 1]
  const elapsedMilliseconds = last.time - first.time
  if (elapsedMilliseconds < MINIMUM_VELOCITY_SAMPLE_MILLISECONDS) return 0
  return ((last.x - first.x) / elapsedMilliseconds) * 1000
}

/** 애니메이션 중에 다시 잡으면 화면에 보이는 현재 위치에서 이어서 끈다. */
function presentationOffsetX(element: HTMLElement, fallbackOffsetX: number): number {
  if (typeof DOMMatrixReadOnly === 'undefined') return fallbackOffsetX
  const transform = getComputedStyle(element).transform
  if (!transform || transform === 'none') return fallbackOffsetX
  try {
    return new DOMMatrixReadOnly(transform).m41
  } catch {
    return fallbackOffsetX
  }
}

/**
 * 카드 한 장. pointer events 로 1:1 드래그한다 (잡은 지점 기준).
 * 가로 이동이 카드 너비의 30% 이상이거나, 놓은 속도로 투영한 착지점이 30% 를 넘으면 그 방향으로 확정(오른쪽 = 좋아요).
 * 아니면 살짝 튕기며 원위치로 돌아간다.
 */
export function SwipeCard({
  card,
  onAnswer,
  onDragProgress,
}: {
  card: SwipeCardDto
  onAnswer: (liked: boolean, releaseOffsetX: number) => void
  onDragProgress?: (progress: number) => void
}) {
  const [offsetX, setOffsetX] = useState(0)
  const [offsetY, setOffsetY] = useState(0)
  const [isDragging, setIsDragging] = useState(false)
  const dragStart = useRef<{ pointerX: number; pointerY: number; offsetX: number } | null>(null)
  const pointerSamples = useRef<PointerSample[]>([])
  const cardWidth = useRef(0)

  function reportProgress(nextOffsetX: number) {
    if (onDragProgress && cardWidth.current > 0) onDragProgress(Math.min(1, Math.abs(nextOffsetX) / cardWidth.current))
  }

  function handlePointerDown(event: PointerEvent<HTMLDivElement>) {
    const element = event.currentTarget
    if (typeof element.setPointerCapture === 'function') element.setPointerCapture(event.pointerId)
    cardWidth.current = element.getBoundingClientRect().width
    const startOffsetX = presentationOffsetX(element, offsetX)
    dragStart.current = { pointerX: event.clientX, pointerY: event.clientY, offsetX: startOffsetX }
    // 속도는 실제 움직임(pointermove)만으로 잰다. 누른 지점은 넣지 않는다
    pointerSamples.current = []
    setIsDragging(true)
    setOffsetX(startOffsetX)
  }

  function handlePointerMove(event: PointerEvent<HTMLDivElement>) {
    const start = dragStart.current
    if (start === null) return
    const nextOffsetX = start.offsetX + event.clientX - start.pointerX
    pointerSamples.current = [...pointerSamples.current, { x: event.clientX, time: event.timeStamp }].filter(
      (sample) => event.timeStamp - sample.time <= VELOCITY_WINDOW_MILLISECONDS,
    )
    setOffsetX(nextOffsetX)
    setOffsetY((event.clientY - start.pointerY) * VERTICAL_FOLLOW_RATIO)
    reportProgress(nextOffsetX)
  }

  function handlePointerUp(event: PointerEvent<HTMLDivElement>) {
    const start = dragStart.current
    if (start === null) return
    dragStart.current = null
    const finalOffsetX = start.offsetX + event.clientX - start.pointerX
    const recentSamples = pointerSamples.current.filter(
      (sample) => event.timeStamp - sample.time <= VELOCITY_WINDOW_MILLISECONDS,
    )
    const releaseVelocity = velocityOf([...recentSamples, { x: event.clientX, time: event.timeStamp }])
    const projectedOffsetX = finalOffsetX + projectDistance(releaseVelocity)
    const confirmDistance = cardWidth.current * CONFIRM_DISTANCE_RATIO
    setIsDragging(false)
    setOffsetX(0)
    setOffsetY(0)
    reportProgress(0)
    if (cardWidth.current <= 0) return
    if (Math.abs(finalOffsetX) >= confirmDistance) onAnswer(finalOffsetX > 0, finalOffsetX)
    else if (Math.abs(projectedOffsetX) >= confirmDistance) onAnswer(projectedOffsetX > 0, finalOffsetX)
  }

  function handlePointerCancel() {
    dragStart.current = null
    setIsDragging(false)
    setOffsetX(0)
    setOffsetY(0)
    reportProgress(0)
  }

  const stampOpacity = cardWidth.current > 0 ? Math.min(1, Math.abs(offsetX) / (cardWidth.current * CONFIRM_DISTANCE_RATIO)) : 0

  return (
    <div
      role="group"
      aria-label="상의 카드"
      className={`swipe-card${isDragging ? ' is-dragging' : ''}`}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerCancel}
      style={{ transform: `translateX(${offsetX}px) translateY(${offsetY}px) rotate(${rotationOf(offsetX)}deg)` }}
    >
      <img src={card.imageUrl} alt="상의 이미지" draggable={false} />
      <span
        className="swipe-stamp swipe-stamp-like"
        aria-hidden="true"
        style={{ opacity: offsetX > 0 ? stampOpacity : 0 }}
      >
        LIKE
      </span>
      <span
        className="swipe-stamp swipe-stamp-nope"
        aria-hidden="true"
        style={{ opacity: offsetX < 0 ? stampOpacity : 0 }}
      >
        NOPE
      </span>
    </div>
  )
}
