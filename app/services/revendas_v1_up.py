"""Executor temporario do unico UP revisado de Revendas V1."""

import hashlib
import logging
import re
from pathlib import Path

from app.database import engine


logger = logging.getLogger("uvicorn.error.revendas_v1_up")
MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "20261102_revendas_cadastro_completo_v1_up.sql"
)
REVIEWED_SHA256 = "c7a50420a9a633a5db23fb681f6b0c5515c33ae062d3a6c05afbc1c898d6634d"
DATABASE = "smarttec_erp_staging"
COLUMNS = {
    "tipo_pessoa": ("character varying(8)", False, None),
    "nome_fantasia": ("character varying(255)", False, None),
    "razao_social": ("character varying(255)", False, None),
    "situacao_cadastral": ("character varying(100)", False, None),
    "inscricao_estadual": ("character varying(80)", False, None),
    "inscricao_municipal": ("character varying(80)", False, None),
    "tipo_contribuinte": ("character varying(30)", False, None),
    "isento_ie": ("boolean", True, "false"),
    "telefone_celular": ("character varying(50)", False, None),
    "responsavel": ("character varying(120)", False, None),
    "site": ("character varying(500)", False, None),
    "cep": ("character varying(8)", False, None),
    "logradouro": ("character varying(255)", False, None),
    "numero": ("character varying(30)", False, None),
    "complemento": ("character varying(255)", False, None),
    "bairro": ("character varying(100)", False, None),
    "cidade": ("character varying(150)", False, None),
    "estado": ("character varying(2)", False, None),
    "vendedor_responsavel_id": ("integer", False, None),
    "limite_credito": ("numeric(14,2)", False, None),
    "permitir_exceder_limite": ("boolean", True, "false"),
}
CATALOG_SQL = """
SELECT a.attname, format_type(a.atttypid, a.atttypmod),
       a.attnotnull, pg_get_expr(d.adbin, d.adrelid)
FROM pg_attribute a
LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
WHERE a.attrelid = 'public.parceiros_comerciais'::regclass
  AND a.attnum > 0 AND NOT a.attisdropped
"""


class RevendasV1UpError(RuntimeError):
    def __init__(self, message: str, error_type: str = "ValidationError"):
        super().__init__(message)
        self.error_type = error_type


def _read_migration():
    try:
        sql = MIGRATION_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")
    except (OSError, UnicodeError) as exc:
        raise RevendasV1UpError("Arquivo UP fixo ausente ou ilegivel.", type(exc).__name__) from exc
    if hashlib.sha256(sql.encode("utf-8")).hexdigest() != REVIEWED_SHA256:
        raise RevendasV1UpError("Arquivo UP diverge do SHA-256 revisado.")
    executable = re.sub(r"(?m)^\s*--.*$", "", sql).strip()
    if not executable.startswith("BEGIN;") or not executable.endswith("COMMIT;"):
        raise RevendasV1UpError("UP deve iniciar em BEGIN e terminar em COMMIT.")
    if re.search(r"\bROLLBACK\b", executable, re.IGNORECASE):
        raise RevendasV1UpError("ROLLBACK indevido no UP.")
    validations = []
    for tag in ("columns", "validate_constraints", "validate_index"):
        match = re.search(rf"DO \${tag}\$.*?\${tag}\$;", sql, re.DOTALL)
        if match is None:
            raise RevendasV1UpError("Validacoes obrigatorias ausentes no UP.")
        validations.append(match.group())
    # Os delimitadores do proprio arquivo sao executados separadamente para
    # manter o lock e a contagem na mesma transacao que o DDL revisado.
    return executable[len("BEGIN;"):-len("COMMIT;")], validations


def _validate_columns(cursor, complete=False):
    cursor.execute(CATALOG_SQL)
    found = {}
    for name, data_type, not_null, default in cursor.fetchall():
        if name in COLUMNS:
            normalized = None if default is None else re.sub(
                r"[()\s]", "", default.lower().replace("::boolean", "")
            )
            found[name] = (data_type, not_null, normalized)
    if complete and set(found) != set(COLUMNS):
        raise RevendasV1UpError("As 21 colunas nao estao presentes.")
    for name, definition in found.items():
        if definition != COLUMNS[name]:
            raise RevendasV1UpError(f"Coluna V1 incompativel: {name}.")


def run_revendas_v1_up():
    body, validations = _read_migration()
    connection = None
    driver = None
    cursor = None
    previous_autocommit = None
    committed = False
    transaction_open = False
    try:
        connection = engine.raw_connection()
        driver = connection.driver_connection
        previous_autocommit = driver.autocommit
        driver.autocommit = True
        cursor = driver.cursor()
        cursor.execute("SELECT current_database(), to_regclass('public.parceiros_comerciais')")
        database, table = cursor.fetchone()
        if database != DATABASE:
            raise RevendasV1UpError("Destino incorreto: somente smarttec_erp_staging e permitido.")
        if table is None:
            raise RevendasV1UpError("public.parceiros_comerciais nao existe.")

        cursor.execute("BEGIN;")
        transaction_open = True
        cursor.execute("SET LOCAL lock_timeout = '10s'; SET LOCAL statement_timeout = '120s';")
        cursor.execute("LOCK TABLE public.parceiros_comerciais IN SHARE ROW EXCLUSIVE MODE")
        _validate_columns(cursor)
        cursor.execute("SELECT count(*) FROM public.parceiros_comerciais")
        baseline = cursor.fetchone()[0]
        cursor.execute(body)
        cursor.execute("SELECT count(*) FROM public.parceiros_comerciais")
        if cursor.fetchone()[0] != baseline:
            raise RevendasV1UpError("Contagem de parceiros divergente antes do COMMIT.")
        cursor.execute("COMMIT;")
        committed = True
        transaction_open = False

        cursor.execute("BEGIN READ ONLY;")
        transaction_open = True
        cursor.execute("SET LOCAL statement_timeout = '120s';")
        _validate_columns(cursor, complete=True)
        for validation in validations:
            cursor.execute(validation)
        cursor.execute("SELECT count(*) FROM public.parceiros_comerciais")
        if cursor.fetchone()[0] != baseline:
            raise RevendasV1UpError("Contagem de parceiros divergente apos aplicacao.")
        cursor.execute("COMMIT;")
        transaction_open = False
        return {
            "ok": True,
            "database": DATABASE,
            "message": "REVENDAS V1 aplicada com sucesso",
            "columns_validated": len(COLUMNS),
        }
    except Exception as exc:
        # Nunca devolve mensagens do driver: podem conter SQL, DSN ou credenciais.
        error_type = exc.error_type if isinstance(exc, RevendasV1UpError) else type(exc).__name__
        logger.error("Falha no executor Revendas V1; tipo=%s; commit_confirmado=%s", error_type, committed)
        if committed:
            message = "ERRO GRAVE: divergencia apos aplicacao COMMITADA de Revendas V1. Nao houve reversao da migration."
        elif isinstance(exc, RevendasV1UpError):
            message = str(exc)
        else:
            message = "Falha na execucao de Revendas V1. Verifique o destino antes de repetir."
        raise RevendasV1UpError(message, error_type) from None
    finally:
        if connection is not None:
            try:
                if transaction_open and cursor is not None:
                    # Apos COMMIT, isto encerra somente a verificacao READ ONLY.
                    cursor.execute("ROLLBACK;")
                if cursor is not None:
                    cursor.close()
                if previous_autocommit is not None:
                    driver.autocommit = previous_autocommit
                connection.close()
            except Exception as exc:
                logger.error("Falha ao liberar conexao Revendas V1; tipo=%s", type(exc).__name__)
                try:
                    connection.invalidate()
                except Exception as invalidation_error:
                    logger.error("Falha ao invalidar conexao Revendas V1; tipo=%s", type(invalidation_error).__name__)
                raise RevendasV1UpError(
                    ("ERRO GRAVE: Revendas V1 COMMITADA; falha ao liberar conexao, sem reversao da migration."
                     if committed else "Falha ao liberar conexao. Confira o estado de Revendas V1 antes de repetir."),
                    type(exc).__name__,
                ) from None
