import { useEffect, useMemo } from 'react'
import type { ChangeEvent } from 'react'

/** 사진 1칸: 미리보기 썸네일 + 가이드 + 파일 선택/촬영 버튼. */
export function PhotoSlot({
  label,
  guide,
  selectedFile,
  disabled,
  onSelect,
}: {
  label: string
  guide: string
  selectedFile: File | null
  disabled: boolean
  onSelect: (file: File | null) => void
}) {
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
        {previewUrl ? <img src={previewUrl} alt={`${label} 미리보기`} /> : <span aria-hidden="true">＋</span>}
      </div>
      <div className="photo-slot-body">
        <h2 className="headline">{label}</h2>
        <p className="footnote">{guide}</p>
        <label className={`button ${previewUrl ? 'button-secondary' : 'button-tinted'} button-small photo-slot-picker`}>
          {`${label} 선택`}
          <input
            type="file"
            accept="image/*"
            capture="user"
            className="visually-hidden"
            disabled={disabled}
            onChange={handleFileChange}
          />
        </label>
      </div>
    </section>
  )
}
