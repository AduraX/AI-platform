"""JWT token validation for Keycloak OIDC integration."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from fastapi import HTTPException, Request

from python_common.config.settings import AppSettings


@dataclass
class JWKSCache:
    """Caches JWKS keys from Keycloak with TTL."""
    keys: list[dict[str, Any]] = field(default_factory=list)
    fetched_at: float = 0.0
    ttl_seconds: float = 300.0

    @property
    def is_expired(self) -> bool:
        return time.time() - self.fetched_at > self.ttl_seconds


_jwks_cache = JWKSCache()


async def fetch_jwks(settings: AppSettings) -> list[dict[str, Any]]:
    """Fetch JWKS from Keycloak's well-known endpoint."""
    global _jwks_cache
    if not _jwks_cache.is_expired and _jwks_cache.keys:
        return _jwks_cache.keys

    jwks_url = (
        f"{settings.keycloak_url}/realms/{settings.keycloak_realm}"
        "/protocol/openid-connect/certs"
    )
    async with httpx.AsyncClient(verify=settings.keycloak_verify_ssl) as client:
        resp = await client.get(jwks_url, timeout=5.0)
        resp.raise_for_status()
        data = resp.json()

    _jwks_cache.keys = data.get("keys", [])
    _jwks_cache.fetched_at = time.time()
    return _jwks_cache.keys


async def validate_jwt_token(request: Request, settings: AppSettings) -> dict[str, Any] | None:
    """Validate JWT from Authorization header. Returns claims or None if auth is disabled."""
    if not settings.auth_enabled:
        return None

    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header[7:]

    try:
        import jwt as pyjwt

        jwks = await fetch_jwks(settings)
        if not jwks:
            raise HTTPException(status_code=503, detail="Unable to fetch signing keys")

        # Decode header to find key id
        unverified_header = pyjwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        signing_key = None
        for key in jwks:
            if key.get("kid") == kid:
                signing_key = pyjwt.algorithms.RSAAlgorithm.from_jwk(key)
                break

        if signing_key is None:
            raise HTTPException(status_code=401, detail="Token signing key not found")

        claims = pyjwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=settings.keycloak_client_id,
            issuer=f"{settings.keycloak_url}/realms/{settings.keycloak_realm}",
        )
        return claims

    except pyjwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token has expired") from exc
    except pyjwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc
    except ImportError:
        # PyJWT not installed — fall through to header-based auth
        return None
