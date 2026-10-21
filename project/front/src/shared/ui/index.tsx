import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { LanguageToggle, useMessages } from '../i18n'
import { ROUTES } from '../navigation'
import './ui.css'

const MESSAGES = {
  en: { back: 'Back', progress: 'Progress', loading: 'Loading…', retry: 'Try again' },
  ko: { back: '뒤로', progress: '진행 단계', loading: '불러오는 중…', retry: '다시 시도' },
}

export type ButtonVariant = 'primary' | 'secondary' | 'tinted' | 'plain'
export type ButtonSize = 'regular' | 'small'

/** 버튼과 같은 모양이 필요한 링크(<a>, <Link>)에 붙이는 className. */
export function buttonClassName(variant: ButtonVariant = 'primary', size: ButtonSize = 'regular'): string {
  return `button button-${variant}${size === 'small' ? ' button-small' : ''}`
}

export type PageWidth = 'narrow' | 'regular' | 'wide'

/** 주요 액션 묶음. 데스크톱은 본문 흐름 안에, 좁은 화면은 하단에 고정된다. */
export function PageActions({ children }: { children: ReactNode }) {
  return (
    <div className="page-dock">
      <div className="page-dock-inner">{children}</div>
    </div>
  )
}

/**
 * 화면 골격: 반투명 상단 헤더(브랜드·가운데 제목 또는 단계·우측 액션 + 진행 막대) + 뒤로 + 큰 제목 + 본문 + 주요 액션(footer).
 * width 로 본문 폭을 고른다 (narrow 폼 · regular 2단 · wide 그리드).
 */
export function PageLayout({
  title,
  lede,
  children,
  onBack,
  backLabel,
  navigationTitle,
  navigationAction,
  step,
  footer,
  width = 'narrow',
}: {
  title?: string
  lede?: ReactNode
  children: ReactNode
  onBack?: () => void
  backLabel?: string
  navigationTitle?: string
  navigationAction?: ReactNode
  step?: { current: number; total: number }
  footer?: ReactNode
  width?: PageWidth
}) {
  const messages = useMessages(MESSAGES)
  const centerTitle = navigationTitle ?? (step ? `${step.current} / ${step.total}` : undefined)
  return (
    <div className="page-shell">
      <header className="site-header">
        <div className="site-header-row">
          <Link to={ROUTES.landing} className="site-brand">
            <span className="site-brand-mark" aria-hidden="true" />
            ColorFit
          </Link>
          <span className="site-header-title">{centerTitle}</span>
          <span className="site-header-action">
            {navigationAction}
            <LanguageToggle />
          </span>
        </div>
        {step && (
          <div
            className="step-progress"
            role="progressbar"
            aria-label={messages.progress}
            aria-valuemin={1}
            aria-valuemax={step.total}
            aria-valuenow={step.current}
          >
            <span className="step-progress-fill" style={{ width: `${(step.current / step.total) * 100}%` }} />
          </div>
        )}
      </header>
      <main className={`page page-width-${width}`}>
        {onBack && (
          <button type="button" className="page-back" onClick={onBack}>
            <span aria-hidden="true">‹</span>
            {backLabel ?? messages.back}
          </button>
        )}
        {title && <h1 className="page-title">{title}</h1>}
        {lede && <p className="page-lede">{lede}</p>}
        {children}
        {footer && <PageActions>{footer}</PageActions>}
      </main>
    </div>
  )
}

export function Button({
  variant = 'primary',
  size = 'regular',
  className = '',
  type = 'button',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; size?: ButtonSize }) {
  return <button type={type} className={`${buttonClassName(variant, size)} ${className}`} {...props} />
}

export function Loading({ message }: { message?: string }) {
  const messages = useMessages(MESSAGES)
  return (
    <div className="state" role="status">
      <span className="spinner" aria-hidden="true" />
      {message ?? messages.loading}
    </div>
  )
}

export function ErrorMessage({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const messages = useMessages(MESSAGES)
  return (
    <div className="state state-banner state-error" role="alert">
      <p>{message}</p>
      {onRetry && (
        <Button variant="plain" onClick={onRetry}>
          {messages.retry}
        </Button>
      )}
    </div>
  )
}

/** 정보 안내 배너 (예: 추천 fallback 안내). */
export function Notice({ children }: { children: ReactNode }) {
  return <div className="state state-banner state-notice">{children}</div>
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="state">
      <p>{message}</p>
    </div>
  )
}
