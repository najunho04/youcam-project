import { useEffect, useMemo } from 'react'
import type { ChangeEvent } from 'react'
import { useMessages } from '../../shared/i18n'
import { Button } from '../../shared/ui'
import { PERSONAL_COLOR_MESSAGES } from './messages'

/** 사진 1칸: 4:5 썸네일 안에 촬영·파일 선택 버튼(사진을 고르면 미리보기 위 아래쪽에) + 아래 이름·가이드. onCaptureRequest 가 있으면 가이드 촬영 버튼을 앞에 함께 둔다. */
export function PhotoSlot({
  label,
  guide,
  selectedFile,
  disabled,
  onSelect,
  onCaptureRequest,
}: {
  label: string
  guide: string
  selectedFile: File | null
  disabled: boolean
  onSelect: (file: File | null) => void
  onCaptureRequest?: () => void
}) {
  const messages = useMessages(PERSONAL_COLOR_MESSAGES)
  const previewUrl = useMemo(() => (selectedFile ? URL.createObjectURL(selectedFile) : null), [selectedFile])

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
    }
  }, [previewUrl])

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    onSelect(event.target.files?.[0] ?? null)
  }

  return (
    <section className="photo-slot">
      <div className={`photo-slot-thumbnail${previewUrl ? ' is-filled' : ''}`}>
        {previewUrl ? (
          <img src={previewUrl} alt={messages.preview(label)} />
        ) : (
          <span className="photo-slot-placeholder" aria-hidden="true">
            ＋
          </span>
        )}
        <div className="photo-slot-actions">
          {onCaptureRequest && (
            <Button
              variant={previewUrl ? 'tinted' : 'secondary'}
              size="small"
              className="photo-slot-picker"
              disabled={disabled}
              onClick={onCaptureRequest}
            >
              {messages.takePhoto(label)}
            </Button>
          )}
          <label className={`button ${previewUrl ? 'button-tinted' : 'button-secondary'} button-small photo-slot-picker`}>
            {onCaptureRequest ? messages.uploadFile : messages.select(label)}
            <input
              type="file"
              accept="image/*"
              // 카메라 촬영 버튼이 따로 있으면 파일 고르기만, 없으면 모바일에서 바로 카메라도 열리게 한다
              capture={onCaptureRequest ? undefined : 'user'}
              aria-label={messages.select(label)}
              className="visually-hidden"
              disabled={disabled}
              onChange={handleFileChange}
            />
          </label>
        </div>
      </div>
      <div className="photo-slot-body">
        <h2 className="headline">{label}</h2>
        <p className="footnote">{guide}</p>
      </div>
    </section>
  )
}
