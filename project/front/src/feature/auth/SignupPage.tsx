import { useNavigate } from 'react-router-dom'
import type { AuthRequest } from '../../common/type'
import { tokenStorage } from '../../shared/auth'
import { ROUTES } from '../../shared/navigation'
import { PageLayout } from '../../shared/ui'
import { signup } from './api'
import { AuthForm } from './AuthForm'

export function SignupPage() {
  const navigate = useNavigate()

  async function handleSubmit(request: AuthRequest) {
    const response = await signup(request)
    tokenStorage.set(response.accessToken)
    navigate(ROUTES.profile)
  }

  return (
    <PageLayout title="회원가입">
      <AuthForm submitLabel="가입하기" onSubmit={handleSubmit} />
    </PageLayout>
  )
}
