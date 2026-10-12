import { useNavigate } from 'react-router-dom'
import type { AuthRequest } from '../../common/type'
import { tokenStorage } from '../../shared/auth'
import { ROUTES } from '../../shared/navigation'
import { PageLayout } from '../../shared/ui'
import { login } from './api'
import { AuthForm } from './AuthForm'

export function LoginPage() {
  const navigate = useNavigate()

  async function handleSubmit(request: AuthRequest) {
    const response = await login(request)
    tokenStorage.set(response.accessToken)
    navigate(ROUTES.landing)
  }

  return (
    <PageLayout title="로그인">
      <AuthForm submitLabel="로그인" onSubmit={handleSubmit} />
    </PageLayout>
  )
}
