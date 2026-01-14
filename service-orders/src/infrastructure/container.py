"""
Контейнер для infrastructure/services уровня.
"""

from dependency_injector import containers, providers

from src.infrastructure.persistence.db import Database
from src.infrastructure.persistence.repositories.orders import OrderRepository
from src.infrastructure.persistence.uow import UnitOfWork
from src.infrastructure.messaging.rabbitmq_client import RabbitMQClient
from src.infrastructure.messaging.outbox_publisher import OutboxPublisher


def get_db_url(
    pg_user: str,
    pg_password: str,
    pg_host: str,
    pg_port: str,
    pg_db: str,
) -> str:
    return f"postgresql+asyncpg://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"


class InfrastructureContainer(containers.DeclarativeContainer):

    config = providers.Configuration()

    db = providers.Singleton(
        Database,
        db_url=providers.Resource(
            get_db_url,
            pg_user=config.DB_USER,
            pg_password=config.DB_PASS,
            pg_host=config.DB_HOST,
            pg_port=config.DB_PORT,
            pg_db=config.DB_NAME,
        ),
    )

    session_factory = providers.Factory(
        lambda db: db.session_factory(),
        db=db,
    )

    order_repository = providers.Factory(
        OrderRepository,
        session=session_factory,
    )


    uow = providers.Singleton(
        UnitOfWork,
        db=db,
    )
    
    rabbitmq_client = providers.Singleton(
        RabbitMQClient,
    )
    
    outbox_publisher = providers.Singleton(
        OutboxPublisher,
        db=db,
        rabbitmq_client=rabbitmq_client,
        batch_size=100,
        poll_interval=5.0,
        max_retries=3,
    )