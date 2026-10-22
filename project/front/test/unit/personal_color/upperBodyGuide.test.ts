import { describe, expect, it } from 'vitest'
import { PHOTO_HEIGHT, PHOTO_WIDTH } from '../../../src/feature/personal_color/photoGuide'
import {
  cropRectangleAroundShoulders,
  evaluateUpperBodyGuide,
  UpperBodyGuideStatus,
} from '../../../src/feature/personal_color/upperBodyGuide'
import type { UpperBodyMeasurement } from '../../../src/feature/personal_color/upperBodyGuide'

/** 실루엣 가이드에 정면으로 잘 맞춘 상반신 (crop 비율 좌표). */
function wellFittedUpperBody(overrides: Partial<UpperBodyMeasurement> = {}): UpperBodyMeasurement {
  return {
    personCount: 1,
    nose: { x: 0.5, y: 0.35 },
    leftShoulder: { x: 0.765, y: 0.66, visibility: 0.99 },
    rightShoulder: { x: 0.235, y: 0.66, visibility: 0.99 },
    brightness: 140,
    ...overrides,
  }
}

describe('evaluateUpperBodyGuide', () => {
  it('사람이 없으면 NO_PERSON', () => {
    expect(evaluateUpperBodyGuide(null).status).toBe(UpperBodyGuideStatus.NO_PERSON)
  })

  it('여러 명이면 MULTIPLE_PEOPLE', () => {
    const result = evaluateUpperBodyGuide(wellFittedUpperBody({ personCount: 2 }))
    expect(result.status).toBe(UpperBodyGuideStatus.MULTIPLE_PEOPLE)
    expect(result.checks.singlePerson).toBe(false)
  })

  it('실루엣에 정면으로 맞으면 READY, 모든 항목 통과', () => {
    const result = evaluateUpperBodyGuide(wellFittedUpperBody())
    expect(result.status).toBe(UpperBodyGuideStatus.READY)
    expect(Object.values(result.checks).every(Boolean)).toBe(true)
  })

  it('가슴 위 상반신 예시 사진(포즈 모델 실측값)은 READY', () => {
    const result = evaluateUpperBodyGuide({
      personCount: 1,
      nose: { x: 0.489, y: 0.349 },
      leftShoulder: { x: 0.764, y: 0.68, visibility: 1 },
      rightShoulder: { x: 0.235, y: 0.646, visibility: 1 },
      brightness: 140,
    })
    expect(result.status).toBe(UpperBodyGuideStatus.READY)
  })

  it('어깨가 화면 밖이거나 가려지면 SHOULDERS_HIDDEN', () => {
    expect(
      evaluateUpperBodyGuide(wellFittedUpperBody({ leftShoulder: { x: 1.04, y: 0.66, visibility: 0.9 } })).status,
    ).toBe(UpperBodyGuideStatus.SHOULDERS_HIDDEN)
    expect(
      evaluateUpperBodyGuide(wellFittedUpperBody({ rightShoulder: { x: 0.22, y: 0.66, visibility: 0.2 } })).status,
    ).toBe(UpperBodyGuideStatus.SHOULDERS_HIDDEN)
  })

  it('어깨 폭이 좁으면 TOO_FAR, 넓으면 TOO_CLOSE', () => {
    expect(
      evaluateUpperBodyGuide(
        wellFittedUpperBody({
          leftShoulder: { x: 0.65, y: 0.66, visibility: 0.99 },
          rightShoulder: { x: 0.35, y: 0.66, visibility: 0.99 },
        }),
      ).status,
    ).toBe(UpperBodyGuideStatus.TOO_FAR)
    expect(
      evaluateUpperBodyGuide(
        wellFittedUpperBody({
          leftShoulder: { x: 0.9, y: 0.66, visibility: 0.99 },
          rightShoulder: { x: 0.1, y: 0.66, visibility: 0.99 },
        }),
      ).status,
    ).toBe(UpperBodyGuideStatus.TOO_CLOSE)
  })

  it('어깨선이 너무 높거나 머리가 잘리면 OFF_CENTER', () => {
    expect(
      evaluateUpperBodyGuide(
        wellFittedUpperBody({
          leftShoulder: { x: 0.78, y: 0.4, visibility: 0.99 },
          rightShoulder: { x: 0.22, y: 0.4, visibility: 0.99 },
        }),
      ).status,
    ).toBe(UpperBodyGuideStatus.OFF_CENTER)
    expect(evaluateUpperBodyGuide(wellFittedUpperBody({ nose: { x: 0.5, y: 0.05 } })).status).toBe(
      UpperBodyGuideStatus.OFF_CENTER,
    )
  })

  it('어깨가 기울거나 고개를 돌리면 NOT_FRONTAL', () => {
    expect(
      evaluateUpperBodyGuide(wellFittedUpperBody({ leftShoulder: { x: 0.765, y: 0.73, visibility: 0.99 }, rightShoulder: { x: 0.235, y: 0.59, visibility: 0.99 } }))
        .status,
    ).toBe(UpperBodyGuideStatus.NOT_FRONTAL)
    expect(evaluateUpperBodyGuide(wellFittedUpperBody({ nose: { x: 0.65, y: 0.35 } })).status).toBe(
      UpperBodyGuideStatus.NOT_FRONTAL,
    )
  })

  it('어두우면 TOO_DARK, 너무 밝으면 TOO_BRIGHT', () => {
    expect(evaluateUpperBodyGuide(wellFittedUpperBody({ brightness: 40 })).status).toBe(UpperBodyGuideStatus.TOO_DARK)
    expect(evaluateUpperBodyGuide(wellFittedUpperBody({ brightness: 240 })).status).toBe(UpperBodyGuideStatus.TOO_BRIGHT)
  })
})

describe('cropRectangleAroundShoulders', () => {
  it('어깨 폭에 맞춘 4:5 영역을 어깨 중심으로 자른다', () => {
    const crop = cropRectangleAroundShoulders(4000, 3000, { left: { x: 1700, y: 1500 }, right: { x: 2300, y: 1500 } })
    expect(crop.width / crop.height).toBeCloseTo(PHOTO_WIDTH / PHOTO_HEIGHT, 2)
    expect(crop.width).toBe(1132)
    expect(Math.abs(crop.x + crop.width / 2 - 2000)).toBeLessThanOrEqual(1)
  })
})
