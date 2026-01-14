from uuid import UUID as UUIDType
import datetime

from sqlalchemy import UUID, DateTime, Enum, Integer, String, ForeignKey, Numeric, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

import uuid
from src.entity.orders import OrderStatus
from src.infrastructure.persistence.db import Base



class Order(Base):
    __tablename__ = "orders"

    id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True
    )
    customer_id: Mapped[str] = mapped_column(String)
    products: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="order")
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), nullable=False, default=OrderStatus.CREATED
    )
    order_amount: Mapped[str] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[UUIDType] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[str] = mapped_column(String)
    quantity: Mapped[int] = mapped_column(Integer)
    price: Mapped[str] = mapped_column(String)
    order: Mapped["Order"] = relationship("Order", back_populates="products")


class OutboxMessage(Base):
    __tablename__ = "outbox_messages"

    id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(100), nullable=False)
    routing_key: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)  # JSON строка
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    published_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,  # Остаётся TIMESTAMP WITHOUT TIME ZONE
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        index=True
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
