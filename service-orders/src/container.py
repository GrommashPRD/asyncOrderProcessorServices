"""
Корневой контейнер, который подключает все подконтейнеры.
"""

from dependency_injector import containers, providers

from src.infrastructure.container import InfrastructureContainer
from src.usecase.container import UseCaseContainer


class Container(containers.DeclarativeContainer):

    config = providers.Configuration()
    wiring_config = containers.WiringConfiguration(
        modules=["src.api.handlers.orders.orders_handler"],
    )

    infrastructure = providers.Container(
        InfrastructureContainer,
        config=config,
    )

    usecase = providers.Container(
        UseCaseContainer,
        order_repository=infrastructure.order_repository,
        uow=infrastructure.uow,
        rabbitmq_client=infrastructure.rabbitmq_client,
    )
