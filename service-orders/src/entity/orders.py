from __future__ import annotations

import typing
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

OrderId = typing.NewType("OrderID", uuid.UUID)

class OrderStatus(str, Enum):
    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

@dataclass(slots=True)
class CreateOrder:
    user_id: str
    products: list
    amount: str

@dataclass(slots=True)
class Order:
    id: OrderId
    status: OrderStatus
    created_at: datetime
