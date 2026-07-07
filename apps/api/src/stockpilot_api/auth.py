"""Optional Supabase JWT verification.

The agent endpoints attribute runs to a user for the ``agent_runs`` audit table.
When ``SUPABASE_JWT_SECRET`` is configured we verify the bearer token and extract
the user id (``sub``); otherwise we run anonymously (local dev). Enforcement can
be turned on with ``STOCKPILOT_REQUIRE_AUTH=1``.

Verification is HS256 against the project's JWT secret — the standard Supabase
access-token scheme.
"""

from __future__ import annotations

import logging
import os

from fastapi import Header, HTTPException

logger = logging.getLogger(__name__)


def _require_auth() -> bool:
    return os.environ.get("STOCKPILOT_REQUIRE_AUTH", "").strip().lower() in {"1", "true", "yes"}


def optional_user_id(authorization: str | None = Header(default=None)) -> str | None:
    """FastAPI dependency: returns the authenticated user id or None.

    Raises 401 only when auth is explicitly required and the token is missing/invalid.
    """
    secret = os.environ.get("SUPABASE_JWT_SECRET")
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()

    if not token or not secret:
        if _require_auth():
            raise HTTPException(status_code=401, detail="Authentication required")
        return None

    try:
        import jwt

        claims = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_aud": False},  # Supabase aud is 'authenticated'; tolerate variants
        )
        return claims.get("sub")
    except Exception as exc:  # noqa: BLE001
        logger.warning("JWT verification failed: %s", exc)
        if _require_auth():
            raise HTTPException(status_code=401, detail="Invalid token") from exc
        return None
