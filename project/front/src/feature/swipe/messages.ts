// swipe 슬라이스 문구 (영어 · 한국어)

const ENGLISH = {
  title: 'Style swipe',
  lede: 'Like or pass. The next look slides in from the right.',
  goToProfile: 'Fill in your profile',
  noCards: 'No cards to show right now',
  saving: 'Saving…',
  dislike: 'Dislike',
  like: 'Like',
  undo: 'Undo',
  previous: 'Previous',
  next: 'Next',
  card: 'Outfit card',
  cardImage: 'Outfit image',
  hint: 'Swipe the card left or right, or tap a button',
  keyboard: ' · Keyboard ',
}

const KOREAN: typeof ENGLISH = {
  title: '취향 스와이프',
  lede: '좋아요 또는 싫어요를 누르면 오른쪽 코디가 가운데로 들어와요.',
  goToProfile: '프로필 입력하기',
  noCards: '지금 보여줄 카드가 없어요',
  saving: '저장 중…',
  dislike: '싫어요',
  like: '좋아요',
  undo: '되돌리기',
  previous: '이전',
  next: '다음',
  card: '상의 카드',
  cardImage: '상의 이미지',
  hint: '카드를 좌우로 밀거나 버튼을 눌러요',
  keyboard: ' · 키보드 ',
}

export const SWIPE_MESSAGES = { en: ENGLISH, ko: KOREAN }
