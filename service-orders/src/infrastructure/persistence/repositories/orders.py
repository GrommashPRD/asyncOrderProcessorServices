from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from src.entity.orders import CreateOrder, Order, OrderId, OrderStatus
from sqlalchemy.exc import SQLAlchemyError
from src.infrastructure.persistence.db.schema import Order as OrderModel, OrderItem as OrderItemModel
from src.exceptions import RepositoryError, OrderNotFoundError


class OrderRepository:
    """
    Инкапсуляция CRUD-операций.
    """

    def __init__(
            self,
            session: AsyncSession,
            *,
            auto_commit: bool = True
    ) -> None:
        self._session: AsyncSession = session
        self._auto_commit = auto_commit

    async def create_order(self, payload: CreateOrder) -> Order:

        try:
            db_order = OrderModel(
                customer_id=payload.user_id,
                order_amount=payload.amount
            )
            self._session.add(db_order)
            await self._session.flush()

            order_items = []

            for product_item in payload.products:
                if isinstance(product_item, dict):
                    product_id = product_item['product_id']
                    quantity = product_item['quantity']
                else:
                    product_id = product_item.product_id
                    quantity = product_item.quantity

                order_item = OrderItemModel(
                    order_id=db_order.id,
                    product_id=str(product_id),
                    quantity=int(quantity),
                    price="0.00"
                )
                order_items.append(order_item)

            self._session.add_all(order_items)
            
            await self._commit()
            return self._to_entity(db_order)

        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise RepositoryError("Failed to create task") from exc

    async def get_order_by_id(
            self,
            order_id: UUID
    ) -> Order:
        """
        Получить заказ по ID
        """
        try:
            stmt = select(OrderModel).where(OrderModel.id == order_id)
            result = await self._session.execute(stmt)
            db_order = result.scalar_one_or_none()
            
            if db_order is None:
                raise OrderNotFoundError(order_id=order_id)
            
            return self._to_entity(db_order)
        except OrderNotFoundError:
            raise
        except SQLAlchemyError as exc:
            raise RepositoryError("Failed to get order by id") from exc

    async def update_order_status(
        self,
        order_id: UUID,
        status: OrderStatus
    ) -> Order:
        """
        Обновить статус заказа
        """
        try:
            stmt = select(OrderModel).where(OrderModel.id == order_id)
            result = await self._session.execute(stmt)
            db_order = result.scalar_one_or_none()
            
            if db_order is None:
                raise OrderNotFoundError(order_id=order_id)
            
            db_order.status = status
            await self._commit()
            await self._session.refresh(db_order)
            return self._to_entity(db_order)
        except OrderNotFoundError:
            raise
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise RepositoryError("Failed to update order status") from exc

    @staticmethod
    def _to_entity(order: OrderModel) -> Order:
        """
        Преобразование модели ORM в объект entity.
        """
        return Order(
            id=OrderId(order.id),
            status=order.status,
            created_at=order.created_at,
        )


    async def _commit(self) -> None:
        if self._auto_commit:
            await self._session.commit()
        else:
            await self._session.flush()