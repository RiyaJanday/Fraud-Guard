"""
httpOnly cookie helpers for browser-based auth.

Design: the JSON response bodies from /login and /refresh still include
access_token/refresh_token exactly as before — this keeps Swagger,
seed_demo_data.py, and the existing test suite (all of which extract the
token from the body and send it back via `Authorization: Bearer ...`)
working completely unchanged. In ADDITION to the body, the same tokens are
set as httpOnly cookies; the browser SPA (see frontend lib/api.js) is the
one thing that changed to rely on the cookies instead of ever persisting a
token in localStorage/JS.

This is a deliberate, honestly-described partial mitigation, not a silver
bullet: a sufficiently active XSS payload that hooks fetch/XMLHttpRequest
at the exact moment of login could still observe the response body. What
it concretely closes is the much larger, much more common exposure: a
token sitting in localStorage for the entire session, readable by any
injected script at any later point — including long after the original
XSS payload that planted it is gone.

CSRF: cross-origin cookies (Vercel frontend, Render backend are different
registrable domains) require SameSite=None, which removes the CSRF
protection SameSite=Lax/Strict would otherwise give for free. We
compensate with the standard double-submit cookie pattern: a second,
NON-httpOnly `csrf_token` cookie is set alongside the auth cookies; the
frontend reads it and echoes it back as an X-CSRF-Token header on every
mutating request. See core/security.py for where the header is checked
against the cookie — but only for requests actually authenticating via
cookie; a request authenticating via `Authorization: Bearer` (Swagger,
scripts, tests) has no ambient browser credential for a forged cross-site
request to exploit in the first place, so it's exempt.
"""

from fastapi import Response

from app.core.config import get_settings

settings = get_settings()

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "x-csrf-token"


def _cookie_kwargs() -> dict:
    """
    SameSite/Secure are environment-aware: production (Vercel <-> Render)
    is genuinely cross-origin and needs SameSite=None + Secure=True
    (browsers refuse to even set a SameSite=None cookie without Secure).
    Local dev serves frontend and backend both from `localhost` — different
    ports only, which the SameSite spec treats as same-site — so Lax +
    non-Secure works there without requiring HTTPS locally.
    """
    if settings.ENVIRONMENT == "production":
        return {"secure": True, "samesite": "none"}
    return {"secure": False, "samesite": "lax"}


def set_auth_cookies(response: Response, access_token: str, refresh_token: str, csrf_token: str) -> None:
    common = _cookie_kwargs()
    response.set_cookie(
        ACCESS_COOKIE, access_token, httponly=True, path="/",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, **common,
    )
    # Scoped to /api/v1/auth only — the refresh token never needs to be sent
    # on every single API request, just the handful of auth endpoints that
    # actually use it (refresh, logout).
    response.set_cookie(
        REFRESH_COOKIE, refresh_token, httponly=True, path="/api/v1/auth",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60, **common,
    )
    # Deliberately NOT httponly — the frontend must be able to read this one
    # to echo it back as a header; that round-trip IS the CSRF defense.
    response.set_cookie(
        CSRF_COOKIE, csrf_token, httponly=False, path="/",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60, **common,
    )


def clear_auth_cookies(response: Response) -> None:
    common = _cookie_kwargs()
    response.delete_cookie(ACCESS_COOKIE, path="/", **common)
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth", **common)
    response.delete_cookie(CSRF_COOKIE, path="/", **common)
