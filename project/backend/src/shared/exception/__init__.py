import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from common.error import HTTP_STATUS_BY_ERROR_CODE, AppError, ErrorCode
from shared.response import error_response

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, error: AppError) -> JSONResponse:
        if HTTP_STATUS_BY_ERROR_CODE[error.error_code] >= 500:
            # 외부 API 실패는 응답 메시지가 뭉뚱그려지므로 원인(예: YouCam 에러 코드)을 서버 로그에 남긴다
            logger.warning("%s: %s (cause: %r)", error.error_code, error.message, error.__cause__)
        return error_response(HTTP_STATUS_BY_ERROR_CODE[error.error_code], error.error_code, error.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
        first_error = error.errors()[0] if error.errors() else {}
        message = f"{'.'.join(str(part) for part in first_error.get('loc', []))}: {first_error.get('msg', '')}"
        return error_response(422, ErrorCode.VALIDATION_ERROR, message)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, error: Exception) -> JSONResponse:
        logger.exception("unexpected error", exc_info=error)
        return error_response(500, ErrorCode.INTERNAL_ERROR, "서버 오류")
