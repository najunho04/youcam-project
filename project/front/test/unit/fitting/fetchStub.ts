import { vi } from 'vitest'

type StubbedResponse = { status: number; body: unknown } | 'network-failure'

/**
 * 응답을 대체하는 fetch. 응답 목록은 호출 순서대로 쓰고, 마지막 것은 계속 재사용한다.
 */
export function stubFetch(responses: StubbedResponse[]) {
  let callCount = 0

  const fetchMock = vi.fn(async (_path: string, _init?: RequestInit) => {
    const stubbedResponse = responses[Math.min(callCount, responses.length - 1)]
    callCount += 1

    if (stubbedResponse === undefined) throw new Error('stub 되지 않은 요청')
    if (stubbedResponse === 'network-failure') throw new TypeError('Failed to fetch')
    return new Response(JSON.stringify(stubbedResponse.body), { status: stubbedResponse.status })
  })
  vi.stubGlobal('fetch', fetchMock)

  return { fetchMock }
}
