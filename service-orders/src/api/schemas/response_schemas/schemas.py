from datetime import datetime
from pydantic import BaseModel, Field
from src.entity.orders import OrderId, OrderStatus

class OrderResponse(BaseModel):
    id: OrderId
    status: OrderStatus
    created_at: datetime
