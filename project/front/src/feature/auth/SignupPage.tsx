import { Link, useNavigate } from 'react-router-dom'
import type { AuthRequest } from '../../common/type'
import { tokenStorage } from '../../shared/auth'
import { ROUTES } from '../../shared/navigation'
import { PageLayout } from '../../shared/ui'
import { signup } from './api'
import { AuthForm } from './AuthForm'
import './auth.css'

export function SignupPage() {
  const navigate = useNavigate()

  async function handleSubmit(request: AuthRequest) {
    const response = await signup(request)
    tokenStorage.set(response.accessToken)
    navigate(ROUTES.profile)
  }

  return (
    <PageLayout title="회원가입" lede="닉네임과 비밀번호만 있으면 시작할 수 있어요." onBack={() => navigate(ROUTES.landing)}>
      <AuthForm submitLabel="가입하기" onSubmit={handleSubmit} />
      <p className="auth-switch">
        이미 계정이 있나요? <Link to={ROUTES.login}>로그인</Link>
      </p>
    </PageLayout>
  )
}
