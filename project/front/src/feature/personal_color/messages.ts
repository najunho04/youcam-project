// personal_color 슬라이스 문구 (영어 · 한국어)
import { Season, SeasonSubtype } from '../../common/type'
import { FaceGuideStatus } from './faceGuide'
import type { FaceGuideCheckName } from './faceGuide'
import { UpperBodyGuideStatus } from './upperBodyGuide'
import type { UpperBodyGuideCheckName } from './upperBodyGuide'

export type FaceColorPart = 'skin' | 'lip' | 'eye' | 'eyebrow' | 'hair'
export type AxisName = 'warmth' | 'depth' | 'clarity'

const ENGLISH_SEASON_NAMES: Record<Season, string> = {
  [Season.SPRING_WARM]: 'Spring Warm',
  [Season.SUMMER_COOL]: 'Summer Cool',
  [Season.AUTUMN_WARM]: 'Autumn Warm',
  [Season.WINTER_COOL]: 'Winter Cool',
}
const ENGLISH_SEASON_WORDS: Record<Season, string> = {
  [Season.SPRING_WARM]: 'Spring',
  [Season.SUMMER_COOL]: 'Summer',
  [Season.AUTUMN_WARM]: 'Autumn',
  [Season.WINTER_COOL]: 'Winter',
}
const ENGLISH_SUBTYPE_NAMES: Record<SeasonSubtype, string> = {
  [SeasonSubtype.TRUE]: 'True',
  [SeasonSubtype.LIGHT]: 'Light',
  [SeasonSubtype.DEEP]: 'Deep',
  [SeasonSubtype.BRIGHT]: 'Bright',
  [SeasonSubtype.SOFT]: 'Soft',
}
const ENGLISH_SUBTYPE_TRAITS: Record<SeasonSubtype, string> = {
  [SeasonSubtype.TRUE]: 'Undertone',
  [SeasonSubtype.LIGHT]: 'Lightness',
  [SeasonSubtype.DEEP]: 'Depth',
  [SeasonSubtype.BRIGHT]: 'Clarity',
  [SeasonSubtype.SOFT]: 'Softness',
}
const KOREAN_SEASON_NAMES: Record<Season, string> = {
  [Season.SPRING_WARM]: '봄 웜톤',
  [Season.SUMMER_COOL]: '여름 쿨톤',
  [Season.AUTUMN_WARM]: '가을 웜톤',
  [Season.WINTER_COOL]: '겨울 쿨톤',
}
const KOREAN_SUBTYPE_NAMES: Record<SeasonSubtype, string> = {
  [SeasonSubtype.TRUE]: '트루',
  [SeasonSubtype.LIGHT]: '라이트',
  [SeasonSubtype.DEEP]: '딥',
  [SeasonSubtype.BRIGHT]: '브라이트',
  [SeasonSubtype.SOFT]: '소프트',
}
const KOREAN_SUBTYPE_TRAITS: Record<SeasonSubtype, string> = {
  [SeasonSubtype.TRUE]: '웜·쿨 성향',
  [SeasonSubtype.LIGHT]: '밝기',
  [SeasonSubtype.DEEP]: '깊이',
  [SeasonSubtype.BRIGHT]: '선명함',
  [SeasonSubtype.SOFT]: '부드러움',
}

const ENGLISH = {
  title: 'Two photos is all it takes',
  lede: 'Your face photo tells us your skin tone. The upper-body photo is used for virtual try-on.',
  analyze: 'Analyze',
  photoCount: (count: number) => `${count} / 2 photos added`,
  analyzing: 'Analyzing… this takes a few seconds',
  selfieLabel: 'Face photo',
  selfieGuide: 'Face forward, natural light, minimal makeup, face filling the frame',
  bodyImageLabel: 'Upper-body photo',
  bodyImageGuide: 'Stand facing forward, chest up with shoulders visible, nobody else in the shot',
  faceNotDetected: "We couldn't find your face. Please retake the face photo.",
  preview: (label: string) => `${label} preview`,
  select: (label: string) => `Choose ${label.toLowerCase()}`,
  takePhoto: (label: string) => `Take ${label.toLowerCase()}`,
  uploadFile: 'Upload a file',
  captureSpec: 'Saved at 1080×1350, framed to the guide',
  startingCamera: 'Turning on the camera…',
  loadingDetector: 'Getting detection ready…',
  detectorUnavailable: "Automatic detection isn't available. Line up with the guide and press capture.",
  cameraUnavailable: "We can't use your camera. Allow camera access, or upload a front-facing photo instead.",
  uploadInstead: 'Upload a photo file',
  processingUpload: 'Fitting your photo to the guide…',
  capture: 'Capture',
  retake: 'Retake',
  useThisPhoto: 'Use this photo',
  close: 'Close',
  faceCapture: {
    title: 'Take face photo',
    lede: "Fit your face inside the oval. We'll take the photo automatically once everything checks out.",
    uploadNotFound: "We couldn't find a face in that photo. Try a clear, front-facing one.",
    capturedPreview: 'Captured face photo',
    statuses: {
      [FaceGuideStatus.NO_FACE]: 'Fit your face inside the oval',
      [FaceGuideStatus.MULTIPLE_FACES]: 'Only one person, please',
      [FaceGuideStatus.TOO_FAR]: 'Move a little closer',
      [FaceGuideStatus.TOO_CLOSE]: 'Move back a little',
      [FaceGuideStatus.OFF_CENTER]: 'Center your face in the oval',
      [FaceGuideStatus.NOT_FRONTAL]: 'Look straight at the camera',
      [FaceGuideStatus.TOO_DARK]: 'Find somewhere brighter',
      [FaceGuideStatus.TOO_BRIGHT]: 'Too bright. Avoid direct light',
      [FaceGuideStatus.READY]: 'Perfect. Hold still',
    } as Record<FaceGuideStatus, string>,
    checks: {
      singleFace: 'Just you',
      distance: 'Right distance',
      position: 'Centered',
      frontal: 'Facing forward',
      lighting: 'Enough light',
    } as Record<FaceGuideCheckName, string>,
  },
  upperBodyCapture: {
    title: 'Take upper-body photo',
    lede: "Line your head and shoulders up with the outline. We'll take the photo automatically once everything checks out.",
    uploadNotFound: "We couldn't find both shoulders in that photo. Try one showing you from the chest up.",
    capturedPreview: 'Captured upper-body photo',
    statuses: {
      [UpperBodyGuideStatus.NO_PERSON]: 'Step into the outline',
      [UpperBodyGuideStatus.MULTIPLE_PEOPLE]: 'Only one person, please',
      [UpperBodyGuideStatus.SHOULDERS_HIDDEN]: 'Step back so both shoulders show',
      [UpperBodyGuideStatus.TOO_FAR]: 'Move a little closer',
      [UpperBodyGuideStatus.TOO_CLOSE]: 'Move back a little',
      [UpperBodyGuideStatus.OFF_CENTER]: 'Line your shoulders up with the outline',
      [UpperBodyGuideStatus.NOT_FRONTAL]: 'Face the camera with level shoulders',
      [UpperBodyGuideStatus.TOO_DARK]: 'Find somewhere brighter',
      [UpperBodyGuideStatus.TOO_BRIGHT]: 'Too bright. Avoid direct light',
      [UpperBodyGuideStatus.READY]: 'Perfect. Hold still',
    } as Record<UpperBodyGuideStatus, string>,
    checks: {
      singlePerson: 'Just you',
      shouldersVisible: 'Both shoulders visible',
      distance: 'Right distance',
      position: 'Lined up with outline',
      frontal: 'Facing forward',
      lighting: 'Enough light',
    } as Record<UpperBodyGuideCheckName, string>,
  },
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
  // 12유형 이름. 영어는 "Deep Autumn", 트루는 "True Autumn"
  typeName: (season: Season, subtype: SeasonSubtype) => `${ENGLISH_SUBTYPE_NAMES[subtype]} ${ENGLISH_SEASON_WORDS[season]}`,
  avoidColors: 'Colors to avoid',
  avoidPalette: 'Avoid palette',
  avoidNote: 'Items close to these colors rank lower in your recommendations.',
  basisHeading: 'Why this result',
  basisLede: 'Read from the five colors YouCam found on your face.',
  faceColors: 'Face colors',
  faceColorNames: { skin: 'Skin', lip: 'Lips', eye: 'Eyes', eyebrow: 'Brows', hair: 'Hair' } as Record<FaceColorPart, string>,
  axes: {
    warmth: { label: 'Undertone', negative: 'Cool', positive: 'Warm' },
    depth: { label: 'Depth', negative: 'Light', positive: 'Deep' },
    clarity: { label: 'Clarity', negative: 'Soft', positive: 'Bright' },
  } as Record<AxisName, { label: string; negative: string; positive: string }>,
  skinLightness: 'Skin lightness (L*)',
  contrast: 'Contrast with hair, brows, eyes',
  verdict: (warmth: number, depth: number, season: Season, subtype: SeasonSubtype) =>
    `${warmth >= 0 ? 'Yellow-leaning skin and lips read warm' : 'Pink-leaning skin and lips read cool'}, ` +
    `${depth >= 0 ? 'and strong contrast with your hair reads deep' : 'and light skin with soft contrast reads light'} → ${ENGLISH_SEASON_NAMES[season]}. ` +
    (subtype === SeasonSubtype.TRUE
      ? 'Your undertone stands out most, so you are a True type.'
      : `${ENGLISH_SUBTYPE_TRAITS[subtype]} stands out most, so you are ${ENGLISH_SUBTYPE_NAMES[subtype]}.`),
}

const KOREAN: typeof ENGLISH = {
  title: '사진 두 장이면 돼요',
  lede: '얼굴 사진으로 피부톤을 보고, 상반신 사진은 가상 피팅에 써요.',
  analyze: '분석하기',
  photoCount: (count: number) => `사진 ${count} / 2장`,
  analyzing: '분석 중… 몇 초 걸려요',
  selfieLabel: '얼굴 사진',
  selfieGuide: '정면, 자연광, 화장 최소화, 얼굴이 화면을 가득 채우게',
  bodyImageLabel: '상반신 사진',
  bodyImageGuide: '정면으로 서서, 가슴 위 상반신과 어깨가 보이게, 혼자 나오게',
  faceNotDetected: '얼굴을 인식하지 못했어요. 얼굴 사진을 다시 찍어 주세요.',
  preview: (label: string) => `${label} 미리보기`,
  select: (label: string) => `${label} 선택`,
  takePhoto: (label: string) => `${label} 촬영`,
  uploadFile: '파일로 올리기',
  captureSpec: '1080×1350, 가이드 구도로 저장돼요',
  startingCamera: '카메라를 켜는 중…',
  loadingDetector: '인식 준비 중…',
  detectorUnavailable: '자동 인식을 쓸 수 없어요. 가이드에 맞춘 뒤 촬영을 눌러 주세요.',
  cameraUnavailable: '카메라를 쓸 수 없어요. 카메라 권한을 허용하거나 정면 사진 파일을 올려 주세요.',
  uploadInstead: '사진 파일 올리기',
  processingUpload: '사진을 가이드에 맞추는 중…',
  capture: '촬영',
  retake: '다시 찍기',
  useThisPhoto: '이 사진 사용',
  close: '닫기',
  faceCapture: {
    title: '얼굴 사진 촬영',
    lede: '타원 안에 얼굴을 맞춰 주세요. 조건이 모두 맞으면 자동으로 찍혀요.',
    uploadNotFound: '사진에서 얼굴을 찾지 못했어요. 정면이 잘 보이는 사진을 올려 주세요.',
    capturedPreview: '촬영한 얼굴 사진',
    statuses: {
      [FaceGuideStatus.NO_FACE]: '타원 안에 얼굴을 맞춰 주세요',
      [FaceGuideStatus.MULTIPLE_FACES]: '한 명만 나오게 해 주세요',
      [FaceGuideStatus.TOO_FAR]: '조금 더 가까이 와 주세요',
      [FaceGuideStatus.TOO_CLOSE]: '조금 뒤로 가 주세요',
      [FaceGuideStatus.OFF_CENTER]: '얼굴을 타원 가운데로 옮겨 주세요',
      [FaceGuideStatus.NOT_FRONTAL]: '카메라를 정면으로 바라봐 주세요',
      [FaceGuideStatus.TOO_DARK]: '조금 더 밝은 곳으로 가 주세요',
      [FaceGuideStatus.TOO_BRIGHT]: '빛이 너무 강해요. 직사광을 피해 주세요',
      [FaceGuideStatus.READY]: '좋아요, 그대로 있어 주세요',
    },
    checks: {
      singleFace: '혼자 나오기',
      distance: '알맞은 거리',
      position: '타원 가운데',
      frontal: '정면 응시',
      lighting: '적당한 밝기',
    },
  },
  upperBodyCapture: {
    title: '상반신 사진 촬영',
    lede: '머리와 어깨를 실루엣에 맞춰 주세요. 조건이 모두 맞으면 자동으로 찍혀요.',
    uploadNotFound: '사진에서 양 어깨를 찾지 못했어요. 가슴 위 상반신이 나온 사진을 올려 주세요.',
    capturedPreview: '촬영한 상반신 사진',
    statuses: {
      [UpperBodyGuideStatus.NO_PERSON]: '실루엣 안으로 들어와 주세요',
      [UpperBodyGuideStatus.MULTIPLE_PEOPLE]: '한 명만 나오게 해 주세요',
      [UpperBodyGuideStatus.SHOULDERS_HIDDEN]: '양 어깨가 다 보이게 뒤로 가 주세요',
      [UpperBodyGuideStatus.TOO_FAR]: '조금 더 가까이 와 주세요',
      [UpperBodyGuideStatus.TOO_CLOSE]: '조금 뒤로 가 주세요',
      [UpperBodyGuideStatus.OFF_CENTER]: '어깨를 실루엣 어깨선에 맞춰 주세요',
      [UpperBodyGuideStatus.NOT_FRONTAL]: '어깨를 펴고 정면을 바라봐 주세요',
      [UpperBodyGuideStatus.TOO_DARK]: '조금 더 밝은 곳으로 가 주세요',
      [UpperBodyGuideStatus.TOO_BRIGHT]: '빛이 너무 강해요. 직사광을 피해 주세요',
      [UpperBodyGuideStatus.READY]: '좋아요, 그대로 있어 주세요',
    },
    checks: {
      singlePerson: '혼자 나오기',
      shouldersVisible: '양 어깨 보이기',
      distance: '알맞은 거리',
      position: '실루엣에 맞추기',
      frontal: '정면 자세',
      lighting: '적당한 밝기',
    },
  },
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
  typeName: (season: Season, subtype: SeasonSubtype) => `${KOREAN_SEASON_NAMES[season]} · ${KOREAN_SUBTYPE_NAMES[subtype]}`,
  avoidColors: '피해야 할 색',
  avoidPalette: '피해야 할 팔레트',
  avoidNote: '이 색과 가까운 상품은 추천에서 뒤로 밀려요.',
  basisHeading: '판정 근거',
  basisLede: 'YouCam 이 얼굴에서 찾은 색 5가지로 판정했어요.',
  faceColors: '얼굴 색',
  faceColorNames: { skin: '피부', lip: '입술', eye: '눈', eyebrow: '눈썹', hair: '머리' },
  axes: {
    warmth: { label: '웜 · 쿨', negative: '쿨', positive: '웜' },
    depth: { label: '명도', negative: '라이트', positive: '딥' },
    clarity: { label: '선명도', negative: '소프트', positive: '브라이트' },
  },
  skinLightness: '피부 명도 (L*)',
  contrast: '머리·눈썹·눈과의 대비',
  verdict: (warmth: number, depth: number, season: Season, subtype: SeasonSubtype) =>
    `${warmth >= 0 ? '노란 기가 도는 피부와 입술로 웜' : '핑크 기가 도는 피부와 입술로 쿨'}, ` +
    `${depth >= 0 ? '피부와 머리색 대비가 커서 딥' : '밝은 피부에 대비가 부드러워 라이트'} → ${KOREAN_SEASON_NAMES[season]}. ` +
    (subtype === SeasonSubtype.TRUE
      ? '가장 두드러진 특징: 웜·쿨 성향 → 트루'
      : `가장 두드러진 특징: ${KOREAN_SUBTYPE_TRAITS[subtype]} → ${KOREAN_SUBTYPE_NAMES[subtype]}`),
}

export const PERSONAL_COLOR_MESSAGES = { en: ENGLISH, ko: KOREAN }
