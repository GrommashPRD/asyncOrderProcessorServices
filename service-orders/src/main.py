import asyncio

from contextlib import asynccontextmanager

import fastapi

from src.api.handlers.orders.orders_handler import router
from src.container import Container
from src.settings import settings
from src.logger import logger
from src.usecase.orders.orders_usecase import OrderUseCase
from src.infrastructure.messaging.outbox_publisher import OutboxPublisher
from src.exceptions import AppError, MessagingError, SubscriptionError


def create_container() -> Container:
    container = Container()
    container.config.from_pydantic(settings)

    container.init_resources()
    container.wire(
        modules=[__name__],
        packages=["src.api.handlers"],
    )

    return container


async def start_event_consumer(container: Container):
    try:
        rabbitmq_client = container.infrastructure.rabbitmq_client()

        order_usecase: OrderUseCase = container.usecase.order_usecase()

        async def handle_order_processed(message: dict) -> None:
            """
            Обработчик событий order.processed.
            Исключения пробрасываются для обработки retry механизмом в RabbitMQ клиенте.
            """
            order_id = message.get("order_id")
            status = message.get("status")

            await order_usecase.update_order_status_from_event(
                order_id=order_id,
                status=status
            )

        subscribe_task = asyncio.create_task(
            rabbitmq_client.subscribe_to_order_processed(handle_order_processed)
        )
        
        return subscribe_task
        
    except (MessagingError, SubscriptionError) as e:
        logger.error("Failed to start event consumer: %s", e, exc_info=True)
        raise
    except AppError as e:
        logger.error("Application error starting event consumer: %s", e, exc_info=True)
        raise


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    """
    Управление жизненным циклом приложения
    """
    container = app.container

    rabbitmq_client = container.infrastructure.rabbitmq_client()
    await rabbitmq_client.connect()
    outbox_publisher: OutboxPublisher = container.infrastructure.outbox_publisher()
    await outbox_publisher.start()

    subscribe_task = None
    try:
        subscribe_task = await start_event_consumer(container)
        yield
    finally:
        await outbox_publisher.stop()

        if subscribe_task and not subscribe_task.done():
            subscribe_task.cancel()
            try:
                await subscribe_task
            except asyncio.CancelledError:
                pass

        await rabbitmq_client.disconnect()
        logger.info("Order service stopped")


def create_app() -> fastapi.FastAPI:
    app = fastapi.FastAPI(lifespan=lifespan)
    app.container = create_container()
    app.include_router(router)
    return app


app = create_app()