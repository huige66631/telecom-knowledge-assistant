from __future__ import annotations


class AppError(Exception):
    """Base application error with an HTTP status code."""

    def __init__(self, message: str, status_code: int = 500, error_code: str = "app_error") -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


class BadRequestError(AppError):
    def __init__(self, message: str, error_code: str = "bad_request") -> None:
        super().__init__(message=message, status_code=400, error_code=error_code)


class ConfigurationError(AppError):
    def __init__(self, message: str, error_code: str = "configuration_error") -> None:
        super().__init__(message=message, status_code=500, error_code=error_code)
