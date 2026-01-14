from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from uuid import UUID
from typing import List
from datetime import datetime

from src.infrastructure.persistence.db.schema import OutboxMessage as OutboxMessageModel
from src.exceptions import RepositoryError


class OutboxRepository:
    """
    Репозиторий для работы с outbox таблицей.
    """

    def __init__(self, session: AsyncSession, *, auto_commit: bool = True) -> None:
        self._session: AsyncSession = session
        self._auto_commit = auto_commit

    async def create_message(
        self,
        event_type: str,
        exchange: str,
        routing_key: str,
        payload: str
    ) -> OutboxMessageModel:
        """
        Создать новое сообщение в outbox
        """
        try:
            db_message = OutboxMessageModel(
                event_type=event_type,
                exchange=exchange,
                routing_key=routing_key,
                payload=payload,
                published=False,
                retry_count=0
            )
            self._session.add(db_message)
            await self._commit()
            await self._session.refresh(db_message)
            return db_message
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise RepositoryError("Failed to create outbox message") from exc

    async def get_unpublished_messages(
        self,
        limit: int = 100,
        max_retries: int = 3
    ) -> List[OutboxMessageModel]:
        """
        Получить неопубликованные сообщения
        """
        try:
            stmt = (
                select(OutboxMessageModel)
                .where(
                    OutboxMessageModel.published == False,
                    OutboxMessageModel.retry_count < max_retries
                )
                .order_by(OutboxMessageModel.created_at.asc())
                .limit(limit)
            )
            result = await self._session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as exc:
            raise RepositoryError("Failed to get unpublished messages") from exc

    async def mark_as_published(self, message_id: UUID) -> None:
        """
        Пометить сообщение как опубликованное
        """
        try:
            stmt = select(OutboxMessageModel).where(OutboxMessageModel.id == message_id)
            result = await self._session.execute(stmt)
            db_message = result.scalar_one_or_none()
            
            if db_message is None:
                raise RepositoryError(f"Outbox message not found: {message_id}")
            
            db_message.published = True
            db_message.published_at = datetime.utcnow()
            await self._commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise RepositoryError("Failed to mark message as published") from exc

    async def increment_retry_count(self, message_id: UUID) -> None:
        """
        Увеличить счетчик попыток
        """
        try:
            stmt = select(OutboxMessageModel).where(OutboxMessageModel.id == message_id)
            result = await self._session.execute(stmt)
            db_message = result.scalar_one_or_none()
            
            if db_message is None:
                raise RepositoryError(f"Outbox message not found: {message_id}")
            
            db_message.retry_count += 1
            await self._commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise RepositoryError("Failed to increment retry count") from exc

    async def delete_message(self, message_id: UUID) -> None:
        """
        Удалить сообщение из outbox
        """
        try:
            stmt = select(OutboxMessageModel).where(OutboxMessageModel.id == message_id)
            result = await self._session.execute(stmt)
            db_message = result.scalar_one_or_none()
            
            if db_message is None:
                return
            
            await self._session.delete(db_message)
            await self._commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise RepositoryError("Failed to delete outbox message") from exc

    async def _commit(self) -> None:
        if self._auto_commit:
            await self._session.commit()
        else:
            await self._session.flush()
