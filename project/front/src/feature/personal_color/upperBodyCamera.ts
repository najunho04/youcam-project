// 상반신 촬영: MediaPipe 포즈 인식(PoseLandmarker lite) 로딩 · 프레임 측정 · 업로드 사진을 어깨선 기준으로 맞추기.
import type { NormalizedLandmark, PoseLandmarker } from '@mediapipe/tasks-vision'
import { createWithDelegateFallback, loadVisionFileset, measureBrightness, normalizeUploadedPhoto } from './camera'
import type { UploadedPhotoNormalization } from './camera'
import type { Rectangle } from './photoGuide'
import { cropRectangleAroundShoulders } from './upperBodyGuide'
import type { BodyLandmark, UpperBodyMeasurement } from './upperBodyGuide'

const POSE_LANDMARKER_MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task'
/** 여러 명이 나왔는지 알아야 해서 2명까지 찾는다. */
const MAXIMUM_POSE_COUNT = 2
const MINIMUM_POSE_CONFIDENCE = 0.5
const MINIMUM_UPLOAD_SHOULDER_VISIBILITY = 0.5
export const UPPER_BODY_FILE_NAME = 'upper-body.jpg'

// BlazePose 랜드마크 번호: 코 0 · 왼귀 7 · 오른귀 8 · 왼어깨 11 · 오른어깨 12
const NOSE_INDEX = 0
const LEFT_EAR_INDEX = 7
const RIGHT_EAR_INDEX = 8
const LEFT_SHOULDER_INDEX = 11
const RIGHT_SHOULDER_INDEX = 12

type RunningMode = 'VIDEO' | 'IMAGE'

const landmarkerPromises: Partial<Record<RunningMode, Promise<PoseLandmarker>>> = {}

/** 실행 모드별 포즈 인식기를 한 번만 만든다. 실패하면 다음 호출에서 다시 시도한다. */
export function loadPoseLandmarker(runningMode: RunningMode): Promise<PoseLandmarker> {
  const cachedPromise = landmarkerPromises[runningMode]
  if (cachedPromise) return cachedPromise
  const landmarkerPromise = (async () => {
    const [{ PoseLandmarker }, visionFileset] = await Promise.all([import('@mediapipe/tasks-vision'), loadVisionFileset()])
    return createWithDelegateFallback((delegate) =>
      PoseLandmarker.createFromOptions(visionFileset, {
        baseOptions: { modelAssetPath: POSE_LANDMARKER_MODEL_URL, delegate },
        runningMode,
        numPoses: MAXIMUM_POSE_COUNT,
        minPoseDetectionConfidence: MINIMUM_POSE_CONFIDENCE,
        minPosePresenceConfidence: MINIMUM_POSE_CONFIDENCE,
      }),
    )
  })()
  landmarkerPromises[runningMode] = landmarkerPromise
  landmarkerPromise.catch(() => delete landmarkerPromises[runningMode])
  return landmarkerPromise
}

/** 어깨 폭이 가장 넓은(가장 앞에 있는) 사람. */
function closestPose(poses: NormalizedLandmark[][]): NormalizedLandmark[] | undefined {
  const shoulderWidth = (pose: NormalizedLandmark[]) =>
    Math.abs(pose[LEFT_SHOULDER_INDEX].x - pose[RIGHT_SHOULDER_INDEX].x)
  return poses
    .filter((pose) => pose.length > RIGHT_SHOULDER_INDEX)
    .sort((first, second) => shoulderWidth(second) - shoulderWidth(first))[0]
}

/** 비디오 한 프레임에서 상반신을 찾아 crop 비율 좌표로 잰다. 사람이 없으면 null. */
export function measureUpperBodyFrame(
  landmarker: PoseLandmarker,
  video: HTMLVideoElement,
  crop: Rectangle,
  timestamp: number,
): UpperBodyMeasurement | null {
  const { landmarks: poses } = landmarker.detectForVideo(video, timestamp)
  const pose = closestPose(poses)
  if (!pose) return null

  const frameWidth = video.videoWidth
  const frameHeight = video.videoHeight
  // 랜드마크는 프레임 비율이라 crop 비율로 옮긴다
  const toCropLandmark = (landmarkIndex: number): BodyLandmark => ({
    x: (pose[landmarkIndex].x * frameWidth - crop.x) / crop.width,
    y: (pose[landmarkIndex].y * frameHeight - crop.y) / crop.height,
    visibility: pose[landmarkIndex].visibility,
  })
  // 밝기는 얼굴(양 귀 사이, 코 중심)에서만 잰다. 옷·머리 색이 어두워도 조명이 어둡다고 보지 않게 한다.
  const noseX = pose[NOSE_INDEX].x * frameWidth
  const noseY = pose[NOSE_INDEX].y * frameHeight
  const faceHalfSize = (Math.abs(pose[LEFT_EAR_INDEX].x - pose[RIGHT_EAR_INDEX].x) * frameWidth) / 2
  const regionLeft = Math.max(0, noseX - faceHalfSize)
  const regionRight = Math.min(frameWidth, noseX + faceHalfSize)
  const regionTop = Math.max(0, noseY - faceHalfSize)
  const regionBottom = Math.min(frameHeight, noseY + faceHalfSize)
  return {
    personCount: poses.length,
    nose: toCropLandmark(NOSE_INDEX),
    leftShoulder: toCropLandmark(LEFT_SHOULDER_INDEX),
    rightShoulder: toCropLandmark(RIGHT_SHOULDER_INDEX),
    brightness: measureBrightness(video, {
      x: regionLeft,
      y: regionTop,
      width: regionRight - regionLeft,
      height: regionBottom - regionTop,
    }),
  }
}

/** 업로드한 사진을 가장 앞 사람의 어깨선 기준으로 잘라 규격 사진으로 만든다. */
export function normalizeUploadedUpperBody(file: File): Promise<UploadedPhotoNormalization> {
  return normalizeUploadedPhoto(file, UPPER_BODY_FILE_NAME, async (image) => {
    const landmarker = await loadPoseLandmarker('IMAGE')
    const pose = closestPose(landmarker.detect(image).landmarks)
    if (!pose) return null
    const leftShoulder = pose[LEFT_SHOULDER_INDEX]
    const rightShoulder = pose[RIGHT_SHOULDER_INDEX]
    if (Math.min(leftShoulder.visibility, rightShoulder.visibility) < MINIMUM_UPLOAD_SHOULDER_VISIBILITY) return null
    return cropRectangleAroundShoulders(image.width, image.height, {
      left: { x: leftShoulder.x * image.width, y: leftShoulder.y * image.height },
      right: { x: rightShoulder.x * image.width, y: rightShoulder.y * image.height },
    })
  })
}
