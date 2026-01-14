"""
Корневой контейнер, который подключает все подконтейнеры.
"""

from dependency_injector import containers, providers

from src.infrastructure.container import InfrastructureContainer
from src.usecase.container import UseCaseContainer


class Container(containers.DeclarativeContainer):

    config = providers.Configuration()

    infrastructure = providers.Container(
        InfrastructureContainer,
        config=config,
    )

    usecase = providers.Container(
        UseCaseContainer,
        processing_repository=infrastructure.processing_repository,
        uow=infrastructure.uow,
        rabbitmq_client=infrastructure.rabbitmq_client,
    )
