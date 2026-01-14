import asyncio
import json
from typing import Optional

from src.infrastructure.persistence.db import Database
from src.infrastructure.persistence.repositories.outbox import OutboxRepository
from src.infrastructure.messaging.rabbitmq_client import RabbitMQClient
from src.logger import logger
from src.exceptions import (
    MessagingError, 
    MessagePublishError, 
    OutboxPublishError, 
    RepositoryError,
    AppError
)
from sqlalchemy.exc import SQLAlchemyError


class OutboxPublisher:
    """
    Публикатор событий из outbox.
    """

    def __init__(
        self,
        db: Database,
        rabbitmq_client: RabbitMQClient,
        batch_size: int = 100,
        poll_interval: float = 5.0,
        max_retries: int = 3
    ) -> None:
        self._db = db
        self._rabbitmq_client = rabbitmq_client
        self._batch_size = batch_size
        self._poll_interval = poll_interval
        self._max_retries = max_retries
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._running:
            logger.warning("OutboxPublisher is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._publish_loop())
        logger.info("OutboxPublisher started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("OutboxPublisher stopped")

    async def _publish_loop(self) -> None:
        while self._running:
            try:
                await self._publish_batch()
            except (MessagingError, RepositoryError, AppError) as e:
                logger.error("Error in outbox publish loop: %s", e, exc_info=True)
            except SQLAlchemyError as e:
                logger.error("Database error in outbox publish loop: %s", e, exc_info=True)

            try:
                await asyncio.sleep(self._poll_interval)
            except asyncio.CancelledError:
                break

    async def _publish_batch(self) -> None:
        async with self._db.connection() as conn:
            repository = OutboxRepository(conn, auto_commit=False)
            
            try:
                messages = await repository.get_unpublished_messages(
                    limit=self._batch_size,
                    max_retries=self._max_retries
                )
                
                if not messages:
                    return
                
                logger.info(f"Found {len(messages)} unpublished messages in outbox")
                
                published_count = 0
                failed_count = 0
                
                for message in messages:
                    try:
                        await self._publish_message(message)

                        await repository.mark_as_published(message.id)
                        await conn.commit()
                        
                        published_count += 1
                        
                    except (MessagingError, MessagePublishError, OutboxPublishError, ValueError, json.JSONDecodeError) as e:
                        await repository.increment_retry_count(message.id)
                        await conn.commit()
                        
                        failed_count += 1
                        logger.warning(
                            "Failed to publish outbox message %s: %s. Retry count: %s",
                            message.id, e, message.retry_count + 1
                        )

            except (RepositoryError, SQLAlchemyError) as e:
                await conn.rollback()
                logger.error("Error processing outbox batch: %s", e, exc_info=True)
            except AppError as e:
                await conn.rollback()
                logger.error("Application error processing outbox batch: %s", e, exc_info=True)

    async def _publish_message(self, message) -> None:
        try:
            payload = json.loads(message.payload)

            if message.event_type == "order.created":
                await self._rabbitmq_client.publish_order_created(
                    order_id=payload["order_id"],
                    user_id=payload["user_id"],
                    products=payload["products"],
                    amount=payload["amount"],
                    created_at=payload["created_at"]
                )
            else:
                logger.warning(f"Unknown event type: {message.event_type}")
                raise ValueError(f"Unknown event type: {message.event_type}")
                
        except (MessagingError, MessagePublishError, OutboxPublishError) as e:
            logger.error("Error publishing message %s: %s", message.id, e, exc_info=True)
            raise
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error("Error parsing or validating message %s: %s", message.id, e, exc_info=True)
            raise OutboxPublishError("Failed to parse or validate message: %s" % e) from e