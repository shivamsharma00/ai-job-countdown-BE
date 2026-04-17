"""PostgreSQL connection pool via asyncpg.

The pool is initialized on app startup and closed on shutdown.
All other modules should call get_pool() to acquire a connection.

Railway sets DATABASE_URL as:
  postgresql://user:password@host:port/dbname
"""

import logging
import os

import asyncpg

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    """Create the connection pool. Called once at app startup."""
    global _pool
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.warning("DATABASE_URL not set — database features will be unavailable")
        return
    # asyncpg expects 'postgresql://' not 'postgres://' (Railway sometimes uses the latter)
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    _pool = await asyncpg.create_pool(
        database_url,
        min_size=1,
        max_size=10,
        command_timeout=30,
    )
    logger.info("Database pool created (min=1, max=10)")


async def ensure_task_cache_table() -> None:
    """Create task_suggestions_cache table if it does not exist."""
    if _pool is None:
        return
    try:
        await _pool.execute("""
            CREATE TABLE IF NOT EXISTS task_suggestions_cache (
                role_normalized TEXT NOT NULL,
                company_size    TEXT NOT NULL,
                tasks           JSONB NOT NULL,
                created_at      TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (role_normalized, company_size)
            )
        """)
        logger.info("task_suggestions_cache table ready")
    except Exception as e:
        logger.warning("Could not create task_suggestions_cache: %s", e)


async def close_pool() -> None:
    """Close the connection pool. Called once at app shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed")


def get_pool() -> asyncpg.Pool:
    """Return the active pool. Raises RuntimeError if not initialised."""
    if _pool is None:
        raise RuntimeError("Database pool is not initialised")
    return _pool