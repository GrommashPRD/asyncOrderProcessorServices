"""
Тесты для API handlers сервиса заказов.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4
from datetime import datetime
from fastapi import HTTPException

from src.api.handlers.orders.orders_handler import new_order, get_order_status
from src.api.schemas.request_schemas.schemas import CreateNewOrder
from src.entity.orders import Order, OrderId, OrderStatus
from src.exceptions import OrderNotFoundError, OrderCreationError, RepositoryError


@pytest.fixture
def mock_order_usecase():
    return AsyncMock()


@pytest.fixture
def sample_order():
    order_id = uuid4()
    return Order(
        id=OrderId(order_id),
        status=OrderStatus.CREATED,
        created_at=datetime.utcnow()
    )


@pytest.mark.asyncio
async def test_create_order_success(mock_order_usecase, sample_order):
    """
    Тест успешного создания заказа через API.
    """
    mock_order_usecase.create_order.return_value = sample_order
    request_body = CreateNewOrder(
        user_id="user_123",
        products=[{"product_id": "prod_001", "quantity": 2}],
        amount="100.50"
    )

    result = await new_order(request_body, uc=mock_order_usecase)

    assert result.id == sample_order.id
    assert result.status == OrderStatus.CREATED
    assert result.created_at == sample_order.created_at
    mock_order_usecase.create_order.assert_called_once()


@pytest.mark.asyncio
async def test_create_order_creation_error(mock_order_usecase):
    """
    Тест обработки ошибки создания заказа.
    """
    mock_order_usecase.create_order.side_effect = OrderCreationError("Invalid order data")
    request_body = CreateNewOrder(
        user_id="user_123",
        products=[{"product_id": "prod_001", "quantity": 2}],
        amount="100.50"
    )
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await new_order(request_body, uc=mock_order_usecase)
    
    assert exc_info.value.status_code == 400
    assert "Invalid order data" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_order_status_success(mock_order_usecase, sample_order):
    """
    Тест успешного получения статуса заказа.
    """
    order_id = sample_order.id
    mock_order_usecase.get_order_status.return_value = sample_order

    result = await get_order_status(order_id, uc=mock_order_usecase)

    assert result.id == sample_order.id
    assert result.status == OrderStatus.CREATED
    mock_order_usecase.get_order_status.assert_called_once_with(OrderId(order_id))


@pytest.mark.asyncio
async def test_get_order_status_not_found(mock_order_usecase):
    """
    Тест обработки случая, когда заказ не найден.
    """

    order_id = uuid4()
    mock_order_usecase.get_order_status.side_effect = OrderNotFoundError(order_id=order_id)

    with pytest.raises(HTTPException) as exc_info:
        await get_order_status(order_id, uc=mock_order_usecase)
    
    assert exc_info.value.status_code == 404
    assert "Order not found" in str(exc_info.value.detail)
