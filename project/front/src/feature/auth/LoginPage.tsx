import { Link, useNavigate } from 'react-router-dom'
import type { AuthRequest } from '../../common/type'
import { tokenStorage } from '../../shared/auth'
import { ROUTES } from '../../shared/navigation'
import { PageLayout } from '../../shared/ui'
import { login } from './api'
import { AuthForm } from './AuthForm'
import './auth.css'

export function LoginPage() {
  const navigate = useNavigate()

  async function handleSubmit(request: AuthRequest) {
    const response = await login(request)
    tokenStorage.set(response.accessToken)
    navigate(ROUTES.landing)
  }

  return (
    <PageLayout title="로그인" lede="다시 오셨네요. 이어서 해 볼까요?" onBack={() => navigate(ROUTES.landing)}>
      <AuthForm submitLabel="로그인" onSubmit={handleSubmit} />
      <p className="auth-switch">
        처음이신가요? <Link to={ROUTES.signup}>회원가입</Link>
      </p>
    </PageLayout>
  )
}
