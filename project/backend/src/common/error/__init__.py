from enum import StrEnum


class ErrorCode(StrEnum):
    UNAUTHORIZED = "UNAUTHORIZED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    EXTERNAL_API_FAILED = "EXTERNAL_API_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NICKNAME_TAKEN = "NICKNAME_TAKEN"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    FACE_NOT_DETECTED = "FACE_NOT_DETECTED"
    INVALID_IMAGE = "INVALID_IMAGE"
    PROFILE_REQUIRED = "PROFILE_REQUIRED"
    PERSONAL_COLOR_REQUIRED = "PERSONAL_COLOR_REQUIRED"
    PRODUCT_NOT_FOUND = "PRODUCT_NOT_FOUND"
    PIN_NOT_FOUND = "PIN_NOT_FOUND"
    WARDROBE_LIMIT_EXCEEDED = "WARDROBE_LIMIT_EXCEEDED"
    FITTING_NOT_FOUND = "FITTING_NOT_FOUND"


HTTP_STATUS_BY_ERROR_CODE: dict[ErrorCode, int] = {
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.EXTERNAL_API_FAILED: 502,
    ErrorCode.INTERNAL_ERROR: 500,
    ErrorCode.NICKNAME_TAKEN: 409,
    ErrorCode.INVALID_CREDENTIALS: 401,
    ErrorCode.FACE_NOT_DETECTED: 422,
    ErrorCode.INVALID_IMAGE: 400,
    ErrorCode.PROFILE_REQUIRED: 409,
    ErrorCode.PERSONAL_COLOR_REQUIRED: 409,
    ErrorCode.PRODUCT_NOT_FOUND: 404,
    ErrorCode.PIN_NOT_FOUND: 404,
    ErrorCode.WARDROBE_LIMIT_EXCEEDED: 409,
    ErrorCode.FITTING_NOT_FOUND: 404,
}


class AppError(Exception):
    """슬라이스는 이 예외만 던진다. 응답 변환은 shared/exception 이 한다."""

    def __init__(self, error_code: ErrorCode, message: str | None = None) -> None:
        self.error_code = error_code
        self.message = message or error_code.value
        super().__init__(self.message)
