import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { ROUTES } from '../navigation'

const ACCESS_TOKEN_KEY = 'colorfit.accessToken'

export const tokenStorage = {
  get(): string | null {
    try {
      return localStorage.getItem(ACCESS_TOKEN_KEY)
    } catch {
      return null
    }
  },
  set(accessToken: string): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
  },
  clear(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
  },
}

/** 토큰이 없으면 로그인 화면으로 보낸다. 로그인이 필요한 페이지는 이걸로 감싼다. */
export function RequireAuth({ children }: { children: ReactNode }) {
  if (!tokenStorage.get()) return <Navigate to={ROUTES.login} replace />
  return <>{children}</>
}
