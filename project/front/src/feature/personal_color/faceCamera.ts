// 얼굴 촬영: MediaPipe 얼굴 인식(BlazeFace) 로딩 · 프레임 측정 · 업로드 사진을 얼굴 기준으로 맞추기.
import type { FaceDetector } from '@mediapipe/tasks-vision'
import { createWithDelegateFallback, loadVisionFileset, measureBrightness, normalizeUploadedPhoto } from './camera'
import type { UploadedPhotoNormalization } from './camera'
import { cropRectangleAroundFace } from './faceGuide'
import type { FaceMeasurement } from './faceGuide'
import type { Rectangle } from './photoGuide'

const FACE_DETECTOR_MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite'
const MINIMUM_DETECTION_CONFIDENCE = 0.6
export const SELFIE_FILE_NAME = 'selfie.jpg'

// BlazeFace 키포인트 순서: 오른눈 · 왼눈 · 코끝 · 입 · 오른귀 · 왼귀
const RIGHT_EYE_INDEX = 0
const LEFT_EYE_INDEX = 1
const NOSE_INDEX = 2

type RunningMode = 'VIDEO' | 'IMAGE'

const detectorPromises: Partial<Record<RunningMode, Promise<FaceDetector>>> = {}

/** 실행 모드별 얼굴 인식기를 한 번만 만든다. 실패하면 다음 호출에서 다시 시도한다. */
export function loadFaceDetector(runningMode: RunningMode): Promise<FaceDetector> {
  const cachedPromise = detectorPromises[runningMode]
  if (cachedPromise) return cachedPromise
  const detectorPromise = (async () => {
    const [{ FaceDetector }, visionFileset] = await Promise.all([import('@mediapipe/tasks-vision'), loadVisionFileset()])
    return createWithDelegateFallback((delegate) =>
      FaceDetector.createFromOptions(visionFileset, {
        baseOptions: { modelAssetPath: FACE_DETECTOR_MODEL_URL, delegate },
        runningMode,
        minDetectionConfidence: MINIMUM_DETECTION_CONFIDENCE,
      }),
    )
  })()
  detectorPromises[runningMode] = detectorPromise
  detectorPromise.catch(() => delete detectorPromises[runningMode])
  return detectorPromise
}

/** 비디오 한 프레임에서 얼굴을 찾아 crop 비율 좌표로 잰다. 얼굴이 없으면 null. */
export function measureFaceFrame(
  detector: FaceDetector,
  video: HTMLVideoElement,
  crop: Rectangle,
  timestamp: number,
): FaceMeasurement | null {
  const { detections } = detector.detectForVideo(video, timestamp)
  const largestDetection = detections
    .filter((detection) => detection.boundingBox)
    .sort((first, second) => (second.boundingBox?.width ?? 0) - (first.boundingBox?.width ?? 0))[0]
  const boundingBox = largestDetection?.boundingBox
  if (!largestDetection || !boundingBox || largestDetection.keypoints.length <= NOSE_INDEX) return null

  const frameWidth = video.videoWidth
  const frameHeight = video.videoHeight
  // 키포인트는 프레임 비율, 박스는 프레임 px 이라 둘 다 crop 비율로 옮긴다
  const toCropPoint = (keypointIndex: number) => ({
    x: (largestDetection.keypoints[keypointIndex].x * frameWidth - crop.x) / crop.width,
    y: (largestDetection.keypoints[keypointIndex].y * frameHeight - crop.y) / crop.height,
  })
  return {
    faceCount: detections.length,
    faceBox: {
      x: (boundingBox.originX - crop.x) / crop.width,
      y: (boundingBox.originY - crop.y) / crop.height,
      width: boundingBox.width / crop.width,
      height: boundingBox.height / crop.height,
    },
    leftEye: toCropPoint(LEFT_EYE_INDEX),
    rightEye: toCropPoint(RIGHT_EYE_INDEX),
    nose: toCropPoint(NOSE_INDEX),
    brightness: measureBrightness(video, {
      x: boundingBox.originX,
      y: boundingBox.originY,
      width: boundingBox.width,
      height: boundingBox.height,
    }),
  }
}

/** 업로드한 사진을 가장 큰 얼굴 기준으로 잘라 규격 사진으로 만든다. */
export function normalizeUploadedSelfie(file: File): Promise<UploadedPhotoNormalization> {
  return normalizeUploadedPhoto(file, SELFIE_FILE_NAME, async (image) => {
    const detector = await loadFaceDetector('IMAGE')
    const largestFaceBox = detector
      .detect(image)
      .detections.map((detection) => detection.boundingBox)
      .filter((boundingBox) => boundingBox !== undefined)
      .sort((first, second) => second.width - first.width)[0]
    if (!largestFaceBox) return null
    return cropRectangleAroundFace(image.width, image.height, {
      x: largestFaceBox.originX,
      y: largestFaceBox.originY,
      width: largestFaceBox.width,
      height: largestFaceBox.height,
    })
  })
}
