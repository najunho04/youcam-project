// 화면 언어(영어·한국어). 슬라이스는 자기 문구 사전을 { en, ko } 로 두고 useMessages 로 고른다.
import { useSyncExternalStore } from 'react'

export type Language = 'en' | 'ko'

const LANGUAGE_STORAGE_KEY = 'colorfit.language'
const DEFAULT_LANGUAGE: Language = 'en'

function isLanguage(value: unknown): value is Language {
  return value === 'en' || value === 'ko'
}

/** 저장된 언어. 저장소를 못 쓰는 환경(사생활 보호 창 등)이면 기본 언어. */
function readStoredLanguage(): Language {
  try {
    const storedLanguage = localStorage.getItem(LANGUAGE_STORAGE_KEY)
    return isLanguage(storedLanguage) ? storedLanguage : DEFAULT_LANGUAGE
  } catch {
    return DEFAULT_LANGUAGE
  }
}

let currentLanguage: Language = readStoredLanguage()
const listeners = new Set<() => void>()

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

/** 훅을 못 쓰는 곳(shared/api 등)에서 지금 언어를 읽는다. */
export function getLanguage(): Language {
  return currentLanguage
}

export function setLanguage(language: Language): void {
  currentLanguage = language
  try {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, language)
  } catch {
    // 저장하지 못해도 이번 방문 동안은 바뀐 언어로 보인다
  }
  document.documentElement.lang = language
  for (const listener of listeners) listener()
}

export function useLanguage(): Language {
  return useSyncExternalStore(subscribe, getLanguage, getLanguage)
}

/** 문구 사전에서 지금 언어 묶음을 고른다. 언어를 바꾸면 다시 렌더된다. */
export function useMessages<Messages>(messages: Record<Language, Messages>): Messages {
  return messages[useLanguage()]
}

/** 상품 가격을 통화 기준으로. USD 는 $19.99, KRW 는 영어 ₩12,900 / 한국어 12,900원. */
export function formatMoney(price: number, currency: string, language: Language): string {
  if (currency === 'KRW') return formatPrice(price, language)
  return new Intl.NumberFormat(language === 'ko' ? 'ko-KR' : 'en-US', { style: 'currency', currency }).format(price)
}

/** 원화 가격. 영어는 ₩12,900, 한국어는 12,900원. 상품 가격은 formatMoney 를 쓴다. */
export function formatPrice(price: number, language: Language): string {
  return language === 'ko' ? `${price.toLocaleString('ko-KR')}원` : `₩${price.toLocaleString('en-US')}`
}

/** EN / KO 전환. 고른 언어는 브라우저에 기억된다. */
export function LanguageToggle({ className = '' }: { className?: string }) {
  const language = useLanguage()
  return (
    <span className={`language-toggle ${className}`} role="group" aria-label="Language">
      {(['en', 'ko'] as const).map((option) => (
        <button
          key={option}
          type="button"
          className="language-toggle-option"
          aria-pressed={language === option}
          onClick={() => setLanguage(option)}
        >
          {option.toUpperCase()}
        </button>
      ))}
    </span>
  )
}
