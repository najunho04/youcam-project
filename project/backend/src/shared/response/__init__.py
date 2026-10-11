from fastapi.responses import JSONResponse

from common.dto import ErrorBody, ErrorResponse
from common.error import ErrorCode


def error_response(status_code: int, error_code: ErrorCode, message: str) -> JSONResponse:
    """에러 응답 형태: { "error": { "code", "message" } }"""
    body = ErrorResponse(error=ErrorBody(code=error_code, message=message))
    return JSONResponse(status_code=status_code, content=body.model_dump(by_alias=True, mode="json"))
