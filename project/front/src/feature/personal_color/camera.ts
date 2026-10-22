// 가이드 촬영 공용: 전면 카메라 · MediaPipe wasm 로딩 · 밝기 측정 · 규격(1080×1350 JPEG) 사진 만들기 · 업로드 사진 맞추기.
// MediaPipe 는 무거워서 촬영 창을 열 때만 동적 import 하고, wasm·모델은 CDN 에서 받는다. 인식은 모두 브라우저 안에서 한다.
import type { FilesetResolver } from '@mediapipe/tasks-vision'
import { PHOTO_HEIGHT, PHOTO_WIDTH } from './photoGuide'
import type { Rectangle } from './photoGuide'

const MEDIAPIPE_WASM_URL = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.1.1/wasm'
const PHOTO_JPEG_QUALITY = 0.92
const BRIGHTNESS_SAMPLE_SIZE = 24

/** MediaPipe 가 WasmFileset 타입을 내보내지 않아서 forVisionTasks 결과 타입을 그대로 쓴다. */
type VisionFileset = Awaited<ReturnType<typeof FilesetResolver.forVisionTasks>>

let visionFilesetPromise: Promise<VisionFileset> | null = null

/** MediaPipe wasm 을 한 번만 받는다. 실패하면 다음 호출에서 다시 시도한다. */
export function loadVisionFileset(): Promise<VisionFileset> {
  if (!visionFilesetPromise) {
    visionFilesetPromise = import('@mediapipe/tasks-vision').then(({ FilesetResolver }) =>
      FilesetResolver.forVisionTasks(MEDIAPIPE_WASM_URL),
    )
    visionFilesetPromise.catch(() => {
      visionFilesetPromise = null
    })
  }
  return visionFilesetPromise
}

/** WebGL 을 못 쓰는 환경은 CPU 로 다시 만든다. */
export function createWithDelegateFallback<Task>(create: (delegate: 'GPU' | 'CPU') => Promise<Task>): Promise<Task> {
  return create('GPU').catch(() => create('CPU'))
}

export function isCameraSupported(): boolean {
  return typeof navigator !== 'undefined' && typeof navigator.mediaDevices?.getUserMedia === 'function'
}

export function openFrontCamera(): Promise<MediaStream> {
  return navigator.mediaDevices.getUserMedia({
    video: { facingMode: 'user', width: { ideal: 1920 }, height: { ideal: 1080 } },
    audio: false,
  })
}

/** region 평균 밝기 (Rec. 601 luma, 0~255). 작은 캔버스로 줄여서 잰다. */
export function measureBrightness(source: CanvasImageSource, region: Rectangle): number {
  const canvas = document.createElement('canvas')
  canvas.width = BRIGHTNESS_SAMPLE_SIZE
  canvas.height = BRIGHTNESS_SAMPLE_SIZE
  const context = canvas.getContext('2d', { willReadFrequently: true })
  if (!context || region.width <= 0 || region.height <= 0) return 0
  context.drawImage(source, region.x, region.y, region.width, region.height, 0, 0, BRIGHTNESS_SAMPLE_SIZE, BRIGHTNESS_SAMPLE_SIZE)
  const pixels = context.getImageData(0, 0, BRIGHTNESS_SAMPLE_SIZE, BRIGHTNESS_SAMPLE_SIZE).data
  let lumaSum = 0
  for (let index = 0; index < pixels.length; index += 4) {
    lumaSum += 0.299 * pixels[index] + 0.587 * pixels[index + 1] + 0.114 * pixels[index + 2]
  }
  return lumaSum / (pixels.length / 4)
}

/** source 의 region 을 1080×1350 JPEG 파일로 만든다. mirrored 면 좌우를 뒤집어 거울 모습으로 저장한다. */
export function renderPhotoFile(
  source: CanvasImageSource,
  region: Rectangle,
  fileName: string,
  { mirrored = false }: { mirrored?: boolean } = {},
): Promise<File> {
  const canvas = document.createElement('canvas')
  canvas.width = PHOTO_WIDTH
  canvas.height = PHOTO_HEIGHT
  const context = canvas.getContext('2d')
  if (!context) return Promise.reject(new Error('canvas 2d context 를 만들 수 없음'))
  context.imageSmoothingQuality = 'high'
  if (mirrored) {
    context.translate(PHOTO_WIDTH, 0)
    context.scale(-1, 1)
  }
  context.drawImage(source, region.x, region.y, region.width, region.height, 0, 0, PHOTO_WIDTH, PHOTO_HEIGHT)
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(new File([blob], fileName, { type: 'image/jpeg' })) : reject(new Error('JPEG 변환 실패'))),
      'image/jpeg',
      PHOTO_JPEG_QUALITY,
    )
  })
}

export const UploadedPhotoResult = { NORMALIZED: 'NORMALIZED', NOT_FOUND: 'NOT_FOUND', UNSUPPORTED: 'UNSUPPORTED' } as const
export type UploadedPhotoResult = (typeof UploadedPhotoResult)[keyof typeof UploadedPhotoResult]
export type UploadedPhotoNormalization = { result: UploadedPhotoResult; file: File }

/**
 * 업로드한 사진을 가이드와 같은 구도로 잘라 규격 사진으로 만든다.
 * 찾는 대상(얼굴·상반신)이 없으면 NOT_FOUND, 브라우저가 이미지 처리나 인식을 못 하면 UNSUPPORTED (원본을 그대로 쓴다).
 */
export async function normalizeUploadedPhoto(
  file: File,
  outputFileName: string,
  findCropRectangle: (image: ImageBitmap) => Promise<Rectangle | null>,
): Promise<UploadedPhotoNormalization> {
  if (typeof createImageBitmap !== 'function') return { result: UploadedPhotoResult.UNSUPPORTED, file }
  let image: ImageBitmap
  try {
    image = await createImageBitmap(file)
  } catch {
    return { result: UploadedPhotoResult.UNSUPPORTED, file }
  }
  try {
    const crop = await findCropRectangle(image)
    if (!crop) return { result: UploadedPhotoResult.NOT_FOUND, file }
    return { result: UploadedPhotoResult.NORMALIZED, file: await renderPhotoFile(image, crop, outputFileName) }
  } catch {
    return { result: UploadedPhotoResult.UNSUPPORTED, file }
  } finally {
    image.close()
  }
}
