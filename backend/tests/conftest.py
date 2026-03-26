import pytest
from app import cache


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear global cache state between tests to prevent cross-test pollution."""
    cache._store.clear()
    cache._locks.clear()
    yield
    cache._store.clear()
    cache._locks.clear()
