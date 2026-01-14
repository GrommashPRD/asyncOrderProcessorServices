import json
from uuid import UUID

from src.entity.orders import CreateOrder, Order, OrderId, OrderStatus
from src.infrastructure.persistence.repositories.orders import OrderRepository
from src.infrastructure.persistence.uow import UnitOfWork
from src.settings import settings

class OrderUseCase:
    """
    Координирует операции заказов между репозиториями и уровнем обмена сообщениями.
    """

    def __init__(
            self,
            repository: OrderRepository,
            uow: UnitOfWork,
            rabbitmq_client=None
    ) -> None:
        self._repository = repository
        self._uow = uow
        self._rabbitmq_client = rabbitmq_client

    async def create_order(
            self,
            payload: CreateOrder
    ) -> Order:
        async with self._uow.init() as repositories:
            order = await repositories.orders.create_order(payload)
            
            if payload.products:
                products_list = self._normalize_products(payload.products)
                await self._create_order_created_event(
                    repositories, order, payload, products_list
                )

            return order

    def _normalize_products(self, products) -> list[dict]:
        """
        Преобразует список продуктов в единый формат.
        """
        products_list = []
        for product in products:
            normalized_product = self._normalize_single_product(product)
            products_list.append(normalized_product)
        return products_list

    def _normalize_single_product(self, product) -> dict:
        """
        Преобразует один продукт в словарь с product_id и quantity.
        """
        if isinstance(product, dict):
            return product
        
        if hasattr(product, 'product_id') and hasattr(product, 'quantity'):
            return {
                "product_id": str(product.product_id),
                "quantity": int(product.quantity)
            }
        
        return {
            "product_id": str(product),
            "quantity": 1
        }

    async def _create_order_created_event(
            self,
            repositories,
            order: Order,
            payload: CreateOrder,
            products_list: list[dict]
    ) -> None:
        """
        Создает событие order.created в outbox.
        """
        event_payload = {
            "order_id": str(order.id),
            "user_id": payload.user_id,
            "products": products_list,
            "amount": float(payload.amount),
            "created_at": order.created_at.isoformat()
        }

        await repositories.outbox.create_message(
            event_type="order.created",
            exchange=settings.ORDER_CREATED_EXCHANGE,
            routing_key=settings.ORDER_CREATED_ROUTING_KEY,
            payload=json.dumps(event_payload)
        )

    async def get_order_status(self, order_id: OrderId) -> Order:
        async with self._uow.init() as repositories:
            order_uuid = UUID(str(order_id))
            order = await repositories.orders.get_order_by_id(order_uuid)
            return order

    async def update_order_status_from_event(
        self,
        order_id: str,
        status: str,
    ) -> Order:
        
        try:
            order_uuid = UUID(order_id)
        except ValueError:
            from src.logger import logger
            logger.error("Invalid order_id format: %s", order_id)
            raise ValueError("Invalid order_id format: %s" % order_id)

        status_mapping = {
            "SUCCESS": OrderStatus.COMPLETED,
            "FAILED": OrderStatus.FAILED,
            "PROCESSING": OrderStatus.IN_PROGRESS,
        }
        
        order_status = status_mapping.get(status, OrderStatus.IN_PROGRESS)
        
        async with self._uow.init() as repositories:
            order = await repositories.orders.update_order_status(
                order_uuid,
                order_status
            )
            
            from src.logger import logger
            logger.info(
                f"Updated order {order_id} status to {order_status} "
                f"(from processor status: {status})"
            )
            
            return order
