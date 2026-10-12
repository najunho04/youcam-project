import type { RecommendationResponse } from '../../common/type'
import { apiRequest } from '../../shared/api'

export function fetchRecommendations(): Promise<RecommendationResponse> {
  return apiRequest<RecommendationResponse>('GET', '/api/recommendations')
}
