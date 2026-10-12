import type { ProfileUpdateRequest, UserDto } from '../../common/type'
import { apiRequest } from '../../shared/api'

export function fetchMe(): Promise<UserDto> {
  return apiRequest<UserDto>('GET', '/api/users/me')
}

export function updateProfile(request: ProfileUpdateRequest): Promise<UserDto> {
  return apiRequest<UserDto>('PUT', '/api/users/me/profile', request)
}
