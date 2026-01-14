from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


class AppError(Exception):
    """
    Исключение базового уровня приложения.
    """
    def __init__(self, message: str = "", *, context: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.context: Dict[str, Any] = context or {}

    def __str__(self) -> str:
        return self.message or self.__class__.__name__


class RepositoryError(AppError):
    """
    Базовый класс ошибок для persistence/repository слоя.
    """


class UnitOfWorkError(AppError):
    """
    Ошибка для UOW при которой падает транзакция
    """


class MessagingError(AppError):
    """
    Базовый класс ошибок для messaging / RabbitMQ операций.
    """


@dataclass
class ProcessingError(AppError):
    """
    Ошибка при обработке заказа.
    """
    order_id: Any
    message: str = "Failed to process order"
    
    def __post_init__(self) -> None:
        self.context = {"order_id": str(self.order_id)}


@dataclass
class MessageConsumeError(MessagingError):
    """
    Вызывается, когда сообщение не может быть обработано.
    """
    raw_message: Any | None = None
    message: str = "Failed to consume message from the queue"

    def __post_init__(self) -> None:
        if self.raw_message is not None:
            self.context = {"raw_message": str(self.raw_message)}


@dataclass
class MessagePublishError(MessagingError):
    """
    Возникает, когда сообщение не может быть опубликовано в очередь.
    """
    order_id: Any
    message: str = "Failed to publish message to the message queue"

    def __post_init__(self) -> None:
        self.context = {"order_id": str(self.order_id)}


class ConnectionError(MessagingError):
    """
    Ошибка подключения к RabbitMQ.
    """


class SubscriptionError(MessagingError):
    """
    Ошибка подписки на события RabbitMQ.
    """


class DatabaseConnectionError(RepositoryError):
    """
    Ошибка подключения к базе данных.
    """
