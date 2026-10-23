// auth 슬라이스 문구 (영어 · 한국어)
import { ErrorCode } from '../../common/type'

const ENGLISH = {
  landing: {
    deckStart: 'Get started with ColorFit looks',
    deckHint: 'Click a card to start',
    accountMenu: 'Account',
    login: 'LOGIN',
    continue: 'CONTINUE',
    logout: 'LOGOUT',
    retry: 'RETRY',
  },
  lookDeck: {
    label: 'ColorFit looks',
    bringToFront: (lookName: string) => `Bring ${lookName} to the front`,
    looks: [
      'Gray tank top with wide jeans',
      'Blue gingham shirt with brown trousers',
      'Denim jacket with olive trousers',
      'Zip hoodie with light jeans',
      'Gray knit with brown slacks',
    ],
  },
  login: {
    title: 'Log in',
    lede: 'Welcome back. Pick up where you left off.',
    submit: 'Log in',
    switchQuestion: 'New here?',
    switchLink: 'Sign up',
  },
  signup: {
    title: 'Sign up',
    lede: 'All you need is a nickname and a password.',
    submit: 'Create account',
    switchQuestion: 'Already have an account?',
    switchLink: 'Log in',
  },
  form: {
    nickname: 'Nickname',
    nicknamePlaceholder: '2–20 characters',
    password: 'Password',
    passwordPlaceholder: 'At least 4 characters',
    errors: {
      [ErrorCode.NICKNAME_TAKEN]: 'That nickname is already taken.',
      [ErrorCode.INVALID_CREDENTIALS]: 'Wrong nickname or password.',
      [ErrorCode.VALIDATION_ERROR]: 'Use 2–20 characters for the nickname and 4–72 for the password.',
    } as Partial<Record<ErrorCode, string>>,
  },
}

const KOREAN: typeof ENGLISH = {
  landing: {
    deckStart: 'ColorFit 코디로 시작하기',
    deckHint: '카드를 눌러 시작하세요',
    accountMenu: '계정',
    login: '로그인',
    continue: '이어하기',
    logout: '로그아웃',
    retry: '다시 시도',
  },
  lookDeck: {
    label: 'ColorFit 코디',
    bringToFront: (lookName: string) => `${lookName} 카드를 가운데로`,
    looks: [
      '회색 나시와 와이드 청바지 코디',
      '블루 깅엄 셔츠와 브라운 팬츠 코디',
      '데님 재킷과 올리브 팬츠 코디',
      '후드 집업과 연청 바지 코디',
      '그레이 니트와 브라운 슬랙스 코디',
    ],
  },
  login: {
    title: '로그인',
    lede: '다시 오셨네요. 이어서 해 볼까요?',
    submit: '로그인',
    switchQuestion: '처음이신가요?',
    switchLink: '회원가입',
  },
  signup: {
    title: '회원가입',
    lede: '닉네임과 비밀번호만 있으면 시작할 수 있어요.',
    submit: '가입하기',
    switchQuestion: '이미 계정이 있나요?',
    switchLink: '로그인',
  },
  form: {
    nickname: '닉네임',
    nicknamePlaceholder: '2~20자',
    password: '비밀번호',
    passwordPlaceholder: '4자 이상',
    errors: {
      [ErrorCode.NICKNAME_TAKEN]: '이미 사용 중인 닉네임입니다',
      [ErrorCode.INVALID_CREDENTIALS]: '닉네임 또는 비밀번호가 올바르지 않습니다',
      [ErrorCode.VALIDATION_ERROR]: '닉네임은 2~20자, 비밀번호는 4~72자로 입력해 주세요',
    },
  },
}

export const AUTH_MESSAGES = { en: ENGLISH, ko: KOREAN }
