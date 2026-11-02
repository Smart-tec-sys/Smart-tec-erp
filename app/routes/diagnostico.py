"""TEMPORARIO: remover este router e seu registro no app apos o diagnostico."""

import os
import logging
from secrets import compare_digest

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.services.phase1_dry_run import (
    ArquivoDryRunInvalido,
    ReversaoDryRunInvalida,
    executar_dry_run,
)


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


_TABELAS_CONTAGEM = (
    "clientes", "orcamentos", "orcamentos_itens",
    "pedidos", "pedidos_itens", "financeiro",
)
_TABELAS_COMERCIAIS = (
    "parceiros_comerciais", "representantes", "representantes_rt",
    "parceiro_representantes", "parceiro_clientes",
)
_COLUNAS_FASE1 = {
    "clientes": ("parceiro_id", "representante_id"),
    "orcamentos": (
        "observacao_interna", "parceiro_id", "representante_id",
        "percentual_parceiro", "incluir_rt", "tipo_rt", "percentual_rt",
        "valor_rt", "incluir_taxa_bancaria", "taxa_bancaria_percentual",
        "valor_parceiro", "base_protegida", "valor_taxa_bancaria",
        "total_cliente_final", "vendedor_id", "cliente_final_nome",
        "cliente_final_documento", "cliente_final_telefone",
        "cliente_final_email", "cliente_final_endereco",
    ),
    "orcamentos_itens": ("dados_tecnicos",),
    "pedidos": (
        "orcamento_id", "perfil_comercial", "data_venda", "canal_venda",
        "observacao_interna", "vendedor_id", "parceiro_id", "representante_id",
        "cliente_final_nome", "cliente_final_documento", "cliente_final_telefone",
        "cliente_final_email", "cliente_final_endereco", "percentual_parceiro",
        "incluir_rt", "tipo_rt", "percentual_rt", "valor_rt",
        "incluir_taxa_bancaria", "taxa_bancaria_percentual", "valor_parceiro",
        "valor_taxa_bancaria", "total_cliente_final",
    ),
    "pedidos_itens": (
        "tipo_item", "descricao", "codigo_interno", "grupo_tecnico",
        "modelo_tecnico", "unidade", "largura", "altura", "area",
        "observacao_item", "material", "cor", "acionamento",
        "lado_comando", "calculo_producao_status", "dados_tecnicos",
    ),
}

_SQL_ESTRUTURA = text("""
    SELECT
        c.relname::text AS table_name,
        a.attname::text AS name,
        pg_catalog.format_type(a.atttypid, a.atttypmod) AS type,
        NOT a.attnotnull AS nullable,
        pg_catalog.pg_get_expr(d.adbin, d.adrelid) AS default,
        pg_catalog.row_security_active(c.oid) AS row_security_active
    FROM pg_catalog.pg_class c
    JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
    LEFT JOIN pg_catalog.pg_attribute a
      ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
    LEFT JOIN pg_catalog.pg_attrdef d
      ON d.adrelid = a.attrelid AND d.adnum = a.attnum
    WHERE n.nspname = 'public'
      AND c.relkind IN ('r', 'p')
      AND c.relname IN (
          'clientes', 'orcamentos', 'orcamentos_itens',
          'pedidos', 'pedidos_itens', 'financeiro',
          'parceiros_comerciais', 'representantes', 'representantes_rt',
          'parceiro_representantes', 'parceiro_clientes'
      )
    ORDER BY c.relname, a.attnum
""")

# SQL fixo: nenhum nome de tabela/coluna vem da requisicao.
# Duplicidades contam grupos repetidos; nunca retornam os numeros.
_VERIFICACOES = (
    (
        "orcamentos_numero_duplicate_groups",
        {"orcamentos": ("numero",)},
        """SELECT count(*) FROM (
            SELECT 1 FROM public.orcamentos
            WHERE numero IS NOT NULL
            GROUP BY numero HAVING count(*) > 1
        ) AS repetidos""",
    ),
    (
        "pedidos_numero_duplicate_groups",
        {"pedidos": ("numero",)},
        """SELECT count(*) FROM (
            SELECT 1 FROM public.pedidos
            WHERE numero IS NOT NULL
            GROUP BY numero HAVING count(*) > 1
        ) AS repetidos""",
    ),
    (
        "orcamentos_clientes_orphans",
        {"orcamentos": ("cliente_id",), "clientes": ("id",)},
        """SELECT count(*) FROM public.orcamentos filha
        WHERE filha.cliente_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM public.clientes pai WHERE pai.id = filha.cliente_id
        )""",
    ),
    (
        "orcamentos_itens_orcamentos_orphans",
        {"orcamentos_itens": ("orcamento_id",), "orcamentos": ("id",)},
        """SELECT count(*) FROM public.orcamentos_itens filha
        WHERE filha.orcamento_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM public.orcamentos pai WHERE pai.id = filha.orcamento_id
        )""",
    ),
    (
        "pedidos_itens_pedidos_orphans",
        {"pedidos_itens": ("pedido_id",), "pedidos": ("id",)},
        """SELECT count(*) FROM public.pedidos_itens filha
        WHERE filha.pedido_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM public.pedidos pai WHERE pai.id = filha.pedido_id
        )""",
    ),
    (
        "financeiro_pedidos_orphans",
        {"financeiro": ("pedido_id",), "pedidos": ("id",)},
        """SELECT count(*) FROM public.financeiro filha
        WHERE filha.pedido_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM public.pedidos pai WHERE pai.id = filha.pedido_id
        )""",
    ),
    (
        "pedidos_orcamento_duplicate_groups",
        {"pedidos": ("orcamento_id",)},
        """SELECT count(*) FROM (
            SELECT 1 FROM public.pedidos
            WHERE orcamento_id IS NOT NULL
            GROUP BY orcamento_id HAVING count(*) > 1
        ) AS repetidos""",
    ),
)


def _estrutura_ausente(necessarias, estrutura):
    ausentes = []
    for tabela, colunas in necessarias.items():
        if tabela not in estrutura:
            ausentes.append(f"public.{tabela}")
        else:
            ausentes.extend(
                f"public.{tabela}.{coluna}"
                for coluna in colunas
                if coluna not in estrutura[tabela]["columns"]
            )
    return ausentes


def _inventariar_banco(db: Session):
    estrutura = {}
    for linha in db.execute(_SQL_ESTRUTURA).mappings().all():
        tabela = linha["table_name"]
        entrada = estrutura.setdefault(
            tabela, {"columns": {}, "row_security_active": linha["row_security_active"]}
        )
        if linha["name"] is not None:
            entrada["columns"][linha["name"]] = {
                chave: linha[chave] for chave in ("name", "type", "nullable", "default")
            }

    inventario = {
        "schema": "public",
        "counts": dict.fromkeys(_TABELAS_CONTAGEM),
        "tables": {tabela: tabela in estrutura for tabela in _TABELAS_COMERCIAIS},
        "table_status": {
            tabela: {
                "exists": tabela in estrutura,
                "row_security_active": estrutura.get(tabela, {}).get("row_security_active"),
            }
            for tabela in _TABELAS_CONTAGEM
        },
        "columns": {
            tabela: list(estrutura.get(tabela, {}).get("columns", {}).values())
            for tabela in _TABELAS_CONTAGEM
        },
        "phase1_columns": {},
        "checks": {},
    }
    for tabela, esperadas in _COLUNAS_FASE1.items():
        existentes = estrutura.get(tabela, {}).get("columns", {})
        inventario["phase1_columns"][tabela] = {
            "expected": list(esperadas),
            "present": [coluna for coluna in esperadas if coluna in existentes],
            "missing": [coluna for coluna in esperadas if coluna not in existentes],
        }

    consultas = []
    for tabela in _TABELAS_CONTAGEM:
        if tabela in estrutura:
            consultas.append((
                f"count:{tabela}",
                f"SELECT count(*) FROM public.{tabela}",
            ))

    for nome, necessarias, sql in _VERIFICACOES:
        ausentes = _estrutura_ausente(necessarias, estrutura)
        inventario["checks"][nome] = {
            "status": "not_checked" if ausentes else "checked",
            "count": None,
            "missing": ausentes,
        }
        if not ausentes:
            consultas.append((f"check:{nome}", sql))

    if consultas:
        # Cada ramo produz somente uma identificacao fixa e uma contagem.
        sql = " UNION ALL ".join(
            f"SELECT '{metrica}' AS metric, ({consulta}) AS count"
            for metrica, consulta in consultas
        )
        resultados = {
            linha["metric"]: int(linha["count"])
            for linha in db.execute(text(sql)).mappings().all()
        }
        for tabela in _TABELAS_CONTAGEM:
            if tabela in estrutura:
                inventario["counts"][tabela] = resultados[f"count:{tabela}"]
        for nome, verificacao in inventario["checks"].items():
            if verificacao["status"] == "checked":
                verificacao["count"] = resultados[f"check:{nome}"]

    return inventario



@router.get("/db-target", include_in_schema=False)
def diagnosticar_destino_banco(
    response: Response,
    db: Session = Depends(get_db),
):
    # TEMPORARIO: somente metadados e agregados, nunca registros individuais.
    response.headers["Cache-Control"] = "no-store"
    try:
        try:
            db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
            db.execute(text("SET LOCAL statement_timeout = '15s'"))
            db.execute(text("SET LOCAL lock_timeout = '3s'"))
            resultado = dict(db.execute(_SQL_DESTINO_BANCO).mappings().one())
            resultado["inventory"] = _inventariar_banco(db)
        finally:
            db.rollback()
    except SQLAlchemyError:
        # Nao registrar excecoes de conexao: podem conter dados sensiveis.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="diagnóstico de banco indisponível",
        ) from None

    return resultado


async def recusar_conteudo_dry_run(request: Request) -> None:
    if request.query_params or await request.body():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="DRY RUN nao aceita corpo ou parametros de consulta.",
            headers={"Cache-Control": "no-store"},
        )


@router.post(
    "/run-phase1-dry-run",
    include_in_schema=False,
    dependencies=[Depends(recusar_conteudo_dry_run)],
)
def executar_diagnostico_fase1(response: Response):
    # TEMPORARIO: sem body, caminho ou SQL fornecido pelo solicitante.
    response.headers["Cache-Control"] = "no-store"
    try:
        return executar_dry_run(engine)
    except Exception as erro:
        tipo = type(erro).__name__
        mensagem = (
            str(erro)
            if isinstance(erro, (ArquivoDryRunInvalido, ReversaoDryRunInvalida))
            else "Falha ao executar ou verificar o DRY RUN FASE 1."
        )
        # Nunca registrar excecao original: driver/SQLAlchemy podem incluir segredos.
        logging.getLogger(__name__).error("DRY RUN FASE 1 falhou: tipo=%s", tipo)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"ok": False, "error_type": tipo, "message": mensagem},
            headers={"Cache-Control": "no-store"},
        ) from None
