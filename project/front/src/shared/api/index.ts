import type { ErrorCode, ErrorResponse } from '../../common/type'
import { ErrorCode as ErrorCodes } from '../../common/type'
import { tokenStorage } from '../auth'
import { getLanguage, useLanguage } from '../i18n'
import type { Language } from '../i18n'

export class ApiError extends Error {
  readonly status: number
  readonly code: ErrorCode

  constructor(status: number, code: ErrorCode, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

const GENERIC_ERROR_MESSAGES: Record<Language, string> = {
  en: 'Something went wrong. Please try again.',
  ko: '요청에 실패했습니다',
}

const NETWORK_ERROR_MESSAGES: Record<Language, string> = {
  en: "Can't reach the server.",
  ko: '서버에 연결할 수 없습니다',
}

/** 영어 화면용 오류 문구. 서버 문구는 한국어라서 오류 코드로 번역한다. */
const ENGLISH_ERROR_MESSAGES: Record<ErrorCode, string> = {
  UNAUTHORIZED: 'Please log in again.',
  VALIDATION_ERROR: 'Please check what you entered.',
  EXTERNAL_API_FAILED: 'An outside service is not responding. Please try again.',
  INTERNAL_ERROR: 'Something went wrong. Please try again.',
  NICKNAME_TAKEN: 'That nickname is already taken.',
  INVALID_CREDENTIALS: 'Wrong nickname or password.',
  FACE_NOT_DETECTED: "We couldn't find a face. Please retake the photo.",
  INVALID_IMAGE: 'Please upload a JPG or PNG image under 10MB.',
  PROFILE_REQUIRED: 'Please tell us your age group and gender first.',
  PERSONAL_COLOR_REQUIRED: 'Please finish the personal color analysis first.',
  PRODUCT_NOT_FOUND: 'That product is no longer available.',
  PIN_NOT_FOUND: 'Some of those looks are no longer available.',
  WARDROBE_LIMIT_EXCEEDED: 'You can save up to 4 photos.',
  FITTING_NOT_FOUND: 'That fitting could not be found.',
}

/** 화면에 보여 줄 오류 문구. 한국어는 서버 문구 그대로, 영어는 오류 코드로 번역한다. */
export function describeError(error: unknown, language: Language): string {
  if (!(error instanceof Error)) return GENERIC_ERROR_MESSAGES[language]
  if (!(error instanceof ApiError) || language === 'ko') return error.message || GENERIC_ERROR_MESSAGES[language]
  if (error.status === 0) return NETWORK_ERROR_MESSAGES.en
  return ENGLISH_ERROR_MESSAGES[error.code]
}

/** 지금 언어로 오류 문구를 만드는 함수. */
export function useDescribeError(): (error: unknown) => string {
  const language = useLanguage()
  return (error: unknown) => describeError(error, language)
}

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE'

/**
 * 모든 API 호출은 이 함수를 쓴다. body 가 FormData 면 multipart, 객체면 JSON.
 * 실패 시 ApiError(code) 를 던진다. 401 이면 토큰을 지운다.
 */
export async function apiRequest<ResponseBody>(
  method: HttpMethod,
  path: string,
  body?: unknown,
): Promise<ResponseBody> {
  const headers: Record<string, string> = {}
  const accessToken = tokenStorage.get()
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`

  let requestBody: BodyInit | undefined
  if (body instanceof FormData) {
    requestBody = body
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    requestBody = JSON.stringify(body)
  }

  let response: Response
  try {
    response = await fetch(path, { method, headers, body: requestBody })
  } catch {
    throw new ApiError(0, ErrorCodes.INTERNAL_ERROR, NETWORK_ERROR_MESSAGES[getLanguage()])
  }

  if (!response.ok) {
    if (response.status === 401) tokenStorage.clear()
    const errorBody = (await response.json().catch(() => null)) as ErrorResponse | null
    throw new ApiError(
      response.status,
      errorBody?.error.code ?? ErrorCodes.INTERNAL_ERROR,
      errorBody?.error.message ?? GENERIC_ERROR_MESSAGES[getLanguage()],
    )
  }
  return (await response.json()) as ResponseBody
}
