from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from uuid import UUID

from src.entity.processing import OrderProcessing, ProcessingStatus
from src.infrastructure.persistence.db.schema import OrderProcessing as OrderProcessingModel
from src.exceptions import RepositoryError


class ProcessingRepository:
    """
    Репозиторий для работы с состоянием обработки заказов.
    """

    def __init__(self, session: AsyncSession, *, auto_commit: bool = True) -> None:
        self._session: AsyncSession = session
        self._auto_commit = auto_commit

    async def get_by_order_id(self, order_id: UUID) -> OrderProcessing | None:
        try:
            stmt = select(OrderProcessingModel).where(
                OrderProcessingModel.order_id == order_id
            )
            result = await self._session.execute(stmt)
            db_processing = result.scalar_one_or_none()
            
            if db_processing is None:
                return None
                
            return self._to_entity(db_processing)
        except SQLAlchemyError as exc:
            raise RepositoryError("Failed to get processing by order_id") from exc

    async def create_processing(self, order_id: UUID) -> OrderProcessing:
        try:
            db_processing = OrderProcessingModel(
                order_id=order_id,
                status=ProcessingStatus.PENDING
            )
            self._session.add(db_processing)
            await self._commit()
            await self._session.refresh(db_processing)
            return self._to_entity(db_processing)
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise RepositoryError("Failed to create processing") from exc

    async def update_status(
        self,
        order_id: UUID,
        status: ProcessingStatus,
        error_message: str | None = None
    ) -> OrderProcessing:
        try:
            stmt = select(OrderProcessingModel).where(
                OrderProcessingModel.order_id == order_id
            )
            result = await self._session.execute(stmt)
            db_processing = result.scalar_one_or_none()
            
            if db_processing is None:
                raise RepositoryError(f"Processing not found for order_id: {order_id}")
            
            db_processing.status = status
            db_processing.error_message = error_message
            if status in (ProcessingStatus.SUCCESS, ProcessingStatus.FAILED):
                from datetime import datetime
                db_processing.processed_at = datetime.utcnow()
            
            await self._commit()
            await self._session.refresh(db_processing)
            return self._to_entity(db_processing)
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise RepositoryError("Failed to update processing status") from exc

    @staticmethod
    def _to_entity(processing: OrderProcessingModel) -> OrderProcessing:
        """
        Преобразование модели ORM в объект entity
        """
        return OrderProcessing(
            order_id=processing.order_id,
            status=processing.status,
            error_message=processing.error_message,
            processed_at=processing.processed_at,
            created_at=processing.created_at,
        )

    async def _commit(self) -> None:
        if self._auto_commit:
            await self._session.commit()
        else:
            await self._session.flush()
