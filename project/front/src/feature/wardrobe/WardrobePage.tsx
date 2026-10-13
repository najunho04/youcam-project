import { useEffect, useMemo, useState } from 'react'
import type { ChangeEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../../shared/api'
import { ROUTES } from '../../shared/navigation'
import { Button, ErrorMessage, Loading, PageLayout } from '../../shared/ui'
import { uploadWardrobePhotos } from './api'
import './wardrobe.css'

const WARDROBE_PHOTO_LIMIT = 4
const ONBOARDING_STEP = { current: 4, total: 4 }
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png']
const GUIDE_MESSAGE = `좋아하는 착용 사진이나 옷 사진을 최대 ${WARDROBE_PHOTO_LIMIT}장 올리면 취향 분석에 반영돼요`

function toErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '요청에 실패했습니다'
}

function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

/** 선택한 파일이 올릴 수 없는 조건이면 에러 문구, 괜찮으면 null. */
function validateSelectedFiles(files: File[]): string | null {
  if (files.length > WARDROBE_PHOTO_LIMIT) return `사진은 최대 ${WARDROBE_PHOTO_LIMIT}장까지 선택할 수 있습니다`
  if (files.some((file) => !ALLOWED_IMAGE_TYPES.includes(file.type))) return 'jpg 또는 png 사진만 올릴 수 있습니다'
  return null
}

/** 취향 사진 1~4장 업로드. 업로드하거나 건너뛰면 추천 화면으로 보낸다. */
export function WardrobePage() {
  const navigate = useNavigate()
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const previewUrls = useMemo(() => selectedFiles.map((file) => URL.createObjectURL(file)), [selectedFiles])

  useEffect(() => {
    return () => {
      for (const previewUrl of previewUrls) URL.revokeObjectURL(previewUrl)
    }
  }, [previewUrls])

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? [])
    const validationMessage = validateSelectedFiles(files)
    setErrorMessage(validationMessage)
    setSelectedFiles(validationMessage === null ? files : [])
    if (validationMessage !== null) event.target.value = ''
  }

  async function handleUpload() {
    if (selectedFiles.length === 0) return
    setIsUploading(true)
    setErrorMessage(null)
    try {
      await uploadWardrobePhotos(selectedFiles)
      navigate(ROUTES.recommendation)
    } catch (error) {
      if (isUnauthorized(error)) {
        navigate(ROUTES.login, { replace: true })
        return
      }
      setErrorMessage(toErrorMessage(error))
      setIsUploading(false)
    }
  }

  const emptySlotCount = Math.max(0, WARDROBE_PHOTO_LIMIT - previewUrls.length - 1)

  return (
    <PageLayout
      width="regular"
      title="평소 즐겨 입는 옷"
      lede={GUIDE_MESSAGE}
      step={ONBOARDING_STEP}
      footer={
        <>
          <Button disabled={selectedFiles.length === 0 || isUploading} onClick={handleUpload}>
            업로드
          </Button>
          <Button variant="plain" disabled={isUploading} onClick={() => navigate(ROUTES.recommendation)}>
            건너뛰기
          </Button>
        </>
      }
    >
      <div className="wardrobe-heading">
        <p className="eyebrow">선택 사항이에요</p>
        <p className="footnote wardrobe-counter">{`${previewUrls.length} / ${WARDROBE_PHOTO_LIMIT}`}</p>
      </div>
      <div className="wardrobe-grid">
        {previewUrls.map((previewUrl, index) => (
          <img key={previewUrl} className="wardrobe-cell" src={previewUrl} alt={`선택한 사진 ${index + 1}`} />
        ))}
        <label className="wardrobe-cell wardrobe-picker">
          사진 선택
          <input
            type="file"
            className="visually-hidden"
            accept={ALLOWED_IMAGE_TYPES.join(',')}
            multiple
            disabled={isUploading}
            onChange={handleFileChange}
          />
        </label>
        {Array.from({ length: emptySlotCount }, (_, index) => (
          <span key={index} className="wardrobe-cell wardrobe-empty" aria-hidden="true" />
        ))}
      </div>
      <p className="footnote">jpg 또는 png 사진만 올릴 수 있어요</p>
      {isUploading && <Loading message="업로드 중…" />}
      {errorMessage && <ErrorMessage message={errorMessage} />}
    </PageLayout>
  )
}
