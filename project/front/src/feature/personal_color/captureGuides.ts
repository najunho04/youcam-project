// 가이드 촬영 대상(얼굴·상반신)별 설정: 판정기 로딩 · 화면 가이드 모양 · 업로드 사진 맞추기.
import type { UploadedPhotoNormalization } from './camera'
import { loadFaceDetector, measureFaceFrame, normalizeUploadedSelfie, SELFIE_FILE_NAME } from './faceCamera'
import { evaluateFaceGuide, FACE_GUIDE_CHECK_NAMES, FACE_GUIDE_OVAL, FaceGuideStatus } from './faceGuide'
import type { FaceGuideCheckName } from './faceGuide'
import { PHOTO_HEIGHT, PHOTO_WIDTH } from './photoGuide'
import type { GuideResult, Rectangle } from './photoGuide'
import {
  loadPoseLandmarker,
  measureUpperBodyFrame,
  normalizeUploadedUpperBody,
  UPPER_BODY_FILE_NAME,
} from './upperBodyCamera'
import {
  evaluateUpperBodyGuide,
  UPPER_BODY_GUIDE_CHECK_NAMES,
  UPPER_BODY_GUIDE_SILHOUETTE,
  UpperBodyGuideStatus,
} from './upperBodyGuide'
import type { UpperBodyGuideCheckName } from './upperBodyGuide'

export const CaptureSubject = { FACE: 'FACE', UPPER_BODY: 'UPPER_BODY' } as const
export type CaptureSubject = (typeof CaptureSubject)[keyof typeof CaptureSubject]

/** 비디오 한 프레임을 판정한다. crop 은 저장될 4:5 영역(프레임 px). */
export type FrameAnalyzer<Status extends string, CheckName extends string> = (
  video: HTMLVideoElement,
  crop: Rectangle,
  timestamp: number,
) => GuideResult<Status, CheckName>

export type CaptureGuide<Status extends string, CheckName extends string> = {
  checkNames: readonly CheckName[]
  readyStatus: Status
  initialResult: GuideResult<Status, CheckName>
  /** 가이드 모양 SVG path (viewBox 0 0 1080 1350). 바깥은 어둡게, 안은 뚫어서 보여준다. */
  outlinePath: string
  fileName: string
  loadFrameAnalyzer: () => Promise<FrameAnalyzer<Status, CheckName>>
  normalizeUpload: (file: File) => Promise<UploadedPhotoNormalization>
}

function ellipsePath(centerX: number, centerY: number, radiusX: number, radiusY: number): string {
  return `M ${centerX - radiusX} ${centerY} A ${radiusX} ${radiusY} 0 1 1 ${centerX + radiusX} ${centerY} A ${radiusX} ${radiusY} 0 1 1 ${centerX - radiusX} ${centerY} Z`
}

/** 머리 타원 위쪽 호 + 목 + 어깨선 + 가슴까지 이어진 상반신 실루엣. */
function upperBodySilhouettePath(): string {
  const { head, shoulderY, shoulderHalfWidth } = UPPER_BODY_GUIDE_SILHOUETTE
  const headCenterX = head.centerX * PHOTO_WIDTH
  const headCenterY = head.centerY * PHOTO_HEIGHT
  const headRadiusX = head.radiusX * PHOTO_WIDTH
  const headRadiusY = head.radiusY * PHOTO_HEIGHT
  // 목이 머리 타원과 만나는 높이와 그 높이의 타원 폭
  const neckTopY = headCenterY + headRadiusY * 0.92
  const neckHalfWidth = headRadiusX * Math.sqrt(1 - 0.92 ** 2)
  const neckBottomY = neckTopY + 115
  const shoulderPixelY = shoulderY * PHOTO_HEIGHT
  const shoulderLeftX = (0.5 - shoulderHalfWidth) * PHOTO_WIDTH
  const shoulderRightX = (0.5 + shoulderHalfWidth) * PHOTO_WIDTH
  const sideLeftX = shoulderLeftX - 135
  const sideRightX = shoulderRightX + 135
  return [
    `M ${headCenterX - neckHalfWidth} ${neckTopY}`,
    `A ${headRadiusX} ${headRadiusY} 0 1 1 ${headCenterX + neckHalfWidth} ${neckTopY}`,
    `L ${headCenterX + neckHalfWidth + 9} ${neckBottomY}`,
    `C ${headCenterX + 120} ${neckBottomY + 30}, ${shoulderRightX - 90} ${shoulderPixelY - 40}, ${shoulderRightX} ${shoulderPixelY}`,
    `C ${shoulderRightX + 95} ${shoulderPixelY + 31}, ${sideRightX} ${shoulderPixelY + 111}, ${sideRightX} ${shoulderPixelY + 241}`,
    `L ${sideRightX} ${PHOTO_HEIGHT}`,
    `L ${sideLeftX} ${PHOTO_HEIGHT}`,
    `L ${sideLeftX} ${shoulderPixelY + 241}`,
    `C ${sideLeftX} ${shoulderPixelY + 111}, ${shoulderLeftX - 95} ${shoulderPixelY + 31}, ${shoulderLeftX} ${shoulderPixelY}`,
    `C ${shoulderLeftX + 90} ${shoulderPixelY - 40}, ${headCenterX - 120} ${neckBottomY + 30}, ${headCenterX - neckHalfWidth - 9} ${neckBottomY}`,
    'Z',
  ].join(' ')
}

export const FACE_CAPTURE_GUIDE: CaptureGuide<FaceGuideStatus, FaceGuideCheckName> = {
  checkNames: FACE_GUIDE_CHECK_NAMES,
  readyStatus: FaceGuideStatus.READY,
  initialResult: evaluateFaceGuide(null),
  outlinePath: ellipsePath(
    FACE_GUIDE_OVAL.centerX * PHOTO_WIDTH,
    FACE_GUIDE_OVAL.centerY * PHOTO_HEIGHT,
    FACE_GUIDE_OVAL.radiusX * PHOTO_WIDTH,
    FACE_GUIDE_OVAL.radiusY * PHOTO_HEIGHT,
  ),
  fileName: SELFIE_FILE_NAME,
  loadFrameAnalyzer: async () => {
    const detector = await loadFaceDetector('VIDEO')
    return (video, crop, timestamp) => evaluateFaceGuide(measureFaceFrame(detector, video, crop, timestamp))
  },
  normalizeUpload: normalizeUploadedSelfie,
}

export const UPPER_BODY_CAPTURE_GUIDE: CaptureGuide<UpperBodyGuideStatus, UpperBodyGuideCheckName> = {
  checkNames: UPPER_BODY_GUIDE_CHECK_NAMES,
  readyStatus: UpperBodyGuideStatus.READY,
  initialResult: evaluateUpperBodyGuide(null),
  outlinePath: upperBodySilhouettePath(),
  fileName: UPPER_BODY_FILE_NAME,
  loadFrameAnalyzer: async () => {
    const landmarker = await loadPoseLandmarker('VIDEO')
    return (video, crop, timestamp) => evaluateUpperBodyGuide(measureUpperBodyFrame(landmarker, video, crop, timestamp))
  },
  normalizeUpload: normalizeUploadedUpperBody,
}
