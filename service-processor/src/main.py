import asyncio
import signal
import sys
from contextlib import asynccontextmanager

from src.container import Container
from src.settings import settings
from src.entity.processing import OrderCreatedEvent
from src.logger import logger
from src.usecase.processing.processing_usecase import ProcessingUseCase
from src.exceptions import AppError, ProcessingError, MessagingError, ConnectionError


class ProcessorService:
    """Сервис обработки заказов"""
    
    def __init__(self, container: Container):
        self.container = container
        self._running = False
        
    async def start(self) -> None:
        self._running = True

        self.container.config.from_pydantic(settings)
        self.container.init_resources()

        db = self.container.infrastructure.db()
        await db.create_database()
        logger.info("Database initialized")

        rabbitmq_client = self.container.infrastructure.rabbitmq_client()
        await rabbitmq_client.connect()
        logger.info("RabbitMQ connected")

        processing_usecase: ProcessingUseCase = self.container.usecase.processing_usecase()

        async def handle_order_created(message: dict) -> None:
            event = OrderCreatedEvent(
                order_id=message.get("order_id"),
                user_id=message.get("user_id"),
                products=message.get("products", []),
                amount=message.get("amount"),
                created_at=message.get("created_at")
            )
            await processing_usecase.process_order(event)
        
        # Подписываемся на события order.created (это запускает бесконечный цикл)
        logger.info("Subscribed to order.created events")
        
        # Запускаем подписку в фоне
        subscribe_task = asyncio.create_task(
            rabbitmq_client.subscribe_to_order_created(handle_order_created)
        )
        
        logger.info("Processor service started. Waiting for messages...")
        
        try:
            await subscribe_task
        except asyncio.CancelledError:
            logger.info("Subscription cancelled")
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            if not subscribe_task.done():
                subscribe_task.cancel()
                try:
                    await subscribe_task
                except asyncio.CancelledError:
                    pass
            await self.stop()
    
    async def stop(self) -> None:
        self._running = False
        rabbitmq_client = self.container.infrastructure.rabbitmq_client()
        await rabbitmq_client.disconnect()
        logger.info("Processor service stopped")


def create_container() -> Container:
    container = Container()
    container.config.from_pydantic(settings)
    return container


async def main():
    container = create_container()
    service = ProcessorService(container)

    def signal_handler(sig, frame):
        logger.info("Received signal, shutting down...")
        asyncio.create_task(service.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await service.start()
    except (ProcessingError, MessagingError, ConnectionError) as e:
        logger.error("Fatal error: %s", e, exc_info=True)
        sys.exit(1)
    except AppError as e:
        logger.error("Application error: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
