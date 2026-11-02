"""TEMPORARIO: remover este router e seu registro no app apos o diagnostico."""

import os
from secrets import compare_digest

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db


def autorizar_diagnostico(
    token: str | None = Header(default=None, alias="X-Diagnostic-Token"),
) -> None:
    token_configurado = os.getenv("DIAG_DB_TARGET_TOKEN", "").strip()
    if not token_configurado:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="diagnóstico temporário desabilitado",
        )
    if not token or not compare_digest(
        token.encode("utf-8"), token_configurado.encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="acesso diagnóstico não autorizado",
        )


router = APIRouter(
    prefix="/diag",
    dependencies=[Depends(autorizar_diagnostico)],
)

_SQL_DESTINO_BANCO = text("""
    SELECT
        pg_catalog.current_database() AS database,
        pg_catalog.current_schema() AS schema,
        current_user AS "user",
        pg_catalog.inet_server_addr()::text AS server_addr,
        pg_catalog.inet_server_port() AS server_port,
        pg_catalog.current_setting('search_path') AS search_path,
        pg_catalog.to_regclass('public.representantes') IS NOT NULL
            AS representantes_exists,
        pg_catalog.to_regclass('public.orcamentos') IS NOT NULL
            AS orcamentos_exists,
        EXISTS (
            SELECT 1
            FROM pg_catalog.pg_attribute
            WHERE attrelid = pg_catalog.to_regclass('public.orcamentos')
              AND attname = 'cliente_final_nome'
              AND attnum > 0
              AND NOT attisdropped
        ) AS cliente_final_nome_exists
""")


@router.get("/db-target", include_in_schema=False)
def diagnosticar_destino_banco(
    response: Response,
    db: Session = Depends(get_db),
):
    # TEMPORARIO: consulta apenas metadados da conexao usada pelo backend.
    response.headers["Cache-Control"] = "no-store"
    try:
        try:
            db.execute(text("SET TRANSACTION READ ONLY"))
            resultado = dict(db.execute(_SQL_DESTINO_BANCO).mappings().one())
        finally:
            db.rollback()
    except SQLAlchemyError:
        # Nao registrar excecoes de conexao: podem conter dados sensiveis.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="diagnóstico de banco indisponível",
        ) from None

    return resultado
