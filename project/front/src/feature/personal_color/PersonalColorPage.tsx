import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ErrorCode, Season } from '../../common/type'
import type { PersonalColorDto } from '../../common/type'
import { ApiError, useDescribeError } from '../../shared/api'
import { useMessages } from '../../shared/i18n'
import { ROUTES } from '../../shared/navigation'
import { Button, ErrorMessage, Loading, PageLayout } from '../../shared/ui'
import { analyzePersonalColor } from './api'
import { PhotoSlot } from './PhotoSlot'
import { PERSONAL_COLOR_MESSAGES } from './messages'
import './personal_color.css'

/** 시즌 카드 배경. 시즌마다 대표 팔레트 그라데이션. */
const SEASON_CARD_CLASS_NAMES: Record<Season, string> = {
  [Season.SPRING_WARM]: 'season-card-spring',
  [Season.SUMMER_COOL]: 'season-card-summer',
  [Season.AUTUMN_WARM]: 'season-card-autumn',
  [Season.WINTER_COOL]: 'season-card-winter',
}

const ONBOARDING_STEP = { current: 2, total: 4 }

function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

function isFaceNotDetected(error: unknown): boolean {
  return error instanceof ApiError && error.code === ErrorCode.FACE_NOT_DETECTED
}

function PersonalColorResult({
  personalColor,
  onNext,
  onBack,
}: {
  personalColor: PersonalColorDto
  onNext: () => void
  onBack: () => void
}) {
  const messages = useMessages(PERSONAL_COLOR_MESSAGES)
  return (
    <PageLayout width="regular" step={ONBOARDING_STEP} onBack={onBack} footer={<Button onClick={onNext}>{messages.next}</Button>}>
      <h1 className="visually-hidden">{messages.resultHeading}</h1>
      <div className="personal-color-result">
      <section className={`season-card ${SEASON_CARD_CLASS_NAMES[personalColor.season]}`}>
        <img className="season-card-face" src={personalColor.selfieUrl} alt={messages.selfieLabel} />
        <p className="season-card-kicker">{messages.myPersonalColor}</p>
        <h2 className="season-card-name">{messages.seasonNames[personalColor.season]}</h2>
        <p className="season-card-description">{messages.seasonDescriptions[personalColor.season]}</p>
      </section>
      <section className="personal-color-palette">
        <p className="eyebrow">{messages.matchingColors}</p>
        <ul aria-label={messages.palette} className="palette-grid">
          {personalColor.palette.map((hexColor) => (
            <li key={hexColor} title={hexColor} style={{ background: hexColor }} />
          ))}
        </ul>
        <p className="footnote">{messages.paletteNote}</p>
      </section>
      </div>
    </PageLayout>
  )
}

/** 얼굴·상반신 사진 2장으로 퍼스널컬러 진단. 결과 확인 후 스와이프 화면으로 보낸다. */
export function PersonalColorPage() {
  const navigate = useNavigate()
  const messages = useMessages(PERSONAL_COLOR_MESSAGES)
  const describeError = useDescribeError()
  const [selfie, setSelfie] = useState<File | null>(null)
  const [bodyImage, setBodyImage] = useState<File | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isFaceNotDetectedError, setIsFaceNotDetectedError] = useState(false)
  const [personalColor, setPersonalColor] = useState<PersonalColorDto | null>(null)

  async function handleAnalyze() {
    if (!selfie || !bodyImage) return
    setIsAnalyzing(true)
    setErrorMessage(null)
    setIsFaceNotDetectedError(false)
    try {
      setPersonalColor(await analyzePersonalColor(selfie, bodyImage))
    } catch (error) {
      if (isUnauthorized(error)) {
        navigate(ROUTES.login, { replace: true })
        return
      }
      if (isFaceNotDetected(error)) {
        setIsFaceNotDetectedError(true)
      } else {
        setErrorMessage(describeError(error))
      }
    }
    setIsAnalyzing(false)
  }

  if (personalColor) {
    return (
      <PersonalColorResult
        personalColor={personalColor}
        onNext={() => navigate(ROUTES.swipe)}
        onBack={() => setPersonalColor(null)}
      />
    )
  }

  return (
    <PageLayout
      width="regular"
      title={messages.title}
      lede={messages.lede}
      step={ONBOARDING_STEP}
      onBack={() => navigate(ROUTES.profile)}
      footer={
        <Button disabled={!selfie || !bodyImage || isAnalyzing} onClick={handleAnalyze}>
          {messages.analyze}
        </Button>
      }
    >
      <div className="photo-slot-list">
        <PhotoSlot label={messages.selfieLabel} guide={messages.selfieGuide} selectedFile={selfie} disabled={isAnalyzing} onSelect={setSelfie} />
        <PhotoSlot
          label={messages.bodyImageLabel}
          guide={messages.bodyImageGuide}
          selectedFile={bodyImage}
          disabled={isAnalyzing}
          onSelect={setBodyImage}
        />
      </div>
      {isAnalyzing && <Loading message={messages.analyzing} />}
      {isFaceNotDetectedError && <ErrorMessage message={`${messages.faceNotDetected} (${messages.selfieGuide})`} />}
      {errorMessage && <ErrorMessage message={errorMessage} />}
    </PageLayout>
  )
}
