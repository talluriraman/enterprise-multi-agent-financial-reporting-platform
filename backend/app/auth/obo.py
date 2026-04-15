"""
On-Behalf-Of (OBO) token validation for client → platform calls.

Production: validate JWT from Authorization: Bearer using tenant JWKS, audience, issuer,
and optional user impersonation scopes. This POC can run with OBO_REQUIRE_AUTH=false.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

security = HTTPBearer(auto_error=False)


@dataclass
class OboContext:
    subject: str | None
    raw_token: str | None
    claims: dict


async def get_obo_context(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> OboContext:
    if not settings.obo_require_auth:
        return OboContext(subject="demo-user", raw_token=None, claims={"demo": True})

    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token (OBO).",
        )

    # POC: decode without verification if python-jose not configured with JWKS.
    # Replace with full validation (signature, aud, iss, exp) in production.
    token = creds.credentials
    return OboContext(subject="validated-user", raw_token=token, claims={})
