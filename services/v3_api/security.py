"""Verification JWT Supabase pour le service V3.

Le mode ``development`` n'est accepte que si ``LIDAL_V3_ALLOW_DEV_AUTH=true``.
En production, la signature asymetrique est verifiee via le JWKS du projet.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from fastapi import Header, HTTPException, status


@dataclass(frozen=True)
class RequestIdentity:
    user_id: str
    organization_id: str
    role: str


@lru_cache(maxsize=1)
def _jwks_client():
    try:
        import jwt
    except ImportError as exc:  # pragma: no cover - dependance d'exploitation
        raise RuntimeError("PyJWT[crypto] est requis pour verifier Supabase Auth") from exc
    project_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    if not project_url:
        raise RuntimeError("SUPABASE_URL est obligatoire en mode Supabase")
    return jwt.PyJWKClient(f"{project_url}/auth/v1/.well-known/jwks.json", cache_jwk_set=True)


def _verify_supabase_token(token: str) -> dict[str, object]:
    import jwt

    project_url = os.environ["SUPABASE_URL"].rstrip("/")
    signing_key = _jwks_client().get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256", "ES256", "EdDSA"],
        audience="authenticated",
        issuer=f"{project_url}/auth/v1",
        options={"require": ["exp", "sub", "role"]},
    )


def resolve_identity(
    authorization: str | None = Header(default=None, alias="Authorization"),
    organization_header: str | None = Header(default=None, alias="X-Organization-Id"),
) -> RequestIdentity:
    allow_dev = os.getenv("LIDAL_V3_ALLOW_DEV_AUTH", "false").lower() == "true"
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        try:
            claims = _verify_supabase_token(token)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="JWT invalide ou expire") from exc
        user_id = str(claims["sub"])
        app_metadata = claims.get("app_metadata")
        metadata = app_metadata if isinstance(app_metadata, dict) else {}
        primary_organization = str(metadata.get("organization_id") or "")
        organization_values = metadata.get("organization_ids")
        organization_ids = (
            {str(value) for value in organization_values if isinstance(value, (str, int))}
            if isinstance(organization_values, list)
            else set()
        )
        if primary_organization:
            organization_ids.add(primary_organization)
        organization_id = organization_header or primary_organization
        if not organization_id:
            raise HTTPException(status_code=400, detail="organisation non selectionnee")
        if organization_id not in organization_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="acces refuse pour cette organisation",
            )
        role_values = metadata.get("organization_roles")
        organization_roles = role_values if isinstance(role_values, dict) else {}
        return RequestIdentity(
            user_id=user_id,
            organization_id=organization_id,
            role=str(organization_roles.get(organization_id) or metadata.get("role") or "viewer"),
        )
    if allow_dev and organization_header:
        return RequestIdentity("dev-user", organization_header, "owner")
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentification requise")
