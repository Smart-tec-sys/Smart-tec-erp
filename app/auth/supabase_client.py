"""Cliente mínimo do Supabase Auth para o frontend Streamlit."""

import os
import time
from dataclasses import dataclass, field

import requests


class SupabaseLoginError(PermissionError):
    pass


class SupabaseClientConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class SupabaseSession:
    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    expires_in: int
    expires_at: float
    user_id: str
    email: str

    def __repr__(self) -> str:
        return (
            "SupabaseSession(access_token=<redacted>, refresh_token=<redacted>, "
            f"expires_in={self.expires_in!r}, expires_at={self.expires_at!r}, "
            f"user_id={self.user_id!r}, email={self.email!r})"
        )


def _config() -> tuple[str, str]:
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
    if not url or not key:
        raise SupabaseClientConfigurationError("Supabase Auth não configurado")
    return url, key


def _parse_session(payload: dict) -> SupabaseSession:
    user = payload.get("user") or {}
    access_token = str(payload.get("access_token") or "")
    refresh_token = str(payload.get("refresh_token") or "")
    user_id = str(user.get("id") or "")
    if not access_token or not refresh_token or not user_id:
        raise SupabaseLoginError("Resposta de autenticação inválida")
    expires_in = int(payload.get("expires_in") or 0)
    return SupabaseSession(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        expires_at=time.time() + expires_in,
        user_id=user_id,
        email=str(user.get("email") or ""),
    )


def _token_request(grant_type: str, payload: dict, timeout: float = 15) -> SupabaseSession:
    url, key = _config()
    try:
        response = requests.post(
            f"{url}/auth/v1/token",
            params={"grant_type": grant_type},
            headers={"apikey": key, "Content-Type": "application/json"},
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise SupabaseLoginError("Não foi possível conectar ao serviço de autenticação") from exc
    if response.status_code >= 400:
        detail = (response.json() if response.content else {})
        message = str(detail.get("msg") or detail.get("error_description") or "")
        if "confirm" in message.lower():
            raise SupabaseLoginError("Confirme seu e-mail antes de entrar")
        raise SupabaseLoginError("E-mail ou senha inválidos")
    return _parse_session(response.json())


def login_with_password(email: str, password: str) -> SupabaseSession:
    normalized_email = (email or "").strip().lower()
    if not normalized_email or not password:
        raise SupabaseLoginError("Informe e-mail e senha")
    return _token_request("password", {"email": normalized_email, "password": password})


def refresh_session(refresh_token: str) -> SupabaseSession:
    if not (refresh_token or "").strip():
        raise SupabaseLoginError("Sessão expirada")
    return _token_request("refresh_token", {"refresh_token": refresh_token})
