import { useEffect, useMemo } from 'react'
import type { ChangeEvent } from 'react'

/** 사진 1칸: 가이드 + 파일 선택/촬영 + 미리보기. */
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
    <section style={{ display: 'grid', gap: 8 }}>
      <h2>{label}</h2>
      <p>{guide}</p>
      <label style={{ display: 'grid', gap: 8 }}>
        {`${label} 선택`}
        <input type="file" accept="image/*" capture="user" disabled={disabled} onChange={handleFileChange} />
      </label>
      {previewUrl && (
        <img
          src={previewUrl}
          alt={`${label} 미리보기`}
          style={{ width: '100%', aspectRatio: '3 / 4', objectFit: 'cover' }}
        />
      )}
    </section>
  )
}
