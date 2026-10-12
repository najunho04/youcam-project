"""YouCam API 클라이언트. 슬라이스는 get_youcam_client() 의존성으로만 접근한다.

참고: https://docs.perfectcorp.com/reference/ai_skin_tone_analysis , https://docs.perfectcorp.com/reference/ai_clothes
- 입력은 URL 로 전달 (src_file_url / ref_file_url). File API 업로드 단계는 쓰지 않는다.
- 작업은 비동기: POST /s2s/v2.0/task/{feature} → task_id → GET 으로 폴링 (running / success / error).
- 폴링하지 않으면 타임아웃돼도 과금된다. 시작한 작업은 반드시 끝까지 폴링한다.
"""
import time
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from typing import Protocol

import httpx

from common.error import AppError, ErrorCode
from shared.config import YouCamMode, get_settings

SKIN_TONE_FEATURE = "skin-tone-analysis"
CLOTH_FEATURE = "cloth-v4"
# 얼굴 인식 실패로 보는 코드 (error_face* 접두 코드 외). 공식 스펙 ai_skin_tone_analysis.yaml 기준
FACE_ERROR_CODES = {"error_no_face", "error_below_min_image_size"}


class YouCamTaskStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


@dataclass(frozen=True)
class SkinToneResult:
    skin_color_hex: str  # 예: "#E0B89A"


@dataclass(frozen=True)
class ClothFittingTask:
    status: YouCamTaskStatus
    result_image_url: str | None  # SUCCESS 일 때만. YouCam 임시 URL 이므로 받아서 Storage 에 저장할 것
    error_code: str | None


class YouCamClient(Protocol):
    def analyze_skin_tone(self, image_url: str) -> SkinToneResult:
        """작업 생성 + 완료까지 폴링 (동기). 얼굴 인식 실패 → FACE_NOT_DETECTED, 그 외 → EXTERNAL_API_FAILED."""
        ...

    def start_cloth_fitting(self, user_image_url: str, garment_image_url: str) -> str:
        """작업 생성만. task_id 반환."""
        ...

    def get_cloth_fitting(self, task_id: str) -> ClothFittingTask: ...

    def wait_cloth_fitting(self, task_id: str) -> ClothFittingTask:
        """완료(SUCCESS/ERROR)까지 폴링. 백그라운드 작업에서 쓴다."""
        ...


class LiveYouCamClient:
    def __init__(self, base_url: str, api_key: str, poll_interval_seconds: float, poll_timeout_seconds: float) -> None:
        self._http = httpx.Client(
            base_url=base_url, headers={"Authorization": f"Bearer {api_key}"}, timeout=30.0
        )
        self._poll_interval_seconds = poll_interval_seconds
        self._poll_timeout_seconds = poll_timeout_seconds

    def _create_task(self, feature: str, body: dict) -> str:
        try:
            response = self._http.post(f"/s2s/v2.0/task/{feature}", json=body)
            response.raise_for_status()
            return response.json()["data"]["task_id"]
        except (httpx.HTTPError, KeyError, ValueError) as error:
            raise AppError(ErrorCode.EXTERNAL_API_FAILED, "YouCam 작업 생성 실패") from error

    def _get_task(self, feature: str, task_id: str) -> dict:
        try:
            response = self._http.get(f"/s2s/v2.0/task/{feature}/{task_id}")
            response.raise_for_status()
            return response.json()["data"]
        except (httpx.HTTPError, KeyError, ValueError) as error:
            raise AppError(ErrorCode.EXTERNAL_API_FAILED, "YouCam 작업 조회 실패") from error

    def _wait_task(self, feature: str, task_id: str) -> dict:
        deadline = time.monotonic() + self._poll_timeout_seconds
        while True:
            data = self._get_task(feature, task_id)
            if data.get("task_status") != YouCamTaskStatus.RUNNING:
                return data
            if time.monotonic() > deadline:
                raise AppError(ErrorCode.EXTERNAL_API_FAILED, "YouCam 응답 시간 초과")
            time.sleep(self._poll_interval_seconds)

    def analyze_skin_tone(self, image_url: str) -> SkinToneResult:
        task_id = self._create_task(SKIN_TONE_FEATURE, {"src_file_url": image_url})
        data = self._wait_task(SKIN_TONE_FEATURE, task_id)
        if data.get("task_status") == YouCamTaskStatus.SUCCESS:
            try:
                return SkinToneResult(skin_color_hex=data["results"]["color"]["skin_color"])
            except (KeyError, TypeError) as error:
                raise AppError(ErrorCode.EXTERNAL_API_FAILED, "YouCam 응답 형식 오류") from error
        error_code = str(data.get("error") or data.get("error_code") or "")
        if error_code.startswith("error_face") or error_code in FACE_ERROR_CODES:
            raise AppError(ErrorCode.FACE_NOT_DETECTED, error_code)
        raise AppError(ErrorCode.EXTERNAL_API_FAILED, error_code or "YouCam 분석 실패")

    def start_cloth_fitting(self, user_image_url: str, garment_image_url: str) -> str:
        return self._create_task(
            CLOTH_FEATURE,
            {"src_file_url": user_image_url, "ref_file_url": garment_image_url, "garment_category": "auto"},
        )

    def _to_cloth_task(self, data: dict) -> ClothFittingTask:
        status = YouCamTaskStatus(data.get("task_status", YouCamTaskStatus.ERROR))
        result_url = (data.get("results") or {}).get("url") if status == YouCamTaskStatus.SUCCESS else None
        error_code = None if status != YouCamTaskStatus.ERROR else str(data.get("error") or data.get("error_code") or "")
        return ClothFittingTask(status=status, result_image_url=result_url, error_code=error_code)

    def get_cloth_fitting(self, task_id: str) -> ClothFittingTask:
        return self._to_cloth_task(self._get_task(CLOTH_FEATURE, task_id))

    def wait_cloth_fitting(self, task_id: str) -> ClothFittingTask:
        return self._to_cloth_task(self._wait_task(CLOTH_FEATURE, task_id))


class MockYouCamClient:
    """크레딧 없이 개발·테스트. 동작을 바꾸려면 속성을 덮어쓴다 (테스트에서 사용)."""

    def __init__(self) -> None:
        self.skin_color_hex = "#E0B89A"
        self.face_detected = True
        self.cloth_fitting_succeeds = True
        self._garment_url_by_task_id: dict[str, str] = {}

    def analyze_skin_tone(self, image_url: str) -> SkinToneResult:
        if not self.face_detected:
            raise AppError(ErrorCode.FACE_NOT_DETECTED, "error_face_position_invalid")
        return SkinToneResult(skin_color_hex=self.skin_color_hex)

    def start_cloth_fitting(self, user_image_url: str, garment_image_url: str) -> str:
        task_id = f"mock-task-{len(self._garment_url_by_task_id) + 1}"
        self._garment_url_by_task_id[task_id] = garment_image_url
        return task_id

    def get_cloth_fitting(self, task_id: str) -> ClothFittingTask:
        if not self.cloth_fitting_succeeds:
            return ClothFittingTask(status=YouCamTaskStatus.ERROR, result_image_url=None, error_code="mock_error")
        # 결과 이미지 대신 상품 이미지를 돌려준다
        return ClothFittingTask(
            status=YouCamTaskStatus.SUCCESS, result_image_url=self._garment_url_by_task_id[task_id], error_code=None
        )

    def wait_cloth_fitting(self, task_id: str) -> ClothFittingTask:
        return self.get_cloth_fitting(task_id)


@lru_cache
def get_youcam_client() -> YouCamClient:
    settings = get_settings()
    if settings.youcam_mode == YouCamMode.MOCK:
        return MockYouCamClient()
    return LiveYouCamClient(
        settings.youcam_base_url,
        settings.youcam_api_key,
        settings.youcam_poll_interval_seconds,
        settings.youcam_poll_timeout_seconds,
    )
