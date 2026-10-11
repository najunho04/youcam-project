import type { ButtonHTMLAttributes, ReactNode } from 'react'
import './ui.css'

export function PageLayout({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <main className="page">
      {title && <h1 className="page-title">{title}</h1>}
      {children}
    </main>
  )
}

export function Button({
  variant = 'primary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' }) {
  return <button className={`button button-${variant} ${className}`} {...props} />
}

export function Loading({ message = '불러오는 중…' }: { message?: string }) {
  return (
    <div className="state" role="status">
      <span className="spinner" aria-hidden="true" />
      {message}
    </div>
  )
}

export function ErrorMessage({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="state state-error" role="alert">
      <p>{message}</p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          다시 시도
        </Button>
      )}
    </div>
  )
}

export function EmptyState({ message }: { message: string }) {
  return <div className="state">{message}</div>
}
