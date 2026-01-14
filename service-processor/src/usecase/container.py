"""
Контейнер для usecase слоя
"""

from dependency_injector import containers, providers

from src.infrastructure.persistence.repositories.processing import ProcessingRepository
from src.infrastructure.persistence.uow import UnitOfWork
from src.infrastructure.messaging.rabbitmq_client import RabbitMQClient
from src.usecase.processing.processing_usecase import ProcessingUseCase


class UseCaseContainer(containers.DeclarativeContainer):

    processing_repository: providers.Dependency[ProcessingRepository] = providers.Dependency()
    uow: providers.Dependency[UnitOfWork] = providers.Dependency()
    rabbitmq_client: providers.Dependency[RabbitMQClient] = providers.Dependency()

    processing_usecase = providers.Factory(
        ProcessingUseCase,
        repository=processing_repository,
        uow=uow,
        rabbitmq_client=rabbitmq_client,
    )
