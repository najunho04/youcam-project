import { useState } from 'react'
import type { FormEvent } from 'react'
import type { AuthRequest } from '../../common/type'
import { ErrorCode } from '../../common/type'
import { ApiError } from '../../shared/api'
import { Button } from '../../shared/ui'

const ERROR_MESSAGES: Partial<Record<ErrorCode, string>> = {
  [ErrorCode.NICKNAME_TAKEN]: '이미 사용 중인 닉네임입니다',
  [ErrorCode.INVALID_CREDENTIALS]: '닉네임 또는 비밀번호가 올바르지 않습니다',
  [ErrorCode.VALIDATION_ERROR]: '닉네임은 2~20자, 비밀번호는 4~72자로 입력해 주세요',
}

function toErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return ERROR_MESSAGES[error.code] ?? error.message
  return '요청에 실패했습니다'
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

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsSubmitting(true)
    setErrorMessage(null)
    try {
      await onSubmit({ nickname, password })
    } catch (error) {
      setErrorMessage(toErrorMessage(error))
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="auth-form">
      <div>
        <div className="grouped-list">
          <label className="grouped-field">
            <span>닉네임</span>
            <input
              name="nickname"
              value={nickname}
              onChange={(event) => setNickname(event.target.value)}
              minLength={2}
              maxLength={20}
              required
              autoComplete="username"
              placeholder="2~20자"
            />
          </label>
          <label className="grouped-field">
            <span>비밀번호</span>
            <input
              name="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={4}
              maxLength={72}
              required
              autoComplete="current-password"
              placeholder="4자 이상"
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
