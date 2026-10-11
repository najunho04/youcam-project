// 화면 경로. 슬라이스는 다른 화면으로 이동할 때 이 상수만 쓴다 (다른 슬라이스 import 금지).
export const ROUTES = {
  landing: '/',
  signup: '/signup',
  login: '/login',
  profile: '/profile',
  personalColor: '/personal-color',
  swipe: '/swipe',
  wardrobe: '/wardrobe',
  recommendation: '/recommendations',
  fitting: (productId: number | string) => `/fittings/${productId}`,
  fittingPattern: '/fittings/:productId',
} as const
