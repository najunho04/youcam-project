// 백엔드 backend/src/common/{enums,error,dto} 와 1:1. 재정의 금지, 여기서 import 해서 쓴다.

export const AgeGroup = {
  LATE_TEENS: 'LATE_TEENS',
  TWENTIES: 'TWENTIES',
  THIRTIES: 'THIRTIES',
  FORTIES_PLUS: 'FORTIES_PLUS',
} as const
export type AgeGroup = (typeof AgeGroup)[keyof typeof AgeGroup]

export const Gender = { FEMALE: 'FEMALE', MALE: 'MALE' } as const
export type Gender = (typeof Gender)[keyof typeof Gender]

export const Season = {
  SPRING_WARM: 'SPRING_WARM',
  SUMMER_COOL: 'SUMMER_COOL',
  AUTUMN_WARM: 'AUTUMN_WARM',
  WINTER_COOL: 'WINTER_COOL',
} as const
export type Season = (typeof Season)[keyof typeof Season]

export const Style = {
  MINIMAL: 'MINIMAL',
  CASUAL: 'CASUAL',
  STREET: 'STREET',
  FORMAL: 'FORMAL',
  LOVELY: 'LOVELY',
} as const
export type Style = (typeof Style)[keyof typeof Style]

export const FittingStatus = { PENDING: 'PENDING', DONE: 'DONE', FAILED: 'FAILED' } as const
export type FittingStatus = (typeof FittingStatus)[keyof typeof FittingStatus]

export const ErrorCode = {
  UNAUTHORIZED: 'UNAUTHORIZED',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  EXTERNAL_API_FAILED: 'EXTERNAL_API_FAILED',
  INTERNAL_ERROR: 'INTERNAL_ERROR',
  NICKNAME_TAKEN: 'NICKNAME_TAKEN',
  INVALID_CREDENTIALS: 'INVALID_CREDENTIALS',
  FACE_NOT_DETECTED: 'FACE_NOT_DETECTED',
  INVALID_IMAGE: 'INVALID_IMAGE',
  PROFILE_REQUIRED: 'PROFILE_REQUIRED',
  PERSONAL_COLOR_REQUIRED: 'PERSONAL_COLOR_REQUIRED',
  PRODUCT_NOT_FOUND: 'PRODUCT_NOT_FOUND',
  WARDROBE_LIMIT_EXCEEDED: 'WARDROBE_LIMIT_EXCEEDED',
  FITTING_NOT_FOUND: 'FITTING_NOT_FOUND',
} as const
export type ErrorCode = (typeof ErrorCode)[keyof typeof ErrorCode]

// ---- 공통 ----
export interface ErrorResponse {
  error: { code: ErrorCode; message: string }
}

// ---- auth ----
export interface AuthRequest {
  nickname: string
  password: string
}
export interface PersonalColorDto {
  season: Season
  palette: string[]
  selfieUrl: string // 얼굴 사진
  bodyImageUrl: string // 상반신 사진 (가상 피팅 원본)
}
export interface UserDto {
  id: number
  nickname: string
  ageGroup: AgeGroup | null
  gender: Gender | null
  personalColor: PersonalColorDto | null
}
export interface AuthResponse {
  accessToken: string
  user: UserDto
}

// ---- profile ----
export interface ProfileUpdateRequest {
  ageGroup: AgeGroup
  gender: Gender
}

// ---- swipe ----
export interface SwipeCardDto {
  productId: number
  imageUrl: string
  style: Style
}
export interface SwipeCardsResponse {
  cards: SwipeCardDto[]
}
export interface SwipeAnswer {
  productId: number
  liked: boolean
}
export interface SwipeAnswersRequest {
  answers: SwipeAnswer[]
}
export interface SwipeAnswersResponse {
  likedCount: number
  totalCount: number
}

// ---- wardrobe ----
export interface WardrobePhotoDto {
  id: number
  imageUrl: string
}
export interface WardrobePhotosResponse {
  photos: WardrobePhotoDto[]
}

// ---- recommendation ----
export interface ProductDto {
  id: number
  title: string
  price: number
  mallName: string
  purchaseUrl: string
  imageUrl: string
  style: Style
}
export interface RecommendationItem {
  product: ProductDto
  score: number
  tasteScore: number
  colorScore: number
  reasonTags: string[]
}
export interface RecommendationResponse {
  styleTags: string[]
  season: Season
  palette: string[]
  isFallback: boolean
  items: RecommendationItem[]
}

// ---- fitting ----
export interface FittingCreateRequest {
  productId: number
}
export interface FittingDto {
  id: number
  productId: number
  product: ProductDto // 피팅 화면의 상품 정보(이름·가격·구매 링크)
  status: FittingStatus
  originalImageUrl: string
  resultImageUrl: string | null
}
