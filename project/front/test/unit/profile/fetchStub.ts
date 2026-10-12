import { vi } from 'vitest'

type HttpMethod = 'GET' | 'PUT'
type StubbedResponse = { status: number; body: unknown } | 'pending' | 'network-failure'

/**
 * method 별로 응답을 대체하는 fetch. 같은 method 의 응답 목록은 호출 순서대로 쓰고, 마지막 것은 계속 재사용한다.
 * 'pending' 응답은 respondPending 으로 직접 풀어 줄 때까지 대기한다.
 */
export function stubFetchByMethod(responsesByMethod: Partial<Record<HttpMethod, StubbedResponse[]>>) {
  const callCountByMethod: Record<string, number> = {}
  let resolvePendingResponse: (response: Response) => void = () => {}

  const fetchMock = vi.fn(async (_path: string, init?: RequestInit) => {
    const method = (init?.method ?? 'GET') as HttpMethod
    const responses = responsesByMethod[method] ?? []
    const callIndex = callCountByMethod[method] ?? 0
    callCountByMethod[method] = callIndex + 1
    const stubbedResponse = responses[Math.min(callIndex, responses.length - 1)]

    if (stubbedResponse === undefined) throw new Error(`stub 되지 않은 요청: ${method}`)
    if (stubbedResponse === 'network-failure') throw new TypeError('Failed to fetch')
    if (stubbedResponse === 'pending') {
      return new Promise<Response>((resolve) => {
        resolvePendingResponse = resolve
      })
    }
    return new Response(JSON.stringify(stubbedResponse.body), { status: stubbedResponse.status })
  })
  vi.stubGlobal('fetch', fetchMock)

  return {
    fetchMock,
    respondPending: (status: number, body: unknown) =>
      resolvePendingResponse(new Response(JSON.stringify(body), { status })),
  }
}
