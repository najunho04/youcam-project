import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { AgeGroup, Gender } from '../../common/type'
import { ApiError, useDescribeError } from '../../shared/api'
import { useMessages } from '../../shared/i18n'
import { ROUTES } from '../../shared/navigation'
import { Button, ErrorMessage, Loading, PageLayout } from '../../shared/ui'
import { fetchMe, updateProfile } from './api'
import { PROFILE_MESSAGES } from './messages'
import './profile.css'

const AGE_GROUP_ORDER: AgeGroup[] = [AgeGroup.LATE_TEENS, AgeGroup.TWENTIES, AgeGroup.THIRTIES, AgeGroup.FORTIES_PLUS]
const GENDER_ORDER: Gender[] = [Gender.FEMALE, Gender.MALE]
const ONBOARDING_STEP = { current: 1, total: 4 }
const FORM_ID = 'profile-form'

function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

/** 나이대·성별 입력. 기존 값은 users/me 로 채우고, 저장 후 퍼스널 컬러 화면으로 보낸다. */
export function ProfilePage() {
  const navigate = useNavigate()
  const messages = useMessages(PROFILE_MESSAGES)
  const describeError = useDescribeError()
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
        else setLoadErrorMessage(describeError(error))
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
      setSaveErrorMessage(describeError(error))
      setIsSaving(false)
    }
  }

  const layoutProps = {
    title: messages.title,
    lede: messages.lede,
    step: ONBOARDING_STEP,
    onBack: () => navigate(ROUTES.landing),
  }

  if (loadErrorMessage) {
    return (
      <PageLayout {...layoutProps}>
        <ErrorMessage message={loadErrorMessage} onRetry={handleRetry} />
      </PageLayout>
    )
  }

  if (!isLoaded) {
    return (
      <PageLayout {...layoutProps}>
        <Loading />
      </PageLayout>
    )
  }

  return (
    <PageLayout
      {...layoutProps}
      footer={
        <Button type="submit" form={FORM_ID} disabled={ageGroup === null || gender === null || isSaving}>
          {messages.next}
        </Button>
      }
    >
      <form id={FORM_ID} onSubmit={handleSubmit} className="profile-form">
        <fieldset className="profile-fieldset">
          <legend className="eyebrow">{messages.gender}</legend>
          <div className="profile-segmented">
            {GENDER_ORDER.map((value) => (
              <label key={value} className="profile-segment">
                <input
                  type="radio"
                  name="gender"
                  className="visually-hidden"
                  value={value}
                  checked={gender === value}
                  onChange={() => setGender(value)}
                />
                {messages.genderLabels[value]}
              </label>
            ))}
          </div>
        </fieldset>
        <fieldset className="profile-fieldset">
          <legend className="eyebrow">{messages.ageGroup}</legend>
          <div className="profile-choice-grid">
            {AGE_GROUP_ORDER.map((value) => (
              <label key={value} className="profile-choice">
                <input
                  type="radio"
                  name="ageGroup"
                  className="visually-hidden"
                  value={value}
                  checked={ageGroup === value}
                  onChange={() => setAgeGroup(value)}
                />
                {messages.ageGroupLabels[value]}
              </label>
            ))}
          </div>
        </fieldset>
        {isSaving && <Loading message={messages.saving} />}
        {saveErrorMessage && <ErrorMessage message={saveErrorMessage} />}
      </form>
    </PageLayout>
  )
}
