from uuid import UUID as UUIDType
import datetime
from sqlalchemy import UUID, DateTime, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column
import uuid

from src.entity.processing import ProcessingStatus
from src.infrastructure.persistence.db import Base


class OrderProcessing(Base):
    """Модель для хранения состояния обработки заказа"""
    __tablename__ = "order_processing"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True
    )
    order_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True, index=True
    )
    status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus), nullable=False, default=ProcessingStatus.PENDING
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )
