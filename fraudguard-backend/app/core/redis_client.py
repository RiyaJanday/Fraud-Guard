"""
Minimal Redis client wrapper, used right now only for the JWT logout
blacklist (a revoked token's `jti` is stored with a TTL matching its
remaining lifetime).

Deliberately fails soft: if Redis is unreachable, blacklist checks log a
warning and return False (fail-open) rather than raising — a missing Redis
instance should degrade "logout revokes instantly" down to "logout relies
on the access token's natural ~30 minute expiry", not take the whole API
down. This means Redis is optional for local development; it becomes a hard
requirement only when rate limiting / WebSocket pub-sub are wired up in
later steps.
"""

from functools import lru_cache
from typing import Optional

import redis

from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()


@lru_cache
def get_redis_client() -> Optional[redis.Redis]:
    """Returns a cached Redis client, or None if Redis can't be reached at all."""
    try:
        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2)
        client.ping()
        return client
    except redis.RedisError as exc:
        logger.warning(
            "Redis unavailable at {} — logout blacklist will fail open "
            "(tokens still expire naturally). Error: {}",
            settings.REDIS_URL,
            exc,
        )
        return None


def blacklist_token(jti: str, expires_in_seconds: int) -> None:
    """Marks a token's jti as revoked until it would have expired anyway."""
    if not jti or expires_in_seconds <= 0:
        return
    client = get_redis_client()
    if client is None:
        return
    try:
        client.setex(f"blacklist:jti:{jti}", expires_in_seconds, "1")
    except redis.RedisError as exc:
        logger.error("Failed to blacklist token jti={}: {}", jti, exc)


def is_token_blacklisted(jti: str) -> bool:
    if not jti:
        return False
    client = get_redis_client()
    if client is None:
        return False  # fail open — see module docstring
    try:
        return client.exists(f"blacklist:jti:{jti}") == 1
    except redis.RedisError as exc:
        logger.error("Failed to check blacklist for jti={}: {}", jti, exc)
        return False
