"""
Password hashing, JWT issuance/verification, and the FastAPI dependencies
that protect endpoints (`get_current_user`, `require_role`).

Token design:
  - Access tokens:  signed with SECRET_KEY, short-lived (30 min default),
                     carry `sub` (user id) and `role` for RBAC checks
                     without hitting the DB on every request... except we
                     DO still hit the DB (see get_current_user) to catch
                     deactivated accounts immediately rather than waiting
                     out a stale token. Trade-off documented there.
  - Refresh tokens: signed with a SEPARATE secret (JWT_REFRESH_SECRET_KEY),
                     longer-lived (7 days default). Using a different key
                     means a leaked access token can never be replayed as
                     a refresh token, and vice versa.
  - Password reset tokens: signed with SECRET_KEY, very short-lived
                     (30 min default), `type=password_reset` distinguishes
                     them from access tokens using the same secret.

Every token carries a `jti` (JWT ID). Logout blacklists that jti in Redis
until the token's natural expiry — see app/core/redis_client.py.
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.cookies import ACCESS_COOKIE, CSRF_COOKIE, CSRF_HEADER
from app.core.exceptions import CredentialsException, PermissionDeniedException
from app.core.logging import logger
from app.core.redis_client import is_token_blacklisted
from app.database.session import get_db
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository

settings = get_settings()

# ---------------------------------------------------------------------- #
# Password hashing
# ---------------------------------------------------------------------- #
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------- #
# Token creation
# ---------------------------------------------------------------------- #
class TokenType:
    ACCESS = "access"
    REFRESH = "refresh"
    PASSWORD_RESET = "password_reset"


def _create_token(
    subject: str,
    secret_key: str,
    expires_delta: timedelta,
    token_type: str,
    extra_claims: Optional[dict] = None,
) -> tuple[str, str]:
    """Returns (encoded_token, jti). Shared by every token-creation helper below."""
    now = datetime.now(timezone.utc)
    jti = str(uuid.uuid4())
    payload = {
        "sub": subject,
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": now + expires_delta,
        **(extra_claims or {}),
    }
    token = jwt.encode(payload, secret_key, algorithm=settings.ALGORITHM)
    return token, jti


def create_access_token(user_id: uuid.UUID, role: UserRole) -> str:
    token, _ = _create_token(
        subject=str(user_id),
        secret_key=settings.SECRET_KEY,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type=TokenType.ACCESS,
        extra_claims={"role": role.value},
    )
    return token


def create_refresh_token(user_id: uuid.UUID) -> str:
    token, _ = _create_token(
        subject=str(user_id),
        secret_key=settings.JWT_REFRESH_SECRET_KEY,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type=TokenType.REFRESH,
    )
    return token


def create_password_reset_token(user_id: uuid.UUID) -> str:
    token, _ = _create_token(
        subject=str(user_id),
        secret_key=settings.SECRET_KEY,
        expires_delta=timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
        token_type=TokenType.PASSWORD_RESET,
    )
    return token


# ---------------------------------------------------------------------- #
# Token decoding / verification
# ---------------------------------------------------------------------- #
def decode_token(token: str, secret_key: str, expected_type: str) -> dict:
    """
    Decode + validate a JWT. Raises CredentialsException (never a raw
    JWTError) so callers never need to know about python-jose internals.
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=[settings.ALGORITHM])
    except ExpiredSignatureError:
        raise CredentialsException("Token has expired.")
    except JWTError:
        raise CredentialsException("Could not validate credentials.")

    if payload.get("type") != expected_type:
        raise CredentialsException(f"Expected a {expected_type} token.")

    if is_token_blacklisted(payload.get("jti", "")):
        raise CredentialsException("Token has been revoked.")

    return payload


# ---------------------------------------------------------------------- #
# FastAPI dependencies
#
# HTTPBearer (rather than OAuth2PasswordBearer) is used deliberately: our
# /login endpoint takes a JSON body (email/password), not the OAuth2 form-
# encoded username/password grant. HTTPBearer just extracts whatever's in
# `Authorization: Bearer <token>` and, as a bonus, renders as a simple
# "paste your token" field in Swagger's Authorize dialog rather than a
# username/password form that wouldn't actually match our login route.
#
# auto_error=False: a request can ALSO authenticate purely via the
# access_token httpOnly cookie set by /login (see core/cookies.py), with no
# Authorization header at all — that's how the browser SPA authenticates.
# HTTPBearer must not 401 just because the header is absent; get_current_user
# below is what actually decides whether *any* valid credential was found.
# ---------------------------------------------------------------------- #
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Paste the access_token returned by POST /api/v1/auth/login",
)

_CSRF_PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def verify_csrf(request: Request) -> None:
    """
    Double-submit CSRF check: the csrf_token cookie (readable by JS, set
    alongside the httpOnly auth cookies) must match an X-CSRF-Token header
    the frontend echoes back. Only meaningful — and only ever called — for
    requests authenticating via cookie; see callers.
    """
    cookie_value = request.cookies.get(CSRF_COOKIE)
    header_value = request.headers.get(CSRF_HEADER)
    if not cookie_value or not header_value or not secrets.compare_digest(cookie_value, header_value):
        raise PermissionDeniedException(
            "Missing or invalid CSRF token. Browser sessions must echo the "
            "csrf_token cookie back as an X-CSRF-Token header on this request."
        )


def _resolve_access_token(request: Request, credentials: Optional[HTTPAuthorizationCredentials]) -> str:
    """
    Returns the raw access token string from whichever source is present:
    an `Authorization: Bearer` header takes priority (Swagger, scripts, the
    test suite all use this), falling back to the access_token httpOnly
    cookie (the browser SPA's only mechanism). CSRF is enforced here, not
    earlier, because it only applies to the cookie path — a header-based
    caller has no ambient browser credential for a forged request to abuse.
    """
    if credentials is not None:
        return credentials.credentials

    cookie_token = request.cookies.get(ACCESS_COOKIE)
    if cookie_token:
        if request.method in _CSRF_PROTECTED_METHODS:
            verify_csrf(request)
        return cookie_token

    raise CredentialsException("Not authenticated. Provide a Bearer token or a valid browser session.")


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Resolves the caller's User from the access token (header or cookie —
    see _resolve_access_token).

    Deliberately still queries the database on every request (rather than
    trusting the token's embedded role claim alone) so that deactivating a
    user takes effect immediately, instead of waiting up to
    ACCESS_TOKEN_EXPIRE_MINUTES for their existing token to expire.
    """
    access_token = _resolve_access_token(request, credentials)
    payload = decode_token(access_token, settings.SECRET_KEY, TokenType.ACCESS)

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise CredentialsException("Malformed token subject.")

    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise CredentialsException("User no longer exists.")
    if not user.is_active:
        raise CredentialsException("This account has been deactivated.")

    return user


def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    """Alias kept separate from get_current_user for readability at call sites."""
    return user


def require_role(*allowed_roles: UserRole):
    """
    RBAC dependency factory.

        @router.get("/admin-only", dependencies=[Depends(require_role(UserRole.ADMIN))])

    or, to also get the user object:

        def route(user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST))):
    """

    def _check_role(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            logger.warning(
                "RBAC denied | user={} role={} required={}",
                user.id, user.role.value, [r.value for r in allowed_roles],
            )
            raise PermissionDeniedException(
                f"This action requires one of the following roles: "
                f"{', '.join(r.value for r in allowed_roles)}."
            )
        return user

    return _check_role
