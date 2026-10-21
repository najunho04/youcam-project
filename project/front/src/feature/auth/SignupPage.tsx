import { Link, useNavigate } from 'react-router-dom'
import type { AuthRequest } from '../../common/type'
import { tokenStorage } from '../../shared/auth'
import { ROUTES } from '../../shared/navigation'
import { useMessages } from '../../shared/i18n'
import { PageLayout } from '../../shared/ui'
import { signup } from './api'
import { AuthForm } from './AuthForm'
import './auth.css'
import { AUTH_MESSAGES } from './messages'

export function SignupPage() {
  const navigate = useNavigate()
  const messages = useMessages(AUTH_MESSAGES).signup

  async function handleSubmit(request: AuthRequest) {
    const response = await signup(request)
    tokenStorage.set(response.accessToken)
    navigate(ROUTES.profile)
  }

  return (
    <PageLayout title={messages.title} lede={messages.lede} onBack={() => navigate(ROUTES.landing)}>
      <AuthForm submitLabel={messages.submit} onSubmit={handleSubmit} />
      <p className="auth-switch">
        {messages.switchQuestion} <Link to={ROUTES.login}>{messages.switchLink}</Link>
      </p>
    </PageLayout>
  )
}
