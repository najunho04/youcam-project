// recommendation 슬라이스 문구 (영어 · 한국어)
import { Season } from '../../common/type'
import type { Language } from '../../shared/i18n'
import { formatPrice } from '../../shared/i18n'

/** 서버가 내려 주는 한국어 시즌 이름. 추천 이유 태그에서 시즌 태그를 찾을 때 쓴다 (화면 언어와 무관). */
export const SERVER_SEASON_NAMES: Record<Season, string> = {
  [Season.SPRING_WARM]: '봄 웜톤',
  [Season.SUMMER_COOL]: '여름 쿨톤',
  [Season.AUTUMN_WARM]: '가을 웜톤',
  [Season.WINTER_COOL]: '겨울 쿨톤',
}

/** 서버 태그(스타일·시즌·추천 이유)에 나오는 한국어 단어 → 영어 */
const ENGLISH_TAG_WORDS: [string, string][] = [
  ['미니멀', 'Minimal'],
  ['캐주얼', 'Casual'],
  ['스트릿', 'Street'],
  ['포멀', 'Formal'],
  ['러블리', 'Lovely'],
  ['봄 웜톤', 'Spring Warm'],
  ['여름 쿨톤', 'Summer Cool'],
  ['가을 웜톤', 'Autumn Warm'],
  ['겨울 쿨톤', 'Winter Cool'],
]

/** 추천 이유 태그 문형: '선호하는 X' · 'X 컬러' · 'X 스타일' */
function translateTagToEnglish(tag: string): string {
  const translatedWords = ENGLISH_TAG_WORDS.reduce((text, [korean, english]) => text.replaceAll(korean, english), tag)
  return translatedWords
    .replace(/^선호하는 (.+)$/, 'Your $1 pick')
    .replace(/^(.+) 컬러$/, '$1 colors')
    .replace(/^(.+) 스타일$/, '$1 style')
}

const ENGLISH = {
  title: 'Recommended tops',
  lede: 'Picked using both your style and your personal color.',
  fallbackNotice: "We don't know your style well yet, so here are items that suit your personal color.",
  preferredStyle: 'Preferred style',
  styleSummary: 'Style summary',
  palette: (seasonName: string) => `${seasonName} palette`,
  goToProfile: 'Fill in your profile',
  goToPersonalColor: 'Analyze my personal color',
  noItems: 'No items to recommend yet',
  rank: (rank: number) => `#${rank}`,
  reasons: 'Why we picked this',
  tryOn: 'Try it on',
  buy: 'Buy now',
  seasonNames: {
    [Season.SPRING_WARM]: 'Spring Warm',
    [Season.SUMMER_COOL]: 'Summer Cool',
    [Season.AUTUMN_WARM]: 'Autumn Warm',
    [Season.WINTER_COOL]: 'Winter Cool',
  } as Record<Season, string>,
  tag: translateTagToEnglish,
  price: (price: number) => formatPrice(price, 'en'),
}

const KOREAN: typeof ENGLISH = {
  title: '추천 상의',
  lede: '취향과 퍼스널컬러를 함께 봤어요.',
  fallbackNotice: '취향 데이터가 적어 퍼스널컬러에 어울리는 상품을 보여드려요',
  preferredStyle: '선호 스타일',
  styleSummary: '취향 요약',
  palette: (seasonName: string) => `${seasonName} 팔레트`,
  goToProfile: '프로필 입력하기',
  goToPersonalColor: '퍼스널컬러 진단하기',
  noItems: '추천할 상품이 아직 없어요',
  rank: (rank: number) => `${rank}위`,
  reasons: '추천 이유',
  tryOn: '입어보기',
  buy: '구매하러 가기',
  seasonNames: SERVER_SEASON_NAMES,
  tag: (tag: string) => tag,
  price: (price: number) => formatPrice(price, 'ko'),
}

export const RECOMMENDATION_MESSAGES: Record<Language, typeof ENGLISH> = { en: ENGLISH, ko: KOREAN }
