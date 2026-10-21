import { useState } from 'react'
import type { FormEvent } from 'react'
import type { AuthRequest } from '../../common/type'
import { ApiError, describeError } from '../../shared/api'
import type { Language } from '../../shared/i18n'
import { useLanguage } from '../../shared/i18n'
import { Button } from '../../shared/ui'
import { AUTH_MESSAGES } from './messages'

function toErrorMessage(error: unknown, language: Language): string {
  const formErrorMessage = error instanceof ApiError ? AUTH_MESSAGES[language].form.errors[error.code] : undefined
  return formErrorMessage ?? describeError(error, language)
}

/** 가입·로그인 공용 폼. 제출 중 버튼 비활성, 실패 시 폼 아래 에러 메시지. */
export function AuthForm({
  submitLabel,
  onSubmit,
}: {
  submitLabel: string
  onSubmit: (request: AuthRequest) => Promise<void>
}) {
  const [nickname, setNickname] = useState('')
  const [password, setPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const language = useLanguage()
  const messages = AUTH_MESSAGES[language].form

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsSubmitting(true)
    setErrorMessage(null)
    try {
      await onSubmit({ nickname, password })
    } catch (error) {
      setErrorMessage(toErrorMessage(error, language))
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="auth-form">
      <div>
        <div className="grouped-list">
          <label className="grouped-field">
            <span>{messages.nickname}</span>
            <input
              name="nickname"
              value={nickname}
              onChange={(event) => setNickname(event.target.value)}
              minLength={2}
              maxLength={20}
              required
              autoComplete="username"
              placeholder={messages.nicknamePlaceholder}
            />
          </label>
          <label className="grouped-field">
            <span>{messages.password}</span>
            <input
              name="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={4}
              maxLength={72}
              required
              autoComplete="current-password"
              placeholder={messages.passwordPlaceholder}
            />
          </label>
        </div>
        {errorMessage && (
          <p role="alert" className="auth-form-error">
            {errorMessage}
          </p>
        )}
      </div>
      <Button type="submit" disabled={isSubmitting}>
        {submitLabel}
      </Button>
    </form>
  )
}
