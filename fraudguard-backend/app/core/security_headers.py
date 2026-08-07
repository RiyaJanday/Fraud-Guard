"""
Security headers middleware.

A small, dependency-free middleware (no extra package needed — just plain
Starlette) that adds standard defensive headers to every response. None of
these replace real access control (already handled by JWT + RBAC
elsewhere) — they're defense-in-depth against browser-side attack classes
(clickjacking, MIME-sniffing, referrer leakage) that cost nothing to close.

HSTS is intentionally NOT unconditional: it's only added when the request
actually arrived over HTTPS. Render terminates TLS in front of the app (the
app itself sees plain HTTP internally), so we check the X-Forwarded-Proto
header Render sets rather than request.url.scheme, which would always read
"http" from the app's own point of view. Sending HSTS over a plain-HTTP
local dev request would incorrectly tell the browser to force HTTPS for
localhost on every future visit.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Content-Security-Policy is deliberately omitted here: this is a pure
        # JSON API (no HTML/JS ever served from this origin), so a CSP aimed
        # at script/style sources would be meaningless — CSP protects a page
        # that renders content, not a JSON response. The actual frontend
        # (a separate origin, served by Vercel) is where a CSP would matter.

        is_https = (
            request.url.scheme == "https"
            or request.headers.get("x-forwarded-proto") == "https"
        )
        if is_https:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"

        return response
