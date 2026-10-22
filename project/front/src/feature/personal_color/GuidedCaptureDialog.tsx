import { useEffect, useId, useMemo, useRef, useState } from 'react'
import type { ChangeEvent } from 'react'
import { createPortal } from 'react-dom'
import { useMessages } from '../../shared/i18n'
import { Button, buttonClassName, ErrorMessage, Loading } from '../../shared/ui'
import { isCameraSupported, openFrontCamera, renderPhotoFile, UploadedPhotoResult } from './camera'
import type { CaptureGuide, FrameAnalyzer } from './captureGuides'
import { PERSONAL_COLOR_MESSAGES } from './messages'
import { PHOTO_HEIGHT, PHOTO_WIDTH, portraitCropRectangle } from './photoGuide'
import type { GuideResult } from './photoGuide'

const CapturePhase = { STARTING: 'STARTING', LIVE: 'LIVE', CAPTURED: 'CAPTURED', UNAVAILABLE: 'UNAVAILABLE' } as const
type CapturePhase = (typeof CapturePhase)[keyof typeof CapturePhase]

/** 가이드 조건을 이만큼 계속 지키면 자동으로 찍는다. */
const HOLD_DURATION_MILLISECONDS = 1200

/** 촬영 대상별 문구. messages.ts 의 faceCapture · upperBodyCapture. */
export type CaptureGuideCopy<Status extends string, CheckName extends string> = {
  title: string
  lede: string
  statuses: Record<Status, string>
  checks: Record<CheckName, string>
  uploadNotFound: string
  capturedPreview: string
}

function stopStream(stream: MediaStream) {
  stream.getTracks().forEach((track) => track.stop())
}

/** 카메라 사진은 미리보기에서 본 그대로 거울 모습으로 저장한다. */
function captureVideoFrame(video: HTMLVideoElement, fileName: string): Promise<File> {
  return renderPhotoFile(video, portraitCropRectangle(video.videoWidth, video.videoHeight), fileName, { mirrored: true })
}

/** 가이드 모양 + 바깥 어둡게 + 자동 촬영까지 남은 시간을 그리는 테두리. */
function GuideOverlay({ outlinePath, isReady }: { outlinePath: string; isReady: boolean }) {
  const maskId = `capture-guide-mask-${useId().replace(/[^a-zA-Z0-9]/g, '')}`
  return (
    <svg className={`capture-overlay${isReady ? ' is-ready' : ''}`} viewBox={`0 0 ${PHOTO_WIDTH} ${PHOTO_HEIGHT}`} aria-hidden="true">
      <defs>
        <mask id={maskId}>
          <rect width={PHOTO_WIDTH} height={PHOTO_HEIGHT} fill="white" />
          <path d={outlinePath} fill="black" />
        </mask>
      </defs>
      <rect className="capture-shade" width={PHOTO_WIDTH} height={PHOTO_HEIGHT} mask={`url(#${maskId})`} />
      <path className="capture-outline" d={outlinePath} />
      <path className="capture-outline-progress" d={outlinePath} pathLength={1} />
    </svg>
  )
}

/**
 * 가이드 촬영 창. 전면 카메라 위에 가이드(얼굴 타원 · 상반신 실루엣)를 띄우고, MediaPipe 로 조건을 확인해
 * 조건이 맞은 채로 잠시 유지되면 1080×1350 JPEG 로 찍는다. 카메라를 못 쓰면 사진 파일을 올려 같은 구도로 맞춘다.
 */
export function GuidedCaptureDialog<Status extends string, CheckName extends string>({
  guide,
  copy,
  onComplete,
  onClose,
}: {
  guide: CaptureGuide<Status, CheckName>
  copy: CaptureGuideCopy<Status, CheckName>
  onComplete: (file: File) => void
  onClose: () => void
}) {
  const messages = useMessages(PERSONAL_COLOR_MESSAGES)
  const titleId = useId()
  const videoRef = useRef<HTMLVideoElement>(null)
  const stageRef = useRef<HTMLDivElement>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const onCloseRef = useRef(onClose)
  const [phase, setPhase] = useState<CapturePhase>(() =>
    isCameraSupported() ? CapturePhase.STARTING : CapturePhase.UNAVAILABLE,
  )
  const [frameAnalyzer, setFrameAnalyzer] = useState<FrameAnalyzer<Status, CheckName> | null>(null)
  const [isAnalyzerUnavailable, setIsAnalyzerUnavailable] = useState(false)
  const [guideResult, setGuideResult] = useState<GuideResult<Status, CheckName>>(guide.initialResult)
  const [capturedFile, setCapturedFile] = useState<File | null>(null)
  const [isProcessingUpload, setIsProcessingUpload] = useState(false)
  const [uploadErrorMessage, setUploadErrorMessage] = useState<string | null>(null)
  const capturedPreviewUrl = useMemo(() => (capturedFile ? URL.createObjectURL(capturedFile) : null), [capturedFile])

  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  useEffect(() => {
    return () => {
      if (capturedPreviewUrl) URL.revokeObjectURL(capturedPreviewUrl)
    }
  }, [capturedPreviewUrl])

  useEffect(() => {
    closeButtonRef.current?.focus()
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onCloseRef.current()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // 카메라를 켜고, 창을 닫으면 끈다
  useEffect(() => {
    if (!isCameraSupported()) return
    let isCancelled = false
    openFrontCamera()
      .then((stream) => {
        if (isCancelled) {
          stopStream(stream)
          return
        }
        streamRef.current = stream
        setPhase(CapturePhase.LIVE)
      })
      .catch(() => {
        if (!isCancelled) setPhase(CapturePhase.UNAVAILABLE)
      })
    return () => {
      isCancelled = true
      if (streamRef.current) stopStream(streamRef.current)
      streamRef.current = null
    }
  }, [])

  // 카메라가 켜진 뒤에만 인식 모델을 불러온다
  const isCameraOn = phase === CapturePhase.LIVE || phase === CapturePhase.CAPTURED
  useEffect(() => {
    if (!isCameraOn) return
    const video = videoRef.current
    if (video && streamRef.current && video.srcObject !== streamRef.current) {
      video.srcObject = streamRef.current
      video.play().catch(() => {})
    }
    if (frameAnalyzer || isAnalyzerUnavailable) return
    let isCancelled = false
    guide
      .loadFrameAnalyzer()
      .then((loadedAnalyzer) => {
        // 함수를 상태로 넣을 때는 업데이트 함수로 감싸야 한다
        if (!isCancelled) setFrameAnalyzer(() => loadedAnalyzer)
      })
      .catch(() => {
        if (!isCancelled) setIsAnalyzerUnavailable(true)
      })
    return () => {
      isCancelled = true
    }
  }, [isCameraOn, frameAnalyzer, isAnalyzerUnavailable, guide])

  // 매 프레임 판정하고, 조건을 HOLD_DURATION 동안 지키면 찍는다. 진행률은 리렌더 없이 CSS 변수로만 그린다.
  useEffect(() => {
    if (phase !== CapturePhase.LIVE || !frameAnalyzer) return
    let animationFrameId = 0
    let lastVideoTime = -1
    let holdStartTime: number | null = null
    let lastResultKey = ''
    let isCancelled = false

    function setHoldProgress(progress: number) {
      stageRef.current?.style.setProperty('--hold-progress', String(progress))
    }

    async function capture(video: HTMLVideoElement) {
      try {
        const file = await captureVideoFrame(video, guide.fileName)
        if (isCancelled) return
        setCapturedFile(file)
        setPhase(CapturePhase.CAPTURED)
      } catch {
        if (!isCancelled) setIsAnalyzerUnavailable(true)
      }
    }

    function analyzeFrame() {
      const video = videoRef.current
      if (
        !frameAnalyzer ||
        !video ||
        video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA ||
        video.currentTime === lastVideoTime
      ) {
        animationFrameId = requestAnimationFrame(analyzeFrame)
        return
      }
      lastVideoTime = video.currentTime
      const now = performance.now()
      const result = frameAnalyzer(video, portraitCropRectangle(video.videoWidth, video.videoHeight), now)
      const resultKey = JSON.stringify(result)
      if (resultKey !== lastResultKey) {
        lastResultKey = resultKey
        setGuideResult(result)
      }
      if (result.status === guide.readyStatus) {
        holdStartTime ??= now
        const progress = Math.min(1, (now - holdStartTime) / HOLD_DURATION_MILLISECONDS)
        setHoldProgress(progress)
        if (progress >= 1) {
          capture(video)
          return
        }
      } else {
        holdStartTime = null
        setHoldProgress(0)
      }
      animationFrameId = requestAnimationFrame(analyzeFrame)
    }

    animationFrameId = requestAnimationFrame(analyzeFrame)
    return () => {
      isCancelled = true
      cancelAnimationFrame(animationFrameId)
      setHoldProgress(0)
    }
  }, [phase, frameAnalyzer, guide])

  async function handleManualCapture() {
    const video = videoRef.current
    if (!video || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) return
    setCapturedFile(await captureVideoFrame(video, guide.fileName))
    setPhase(CapturePhase.CAPTURED)
  }

  function handleRetake() {
    setCapturedFile(null)
    setGuideResult(guide.initialResult)
    setPhase(CapturePhase.LIVE)
  }

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setIsProcessingUpload(true)
    setUploadErrorMessage(null)
    const normalized = await guide.normalizeUpload(file)
    setIsProcessingUpload(false)
    if (normalized.result === UploadedPhotoResult.NOT_FOUND) {
      setUploadErrorMessage(copy.uploadNotFound)
      return
    }
    onComplete(normalized.file)
  }

  const isReady = guideResult.status === guide.readyStatus

  // 페이지 안의 transform·애니메이션에 영향받지 않도록 body 에 바로 띄운다
  return createPortal(
    <div className="capture-backdrop">
      <div className="capture-dialog" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <div className="capture-stage" ref={stageRef}>
          {phase !== CapturePhase.UNAVAILABLE && (
            <video
              ref={videoRef}
              className={`capture-video${phase === CapturePhase.CAPTURED ? ' is-hidden' : ''}`}
              muted
              playsInline
            />
          )}
          {phase === CapturePhase.CAPTURED && capturedPreviewUrl ? (
            <img className="capture-photo" src={capturedPreviewUrl} alt={copy.capturedPreview} />
          ) : (
            <GuideOverlay outlinePath={guide.outlinePath} isReady={isReady && phase === CapturePhase.LIVE} />
          )}
        </div>

        <div className="capture-panel">
          <div className="capture-panel-head">
            <p className="eyebrow">{messages.captureSpec}</p>
            <button
              ref={closeButtonRef}
              type="button"
              className={`${buttonClassName('plain', 'small')} capture-close`}
              onClick={onClose}
            >
              {messages.close}
            </button>
          </div>
          <h2 id={titleId} className="capture-title">
            {copy.title}
          </h2>
          <p className="footnote">{copy.lede}</p>

          {phase === CapturePhase.STARTING && <Loading message={messages.startingCamera} />}

          {phase === CapturePhase.LIVE && !frameAnalyzer && !isAnalyzerUnavailable && (
            <Loading message={messages.loadingDetector} />
          )}

          {phase === CapturePhase.LIVE && frameAnalyzer && !isAnalyzerUnavailable && (
            <>
              <p className={`capture-status${isReady ? ' is-ready' : ''}`} aria-live="polite">
                {copy.statuses[guideResult.status]}
              </p>
              <ul className="capture-checks">
                {guide.checkNames.map((checkName) => (
                  <li key={checkName} className={guideResult.checks[checkName] ? 'is-passed' : undefined}>
                    <span className="capture-check-mark" aria-hidden="true" />
                    {copy.checks[checkName]}
                  </li>
                ))}
              </ul>
            </>
          )}

          {phase === CapturePhase.LIVE && isAnalyzerUnavailable && (
            <>
              <p className="state-banner state-notice">{messages.detectorUnavailable}</p>
              <Button onClick={handleManualCapture}>{messages.capture}</Button>
            </>
          )}

          {phase === CapturePhase.CAPTURED && capturedFile && (
            <div className="capture-actions">
              <Button onClick={() => onComplete(capturedFile)}>{messages.useThisPhoto}</Button>
              <Button variant="secondary" onClick={handleRetake}>
                {messages.retake}
              </Button>
            </div>
          )}

          {phase === CapturePhase.UNAVAILABLE && (
            <>
              <p className="state-banner state-notice">{messages.cameraUnavailable}</p>
              <label className="button button-primary capture-upload">
                {messages.uploadInstead}
                <input
                  type="file"
                  accept="image/*"
                  className="visually-hidden"
                  disabled={isProcessingUpload}
                  onChange={handleUpload}
                />
              </label>
              {isProcessingUpload && <Loading message={messages.processingUpload} />}
              {uploadErrorMessage && <ErrorMessage message={uploadErrorMessage} />}
            </>
          )}
        </div>
      </div>
    </div>,
    document.body,
  )
}
