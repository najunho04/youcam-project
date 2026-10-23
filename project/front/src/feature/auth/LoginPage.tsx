import { Link, useNavigate } from 'react-router-dom'
import type { AuthRequest } from '../../common/type'
import { tokenStorage } from '../../shared/auth'
import { ROUTES } from '../../shared/navigation'
import { useMessages } from '../../shared/i18n'
import { PageLayout } from '../../shared/ui'
import { login } from './api'
import { AuthForm } from './AuthForm'
import { LookWheel } from './LookWheel'
import './auth.css'
import { AUTH_MESSAGES } from './messages'

export function LoginPage() {
  const navigate = useNavigate()
  const messages = useMessages(AUTH_MESSAGES).login

  async function handleSubmit(request: AuthRequest) {
    const response = await login(request)
    tokenStorage.set(response.accessToken)
    navigate(ROUTES.landing)
  }

  return (
    <PageLayout width="wide" title={messages.title} lede={messages.lede} onBack={() => navigate(ROUTES.landing)}>
      <div className="auth-split">
        <div className="auth-split-form">
          <AuthForm submitLabel={messages.submit} onSubmit={handleSubmit} />
          <p className="auth-switch">
            {messages.switchQuestion} <Link to={ROUTES.signup}>{messages.switchLink}</Link>
          </p>
        </div>
        <LookWheel size="compact" />
      </div>
    </PageLayout>
  )
}
