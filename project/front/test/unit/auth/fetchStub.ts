import { vi } from 'vitest'

/** fetch 를 응답 하나로 대체한다. 반환값으로 호출 인자를 검사한다. */
export function stubFetchResponse(status: number, body: unknown) {
  const fetchMock = vi.fn(async () => new Response(JSON.stringify(body), { status }))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

/** 응답을 직접 풀어 줄 때까지 대기하는 fetch. 로딩 상태 검사용. */
export function stubPendingFetch() {
  let resolveResponse: (response: Response) => void = () => {}
  const fetchMock = vi.fn(
    () =>
      new Promise<Response>((resolve) => {
        resolveResponse = resolve
      }),
  )
  vi.stubGlobal('fetch', fetchMock)
  return {
    fetchMock,
    respond: (status: number, body: unknown) => resolveResponse(new Response(JSON.stringify(body), { status })),
  }
}

export function stubNetworkFailure() {
  const fetchMock = vi.fn(async () => {
    throw new TypeError('Failed to fetch')
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}
