"""Backend bootstrap: external environment takes precedence over local .env."""
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.engine import URL

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_SUPABASE_VARIABLES = ("SUPABASE_AUTH_ISSUER", "SUPABASE_JWKS_URL")


def validate_auth_configuration() -> None:
    mode = os.getenv("SMARTTEC_AUTH_MODE", "dev").strip().lower()
    if mode not in {"dev", "authenticated"}:
        raise RuntimeError("SMARTTEC_AUTH_MODE inválido. Use 'dev' ou 'authenticated'.")
    if mode == "authenticated":
        missing = [name for name in REQUIRED_SUPABASE_VARIABLES if not os.getenv(name, "").strip()]
        if missing:
            raise RuntimeError("Configuração Supabase incompleta. Ausentes: " + ", ".join(missing))


def get_database_url():
    configured_url = os.getenv("DATABASE_URL", "").strip()
    if configured_url:
        return configured_url
    required = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER")
    missing = [name for name in required if not os.getenv(name, "").strip()]
    if missing:
        raise RuntimeError("Configuração do banco incompleta. Ausentes: " + ", ".join(missing))
    try:
        port = int(os.environ["DB_PORT"])
        if not 1 <= port <= 65535:
            raise ValueError()
    except ValueError:
        raise RuntimeError("Configuração do banco inválida: DB_PORT.") from None
    return URL.create(
        "postgresql",
        username=os.environ["DB_USER"].strip(),
        password=os.getenv("DB_PASSWORD") or None,
        host=os.environ["DB_HOST"].strip(),
        port=port,
        database=os.environ["DB_NAME"].strip(),
    )


def load_backend_environment() -> None:
    load_dotenv(PROJECT_ROOT / ".env", override=False)


def initialize_backend_configuration() -> None:
    # A missing local file is valid in Render/production; never override the service environment.
    load_backend_environment()
    validate_auth_configuration()
    get_database_url()


def get_commercial_mode_setting() -> str:
    # Valor bruto e opcional; ausente ou invalido e tratado como off pela integracao.
    return os.getenv("SMARTTEC_COMMERCIAL_MODE", "off").strip().lower()
