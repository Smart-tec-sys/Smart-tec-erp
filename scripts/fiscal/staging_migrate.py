"""Aplicação protegida do Fiscal V1 SOMENTE no banco de staging do Render.

Uso na shell do serviço staging, com DATABASE_URL herdado do serviço:
  python scripts/fiscal/staging_migrate.py            # pré-verificação (somente leitura)
  python scripts/fiscal/staging_migrate.py --apply --confirm STAGING_FISCAL_V1

NÃO é executado na inicialização do servidor e não tem acesso a produção por padrão.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

EXPECTED_DATABASE = "smarttec_erp_staging"
CONFIRMATION = "STAGING_FISCAL_V1"
ROOT = Path(__file__).resolve().parents[2]
PREREQUISITE = ROOT / "migrations/20261114_fiscal_v1_staging_prerequisito_up.sql"
FISCAL_MIGRATION = ROOT / "migrations/20261114_fiscal_v1_cadastros_up.sql"


class PreflightError(RuntimeError):
    pass


def check_database_url(url: str):
    if not url:
        raise PreflightError("DATABASE_URL ausente. A migração não foi iniciada.")
    try:
        parsed = make_url(url)
    except Exception as exc:
        raise PreflightError("DATABASE_URL inválida. Migração não iniciada.") from exc
    if not parsed.drivername.startswith("postgresql"):
        raise PreflightError("A migração exige PostgreSQL.")
    if parsed.database != EXPECTED_DATABASE:
        raise PreflightError("Banco de destino não é o staging fiscal esperado.")
    return parsed


def strip_transaction(sql: str) -> str:
    # Os arquivos SQL também podem ser usados em psql; o runner gerencia
    # uma transação única para que os dois scripts sejam atômicos.
    parts = sql.strip().splitlines()
    if not any(line.strip().upper() == "BEGIN;" for line in parts):
        raise PreflightError("Migration sem marcador de transação BEGIN.")
    if not any(line.strip().upper() == "COMMIT;" for line in parts):
        raise PreflightError("Migration sem marcador de transação COMMIT.")
    return "\n".join(
        line for line in parts if line.strip().upper() not in {"BEGIN;", "COMMIT;"}
    )


def inspect(conn) -> dict:
    database = conn.execute(text("SELECT current_database()")).scalar_one()
    if database != EXPECTED_DATABASE:
        raise PreflightError("Conexão não aponta para o banco staging permitido.")

    tables = {
        row[0] for row in conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema='public'
              AND table_name IN ('empresas','produtos','pedidos','fiscal_produtos')
        """))
    }
    if not {"empresas", "produtos", "pedidos"}.issubset(tables):
        raise PreflightError("Faltam tabelas básicas esperadas para o staging.")

    count_empresa = conn.execute(text("SELECT count(*) FROM public.empresas")).scalar_one()
    count_produtos = conn.execute(text("SELECT count(*) FROM public.produtos")).scalar_one()
    count_pedidos = conn.execute(text("SELECT count(*) FROM public.pedidos")).scalar_one()
    if (count_empresa, count_produtos, count_pedidos) != (1, 0, 0):
        raise PreflightError(
            "Dados de staging divergiram do estado verificado (1 empresa, 0 produtos, "
            "0 pedidos). Não executar migração sem reavaliar."
        )

    constraint = conn.execute(text("""
        SELECT pg_get_constraintdef(oid)
          FROM pg_constraint
         WHERE conrelid='public.produtos'::regclass
           AND conname='uq_produtos_id_empresa'
    """)).scalar_one_or_none()
    if constraint is not None and constraint != "UNIQUE (id, empresa_id)":
        raise PreflightError("A constraint de produtos existente tem formato inesperado.")

    if "fiscal_produtos" in tables:
        fiscal_constraints = dict(conn.execute(text("""
            SELECT conname, contype::text
              FROM pg_constraint
             WHERE conrelid='public.fiscal_produtos'::regclass
               AND conname IN ('pk_fiscal_produtos', 'fk_fiscal_produto_tenant')
        """)))
        if fiscal_constraints != {
            "pk_fiscal_produtos": "p",
            "fk_fiscal_produto_tenant": "f",
        }:
            raise PreflightError("Tabela fiscal já existe, mas não tem todas as restrições esperadas.")
        fiscal_total = conn.execute(text("SELECT count(*) FROM public.fiscal_produtos")).scalar_one()
        if fiscal_total:
            raise PreflightError("Tabela fiscal já possui registros. Interrompido.")
        if constraint is None:
            raise PreflightError("Tabela fiscal existe sem a constraint base de produtos.")

    return {
        "banco": database,
        "empresas": count_empresa,
        "produtos": count_produtos,
        "pedidos": count_pedidos,
        "constraint_produtos": constraint == "UNIQUE (id, empresa_id)",
        "fiscal_existe": "fiscal_produtos" in tables,
    }


def run(url: str, *, apply: bool = False, confirmed: bool = False) -> dict:
    check_database_url(url)
    if apply and not confirmed:
        raise PreflightError("Aplicação bloqueada: confirmação STAGING_FISCAL_V1 ausente.")
    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 8})
    try:
        if not apply:
            with engine.connect() as conn:
                conn.execute(text("SET TRANSACTION READ ONLY"))
                state = inspect(conn)
            return {"modo": "PREFLIGHT_SOMENTE_LEITURA", **state}

        with engine.begin() as conn:
            conn.execute(text("SELECT pg_advisory_xact_lock(430014, 20261114)"))
            state = inspect(conn)
            if state["fiscal_existe"]:
                return {"modo": "JA_APLICADA", **state}
            for path in (PREREQUISITE, FISCAL_MIGRATION):
                conn.exec_driver_sql(strip_transaction(path.read_text(encoding="utf-8")))
            after = inspect(conn)
            if not (after["constraint_produtos"] and after["fiscal_existe"]):
                raise PreflightError("Pós-validação falhou: transação será revertida.")
            return {"modo": "APLICADA", **after}
    finally:
        engine.dispose()


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Pré-verificação e migração fiscal só de staging.")
    parser.add_argument("--apply", action="store_true", help="Habilita alterações somente após confirmação explícita.")
    parser.add_argument("--confirm", default="", help="Deve ser STAGING_FISCAL_V1 ao aplicar.")
    args = parser.parse_args(argv)
    try:
        result = run(
            os.getenv("DATABASE_URL", ""),
            apply=args.apply,
            confirmed=args.confirm == CONFIRMATION,
        )
    except (SQLAlchemyError, PreflightError, OSError) as exc:
        # Jamais imprimir URL/conexão ou segredos em logs.
        detail = str(exc) if isinstance(exc, PreflightError) else "Falha de conexão/SQL. Verifique o staging."
        parser.exit(1, "BLOQUEADO: " + detail + "\n")
    print("Fiscal V1:", ", ".join(f"{key}={value}" for key, value in result.items()))


if __name__ == "__main__":
    main()
