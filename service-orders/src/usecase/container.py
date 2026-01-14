"""
Контейнер для usecase слоя
"""

from dependency_injector import containers, providers

from src.infrastructure.persistence.repositories.orders import OrderRepository
from src.infrastructure.persistence.uow import UnitOfWork
from src.usecase.orders.orders_usecase import OrderUseCase
from src.infrastructure.messaging.rabbitmq_client import RabbitMQClient


class UseCaseContainer(containers.DeclarativeContainer):

    order_repository: providers.Dependency[OrderRepository] = providers.Dependency()
    uow: providers.Dependency[UnitOfWork] = providers.Dependency()
    rabbitmq_client: providers.Dependency[RabbitMQClient] = providers.Dependency()

    order_usecase = providers.Factory(
        OrderUseCase,
        repository=order_repository,
        uow=uow,
        rabbitmq_client=rabbitmq_client,
    )
