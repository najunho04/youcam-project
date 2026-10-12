import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { AgeGroup, Gender } from '../../common/type'
import { ApiError } from '../../shared/api'
import { ROUTES } from '../../shared/navigation'
import { Button, ErrorMessage, Loading, PageLayout } from '../../shared/ui'
import { fetchMe, updateProfile } from './api'

const AGE_GROUP_OPTIONS: { value: AgeGroup; label: string }[] = [
  { value: AgeGroup.LATE_TEENS, label: '10대 후반' },
  { value: AgeGroup.TWENTIES, label: '20대' },
  { value: AgeGroup.THIRTIES, label: '30대' },
  { value: AgeGroup.FORTIES_PLUS, label: '40대 이상' },
]

const GENDER_OPTIONS: { value: Gender; label: string }[] = [
  { value: Gender.FEMALE, label: '여성' },
  { value: Gender.MALE, label: '남성' },
]

function toErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '요청에 실패했습니다'
}

function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

/** 나이대·성별 입력. 기존 값은 users/me 로 채우고, 저장 후 퍼스널 컬러 화면으로 보낸다. */
export function ProfilePage() {
  const navigate = useNavigate()
  const [isLoaded, setIsLoaded] = useState(false)
  const [loadErrorMessage, setLoadErrorMessage] = useState<string | null>(null)
  const [requestCount, setRequestCount] = useState(0)
  const [ageGroup, setAgeGroup] = useState<AgeGroup | null>(null)
  const [gender, setGender] = useState<Gender | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [saveErrorMessage, setSaveErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    let isCancelled = false
    fetchMe()
      .then((user) => {
        if (isCancelled) return
        setAgeGroup(user.ageGroup)
        setGender(user.gender)
        setIsLoaded(true)
      })
      .catch((error: unknown) => {
        if (isCancelled) return
        // 401 이면 shared/api 가 토큰을 지운다 → 로그인 화면으로
        if (isUnauthorized(error)) navigate(ROUTES.login, { replace: true })
        else setLoadErrorMessage(toErrorMessage(error))
      })
    return () => {
      isCancelled = true
    }
  }, [requestCount, navigate])

  function handleRetry() {
    setLoadErrorMessage(null)
    setRequestCount((count) => count + 1)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (ageGroup === null || gender === null) return
    setIsSaving(true)
    setSaveErrorMessage(null)
    try {
      await updateProfile({ ageGroup, gender })
      navigate(ROUTES.personalColor)
    } catch (error) {
      if (isUnauthorized(error)) {
        navigate(ROUTES.login, { replace: true })
        return
      }
      setSaveErrorMessage(toErrorMessage(error))
      setIsSaving(false)
    }
  }

  if (loadErrorMessage) {
    return (
      <PageLayout title="프로필">
        <ErrorMessage message={loadErrorMessage} onRetry={handleRetry} />
      </PageLayout>
    )
  }

  if (!isLoaded) {
    return (
      <PageLayout title="프로필">
        <Loading />
      </PageLayout>
    )
  }

  return (
    <PageLayout title="프로필">
      <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 16 }}>
        <fieldset style={{ display: 'grid', gap: 8 }}>
          <legend>나이대</legend>
          {AGE_GROUP_OPTIONS.map((option) => (
            <label key={option.value}>
              <input
                type="radio"
                name="ageGroup"
                value={option.value}
                checked={ageGroup === option.value}
                onChange={() => setAgeGroup(option.value)}
              />
              {option.label}
            </label>
          ))}
        </fieldset>
        <fieldset style={{ display: 'grid', gap: 8 }}>
          <legend>성별</legend>
          {GENDER_OPTIONS.map((option) => (
            <label key={option.value}>
              <input
                type="radio"
                name="gender"
                value={option.value}
                checked={gender === option.value}
                onChange={() => setGender(option.value)}
              />
              {option.label}
            </label>
          ))}
        </fieldset>
        <Button type="submit" disabled={ageGroup === null || gender === null || isSaving}>
          다음
        </Button>
        {isSaving && <Loading message="저장 중…" />}
        {saveErrorMessage && <ErrorMessage message={saveErrorMessage} />}
      </form>
    </PageLayout>
  )
}
