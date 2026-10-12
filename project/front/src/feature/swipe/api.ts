import type { SwipeAnswersRequest, SwipeAnswersResponse, SwipeCardsResponse } from '../../common/type'
import { apiRequest } from '../../shared/api'

export function fetchSwipeCards(count: number): Promise<SwipeCardsResponse> {
  return apiRequest<SwipeCardsResponse>('GET', `/api/swipe/cards?count=${count}`)
}

export function submitSwipeAnswers(request: SwipeAnswersRequest): Promise<SwipeAnswersResponse> {
  return apiRequest<SwipeAnswersResponse>('POST', '/api/swipe/answers', request)
}
