import type { AuthRequest, AuthResponse, UserDto } from '../../common/type'
import { apiRequest } from '../../shared/api'

export function signup(request: AuthRequest): Promise<AuthResponse> {
  return apiRequest<AuthResponse>('POST', '/api/auth/signup', request)
}

export function login(request: AuthRequest): Promise<AuthResponse> {
  return apiRequest<AuthResponse>('POST', '/api/auth/login', request)
}

export function fetchMe(): Promise<UserDto> {
  return apiRequest<UserDto>('GET', '/api/users/me')
}
