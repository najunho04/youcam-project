// 상반신 사진 가이드 판정과 어깨선 기준 크롭 계산.
// 기준 구도: 머리 위에 여백이 조금 있고, 코가 위에서 35%, 어깨선이 66% 높이, 어깨 폭이 화면 폭의 절반 남짓인 가슴 위 상반신.
import { cropRectangleAroundAnchor, PHOTO_BRIGHTNESS, tiltDegrees } from './photoGuide'
import type { GuideResult, Point, Rectangle } from './photoGuide'

/** 화면에 그리는 상반신 실루엣의 머리 타원과 어깨선 (crop 비율 좌표). */
export const UPPER_BODY_GUIDE_SILHOUETTE = {
  head: { centerX: 0.5, centerY: 0.3, radiusX: 0.165, radiusY: 0.19 },
  shoulderY: 0.66,
  shoulderHalfWidth: 0.265,
}

/** 어깨 폭(양 어깨 관절 사이)이 crop 폭에서 차지해야 하는 비율 범위와 크롭 기준값. */
const SHOULDER_WIDTH_RATIO = { minimum: 0.34, maximum: 0.78, target: 0.53 }
/** 어깨선 가운데가 와야 할 위치와 허용 오차 (crop 비율). */
const SHOULDER_CENTER = { x: 0.5, y: UPPER_BODY_GUIDE_SILHOUETTE.shoulderY, toleranceX: 0.12, toleranceY: 0.13 }
/** 머리가 잘리거나 너무 내려오지 않게 코가 있어야 할 세로 범위. */
const NOSE_VERTICAL_RANGE = { minimum: 0.12, maximum: 0.55 }
/** 어깨 랜드마크를 믿을 최소 visibility 와 화면 가장자리 여백. */
const MINIMUM_SHOULDER_VISIBILITY = 0.5
const FRAME_EDGE_MARGIN = 0
const MAXIMUM_SHOULDER_TILT_DEGREES = 14
/** 코가 어깨선 가운데에서 벗어난 정도 (어깨 폭 대비). 넘으면 고개나 몸을 돌린 것. */
const MAXIMUM_NOSE_OFFSET_RATIO = 0.22

export const UpperBodyGuideStatus = {
  NO_PERSON: 'NO_PERSON',
  MULTIPLE_PEOPLE: 'MULTIPLE_PEOPLE',
  SHOULDERS_HIDDEN: 'SHOULDERS_HIDDEN',
  TOO_FAR: 'TOO_FAR',
  TOO_CLOSE: 'TOO_CLOSE',
  OFF_CENTER: 'OFF_CENTER',
  NOT_FRONTAL: 'NOT_FRONTAL',
  TOO_DARK: 'TOO_DARK',
  TOO_BRIGHT: 'TOO_BRIGHT',
  READY: 'READY',
} as const
export type UpperBodyGuideStatus = (typeof UpperBodyGuideStatus)[keyof typeof UpperBodyGuideStatus]

export const UPPER_BODY_GUIDE_CHECK_NAMES = [
  'singlePerson',
  'shouldersVisible',
  'distance',
  'position',
  'frontal',
  'lighting',
] as const
export type UpperBodyGuideCheckName = (typeof UPPER_BODY_GUIDE_CHECK_NAMES)[number]
export type UpperBodyGuideChecks = Record<UpperBodyGuideCheckName, boolean>
export type UpperBodyGuideResult = GuideResult<UpperBodyGuideStatus, UpperBodyGuideCheckName>

export type BodyLandmark = Point & { visibility: number }

/** 한 프레임에서 잰 상반신 정보. 좌표는 모두 crop 비율(0~1). */
export type UpperBodyMeasurement = {
  personCount: number
  nose: Point
  leftShoulder: BodyLandmark
  rightShoulder: BodyLandmark
  brightness: number
}

const NOTHING_PASSED: UpperBodyGuideChecks = {
  singlePerson: false,
  shouldersVisible: false,
  distance: false,
  position: false,
  frontal: false,
  lighting: false,
}

function isInsideFrame(landmark: BodyLandmark): boolean {
  return (
    landmark.visibility >= MINIMUM_SHOULDER_VISIBILITY &&
    landmark.x >= FRAME_EDGE_MARGIN &&
    landmark.x <= 1 - FRAME_EDGE_MARGIN &&
    landmark.y >= 0 &&
    landmark.y <= 1 - FRAME_EDGE_MARGIN
  )
}

/** 가이드 조건을 하나씩 확인하고, 가장 먼저 고쳐야 할 항목을 status 로 돌려준다. */
export function evaluateUpperBodyGuide(measurement: UpperBodyMeasurement | null): UpperBodyGuideResult {
  if (!measurement || measurement.personCount === 0) {
    return { status: UpperBodyGuideStatus.NO_PERSON, checks: NOTHING_PASSED }
  }

  const { nose, leftShoulder, rightShoulder, brightness } = measurement
  const shoulderWidth = Math.abs(leftShoulder.x - rightShoulder.x)
  const shoulderMiddleX = (leftShoulder.x + rightShoulder.x) / 2
  const shoulderMiddleY = (leftShoulder.y + rightShoulder.y) / 2
  const noseOffsetRatio = shoulderWidth > 0 ? Math.abs(nose.x - shoulderMiddleX) / shoulderWidth : Infinity

  const isTooFar = shoulderWidth < SHOULDER_WIDTH_RATIO.minimum
  const isTooClose = shoulderWidth > SHOULDER_WIDTH_RATIO.maximum
  const isTooDark = brightness < PHOTO_BRIGHTNESS.minimum
  const isTooBright = brightness > PHOTO_BRIGHTNESS.maximum
  const checks: UpperBodyGuideChecks = {
    singlePerson: measurement.personCount === 1,
    shouldersVisible: isInsideFrame(leftShoulder) && isInsideFrame(rightShoulder),
    distance: !isTooFar && !isTooClose,
    position:
      Math.abs(shoulderMiddleX - SHOULDER_CENTER.x) <= SHOULDER_CENTER.toleranceX &&
      Math.abs(shoulderMiddleY - SHOULDER_CENTER.y) <= SHOULDER_CENTER.toleranceY &&
      nose.y >= NOSE_VERTICAL_RANGE.minimum &&
      nose.y <= NOSE_VERTICAL_RANGE.maximum,
    frontal:
      tiltDegrees(leftShoulder, rightShoulder) <= MAXIMUM_SHOULDER_TILT_DEGREES &&
      noseOffsetRatio <= MAXIMUM_NOSE_OFFSET_RATIO,
    lighting: !isTooDark && !isTooBright,
  }

  let status: UpperBodyGuideStatus = UpperBodyGuideStatus.READY
  if (!checks.singlePerson) status = UpperBodyGuideStatus.MULTIPLE_PEOPLE
  else if (!checks.shouldersVisible) status = UpperBodyGuideStatus.SHOULDERS_HIDDEN
  else if (isTooFar) status = UpperBodyGuideStatus.TOO_FAR
  else if (isTooClose) status = UpperBodyGuideStatus.TOO_CLOSE
  else if (!checks.position) status = UpperBodyGuideStatus.OFF_CENTER
  else if (!checks.frontal) status = UpperBodyGuideStatus.NOT_FRONTAL
  else if (isTooDark) status = UpperBodyGuideStatus.TOO_DARK
  else if (isTooBright) status = UpperBodyGuideStatus.TOO_BRIGHT
  return { status, checks }
}

/** 업로드한 사진에서 양 어깨(px)가 실루엣과 같은 크기·위치에 오도록 4:5 영역을 잡는다. */
export function cropRectangleAroundShoulders(
  imageWidth: number,
  imageHeight: number,
  shoulders: { left: Point; right: Point },
): Rectangle {
  return cropRectangleAroundAnchor(
    imageWidth,
    imageHeight,
    {
      centerX: (shoulders.left.x + shoulders.right.x) / 2,
      centerY: (shoulders.left.y + shoulders.right.y) / 2,
      width: Math.abs(shoulders.left.x - shoulders.right.x),
    },
    { widthRatio: SHOULDER_WIDTH_RATIO.target, centerY: SHOULDER_CENTER.y },
  )
}
