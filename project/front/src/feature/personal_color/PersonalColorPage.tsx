import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ErrorCode, Season } from '../../common/type'
import type { PersonalColorDto } from '../../common/type'
import { ApiError } from '../../shared/api'
import { ROUTES } from '../../shared/navigation'
import { Button, ErrorMessage, Loading, PageLayout } from '../../shared/ui'
import { analyzePersonalColor } from './api'
import { PhotoSlot } from './PhotoSlot'
import './personal_color.css'

const SELFIE_GUIDE = '정면, 자연광, 화장 최소화, 얼굴이 화면을 가득 채우게'
const BODY_IMAGE_GUIDE = '정면으로 서서, 가슴 위 상반신과 어깨가 보이게, 혼자 나오게'
const FACE_NOT_DETECTED_MESSAGE = '얼굴을 인식하지 못했어요. 얼굴 사진을 다시 찍어 주세요.'

const SEASON_NAMES: Record<Season, string> = {
  [Season.SPRING_WARM]: '봄 웜톤',
  [Season.SUMMER_COOL]: '여름 쿨톤',
  [Season.AUTUMN_WARM]: '가을 웜톤',
  [Season.WINTER_COOL]: '겨울 쿨톤',
}

/** 시즌 카드 배경. 시즌마다 대표 팔레트 그라데이션. */
const SEASON_CARD_CLASS_NAMES: Record<Season, string> = {
  [Season.SPRING_WARM]: 'season-card-spring',
  [Season.SUMMER_COOL]: 'season-card-summer',
  [Season.AUTUMN_WARM]: 'season-card-autumn',
  [Season.WINTER_COOL]: 'season-card-winter',
}

const SEASON_DESCRIPTIONS: Record<Season, string> = {
  [Season.SPRING_WARM]: '밝고 따뜻한 색이 생기를 더해 줘요.',
  [Season.SUMMER_COOL]: '부드럽고 맑은 색이 얼굴을 환하게 만들어요.',
  [Season.AUTUMN_WARM]: '깊고 따뜻한 색이 얼굴을 환하게 만들어요.',
  [Season.WINTER_COOL]: '선명하고 차가운 색이 인상을 또렷하게 해 줘요.',
}

const ONBOARDING_STEP = { current: 2, total: 4 }

function toErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '요청에 실패했습니다'
}

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
  return (
    <PageLayout width="regular" step={ONBOARDING_STEP} onBack={onBack} footer={<Button onClick={onNext}>다음</Button>}>
      <h1 className="visually-hidden">퍼스널컬러 결과</h1>
      <div className="personal-color-result">
      <section className={`season-card ${SEASON_CARD_CLASS_NAMES[personalColor.season]}`}>
        <img className="season-card-face" src={personalColor.selfieUrl} alt="얼굴 사진" />
        <p className="season-card-kicker">나의 퍼스널컬러</p>
        <h2 className="season-card-name">{SEASON_NAMES[personalColor.season]}</h2>
        <p className="season-card-description">{SEASON_DESCRIPTIONS[personalColor.season]}</p>
      </section>
      <section className="personal-color-palette">
        <p className="eyebrow">잘 어울리는 색</p>
        <ul aria-label="팔레트" className="palette-grid">
          {personalColor.palette.map((hexColor) => (
            <li key={hexColor} title={hexColor} style={{ background: hexColor }} />
          ))}
        </ul>
        <p className="footnote">추천 상품은 이 팔레트와 얼마나 가까운지를 함께 봐요.</p>
      </section>
      </div>
    </PageLayout>
  )
}

/** 얼굴·상반신 사진 2장으로 퍼스널컬러 진단. 결과 확인 후 스와이프 화면으로 보낸다. */
export function PersonalColorPage() {
  const navigate = useNavigate()
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
        setErrorMessage(toErrorMessage(error))
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
      title="사진 두 장이면 돼요"
      lede="얼굴 사진으로 피부톤을 보고, 상반신 사진은 가상 피팅에 써요."
      step={ONBOARDING_STEP}
      onBack={() => navigate(ROUTES.profile)}
      footer={
        <Button disabled={!selfie || !bodyImage || isAnalyzing} onClick={handleAnalyze}>
          분석하기
        </Button>
      }
    >
      <div className="photo-slot-list">
        <PhotoSlot label="얼굴 사진" guide={SELFIE_GUIDE} selectedFile={selfie} disabled={isAnalyzing} onSelect={setSelfie} />
        <PhotoSlot
          label="상반신 사진"
          guide={BODY_IMAGE_GUIDE}
          selectedFile={bodyImage}
          disabled={isAnalyzing}
          onSelect={setBodyImage}
        />
      </div>
      {isAnalyzing && <Loading message="분석 중… 몇 초 걸려요" />}
      {isFaceNotDetectedError && <ErrorMessage message={`${FACE_NOT_DETECTED_MESSAGE} (${SELFIE_GUIDE})`} />}
      {errorMessage && <ErrorMessage message={errorMessage} />}
    </PageLayout>
  )
}
