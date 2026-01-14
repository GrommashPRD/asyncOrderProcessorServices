"""
Тесты для usecase сервиса обработки заказов.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4
from datetime import datetime

from src.usecase.processing.processing_usecase import ProcessingUseCase
from src.entity.processing import (
    OrderCreatedEvent,
    OrderProcessing,
    ProcessingStatus
)
from src.exceptions import ProcessingError, RepositoryError, MessagingError


@pytest.fixture
def mock_repository():
    """Мок для ProcessingRepository."""
    return AsyncMock()


@pytest.fixture
def mock_uow():
    """Мок для UnitOfWork."""
    uow = MagicMock()
    uow.init = AsyncMock()
    return uow


@pytest.fixture
def mock_rabbitmq_client():
    """Мок для RabbitMQClient."""
    return AsyncMock()


@pytest.fixture
def mock_repositories(mock_repository):
    """Мок для репозиториев из UOW."""
    repos = MagicMock()
    repos.processing = mock_repository
    return repos


@pytest.fixture
def sample_order_created_event():
    """Пример события создания заказа."""
    return OrderCreatedEvent(
        order_id=str(uuid4()),
        user_id="user_123",
        products=[{"product_id": "prod_001", "quantity": 2}],
        amount=100.50,
        created_at=datetime.utcnow().isoformat()
    )


@pytest.mark.asyncio
async def test_process_order_success(
    mock_repository,
    mock_uow,
    mock_rabbitmq_client,
    mock_repositories,
    sample_order_created_event
):
    """Тест успешной обработки заказа."""
    # Arrange
    order_id = UUID(sample_order_created_event.order_id)
    processing = OrderProcessing(
        order_id=order_id,
        status=ProcessingStatus.PROCESSING,
        created_at=datetime.utcnow()
    )
    
    mock_repository.get_by_order_id = AsyncMock(return_value=None)
    mock_repository.create_processing = AsyncMock(return_value=processing)
    mock_repository.update_status = AsyncMock(return_value=processing)
    mock_repositories.processing = mock_repository
    
    context_manager = AsyncMock()
    context_manager.__aenter__ = AsyncMock(return_value=mock_repositories)
    context_manager.__aexit__ = AsyncMock(return_value=None)
    mock_uow.init = MagicMock(return_value=context_manager)
    
    usecase = ProcessingUseCase(
        repository=mock_repository,
        uow=mock_uow,
        rabbitmq_client=mock_rabbitmq_client
    )
    
    # Мокаем симуляцию обработки для успешного результата
    with patch.object(usecase, '_simulate_processing', return_value=True):
        # Act
        await usecase.process_order(sample_order_created_event)
    
    # Assert
    mock_repository.create_processing.assert_called_once_with(order_id)
    mock_rabbitmq_client.publish_order_processed.assert_called_once_with(
        order_id=sample_order_created_event.order_id,
        status="SUCCESS"
    )


@pytest.mark.asyncio
async def test_process_order_idempotency(
    mock_repository,
    mock_uow,
    mock_rabbitmq_client,
    mock_repositories,
    sample_order_created_event
):
    """Тест идемпотентности обработки заказа - заказ уже обработан."""
    # Arrange
    order_id = UUID(sample_order_created_event.order_id)
    existing_processing = OrderProcessing(
        order_id=order_id,
        status=ProcessingStatus.SUCCESS,
        created_at=datetime.utcnow()
    )
    
    mock_repository.get_by_order_id = AsyncMock(return_value=existing_processing)
    mock_repositories.processing = mock_repository
    
    context_manager = AsyncMock()
    context_manager.__aenter__ = AsyncMock(return_value=mock_repositories)
    context_manager.__aexit__ = AsyncMock(return_value=None)
    mock_uow.init = MagicMock(return_value=context_manager)
    
    usecase = ProcessingUseCase(
        repository=mock_repository,
        uow=mock_uow,
        rabbitmq_client=mock_rabbitmq_client
    )
    
    # Act
    await usecase.process_order(sample_order_created_event)
    
    # Assert
    # Не должно быть попыток создать новую обработку или опубликовать событие
    mock_repository.create_processing.assert_not_called()
    mock_rabbitmq_client.publish_order_processed.assert_not_called()


@pytest.mark.asyncio
async def test_process_order_failure(
    mock_repository,
    mock_uow,
    mock_rabbitmq_client,
    mock_repositories,
    sample_order_created_event
):
    """Тест обработки заказа с ошибкой."""
    # Arrange
    order_id = UUID(sample_order_created_event.order_id)
    processing = OrderProcessing(
        order_id=order_id,
        status=ProcessingStatus.PROCESSING,
        created_at=datetime.utcnow()
    )
    
    mock_repository.get_by_order_id = AsyncMock(return_value=None)
    mock_repository.create_processing = AsyncMock(return_value=processing)
    mock_repository.update_status = AsyncMock(return_value=processing)
    mock_repositories.processing = mock_repository
    
    context_manager = AsyncMock()
    context_manager.__aenter__ = AsyncMock(return_value=mock_repositories)
    context_manager.__aexit__ = AsyncMock(return_value=None)
    mock_uow.init = MagicMock(return_value=context_manager)
    
    usecase = ProcessingUseCase(
        repository=mock_repository,
        uow=mock_uow,
        rabbitmq_client=mock_rabbitmq_client
    )
    
    # Мокаем симуляцию обработки для неуспешного результата
    with patch.object(usecase, '_simulate_processing', return_value=False):
        # Act
        await usecase.process_order(sample_order_created_event)
    
    # Assert
    mock_repository.update_status.assert_called()
    # Проверяем, что статус обновлен на FAILED
    failed_calls = [call for call in mock_repository.update_status.call_args_list 
                    if call[0][1] == ProcessingStatus.FAILED]
    assert len(failed_calls) > 0
    
    mock_rabbitmq_client.publish_order_processed.assert_called_once_with(
        order_id=sample_order_created_event.order_id,
        status="FAILED",
        error_message="Simulated processing failure"
    )


@pytest.mark.asyncio
async def test_process_order_repository_error(
    mock_repository,
    mock_uow,
    mock_rabbitmq_client,
    mock_repositories,
    sample_order_created_event
):
    """Тест обработки ошибки репозитория при обработке заказа."""
    # Arrange
    order_id = UUID(sample_order_created_event.order_id)
    
    mock_repository.get_by_order_id = AsyncMock(return_value=None)
    mock_repository.create_processing = AsyncMock(side_effect=RepositoryError("Database error"))
    mock_repositories.processing = mock_repository
    
    context_manager = AsyncMock()
    context_manager.__aenter__ = AsyncMock(return_value=mock_repositories)
    context_manager.__aexit__ = AsyncMock(return_value=None)
    mock_uow.init = MagicMock(return_value=context_manager)
    
    usecase = ProcessingUseCase(
        repository=mock_repository,
        uow=mock_uow,
        rabbitmq_client=mock_rabbitmq_client
    )
    
    # Act & Assert
    with pytest.raises(RepositoryError) as exc_info:
        await usecase.process_order(sample_order_created_event)
    
    assert "Database error" in str(exc_info.value)
