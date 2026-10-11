import type { ErrorCode, ErrorResponse } from '../../common/type'
import { ErrorCode as ErrorCodes } from '../../common/type'
import { tokenStorage } from '../auth'

export class ApiError extends Error {
  readonly status: number
  readonly code: ErrorCode

  constructor(status: number, code: ErrorCode, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
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
    throw new ApiError(0, ErrorCodes.INTERNAL_ERROR, '서버에 연결할 수 없습니다')
  }

  if (!response.ok) {
    if (response.status === 401) tokenStorage.clear()
    const errorBody = (await response.json().catch(() => null)) as ErrorResponse | null
    throw new ApiError(
      response.status,
      errorBody?.error.code ?? ErrorCodes.INTERNAL_ERROR,
      errorBody?.error.message ?? '요청에 실패했습니다',
    )
  }
  return (await response.json()) as ResponseBody
}
