"""Aplicador temporario exclusivo da Fase 1 no staging.

Arquivo, hash e destino sao fixos. O script revisado controla BEGIN/COMMIT.
Uma falha apos confirmar COMMIT nunca desfaz a aplicacao: somente a transacao
de verificacao READ ONLY pode ser encerrada por rollback. Remover este executor
e a rota apos a homologacao. Alterar o SQL exige nova revisao do hash.
"""

import hashlib
from pathlib import Path
import re

from psycopg2.extensions import TRANSACTION_STATUS_IDLE
from sqlalchemy.engine import Engine

from app.services.phase1_dry_run import _tokens


ARQUIVO_UP = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "20261102_fase1_nucleo_comercial_STAGING_UP.sql"
)
_SHA256_REVISADO = "0ac91e7176a49127253be83abbe33a2f988b5e49bfdfff4bbe7cfb03e5f3c6f5"
_TABELAS_NOVAS = {
    "parceiros_comerciais", "representantes", "representantes_rt",
    "parceiro_representantes", "parceiro_clientes",
}
_DESTINO = ("smarttec_erp_staging", "smarttec_staging")
_CONTAGENS = (1, 0, 0, 0, 0, 0)
_SQL_DESTINO = "SELECT current_database(), current_user"
_SQL_BASELINE = """
    SELECT
        (SELECT count(*) FROM public.clientes),
        (SELECT count(*) FROM public.orcamentos),
        (SELECT count(*) FROM public.orcamentos_itens),
        (SELECT count(*) FROM public.pedidos),
        (SELECT count(*) FROM public.pedidos_itens),
        (SELECT count(*) FROM public.financeiro),
        to_regclass('public.parceiros_comerciais') IS NOT NULL,
        to_regclass('public.representantes') IS NOT NULL,
        EXISTS (
            SELECT 1 FROM pg_catalog.pg_attribute
            WHERE attrelid = to_regclass('public.orcamentos')
              AND attname = 'cliente_final_nome'
              AND attnum > 0 AND NOT attisdropped
        )
"""
_SQL_CONTAGENS = """
    SELECT
        (SELECT count(*) FROM public.clientes),
        (SELECT count(*) FROM public.orcamentos),
        (SELECT count(*) FROM public.orcamentos_itens),
        (SELECT count(*) FROM public.pedidos),
        (SELECT count(*) FROM public.pedidos_itens),
        (SELECT count(*) FROM public.financeiro)
"""
_SQL_TABELAS = """
    SELECT c.relname::text
    FROM pg_catalog.pg_class c
    JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relkind = 'r'
      AND c.relname IN (
        'parceiros_comerciais', 'representantes', 'representantes_rt',
        'parceiro_representantes', 'parceiro_clientes'
      )
"""
_SQL_COLUNAS = """
    SELECT c.relname::text, a.attname::text,
        pg_catalog.format_type(a.atttypid, a.atttypmod)
    FROM pg_catalog.pg_attribute a
    JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
    JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND a.attnum > 0 AND NOT a.attisdropped
      AND c.relkind = 'r'
      AND c.relname IN (
        'clientes', 'orcamentos', 'orcamentos_itens', 'pedidos', 'pedidos_itens'
      )
"""
_SQL_INDICES = """
    SELECT c.relname::text, pg_catalog.pg_get_indexdef(c.oid),
        i.indisunique, i.indisvalid, i.indisready
    FROM pg_catalog.pg_class c
    JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
    JOIN pg_catalog.pg_index i ON i.indexrelid = c.oid
    WHERE n.nspname = 'public'
      AND c.relname IN ('uq_pedidos_orcamento', 'uq_representante_rt_venda_ativa')
"""
_INDICES = {
    "uq_pedidos_orcamento": (
        "CREATE UNIQUE INDEX uq_pedidos_orcamento ON public.pedidos "
        "USING btree (orcamento_id) WHERE (orcamento_id IS NOT NULL)"
    ),
    "uq_representante_rt_venda_ativa": (
        "CREATE UNIQUE INDEX uq_representante_rt_venda_ativa ON public.representantes_rt "
        "USING btree (empresa_id, pedido_id, representante_id) "
        "WHERE ((status)::text <> 'CANCELADO'::text)"
    ),
}


class ArquivoUpInvalido(ValueError):
    pass


class BaselineUpDivergente(RuntimeError):
    pass


class AplicacaoUpFalhou(RuntimeError):
    pass


class ValidacaoPosCommitFalhou(RuntimeError):
    pass


def _ler_sql_validado() -> tuple[str, set[tuple[str, str, str]]]:
    if not ARQUIVO_UP.is_file():
        raise ArquivoUpInvalido("Arquivo fixo UP indisponivel.")
    sql = ARQUIVO_UP.read_text(encoding="utf-8")
    tokens = _tokens(sql)
    comandos = list(tokens)
    for anterior, atual in zip(tokens, tokens[1:]):
        if anterior.upper() == "DO" and atual.startswith("$"):
            tag = atual[:atual.index("$", 1) + 1]
            comandos.extend(_tokens(atual[len(tag):-len(tag)]))
    if any(t.upper() == "ROLLBACK" for t in comandos):
        raise ArquivoUpInvalido("ROLLBACK executavel proibido no UP.")
    if (
        tokens[:2] != ["BEGIN", ";"]
        or tokens[-2:] != ["COMMIT", ";"]
        or sum(t.upper() == "COMMIT" for t in comandos) != 1
    ):
        raise ArquivoUpInvalido("UP deve iniciar com BEGIN e terminar com um unico COMMIT.")
    preflight = next((t for t in tokens if t.startswith("$preflight$")), "")
    for expressao, esperado in (
        (r"current_database\(\)", "smarttec_erp_staging"),
        ("current_user", "smarttec_staging"),
    ):
        if not re.search(r"IF\s+" + expressao + r"\s*<>\s*'" + esperado + r"'\s+THEN", preflight):
            raise ArquivoUpInvalido("Guarda de banco ou usuario staging ausente no UP.")
    if hashlib.sha256(sql.encode("utf-8")).hexdigest() != _SHA256_REVISADO:
        raise ArquivoUpInvalido("UP adulterado ou divergente do SHA-256 revisado.")

    # A lista de tipos e nomes vem do proprio artefato cuja identidade foi validada.
    final = next((t for t in tokens if t.startswith("$fase1_final$")), "")
    colunas = re.findall(r"\('([^']+)', '([^']+)', '([^']+)'\)", final)
    esperado = set(colunas)
    if len(colunas) != 62 or len(esperado) != 62:
        raise ArquivoUpInvalido("Catalogo revisado das 62 colunas incompleto.")
    return sql, esperado


def executar_up(engine: Engine) -> dict[str, str | bool | int]:
    sql, colunas_esperadas = _ler_sql_validado()
    conexao = engine.raw_connection()
    driver = conexao.driver_connection
    commit_confirmado = False
    execucao_iniciada = False
    try:
        driver.rollback()
        driver.autocommit = False
        with driver.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            cursor.execute("SET LOCAL statement_timeout = '15s'")
            cursor.execute("SET LOCAL lock_timeout = '3s'")
            cursor.execute(_SQL_DESTINO)
            if cursor.fetchone() != _DESTINO:
                raise BaselineUpDivergente("Banco ou usuario fora do destino staging autorizado.")
            cursor.execute(_SQL_BASELINE)
            if cursor.fetchone() != _CONTAGENS + (False, False, False):
                raise BaselineUpDivergente("Baseline divergente; UP nao iniciado.")
            driver.rollback()

            # O UP tambem reconfere o baseline sob locks antes de alterar colunas.
            driver.autocommit = True
            execucao_iniciada = True
            cursor.execute(sql)
            if cursor.statusmessage != "COMMIT" or driver.get_transaction_status() != TRANSACTION_STATUS_IDLE:
                raise AplicacaoUpFalhou(
                    "COMMIT nao confirmado; resultado da aplicacao incerto. Verificar antes de repetir."
                )
            commit_confirmado = True

            driver.autocommit = False
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            cursor.execute("SET LOCAL statement_timeout = '15s'")
            cursor.execute("SET LOCAL lock_timeout = '3s'")
            cursor.execute(_SQL_DESTINO)
            if cursor.fetchone() != _DESTINO:
                raise ValidacaoPosCommitFalhou("ERRO GRAVE: destino divergente apos aplicacao.")
            cursor.execute(_SQL_CONTAGENS)
            if cursor.fetchone() != _CONTAGENS:
                raise ValidacaoPosCommitFalhou("ERRO GRAVE: contagens divergentes apos aplicacao.")
            cursor.execute(_SQL_TABELAS)
            if {r[0] for r in cursor.fetchall()} != _TABELAS_NOVAS:
                raise ValidacaoPosCommitFalhou("ERRO GRAVE: tabelas divergentes apos aplicacao.")
            cursor.execute(_SQL_COLUNAS)
            if not colunas_esperadas.issubset(set(cursor.fetchall())):
                raise ValidacaoPosCommitFalhou("ERRO GRAVE: colunas divergentes apos aplicacao.")
            cursor.execute(_SQL_INDICES)
            indices = {r[0]: tuple(r[1:]) for r in cursor.fetchall()}
            if indices != {nome: (definicao, True, True, True) for nome, definicao in _INDICES.items()}:
                raise ValidacaoPosCommitFalhou("ERRO GRAVE: indices divergentes apos aplicacao.")
        return {
            "ok": True,
            "database": "smarttec_erp_staging",
            "message": "FASE 1 NUCLEO COMERCIAL aplicada com sucesso",
            "tables_created": 5,
            "phase1_columns_validated": 62,
        }
    except Exception as erro:
        if commit_confirmado:
            raise ValidacaoPosCommitFalhou(
                "ERRO GRAVE: houve divergencia ou falha de verificacao apos aplicacao "
                "com COMMIT confirmado. Nao foi tentado desfazer a aplicacao."
            ) from None
        if isinstance(erro, (BaselineUpDivergente, AplicacaoUpFalhou)):
            raise
        if execucao_iniciada:
            raise AplicacaoUpFalhou(
                "Falha durante execucao do UP; COMMIT nao confirmado. "
                "Verificar o estado antes de repetir."
            ) from None
        raise AplicacaoUpFalhou("Falha na verificacao anterior ao UP; aplicacao nao iniciada.") from None
    finally:
        try:
            # Se COMMIT ocorreu, encerra somente a nova transacao READ ONLY.
            # Nunca envia ROLLBACK como tentativa de desfazer o COMMIT.
            if not commit_confirmado or driver.get_transaction_status() != TRANSACTION_STATUS_IDLE:
                driver.rollback()
            driver.autocommit = False
        except Exception:
            try:
                conexao.invalidate()
            finally:
                if commit_confirmado:
                    raise ValidacaoPosCommitFalhou(
                        "ERRO GRAVE: falha ao encerrar verificacao apos aplicacao; COMMIT ja confirmado."
                    ) from None
                raise AplicacaoUpFalhou("Falha ao encerrar conexao; verificar antes de repetir.") from None
        finally:
            try:
                conexao.close()
            except Exception:
                if commit_confirmado:
                    raise ValidacaoPosCommitFalhou(
                        "ERRO GRAVE: falha ao liberar conexao apos aplicacao; COMMIT ja confirmado."
                    ) from None
                raise AplicacaoUpFalhou("Falha ao liberar conexao; verificar antes de repetir.") from None
