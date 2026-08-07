"""
Rate limiting via SlowAPI.

Uses in-memory storage (SlowAPI's default), not Redis-backed — deliberate,
not an oversight: the Dockerfile runs a single Uvicorn worker process (no
`--workers N`, no gunicorn), so there's no cross-process/cross-worker state
that actually needs reconciling. In-memory storage also means rate limiting
never depends on Redis being reachable, consistent with this codebase's
existing fail-soft philosophy elsewhere (see core/redis_client.py) — a
Redis outage should never be able to lock everyone out of login by making
the rate limiter itself unavailable.

Keyed by client IP (get_remote_address) rather than by user, since the
endpoints that most need protection (login, register) happen before any
user identity exists.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
