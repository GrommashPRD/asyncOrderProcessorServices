import json
import asyncio
from typing import Callable, Optional
import aio_pika
from aio_pika import Exchange, Queue, IncomingMessage
from aio_pika.abc import AbstractConnection, AbstractChannel

from src.settings import settings
from src.exceptions import (
    MessagingError, 
    MessagePublishError, 
    ConnectionError, 
    SubscriptionError,
    MessageConsumeError,
    AppError,
    RepositoryError,
    OrderNotFoundError
)
from src.logger import logger
import aio_pika


class RabbitMQClient:
    """
    Клиент для работы с RabbitMQ в order-service
    """
    
    def __init__(self):
        self._connection: Optional[AbstractConnection] = None
        self._channel: Optional[AbstractChannel] = None
        self._order_created_exchange: Optional[Exchange] = None
        self._order_processed_exchange: Optional[Exchange] = None
        self._dlx: Optional[Exchange] = None
        self._dlq: Optional[Queue] = None
        
    async def connect(self) -> None:
        try:
            connection_url = (
                f"amqp://{settings.RABBIT_USER}:{settings.RABBIT_PASS}"
                f"@{settings.RABBIT_HOST}:{settings.RABBIT_PORT}/{settings.RABBIT_VHOST}"
            )
            self._connection = await aio_pika.connect_robust(connection_url)
            self._channel = await self._connection.channel()

            self._dlx = await self._channel.declare_exchange(
                settings.DLX_NAME,
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )

            self._dlq = await self._channel.declare_queue(
                settings.DLQ_NAME,
                durable=True
            )
            await self._dlq.bind(self._dlx, routing_key="#")
            logger.info(f"Dead Letter Exchange and Queue configured: {settings.DLX_NAME}/{settings.DLQ_NAME}")

            self._order_created_exchange = await self._channel.declare_exchange(
                settings.ORDER_CREATED_EXCHANGE,
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )

            self._order_processed_exchange = await self._channel.declare_exchange(
                settings.ORDER_PROCESSED_EXCHANGE,
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            
            logger.info("Connected to RabbitMQ")
        except (aio_pika.exceptions.AMQPConnectionError, aio_pika.exceptions.AMQPChannelError, OSError) as e:
            logger.error("Failed to connect to RabbitMQ: %s", e)
            raise ConnectionError("Failed to connect to RabbitMQ: %s" % e) from e
    
    async def disconnect(self) -> None:
        if self._channel:
            await self._channel.close()
        if self._connection:
            await self._connection.close()
        logger.info("Disconnected from RabbitMQ")
    
    def _get_retry_count(self, message: IncomingMessage) -> int:
        if message.headers:
            return message.headers.get("x-retry-count", 0)
        return 0
    
    def _increment_retry_count(self, headers: dict) -> int:
        retry_count = headers.get("x-retry-count", 0) + 1
        headers["x-retry-count"] = retry_count
        return retry_count
    
    def _calculate_delay(self, retry_count: int) -> int:
        delay = settings.RETRY_DELAY_BASE_SECONDS * (2 ** retry_count)
        return min(delay, 300)
    
    async def _publish_to_retry_queue(
        self,
        message: IncomingMessage,
        retry_count: int
    ) -> None:
        delay_ms = self._calculate_delay(retry_count) * 1000

        retry_queue_name = f"orders_order_processed_retry_{retry_count}"
        retry_queue = await self._channel.declare_queue(
            retry_queue_name,
            durable=True,
            arguments={
                "x-message-ttl": delay_ms,
                "x-dead-letter-exchange": settings.ORDER_PROCESSED_EXCHANGE,
                "x-dead-letter-routing-key": settings.ORDER_PROCESSED_ROUTING_KEY,
            }
        )

        headers = dict(message.headers) if message.headers else {}
        headers["x-retry-count"] = retry_count

        await self._channel.default_exchange.publish(
            aio_pika.Message(
                message.body,
                headers=headers,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=retry_queue_name
        )
        
        logger.info(
            f"Message sent to retry queue {retry_queue_name} "
            f"(retry {retry_count}/{settings.MAX_RETRY_ATTEMPTS}, delay {delay_ms}ms)"
        )
    
    async def _publish_to_dlq(self, message: IncomingMessage, error: Exception) -> None:
        """
        Опубликовать сообщение в DLQ
        """
        headers = dict(message.headers) if message.headers else {}
        headers["x-original-routing-key"] = message.routing_key or settings.ORDER_PROCESSED_ROUTING_KEY
        headers["x-failure-reason"] = str(error)
        
        await self._dlx.publish(
            aio_pika.Message(
                message.body,
                headers=headers,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=settings.DLQ_NAME
        )
        
        logger.error(
            f"Message sent to Dead Letter Queue {settings.DLQ_NAME}. "
            f"Reason: {error}"
        )
    
    async def publish_order_created(
        self,
        order_id: str,
        user_id: str,
        products: list,
        amount: float,
        created_at: str
    ) -> None:
        """
        Публикация события order.created
        """
        if not self._order_created_exchange:
            raise MessagingError("Not connected to RabbitMQ")
        
        try:
            message_data = {
                "order_id": order_id,
                "user_id": user_id,
                "products": products,
                "amount": float(amount),
                "created_at": created_at
            }
            
            message_body = json.dumps(message_data).encode()
            
            await self._order_created_exchange.publish(
                aio_pika.Message(
                    message_body,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=settings.ORDER_CREATED_ROUTING_KEY
            )

        except (aio_pika.exceptions.AMQPError, OSError) as e:
            logger.error("Failed to publish order.created: %s", e)
            raise MessagePublishError(order_id=order_id, message=str(e)) from e
    
    async def subscribe_to_order_processed(
        self,
        callback: Callable[[dict], None]
    ) -> None:
        """
        Подписка на события order.processed с retry и DLQ
        """
        if not self._channel or not self._order_processed_exchange:
            raise MessagingError("Not connected to RabbitMQ")
        
        try:
            # Создаем основную очередь с настройками DLQ
            queue_name = f"orders_order_processed_queue"
            queue = await self._channel.declare_queue(
                queue_name,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": settings.DLX_NAME,
                    "x-dead-letter-routing-key": settings.DLQ_NAME,
                }
            )

            await queue.bind(
                self._order_processed_exchange,
                routing_key=settings.ORDER_PROCESSED_ROUTING_KEY
            )
            
            async def message_handler(message: IncomingMessage):
                retry_count = self._get_retry_count(message)
                
                try:
                    body = json.loads(message.body.decode())
                    logger.info(
                        f"Received order.processed event (retry {retry_count}): {body}"
                    )

                    if asyncio.iscoroutinefunction(callback):
                        await callback(body)
                    else:
                        callback(body)

                    await message.ack()
                    logger.info(f"Successfully processed order.processed event (retry {retry_count})")
                    
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.error("Error decoding message (retry %s): %s", retry_count, e, exc_info=True)
                    await message.ack()
                    await self._publish_to_dlq(message, e)
                except (AppError, RepositoryError, OrderNotFoundError) as e:
                    logger.error(
                        "Error processing message (retry %s): %s",
                        retry_count, e,
                        exc_info=True
                    )

                    if retry_count >= settings.MAX_RETRY_ATTEMPTS:
                        await message.ack()
                        await self._publish_to_dlq(message, e)
                    else:
                        await message.ack()
                        new_retry_count = self._increment_retry_count(
                            dict(message.headers) if message.headers else {}
                        )
                        await self._publish_to_retry_queue(message, new_retry_count)
                except (TypeError, AttributeError, KeyError, ValueError) as e:
                    logger.error(
                        "Data validation error processing message (retry %s): %s",
                        retry_count, e,
                        exc_info=True
                    )

            await queue.consume(message_handler)
            await asyncio.Future()
            
        except asyncio.CancelledError:
            raise
        except (aio_pika.exceptions.AMQPError, OSError) as e:
            logger.error("Failed to subscribe to order.processed: %s", e)
            raise SubscriptionError("Failed to subscribe to order.processed: %s" % e) from e
