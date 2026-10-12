import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ErrorCode, Season } from '../../common/type'
import type { PersonalColorDto } from '../../common/type'
import { ApiError } from '../../shared/api'
import { ROUTES } from '../../shared/navigation'
import { Button, ErrorMessage, Loading, PageLayout } from '../../shared/ui'
import { analyzePersonalColor } from './api'
import { PhotoSlot } from './PhotoSlot'

const SELFIE_GUIDE = '정면, 자연광, 화장 최소화, 얼굴이 화면을 가득 채우게'
const BODY_IMAGE_GUIDE = '정면으로 서서, 가슴 위 상반신과 어깨가 보이게, 혼자 나오게'
const FACE_NOT_DETECTED_MESSAGE = '얼굴을 인식하지 못했어요. 얼굴 사진을 다시 찍어 주세요.'

const SEASON_NAMES: Record<Season, string> = {
  [Season.SPRING_WARM]: '봄 웜톤',
  [Season.SUMMER_COOL]: '여름 쿨톤',
  [Season.AUTUMN_WARM]: '가을 웜톤',
  [Season.WINTER_COOL]: '겨울 쿨톤',
}

function toErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '요청에 실패했습니다'
}

function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

function isFaceNotDetected(error: unknown): boolean {
  return error instanceof ApiError && error.code === ErrorCode.FACE_NOT_DETECTED
}

function PersonalColorResult({ personalColor, onNext }: { personalColor: PersonalColorDto; onNext: () => void }) {
  return (
    <PageLayout title="퍼스널컬러 결과">
      <h2>{SEASON_NAMES[personalColor.season]}</h2>
      <ul aria-label="팔레트" style={{ display: 'flex', flexWrap: 'wrap', gap: 8, padding: 0, listStyle: 'none' }}>
        {personalColor.palette.map((hexColor) => (
          <li
            key={hexColor}
            title={hexColor}
            style={{ width: 32, height: 32, borderRadius: '50%', background: hexColor, border: '1px solid #ddd' }}
          />
        ))}
      </ul>
      <img
        src={personalColor.selfieUrl}
        alt="얼굴 사진"
        style={{ width: '100%', aspectRatio: '3 / 4', objectFit: 'cover' }}
      />
      <Button onClick={onNext}>다음</Button>
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
    return <PersonalColorResult personalColor={personalColor} onNext={() => navigate(ROUTES.swipe)} />
  }

  return (
    <PageLayout title="퍼스널컬러 진단">
      <PhotoSlot label="얼굴 사진" guide={SELFIE_GUIDE} selectedFile={selfie} disabled={isAnalyzing} onSelect={setSelfie} />
      <PhotoSlot
        label="상반신 사진"
        guide={BODY_IMAGE_GUIDE}
        selectedFile={bodyImage}
        disabled={isAnalyzing}
        onSelect={setBodyImage}
      />
      <Button disabled={!selfie || !bodyImage || isAnalyzing} onClick={handleAnalyze}>
        분석하기
      </Button>
      {isAnalyzing && <Loading message="분석 중… 몇 초 걸려요" />}
      {isFaceNotDetectedError && <ErrorMessage message={`${FACE_NOT_DETECTED_MESSAGE} (${SELFIE_GUIDE})`} />}
      {errorMessage && <ErrorMessage message={errorMessage} />}
    </PageLayout>
  )
}
