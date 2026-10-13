import type { FittingCreateRequest, FittingDto } from '../../common/type'
import { apiRequest } from '../../shared/api'

export function createFitting(request: FittingCreateRequest): Promise<FittingDto> {
  return apiRequest<FittingDto>('POST', '/api/fittings', request)
}

export function fetchFitting(fittingId: number): Promise<FittingDto> {
  return apiRequest<FittingDto>('GET', `/api/fittings/${fittingId}`)
}
