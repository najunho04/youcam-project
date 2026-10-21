import { useEffect, useMemo, useState } from 'react'
import type { ChangeEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, useDescribeError } from '../../shared/api'
import { useMessages } from '../../shared/i18n'
import { ROUTES } from '../../shared/navigation'
import { Button, ErrorMessage, Loading, PageLayout } from '../../shared/ui'
import { uploadWardrobePhotos } from './api'
import { WARDROBE_MESSAGES } from './messages'
import './wardrobe.css'

const WARDROBE_PHOTO_LIMIT = 4
const ONBOARDING_STEP = { current: 4, total: 4 }
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png']
function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

/** 선택한 파일이 올릴 수 없는 조건이면 에러 문구, 괜찮으면 null. */
function validateSelectedFiles(files: File[], messages: (typeof WARDROBE_MESSAGES)['en']): string | null {
  if (files.length > WARDROBE_PHOTO_LIMIT) return messages.tooManyPhotos(WARDROBE_PHOTO_LIMIT)
  if (files.some((file) => !ALLOWED_IMAGE_TYPES.includes(file.type))) return messages.wrongImageType
  return null
}

/** 취향 사진 1~4장 업로드. 업로드하거나 건너뛰면 추천 화면으로 보낸다. */
export function WardrobePage() {
  const navigate = useNavigate()
  const messages = useMessages(WARDROBE_MESSAGES)
  const describeError = useDescribeError()
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
    const validationMessage = validateSelectedFiles(files, messages)
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
      setErrorMessage(describeError(error))
      setIsUploading(false)
    }
  }

  const emptySlotCount = Math.max(0, WARDROBE_PHOTO_LIMIT - previewUrls.length - 1)

  return (
    <PageLayout
      width="regular"
      title={messages.title}
      lede={messages.guide(WARDROBE_PHOTO_LIMIT)}
      step={ONBOARDING_STEP}
      footer={
        <>
          <Button disabled={selectedFiles.length === 0 || isUploading} onClick={handleUpload}>
            {messages.upload}
          </Button>
          <Button variant="plain" disabled={isUploading} onClick={() => navigate(ROUTES.recommendation)}>
            {messages.skip}
          </Button>
        </>
      }
    >
      <div className="wardrobe-heading">
        <p className="eyebrow">{messages.optional}</p>
        <p className="footnote wardrobe-counter">{`${previewUrls.length} / ${WARDROBE_PHOTO_LIMIT}`}</p>
      </div>
      <div className="wardrobe-grid">
        {previewUrls.map((previewUrl, index) => (
          <img key={previewUrl} className="wardrobe-cell" src={previewUrl} alt={messages.selectedPhoto(index + 1)} />
        ))}
        <label className="wardrobe-cell wardrobe-picker">
          {messages.choosePhotos}
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
      <p className="footnote">{messages.imageTypeNote}</p>
      {isUploading && <Loading message={messages.uploading} />}
      {errorMessage && <ErrorMessage message={errorMessage} />}
    </PageLayout>
  )
}
