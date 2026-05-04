"""Database connection pool management."""
from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import psycopg

DEFAULT_POOL_SIZE = 10
DEFAULT_MAX_OVERFLOW = 5

_pools: dict[str, psycopg.pool.ConnectionPool] = {}


def get_conninfo(
    *,
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
) -> str:
    return f"host={host} port={port} dbname={dbname} user={user} password={password}"


def get_pool(
    conninfo: str,
    *,
    min_size: int = 2,
    max_size: int = DEFAULT_POOL_SIZE,
) -> psycopg.pool.ConnectionPool:
    """Get or create a connection pool for the given conninfo."""
    import psycopg_pool

    if conninfo not in _pools:
        _pools[conninfo] = psycopg_pool.ConnectionPool(
            conninfo=conninfo,
            min_size=min_size,
            max_size=max_size,
            open=True,
        )
    return _pools[conninfo]


@contextmanager
def get_connection(
    conninfo: str,
    *,
    pool_size: int = DEFAULT_POOL_SIZE,
) -> Generator[psycopg.Connection, None, None]:
    """Get a connection from the pool."""
    pool = get_pool(conninfo, max_size=pool_size)
    with pool.connection() as conn:
        yield conn


def close_all_pools() -> None:
    """Close all connection pools. Call on shutdown."""
    for pool in _pools.values():
        pool.close()
    _pools.clear()
