import os
from dataclasses import dataclass
from typing import Any

import jwt
from jwt import PyJWKClient

from app.auth.service import ExternalIdentity


SUPPORTED_ALGORITHMS = {"ES256", "RS256"}
EXPECTED_AUDIENCE = "authenticated"
PROVIDER_NAME = "supabase"


class SupabaseAuthConfigurationError(RuntimeError):
    pass


class SupabaseTokenError(PermissionError):
    pass


@dataclass(frozen=True)
class VerifiedSupabaseToken:
    identity: ExternalIdentity
    claims: dict[str, Any]


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SupabaseAuthConfigurationError(
            f"variável obrigatória não configurada: {name}"
        )
    return value


def get_supabase_auth_config() -> tuple[str, str]:
    issuer = _required_env("SUPABASE_AUTH_ISSUER").rstrip("/")
    jwks_url = _required_env("SUPABASE_JWKS_URL")

    return issuer, jwks_url


def verify_supabase_access_token(
    token: str,
) -> VerifiedSupabaseToken:
    """
    Valida um access token emitido pelo Supabase Auth.

    Verifica:
    - assinatura criptográfica via JWKS;
    - algoritmo permitido;
    - issuer;
    - audience;
    - expiração;
    - subject (sub).

    Não consulta UsuarioDB e não escolhe tenant.
    """

    raw_token = (token or "").strip()

    if not raw_token:
        raise SupabaseTokenError("token ausente")

    issuer, jwks_url = get_supabase_auth_config()

    try:
        header = jwt.get_unverified_header(raw_token)
    except jwt.PyJWTError as exc:
        raise SupabaseTokenError("header JWT inválido") from exc

    algorithm = header.get("alg")

    if algorithm not in SUPPORTED_ALGORITHMS:
        raise SupabaseTokenError(
            f"algoritmo JWT não permitido: {algorithm!r}"
        )

    try:
        jwks_client = PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(raw_token)

        claims = jwt.decode(
            raw_token,
            signing_key.key,
            algorithms=[algorithm],
            audience=EXPECTED_AUDIENCE,
            issuer=issuer,
            options={
                "require": [
                    "exp",
                    "iss",
                    "sub",
                    "aud",
                ]
            },
        )

    except jwt.ExpiredSignatureError as exc:
        raise SupabaseTokenError("token expirado") from exc

    except jwt.InvalidAudienceError as exc:
        raise SupabaseTokenError("audience JWT inválida") from exc

    except jwt.InvalidIssuerError as exc:
        raise SupabaseTokenError("issuer JWT inválido") from exc

    except jwt.PyJWTError as exc:
        raise SupabaseTokenError("JWT inválido") from exc

    except Exception as exc:
        raise SupabaseTokenError(
            "não foi possível validar a assinatura JWT"
        ) from exc

    subject = str(claims.get("sub") or "").strip()

    if not subject:
        raise SupabaseTokenError("JWT sem subject válido")

    role = claims.get("role")

    if role is not None and role != EXPECTED_AUDIENCE:
        raise SupabaseTokenError("role JWT inválida")

    email_claim = claims.get("email")
    email = str(email_claim).strip() if email_claim else None

    identity = ExternalIdentity(
        provider=PROVIDER_NAME,
        subject=subject,
        email=email,
    )

    return VerifiedSupabaseToken(
        identity=identity,
        claims=dict(claims),
    )


def extract_bearer_token(
    authorization: str | None,
) -> str:
    """
    Extrai token de:
        Authorization: Bearer <token>
    """

    value = (authorization or "").strip()

    if not value:
        raise SupabaseTokenError(
            "header Authorization ausente"
        )

    scheme, separator, token = value.partition(" ")

    if (
        separator != " "
        or scheme.lower() != "bearer"
        or not token.strip()
    ):
        raise SupabaseTokenError(
            "Authorization deve usar Bearer token"
        )

    return token.strip()