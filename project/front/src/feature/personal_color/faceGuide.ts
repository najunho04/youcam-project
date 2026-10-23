// 얼굴 사진 가이드 판정과 얼굴 기준 크롭 계산.
import { cropRectangleAroundAnchor, PHOTO_BRIGHTNESS, tiltDegrees } from './photoGuide'
import type { GuideResult, Point, Rectangle } from './photoGuide'

/** 화면에 그리는 얼굴 가이드 타원 (crop 비율 좌표). 얼굴이 화면을 거의 채우는 크기다. */
export const FACE_GUIDE_OVAL = { centerX: 0.5, centerY: 0.46, radiusX: 0.39, radiusY: 0.405 }

/**
 * 얼굴 박스 폭이 crop 폭에서 차지해야 하는 비율 범위와 크롭 기준값.
 * YouCam 피부톤 분석은 얼굴 폭이 사진 폭의 60% 를 넘어야 받는다 (넘지 않으면 error_face_position_too_small).
 * BlazeFace 박스는 실제 얼굴 윤곽과 같거나 조금 작게 잡히므로, 박스가 60% 를 넘으면(minimum 초과) 실제 얼굴도 확실히 넘는다.
 */
const FACE_WIDTH_RATIO = { minimum: 0.6, maximum: 0.78, target: 0.66 }
/** 얼굴 박스 중심(코 근처)이 와야 할 위치와 허용 오차 (crop 비율). 타원 중심보다 살짝 아래다. */
const FACE_CENTER = { x: 0.5, y: 0.49, toleranceX: 0.06, toleranceY: 0.07 }
/** 코가 두 눈 가운데에서 벗어난 정도 (눈 사이 거리 대비). 넘으면 고개를 돌린 것. */
const MAXIMUM_YAW_RATIO = 0.22
/** BlazeFace 눈 키포인트는 몇 도씩 흔들려서 너무 빡빡하게 잡지 않는다. */
const MAXIMUM_ROLL_DEGREES = 15

export const FaceGuideStatus = {
  NO_FACE: 'NO_FACE',
  MULTIPLE_FACES: 'MULTIPLE_FACES',
  TOO_FAR: 'TOO_FAR',
  TOO_CLOSE: 'TOO_CLOSE',
  OFF_CENTER: 'OFF_CENTER',
  NOT_FRONTAL: 'NOT_FRONTAL',
  TOO_DARK: 'TOO_DARK',
  TOO_BRIGHT: 'TOO_BRIGHT',
  READY: 'READY',
} as const
export type FaceGuideStatus = (typeof FaceGuideStatus)[keyof typeof FaceGuideStatus]

export const FACE_GUIDE_CHECK_NAMES = ['singleFace', 'distance', 'position', 'frontal', 'lighting'] as const
export type FaceGuideCheckName = (typeof FACE_GUIDE_CHECK_NAMES)[number]
export type FaceGuideChecks = Record<FaceGuideCheckName, boolean>
export type FaceGuideResult = GuideResult<FaceGuideStatus, FaceGuideCheckName>

/** 한 프레임에서 잰 얼굴 정보. 좌표는 모두 crop 비율(0~1). */
export type FaceMeasurement = {
  faceCount: number
  faceBox: Rectangle
  leftEye: Point
  rightEye: Point
  nose: Point
  brightness: number
}

const NOTHING_PASSED: FaceGuideChecks = { singleFace: false, distance: false, position: false, frontal: false, lighting: false }

/** 가이드 조건을 하나씩 확인하고, 가장 먼저 고쳐야 할 항목을 status 로 돌려준다. */
export function evaluateFaceGuide(measurement: FaceMeasurement | null): FaceGuideResult {
  if (!measurement || measurement.faceCount === 0) return { status: FaceGuideStatus.NO_FACE, checks: NOTHING_PASSED }

  const { faceBox, leftEye, rightEye, nose, brightness } = measurement
  const faceCenterX = faceBox.x + faceBox.width / 2
  const faceCenterY = faceBox.y + faceBox.height / 2
  const eyeMiddleX = (leftEye.x + rightEye.x) / 2
  const eyeDistance = Math.abs(leftEye.x - rightEye.x)
  const yawRatio = eyeDistance > 0 ? Math.abs(nose.x - eyeMiddleX) / eyeDistance : Infinity

  const isTooFar = faceBox.width <= FACE_WIDTH_RATIO.minimum
  const isTooClose = faceBox.width > FACE_WIDTH_RATIO.maximum
  const isTooDark = brightness < PHOTO_BRIGHTNESS.minimum
  const isTooBright = brightness > PHOTO_BRIGHTNESS.maximum
  const checks: FaceGuideChecks = {
    singleFace: measurement.faceCount === 1,
    distance: !isTooFar && !isTooClose,
    position:
      Math.abs(faceCenterX - FACE_CENTER.x) <= FACE_CENTER.toleranceX &&
      Math.abs(faceCenterY - FACE_CENTER.y) <= FACE_CENTER.toleranceY,
    frontal: yawRatio <= MAXIMUM_YAW_RATIO && tiltDegrees(leftEye, rightEye) <= MAXIMUM_ROLL_DEGREES,
    lighting: !isTooDark && !isTooBright,
  }

  let status: FaceGuideStatus = FaceGuideStatus.READY
  if (!checks.singleFace) status = FaceGuideStatus.MULTIPLE_FACES
  else if (isTooFar) status = FaceGuideStatus.TOO_FAR
  else if (isTooClose) status = FaceGuideStatus.TOO_CLOSE
  else if (!checks.position) status = FaceGuideStatus.OFF_CENTER
  else if (!checks.frontal) status = FaceGuideStatus.NOT_FRONTAL
  else if (isTooDark) status = FaceGuideStatus.TOO_DARK
  else if (isTooBright) status = FaceGuideStatus.TOO_BRIGHT
  return { status, checks }
}

/** 업로드한 사진에서 얼굴(px 박스)이 가이드와 같은 크기·위치에 오도록 4:5 영역을 잡는다. */
export function cropRectangleAroundFace(imageWidth: number, imageHeight: number, faceBox: Rectangle): Rectangle {
  return cropRectangleAroundAnchor(
    imageWidth,
    imageHeight,
    { centerX: faceBox.x + faceBox.width / 2, centerY: faceBox.y + faceBox.height / 2, width: faceBox.width },
    { widthRatio: FACE_WIDTH_RATIO.target, centerY: FACE_CENTER.y },
  )
}
