import peewee
import quart

from contextlib import contextmanager
from playhouse import pool
from typing import Optional, Iterable, Union

from bot.constants import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_MAX_CONNECTIONS,
    POSTGRES_CONNECTION_TIMEOUT_SECS,
)

_db: Optional[pool.PooledPostgresqlExtDatabase] = None


def get_db_instance() -> pool.PooledPostgresqlExtDatabase:
    global _db
    if _db is None:
        _db = pool.PooledPostgresqlExtDatabase(
            POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            # If the number of open connections exceeds max_connections, a ValueError will be raised.
            max_connections=POSTGRES_MAX_CONNECTIONS,
            stale_timeout=POSTGRES_CONNECTION_TIMEOUT_SECS,  # 5 minutes.
        )
    return _db


@contextmanager
def atomic() -> Iterable[None]:
    """
    Context manager/decorator for executing multiple SQL statements inside a single transaction.
    https://docs.peewee-orm.com/en/3.4.0/peewee/transactions.html
    """
    with get_db_instance().atomic():
        yield


def execute_sql(sql: str, params: Optional[Iterable[Union[str, int]]] = None):
    """
    Execute a raw SQL statement.
    https://docs.peewee-orm.com/en/latest/peewee/api.html#Database.execute_sql
    """
    return get_db_instance().execute_sql(sql, params=params)


def register_request_handlers(app: quart.Quart) -> None:
    """
    Register handlers for opening and closing DB connections for each request.
    This must be called only once, when the ASGI app starts.
    """

    def connect_db() -> None:
        db = get_db_instance()
        if db.is_closed():
            db.connect()

    def close_db(exc: Optional[BaseException]) -> None:
        db = get_db_instance()
        if not db.is_closed():
            db.close()

    app.before_request(connect_db)
    app.teardown_request(close_db)  # type: ignore [arg-type]