import random
import uuid
from uuid import UUID
from datetime import datetime

from src.entity.processing import (
    OrderProcessing,
    ProcessingStatus,
    OrderCreatedEvent,
    OrderProcessedEvent
)
from src.infrastructure.persistence.repositories.processing import ProcessingRepository
from src.infrastructure.persistence.uow import UnitOfWork
from src.infrastructure.messaging.rabbitmq_client import RabbitMQClient
from src.settings import settings
from src.logger import logger
from src.exceptions import (
    ProcessingError, 
    RepositoryError, 
    MessagingError, 
    MessagePublishError,
    AppError
)


class ProcessingUseCase:
    """
    UseCase для обработки заказов.
    """

    def __init__(
        self,
        repository: ProcessingRepository,
        uow: UnitOfWork,
        rabbitmq_client: RabbitMQClient
    ) -> None:
        self._repository = repository
        self._uow = uow
        self._rabbitmq_client = rabbitmq_client

    async def process_order(self, event: OrderCreatedEvent) -> None:
        """
        Обработка заказа из события order.created.
        """
        order_id = UUID(event.order_id)
        
        async with self._uow.init() as repositories:
            existing_processing = await repositories.processing.get_by_order_id(order_id)
            
            if existing_processing:
                if existing_processing.status in (ProcessingStatus.SUCCESS, ProcessingStatus.FAILED):
                    return
                elif existing_processing.status == ProcessingStatus.PROCESSING:
                    logger.warning(
                        f"Order {order_id} is already being processed. "
                        f"Possible duplicate message."
                    )
                    return

            if not existing_processing:
                processing = await repositories.processing.create_processing(order_id)
            else:
                processing = existing_processing

            processing = await repositories.processing.update_status(
                order_id,
                ProcessingStatus.PROCESSING
            )
        
        # Симулируем псевдослучайную обработку
        try:
            success = await self._simulate_processing()
            
            async with self._uow.init() as repositories:
                if success:
                    processing = await repositories.processing.update_status(
                        order_id,
                        ProcessingStatus.SUCCESS
                    )
                    logger.info(f"Order {order_id} processed successfully")

                    await self._rabbitmq_client.publish_order_processed(
                        order_id=str(order_id),
                        status="SUCCESS"
                    )
                else:
                    error_message = "Simulated processing failure"
                    processing = await repositories.processing.update_status(
                        order_id,
                        ProcessingStatus.FAILED,
                        error_message=error_message
                    )
                    logger.warning(f"Order {order_id} processing failed: {error_message}")

                    await self._rabbitmq_client.publish_order_processed(
                        order_id=str(order_id),
                        status="FAILED",
                        error_message=error_message
                    )
        except (RepositoryError, MessagingError, MessagePublishError) as e:
            logger.error("Error processing order %s: %s", order_id, e, exc_info=True)
            
            async with self._uow.init() as repositories:
                await repositories.processing.update_status(
                    order_id,
                    ProcessingStatus.FAILED,
                    error_message=str(e)
                )
            
            try:
                await self._rabbitmq_client.publish_order_processed(
                    order_id=str(order_id),
                    status="FAILED",
                    error_message=str(e)
                )
            except MessagingError:
                logger.warning("Failed to publish failure event for order %s", order_id)
            
            raise ProcessingError(message=str(e)) from e


    async def _simulate_processing(self) -> bool:
        """
        Симуляция обработки заказа.
        """

        import asyncio
        await asyncio.sleep(random.uniform(0.5, 2.0))

        success_rate = settings.PROCESSING_SUCCESS_RATE
        return random.random() < success_rate
