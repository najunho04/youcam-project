// swipe 슬라이스 문구 (영어 · 한국어)

const ENGLISH = {
  title: 'Style swipe',
  goToProfile: 'Fill in your profile',
  noCards: 'No cards to show right now',
  saving: 'Saving…',
  dislike: 'Dislike',
  like: 'Like',
  card: 'Outfit card',
  cardImage: 'Outfit image',
  hint: 'Swipe the card left or right, or tap a button',
  keyboard: ' · Keyboard ',
}

const KOREAN: typeof ENGLISH = {
  title: '취향 스와이프',
  goToProfile: '프로필 입력하기',
  noCards: '지금 보여줄 카드가 없어요',
  saving: '저장 중…',
  dislike: '싫어요',
  like: '좋아요',
  card: '상의 카드',
  cardImage: '상의 이미지',
  hint: '카드를 좌우로 밀거나 버튼을 눌러요',
  keyboard: ' · 키보드 ',
}

export const SWIPE_MESSAGES = { en: ENGLISH, ko: KOREAN }
