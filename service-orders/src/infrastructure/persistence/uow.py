import contextlib
import dataclasses
from collections.abc import AsyncGenerator

from src.exceptions import UnitOfWorkError, RepositoryError, DatabaseConnectionError
from src.infrastructure.persistence.db import Database
from src.infrastructure.persistence.repositories.orders import OrderRepository
from src.infrastructure.persistence.repositories.outbox import OutboxRepository
from sqlalchemy.exc import SQLAlchemyError



@dataclasses.dataclass
class Repository:
    """
    repo доступные для UOW
    """

    orders: OrderRepository
    outbox: OutboxRepository


class UnitOfWork:
    """
    Обработка жизненного цикла для commit/rollback логики.
    """

    def __init__(self, db: Database) -> None:
        self.db: Database = db

    @contextlib.asynccontextmanager
    async def init(self) -> AsyncGenerator[Repository, None]:
        async with self.db.connection() as conn:
            async with conn.begin():
                try:
                    yield Repository(
                        orders=OrderRepository(conn, auto_commit=False),
                        outbox=OutboxRepository(conn, auto_commit=False),
                    )
                except (SQLAlchemyError, DatabaseConnectionError) as exc:
                    await conn.rollback()
                    raise UnitOfWorkError("UnitOfWork transaction failed") from exc
                except RepositoryError as exc:
                    await conn.rollback()
                    raise UnitOfWorkError("UnitOfWork transaction failed") from exc
