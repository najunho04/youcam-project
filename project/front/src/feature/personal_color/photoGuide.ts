// 가이드 촬영 사진(얼굴·상반신) 공용 규격과 크롭 계산. 카메라·MediaPipe 와 무관한 순수 계산만 둔다.

export const PHOTO_WIDTH = 1080
export const PHOTO_HEIGHT = 1350
export const PHOTO_ASPECT_RATIO = PHOTO_WIDTH / PHOTO_HEIGHT

/** 가이드 영역 평균 밝기 허용 범위 (0~255). */
export const PHOTO_BRIGHTNESS = { minimum: 70, maximum: 220 }

export type Point = { x: number; y: number }
export type Rectangle = { x: number; y: number; width: number; height: number }

/** 한 프레임의 판정 결과. status 는 가장 먼저 고쳐야 할 항목, checks 는 항목별 통과 여부. */
export type GuideResult<Status extends string, CheckName extends string> = {
  status: Status
  checks: Record<CheckName, boolean>
}

/** 세로 차이를 가로와 같은 단위로 되돌려 두 점을 잇는 선의 기울기(도)를 잰다. 좌표는 crop 비율. */
export function tiltDegrees(first: Point, second: Point): number {
  const horizontalDistance = Math.abs(first.x - second.x)
  const verticalDistance = Math.abs(first.y - second.y) / PHOTO_ASPECT_RATIO
  return (Math.atan2(verticalDistance, horizontalDistance) * 180) / Math.PI
}

/** 카메라 프레임 가운데에서 가장 큰 4:5 영역. 화면의 object-fit: cover 미리보기와 같은 영역이다. */
export function portraitCropRectangle(frameWidth: number, frameHeight: number): Rectangle {
  const width = Math.min(frameWidth, Math.round(frameHeight * PHOTO_ASPECT_RATIO))
  const height = Math.round(width / PHOTO_ASPECT_RATIO)
  return { x: Math.round((frameWidth - width) / 2), y: Math.round((frameHeight - height) / 2), width, height }
}

/**
 * 기준 물체(얼굴 박스·어깨선, px)가 가이드와 같은 크기·위치에 오도록 4:5 영역을 잡는다. 이미지 밖으로는 나가지 않는다.
 * placement.widthRatio: 기준 폭이 crop 폭에서 차지할 비율, placement.centerY: 기준 중심이 올 crop 세로 비율.
 */
export function cropRectangleAroundAnchor(
  imageWidth: number,
  imageHeight: number,
  anchor: { centerX: number; centerY: number; width: number },
  placement: { widthRatio: number; centerY: number },
): Rectangle {
  let width = anchor.width / placement.widthRatio
  const shrinkScale = Math.min(1, imageWidth / width, imageHeight / (width / PHOTO_ASPECT_RATIO))
  width = Math.round(width * shrinkScale)
  const height = Math.round(width / PHOTO_ASPECT_RATIO)

  const left = anchor.centerX - width / 2
  const top = anchor.centerY - height * placement.centerY
  return {
    x: Math.round(Math.min(Math.max(left, 0), imageWidth - width)),
    y: Math.round(Math.min(Math.max(top, 0), imageHeight - height)),
    width,
    height,
  }
}
