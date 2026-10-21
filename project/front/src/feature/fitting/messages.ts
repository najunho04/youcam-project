// fitting 슬라이스 문구 (영어 · 한국어)
import type { Language } from '../../shared/i18n'
import { formatPrice } from '../../shared/i18n'

const ENGLISH = {
  title: 'Virtual try-on',
  loading: 'Trying it on',
  timedOut: 'This is taking longer than usual',
  pendingCaption: 'Usually takes 20–40 seconds',
  backLabel: 'Recommendations',
  tryOther: 'Try another item',
  compareHint: 'Drag the divider left and right to compare with the original.',
  buy: 'Buy now',
  failed: 'Virtual try-on failed',
  retry: 'Try again',
  checkAgain: 'Check again',
  original: 'Original',
  result: 'Try-on result',
  compare: 'Compare original and try-on result',
  price: (price: number) => formatPrice(price, 'en'),
}

const KOREAN: typeof ENGLISH = {
  title: '가상 피팅',
  loading: '입혀보는 중',
  timedOut: '시간이 오래 걸리고 있어요',
  pendingCaption: '보통 20~40초 걸려요',
  backLabel: '추천',
  tryOther: '다른 상품 입어보기',
  compareHint: '경계선을 좌우로 끌어 원본과 비교해 보세요.',
  buy: '구매하러 가기',
  failed: '가상 피팅에 실패했어요',
  retry: '다시 시도',
  checkAgain: '다시 확인',
  original: '원본',
  result: '피팅 결과',
  compare: '원본과 피팅 결과 비교',
  price: (price: number) => formatPrice(price, 'ko'),
}

export const FITTING_MESSAGES: Record<Language, typeof ENGLISH> = { en: ENGLISH, ko: KOREAN }
