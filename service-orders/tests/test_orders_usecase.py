"""
Тесты для usecase сервиса заказов.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4
from datetime import datetime

from src.usecase.orders.orders_usecase import OrderUseCase
from src.entity.orders import CreateOrder, Order, OrderId, OrderStatus
from src.exceptions import OrderNotFoundError, RepositoryError


@pytest.fixture
def mock_repository():
    return AsyncMock()


@pytest.fixture
def mock_uow():
    uow = MagicMock()
    uow.init = AsyncMock()
    return uow


@pytest.fixture
def mock_repositories(mock_repository):
    repos = MagicMock()
    repos.orders = mock_repository
    repos.outbox = AsyncMock()
    return repos


@pytest.fixture
def sample_order():
    order_id = uuid4()
    return Order(
        id=OrderId(order_id),
        status=OrderStatus.CREATED,
        created_at=datetime.utcnow()
    )


@pytest.mark.asyncio
async def test_create_order_success(mock_repository, mock_uow, mock_repositories, sample_order):
    """
    Тест успешного создания заказа через usecase.
    """

    mock_repository.create_order = AsyncMock(return_value=sample_order)
    mock_repositories.orders = mock_repository
    
    context_manager = AsyncMock()
    context_manager.__aenter__ = AsyncMock(return_value=mock_repositories)
    context_manager.__aexit__ = AsyncMock(return_value=None)
    mock_uow.init = MagicMock(return_value=context_manager)
    
    usecase = OrderUseCase(
        repository=mock_repository,
        uow=mock_uow,
        rabbitmq_client=None
    )
    
    payload = CreateOrder(
        user_id="user_123",
        products=[{"product_id": "prod_001", "quantity": 2}],
        amount="100.50"
    )

    result = await usecase.create_order(payload)

    assert result.id == sample_order.id
    assert result.status == OrderStatus.CREATED
    mock_repository.create_order.assert_called_once()


@pytest.mark.asyncio
async def test_get_order_status_success(mock_repository, mock_uow, mock_repositories, sample_order):
    """
    Тест успешного получения статуса заказа через usecase.
    """

    order_id = sample_order.id
    mock_repository.get_order_by_id = AsyncMock(return_value=sample_order)
    mock_repositories.orders = mock_repository
    
    context_manager = AsyncMock()
    context_manager.__aenter__ = AsyncMock(return_value=mock_repositories)
    context_manager.__aexit__ = AsyncMock(return_value=None)
    mock_uow.init = MagicMock(return_value=context_manager)
    
    usecase = OrderUseCase(
        repository=mock_repository,
        uow=mock_uow,
        rabbitmq_client=None
    )

    result = await usecase.get_order_status(OrderId(order_id))

    assert result.id == sample_order.id
    assert result.status == OrderStatus.CREATED
    mock_repository.get_order_by_id.assert_called_once_with(UUID(str(order_id)))


@pytest.mark.asyncio
async def test_get_order_status_not_found(mock_repository, mock_uow, mock_repositories):
    """
    Тест обработки случая, когда заказ не найден.
    """

    order_id = uuid4()
    mock_repository.get_order_by_id = AsyncMock(side_effect=OrderNotFoundError(order_id=order_id))
    mock_repositories.orders = mock_repository
    
    context_manager = AsyncMock()
    context_manager.__aenter__ = AsyncMock(return_value=mock_repositories)
    context_manager.__aexit__ = AsyncMock(return_value=None)
    mock_uow.init = MagicMock(return_value=context_manager)
    
    usecase = OrderUseCase(
        repository=mock_repository,
        uow=mock_uow,
        rabbitmq_client=None
    )

    with pytest.raises(OrderNotFoundError):
        await usecase.get_order_status(OrderId(order_id))


@pytest.mark.asyncio
async def test_update_order_status_from_event(mock_repository, mock_uow, mock_repositories, sample_order):
    """
    Тест обновления статуса заказа из события.
    """

    order_id = str(sample_order.id)
    updated_order = Order(
        id=sample_order.id,
        status=OrderStatus.COMPLETED,
        created_at=sample_order.created_at
    )
    
    mock_repository.update_order_status = AsyncMock(return_value=updated_order)
    mock_repositories.orders = mock_repository
    
    context_manager = AsyncMock()
    context_manager.__aenter__ = AsyncMock(return_value=mock_repositories)
    context_manager.__aexit__ = AsyncMock(return_value=None)
    mock_uow.init = MagicMock(return_value=context_manager)
    
    usecase = OrderUseCase(
        repository=mock_repository,
        uow=mock_uow,
        rabbitmq_client=None
    )

    result = await usecase.update_order_status_from_event(order_id, "SUCCESS")

    assert result.status == OrderStatus.COMPLETED
    mock_repository.update_order_status.assert_called_once_with(
        UUID(order_id),
        OrderStatus.COMPLETED
    )
