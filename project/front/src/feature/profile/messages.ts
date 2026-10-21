// profile 슬라이스 문구 (영어 · 한국어)
import { AgeGroup, Gender } from '../../common/type'

const ENGLISH = {
  title: 'Tell us about you',
  lede: 'We only use this to pick the clothes you swipe through.',
  gender: 'Gender',
  ageGroup: 'Age group',
  next: 'Next',
  saving: 'Saving…',
  genderLabels: {
    [Gender.FEMALE]: 'Women',
    [Gender.MALE]: 'Men',
  } as Record<Gender, string>,
  ageGroupLabels: {
    [AgeGroup.LATE_TEENS]: 'Late teens',
    [AgeGroup.TWENTIES]: '20s',
    [AgeGroup.THIRTIES]: '30s',
    [AgeGroup.FORTIES_PLUS]: '40s+',
  } as Record<AgeGroup, string>,
}

const KOREAN: typeof ENGLISH = {
  title: '어떤 분이세요?',
  lede: '스와이프할 옷을 고르는 데만 써요.',
  gender: '성별',
  ageGroup: '나이대',
  next: '다음',
  saving: '저장 중…',
  genderLabels: {
    [Gender.FEMALE]: '여성',
    [Gender.MALE]: '남성',
  },
  ageGroupLabels: {
    [AgeGroup.LATE_TEENS]: '10대 후반',
    [AgeGroup.TWENTIES]: '20대',
    [AgeGroup.THIRTIES]: '30대',
    [AgeGroup.FORTIES_PLUS]: '40대 이상',
  },
}

export const PROFILE_MESSAGES = { en: ENGLISH, ko: KOREAN }
