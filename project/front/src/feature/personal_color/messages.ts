// personal_color 슬라이스 문구 (영어 · 한국어)
import { Season } from '../../common/type'

const ENGLISH = {
  title: 'Two photos is all it takes',
  lede: 'Your face photo tells us your skin tone. The upper-body photo is used for virtual try-on.',
  analyze: 'Analyze',
  analyzing: 'Analyzing… this takes a few seconds',
  selfieLabel: 'Face photo',
  selfieGuide: 'Face forward, natural light, minimal makeup, face filling the frame',
  bodyImageLabel: 'Upper-body photo',
  bodyImageGuide: 'Stand facing forward, chest up with shoulders visible, nobody else in the shot',
  faceNotDetected: "We couldn't find your face. Please retake the face photo.",
  preview: (label: string) => `${label} preview`,
  select: (label: string) => `Choose ${label.toLowerCase()}`,
  resultHeading: 'Your personal color result',
  myPersonalColor: 'My personal color',
  matchingColors: 'Colors that suit you',
  palette: 'Palette',
  paletteNote: 'Recommendations also weigh how close each item is to this palette.',
  next: 'Next',
  seasonNames: {
    [Season.SPRING_WARM]: 'Spring Warm',
    [Season.SUMMER_COOL]: 'Summer Cool',
    [Season.AUTUMN_WARM]: 'Autumn Warm',
    [Season.WINTER_COOL]: 'Winter Cool',
  } as Record<Season, string>,
  seasonDescriptions: {
    [Season.SPRING_WARM]: 'Bright, warm colors bring your face to life.',
    [Season.SUMMER_COOL]: 'Soft, clear colors make your face glow.',
    [Season.AUTUMN_WARM]: 'Deep, warm colors light up your face.',
    [Season.WINTER_COOL]: 'Vivid, cool colors sharpen your look.',
  } as Record<Season, string>,
}

const KOREAN: typeof ENGLISH = {
  title: '사진 두 장이면 돼요',
  lede: '얼굴 사진으로 피부톤을 보고, 상반신 사진은 가상 피팅에 써요.',
  analyze: '분석하기',
  analyzing: '분석 중… 몇 초 걸려요',
  selfieLabel: '얼굴 사진',
  selfieGuide: '정면, 자연광, 화장 최소화, 얼굴이 화면을 가득 채우게',
  bodyImageLabel: '상반신 사진',
  bodyImageGuide: '정면으로 서서, 가슴 위 상반신과 어깨가 보이게, 혼자 나오게',
  faceNotDetected: '얼굴을 인식하지 못했어요. 얼굴 사진을 다시 찍어 주세요.',
  preview: (label: string) => `${label} 미리보기`,
  select: (label: string) => `${label} 선택`,
  resultHeading: '퍼스널컬러 결과',
  myPersonalColor: '나의 퍼스널컬러',
  matchingColors: '잘 어울리는 색',
  palette: '팔레트',
  paletteNote: '추천 상품은 이 팔레트와 얼마나 가까운지를 함께 봐요.',
  next: '다음',
  seasonNames: {
    [Season.SPRING_WARM]: '봄 웜톤',
    [Season.SUMMER_COOL]: '여름 쿨톤',
    [Season.AUTUMN_WARM]: '가을 웜톤',
    [Season.WINTER_COOL]: '겨울 쿨톤',
  },
  seasonDescriptions: {
    [Season.SPRING_WARM]: '밝고 따뜻한 색이 생기를 더해 줘요.',
    [Season.SUMMER_COOL]: '부드럽고 맑은 색이 얼굴을 환하게 만들어요.',
    [Season.AUTUMN_WARM]: '깊고 따뜻한 색이 얼굴을 환하게 만들어요.',
    [Season.WINTER_COOL]: '선명하고 차가운 색이 인상을 또렷하게 해 줘요.',
  },
}

export const PERSONAL_COLOR_MESSAGES = { en: ENGLISH, ko: KOREAN }
