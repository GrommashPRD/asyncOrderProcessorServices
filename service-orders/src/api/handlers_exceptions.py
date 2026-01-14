"""
Общие обработчики ошибок для API эндпоинтов.

Этот модуль предоставляет функции для преобразования исключений приложения
в HTTP ответы с соответствующими статус-кодами.
"""

from fastapi import HTTPException, status

from src.exceptions import (
    AppError,
    MessagingError,
    RepositoryError,
    TaskCancellationError,
    TaskNotFoundError,
)
from src.logger import logger


def map_app_error_to_http(exc: AppError) -> tuple[int, str]:
    """
    Преобразует исключение приложения в HTTP статус-код и сообщение.

    :param exc: Исключение приложения
    :return: Кортеж (status_code, detail_message)
    """
    if isinstance(exc, TaskNotFoundError):
        return status.HTTP_404_NOT_FOUND, "Task not found"
    if isinstance(exc, TaskCancellationError):
        return status.HTTP_400_BAD_REQUEST, "Task cannot be cancelled"
    if isinstance(exc, MessagingError):
        return status.HTTP_500_INTERNAL_SERVER_ERROR, "Messaging error"
    if isinstance(exc, RepositoryError):
        return status.HTTP_500_INTERNAL_SERVER_ERROR, "Database error"

    # Дефолтная обработка для всех остальных AppError
    return status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error"


def raise_http_from_app_error(operation: str, exc: AppError) -> None:
    """
    Преобразует исключение приложения в HTTPException с логированием.

    :param operation: Название операции для логирования (например, "create_user")
    :param exc: Исключение приложения
    :raises HTTPException: HTTP исключение с соответствующим статус-кодом
    """
    status_code, detail = map_app_error_to_http(exc)

    log_extra = {
        "error_type": type(exc).__name__,
        **getattr(exc, "context", {}),
    }

    message = "Application error in %s: %s"

    if 400 <= status_code < 500:
        logger.warning(message, operation, str(exc), extra=log_extra)
    else:
        # 5xx и все остальные - ошибки сервера
        logger.error(message, operation, str(exc), extra=log_extra)

    raise HTTPException(status_code=status_code, detail=detail) from exc

