from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

OrderId = uuid.UUID


class ProcessingStatus(str, Enum):
    """
    Статусы обработки заказа
    """
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass(slots=True)
class OrderProcessing:
    """
    Entity для обработки заказа
    """
    order_id: OrderId
    status: ProcessingStatus
    error_message: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass(slots=True)
class OrderCreatedEvent:
    """
    Событие создания заказа из RabbitMQ
    """
    order_id: str
    user_id: str
    products: list
    amount: float
    created_at: str


@dataclass(slots=True)
class OrderProcessedEvent:
    """
    Событие обработанного заказа для публикации
    """
    order_id: str
    status: str
    error_message: Optional[str] = None
    processed_at: str = None
