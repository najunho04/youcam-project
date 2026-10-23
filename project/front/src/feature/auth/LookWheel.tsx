import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { useMessages } from '../../shared/i18n'
import { AUTH_MESSAGES } from './messages'

/** 코디 일러스트 다섯 장 (public/landing) */
const LOOK_IMAGE_SOURCES = [
  '/landing/hero-woman-sketch.webp',
  '/landing/look-woman-check-shirt.webp',
  '/landing/look-man-denim-jacket.webp',
  '/landing/look-man-zip-hoodie.webp',
  '/landing/look-man-gray-knit.webp',
]
/** 바퀴가 끊기지 않게 다섯 장을 두 번 깔아 10장으로 돈다. */
const CARD_COUNT = LOOK_IMAGE_SOURCES.length * 2
/** 크기별로 가운데에서 이만큼까지만 보이고, 그 너머(보이지 않는 자리)에서 반대편으로 넘어간다. 작은 바퀴는 폼을 덮지 않게 좁게 편다. */
const VISIBLE_RANGE: Record<LookWheelSize, number> = { hero: 3, compact: 2 }
/** 화면 읽기·키보드로 고를 수 있는 범위. 연속 다섯 칸이라 코디가 겹치지 않는다. */
const SELECTABLE_RANGE = 2
const HOLD_MILLISECONDS = 3400

export type LookWheelSize = 'hero' | 'compact'

function prefersReducedMotion(): boolean {
  return typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** 메인(가운데)에서 몇 칸 떨어졌는지. -5 ~ 4 범위로 접는다. */
function centeredOffset(index: number, activeIndex: number): number {
  let offset = (index - activeIndex) % CARD_COUNT
  if (offset < -CARD_COUNT / 2) offset += CARD_COUNT
  if (offset >= CARD_COUNT / 2) offset -= CARD_COUNT
  return offset
}

function wrapIndex(index: number): number {
  return ((index % CARD_COUNT) + CARD_COUNT) % CARD_COUNT
}

/**
 * 반원 코디 카드. 카드를 부채꼴로 펼쳐 두고, 일정 시간마다 바퀴처럼 한 칸 돌아 다음 카드가 가운데로 온다.
 * onSelect 가 있으면(메인 화면) 가운데 카드를 눌러 시작하고 옆 카드를 눌러 가운데로 돌린다.
 * 없으면(로그인 화면) 누를 수 없는 장식으로 그린다.
 */
export function LookWheel({
  size = 'hero',
  onSelect,
  selectLabel,
  hint,
}: {
  size?: LookWheelSize
  onSelect?: () => void
  selectLabel?: string
  hint?: string
}) {
  const messages = useMessages(AUTH_MESSAGES).lookDeck
  const [activeIndex, setActiveIndex] = useState(0)
  const isInteractive = onSelect !== undefined

  // 가운데가 바뀔 때마다 대기 시간을 처음부터 다시 잰다. 탭이 숨겨져 있으면 돌지 않는다.
  useEffect(() => {
    if (prefersReducedMotion()) return
    let timeoutId = window.setTimeout(() => setActiveIndex((index) => wrapIndex(index + 1)), HOLD_MILLISECONDS)
    function handleVisibilityChange() {
      window.clearTimeout(timeoutId)
      if (!document.hidden) {
        timeoutId = window.setTimeout(() => setActiveIndex((index) => wrapIndex(index + 1)), HOLD_MILLISECONDS)
      }
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => {
      window.clearTimeout(timeoutId)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [activeIndex])

  const lookCount = LOOK_IMAGE_SOURCES.length
  const activeLookNumber = String((activeIndex % lookCount) + 1).padStart(2, '0')

  return (
    <section
      className={`look-wheel look-wheel-${size}`}
      aria-label={messages.label}
      onKeyDown={(event) => {
        if (!isInteractive) return
        if (event.key === 'ArrowRight') setActiveIndex(wrapIndex(activeIndex + 1))
        else if (event.key === 'ArrowLeft') setActiveIndex(wrapIndex(activeIndex - 1))
      }}
    >
      {Array.from({ length: CARD_COUNT }, (_, index) => {
        const lookIndex = index % lookCount
        const offset = centeredOffset(index, activeIndex)
        const distance = Math.abs(offset)
        const isFront = offset === 0
        const isSelectable = distance <= SELECTABLE_RANGE
        const visibleRange = VISIBLE_RANGE[size]
        // 숨긴 카드는 보이는 범위 바로 바깥에 머문다. 바퀴 아래까지 돌아가면 화면 밖으로 삐져나가 스크롤이 생긴다.
        const placedOffset = Math.max(-(visibleRange + 1), Math.min(visibleRange + 1, offset))
        const style: CSSProperties = {
          zIndex: 10 - distance,
          transform: `rotate(calc(var(--wheel-step-angle) * ${placedOffset})) scale(${1 - Math.abs(placedOffset) * 0.07})`,
          // 옆 카드는 불투명하게 두고 밝기만 낮춘다 (반투명이면 겹친 카드가 비쳐 지저분하다)
          filter: `brightness(${1 - Math.min(distance, visibleRange) * 0.2})`,
          opacity: distance > visibleRange ? 0 : 1,
        }
        const image = <img src={LOOK_IMAGE_SOURCES[lookIndex]} alt={isSelectable ? messages.looks[lookIndex] : ''} />
        if (!isInteractive) {
          return (
            <figure key={index} className="look-wheel-card" style={style} data-front={isFront} aria-hidden={!isSelectable}>
              {image}
            </figure>
          )
        }
        return (
          <button
            key={index}
            type="button"
            className="look-wheel-card"
            style={style}
            data-front={isFront}
            aria-label={isFront ? selectLabel : messages.bringToFront(messages.looks[lookIndex])}
            aria-hidden={!isSelectable}
            tabIndex={isFront ? 0 : -1}
            onClick={() => (isFront ? onSelect() : setActiveIndex(wrapIndex(activeIndex + offset)))}
          >
            {image}
          </button>
        )
      })}
      {isInteractive && (
        <div className="look-wheel-caption">
          <span className="look-wheel-count">
            {activeLookNumber} / {String(lookCount).padStart(2, '0')}
          </span>
          <span className="look-wheel-progress" aria-hidden="true">
            <span key={activeIndex} className="look-wheel-progress-fill" />
          </span>
          {hint && <span className="look-wheel-hint">{hint}</span>}
        </div>
      )}
    </section>
  )
}
