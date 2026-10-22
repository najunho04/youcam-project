import { describe, expect, it } from 'vitest'
import { cropRectangleAroundFace, evaluateFaceGuide, FaceGuideStatus } from '../../../src/feature/personal_color/faceGuide'
import type { FaceMeasurement } from '../../../src/feature/personal_color/faceGuide'
import { PHOTO_HEIGHT, PHOTO_WIDTH, portraitCropRectangle } from '../../../src/feature/personal_color/photoGuide'

/** 가이드 타원에 정면으로 잘 맞춘 얼굴 (crop 비율 좌표). */
function wellFittedFace(overrides: Partial<FaceMeasurement> = {}): FaceMeasurement {
  return {
    faceCount: 1,
    faceBox: { x: 0.3, y: 0.28, width: 0.4, height: 0.32 },
    leftEye: { x: 0.59, y: 0.37 },
    rightEye: { x: 0.41, y: 0.37 },
    nose: { x: 0.5, y: 0.42 },
    brightness: 140,
    ...overrides,
  }
}

describe('evaluateFaceGuide', () => {
  it('얼굴이 없으면 NO_FACE', () => {
    expect(evaluateFaceGuide(null).status).toBe(FaceGuideStatus.NO_FACE)
  })

  it('여러 명이면 MULTIPLE_FACES', () => {
    const result = evaluateFaceGuide(wellFittedFace({ faceCount: 2 }))
    expect(result.status).toBe(FaceGuideStatus.MULTIPLE_FACES)
    expect(result.checks.singleFace).toBe(false)
  })

  it('가이드에 정면으로 맞으면 READY, 모든 항목 통과', () => {
    const result = evaluateFaceGuide(wellFittedFace())
    expect(result.status).toBe(FaceGuideStatus.READY)
    expect(Object.values(result.checks).every(Boolean)).toBe(true)
  })

  it('얼굴이 작으면 TOO_FAR, 크면 TOO_CLOSE', () => {
    expect(evaluateFaceGuide(wellFittedFace({ faceBox: { x: 0.4, y: 0.37, width: 0.2, height: 0.16 } })).status).toBe(
      FaceGuideStatus.TOO_FAR,
    )
    expect(evaluateFaceGuide(wellFittedFace({ faceBox: { x: 0.1, y: 0.2, width: 0.8, height: 0.64 } })).status).toBe(
      FaceGuideStatus.TOO_CLOSE,
    )
  })

  it('가이드 중심에서 벗어나면 OFF_CENTER', () => {
    const result = evaluateFaceGuide(wellFittedFace({ faceBox: { x: 0.5, y: 0.28, width: 0.4, height: 0.32 } }))
    expect(result.status).toBe(FaceGuideStatus.OFF_CENTER)
    expect(result.checks.position).toBe(false)
  })

  it('고개를 돌리면 NOT_FRONTAL', () => {
    expect(evaluateFaceGuide(wellFittedFace({ nose: { x: 0.57, y: 0.42 } })).status).toBe(FaceGuideStatus.NOT_FRONTAL)
  })

  it('고개를 기울이면 NOT_FRONTAL', () => {
    expect(evaluateFaceGuide(wellFittedFace({ leftEye: { x: 0.59, y: 0.41 }, rightEye: { x: 0.41, y: 0.33 } })).status).toBe(
      FaceGuideStatus.NOT_FRONTAL,
    )
  })

  it('어두우면 TOO_DARK, 너무 밝으면 TOO_BRIGHT', () => {
    expect(evaluateFaceGuide(wellFittedFace({ brightness: 40 })).status).toBe(FaceGuideStatus.TOO_DARK)
    expect(evaluateFaceGuide(wellFittedFace({ brightness: 240 })).status).toBe(FaceGuideStatus.TOO_BRIGHT)
  })
})

describe('portraitCropRectangle', () => {
  it('가로 프레임에서 가운데 4:5 영역을 가장 크게 자른다', () => {
    expect(portraitCropRectangle(1920, 1080)).toEqual({ x: 528, y: 0, width: 864, height: 1080 })
  })

  it('세로로 긴 프레임은 위아래를 자른다', () => {
    expect(portraitCropRectangle(1080, 1920)).toEqual({ x: 0, y: 285, width: 1080, height: 1350 })
  })
})

describe('cropRectangleAroundFace', () => {
  it('얼굴 크기에 맞춘 4:5 영역을 얼굴 중심으로 자른다', () => {
    const crop = cropRectangleAroundFace(4000, 3000, { x: 1800, y: 1200, width: 460, height: 400 })
    expect(crop.width / crop.height).toBeCloseTo(PHOTO_WIDTH / PHOTO_HEIGHT, 2)
    expect(crop.width).toBe(1150)
    expect(crop.x + crop.width / 2).toBe(2030)
  })

  it('이미지 밖으로 나가지 않게 줄이고 안쪽으로 민다', () => {
    const crop = cropRectangleAroundFace(800, 600, { x: 0, y: 0, width: 400, height: 350 })
    expect(crop.x).toBeGreaterThanOrEqual(0)
    expect(crop.y).toBeGreaterThanOrEqual(0)
    expect(crop.x + crop.width).toBeLessThanOrEqual(800)
    expect(crop.y + crop.height).toBeLessThanOrEqual(600)
    expect(crop.width / crop.height).toBeCloseTo(PHOTO_WIDTH / PHOTO_HEIGHT, 2)
  })
})
