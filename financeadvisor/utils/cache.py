"""
Cache and rate-limiting utilities using Redis.

This module provides functions to get a Redis connection, store and retrieve
cached values, and implement a simple per-user rate limit. Redis works as an
extremely fast in-memory database; it supports atomic operations such as counter
increments and has various data types (strings, lists, sets, etc.). Here we use
strings to store serialized results and counters for rate limiting.

Usage example:

>>> from utils.cache import get_or_set_cache
>>> result = get_or_set_cache('metrics:PETR4:1y', lambda: compute_metrics())

This tries to retrieve the key from Redis; if it doesn't exist, it calls
`compute_metrics()` and stores the value with a defined TTL.

Note: To use this module, make sure a Redis server is reachable and that the
REDIS_HOST and REDIS_PORT variables are set in the `.env` file.
"""
import json
import os
import time
from typing import Any, Callable

try:
    import redis  # type: ignore
except Exception:
    redis = None  # type: ignore
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Fallback: if python-dotenv is not available, the environment
    # variables must be set externally.
    pass


_in_memory_store = {}


class InMemoryRedis:
    def get(self, key: str):
        item = _in_memory_store.get(key)
        if not item:
            return None
        value, expiry = item
        if expiry is not None and time.time() > expiry:
            _in_memory_store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: str, ex=None) -> None:
        expiry = time.time() + ex if ex else None
        _in_memory_store[key] = (value, expiry)

    def incr(self, key: str) -> int:
        current = self.get(key)
        try:
            num = int(current) if current is not None else 0
        except Exception:
            num = 0
        num += 1
        self.set(key, str(num))
        return num

    def expire(self, key: str, seconds: int) -> None:
        item = _in_memory_store.get(key)
        if not item:
            return
        value, _ = item
        _in_memory_store[key] = (value, time.time() + seconds)


_in_memory_singleton = InMemoryRedis()


def get_redis_connection():
    """Get a Redis connection, or an in-memory fallback if FAKE_CACHE=1 or redis is missing.

    Returns:
        an object compatible with Redis (get, set, incr, expire).
    """
    if os.getenv("FAKE_CACHE") == "1" or redis is None:
        return _in_memory_singleton
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    return redis.Redis(host=host, port=port, decode_responses=True)


def get_or_set_cache(key: str, func: Callable[[], Any], ttl: int = 86400) -> Any:
    """Get a value from the cache, or compute and store it if absent.

    This pattern is known as *cache aside*: it first tries to read the value
    from the cache; if it doesn't exist, it runs the provided function, stores
    the result with a time-to-live (TTL) and returns the value.

    Args:
        key (str): Redis key.
        func (Callable[[], Any]): function that generates the value if the key
            doesn't exist.
        ttl (int, optional): expiration time in seconds. Default 24h.

    Returns:
        Any: the retrieved or computed value.
    """
    r = get_redis_connection()
    value = r.get(key)
    if value is not None:
        try:
            # Try to deserialize JSON; if it fails, return the string
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    # Value not found; compute and store it
    result = func()
    try:
        serialized = json.dumps(result)
    except (TypeError, ValueError):
        # If not JSON-serializable, store it as a string
        serialized = str(result)
    r.set(key, serialized, ex=ttl)
    return result


def check_rate_limit(user_id: str, limit: int = 5, window: int = 60) -> None:
    """Apply rate limiting to a user's calls.

    Increments a Redis counter keyed by user and time window. If the counter
    exceeds the limit, it raises an exception. The key expires automatically at
    the end of the window to reset the count.

    Args:
        user_id (str): unique user identifier (may be a session ID or IP address).
        limit (int): maximum number of calls allowed in the window.
        window (int): window size in seconds (default 1 minute).

    Raises:
        Exception: if the limit is exceeded.
    """
    r = get_redis_connection()
    current_window = int(time.time() // window)
    key = f"rate:{user_id}:{current_window}"
    count = r.incr(key)
    if count == 1:
        # Set expiration only on the first call of the window
        r.expire(key, window)
    if count > limit:
        raise Exception(
            "You have exceeded the maximum number of allowed requests. Please try again later."
        )
