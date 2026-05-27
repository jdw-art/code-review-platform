from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """统一的业务错误响应结构。"""

    code: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str | None = None


class DomainError(Exception):
    """业务层可识别异常的基类。"""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class DomainForbiddenError(DomainError):
    """已认证但无权访问时抛出的异常。"""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=403,
            details=details,
        )


class DomainUnauthorizedError(DomainError):
    """缺少认证信息或认证失效时抛出的异常。"""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=401,
            details=details,
        )


class DomainConflictError(DomainError):
    """违反业务约束或资源冲突时抛出的异常。"""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=409,
            details=details,
        )
