"""Executor temporario de um unico artefato revisado; remover apos homologacao.

O arquivo nao e selecionavel por request e seu SHA-256 normalizado em LF esta
fixado abaixo. Qualquer revisao do SQL exige nova revisao desta assinatura.
Usa o driver do pool do backend com autocommit apenas para permitir que o
proprio script controle BEGIN/ROLLBACK; nunca confirma a transacao.
A verificacao posterior e somente leitura. Rota, executor e token temporario
devem ser removidos/desabilitados apos concluir este diagnostico.
"""

import hashlib
from pathlib import Path
import re

from psycopg2.extensions import TRANSACTION_STATUS_IDLE
from sqlalchemy.engine import Engine


ARQUIVO_DRY_RUN = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "20261102_fase1_nucleo_comercial_STAGING_DRY_RUN.sql"
)
_SHA256_REVISADO = "116e69c6940f1f9d6164f1efc2504d8d7f77e4f904ecf28b4f64311b273b8fcc"
_AVISO_FINAL = (
    "DRY RUN STAGING: validações concluídas com sucesso; 62 colunas verificadas. "
    "A transação será revertida por ROLLBACK."
)
_TOKENS = re.compile(
    r"--[^\n]*|/\*.*?\*/"
    r"|(?P<tag>\$(?:[a-zA-Z_][a-zA-Z_0-9]*)?\$).*?(?P=tag)"
    r"|'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\""
    r"|[a-zA-Z_][a-zA-Z_0-9]*|[^\s]",
    re.DOTALL,
)
_SQL_POS_ROLLBACK = """
    SELECT current_database(), current_user,
        to_regclass('public.parceiros_comerciais') IS NOT NULL,
        to_regclass('public.representantes') IS NOT NULL,
        EXISTS (
            SELECT 1 FROM pg_catalog.pg_attribute
            WHERE attrelid IN (
                to_regclass('public.orcamentos'),
                to_regclass('public.pedidos')
            )
              AND attname = 'cliente_final_nome'
              AND attnum > 0 AND NOT attisdropped
        ),
        (SELECT count(*) FROM public.clientes),
        (SELECT count(*) FROM public.pedidos)
"""


class ArquivoDryRunInvalido(ValueError):
    pass


class ReversaoDryRunInvalida(RuntimeError):
    pass


def _tokens(sql: str) -> list[str]:
    return [
        m.group() for m in _TOKENS.finditer(sql)
        if not m.group().startswith(("--", "/*"))
    ]


def _ler_sql_validado() -> str:
    if not ARQUIVO_DRY_RUN.is_file():
        raise ArquivoDryRunInvalido("Arquivo fixo do DRY RUN indisponivel.")
    sql = ARQUIVO_DRY_RUN.read_text(encoding="utf-8")
    tokens = _tokens(sql)
    # Corpos DO sao executaveis, mas seus literais e comentarios nao sao comandos.
    comandos = list(tokens)
    for anterior, atual in zip(tokens, tokens[1:]):
        if anterior.upper() == "DO" and atual.startswith("$"):
            tag = atual[:atual.index("$", 1) + 1]
            comandos.extend(_tokens(atual[len(tag):-len(tag)]))
    if any(t.upper() == "COMMIT" for t in comandos):
        raise ArquivoDryRunInvalido("COMMIT executavel proibido no DRY RUN.")
    if tokens[:2] != ["BEGIN", ";"] or tokens[-2:] != ["ROLLBACK", ";"]:
        raise ArquivoDryRunInvalido("DRY RUN deve iniciar com BEGIN e terminar com ROLLBACK.")
    if sum(t.upper() == "ROLLBACK" for t in tokens) != 1:
        raise ArquivoDryRunInvalido("Encerramento ROLLBACK invalido.")
    preflight = next((t for t in tokens if t.startswith("$preflight$")), "")
    if not re.search(
        r"IF\s+current_database\(\)\s*<>\s*'smarttec_erp_staging'\s+THEN",
        preflight,
    ):
        raise ArquivoDryRunInvalido("Guarda de destino staging ausente.")
    aviso = next((t for t in tokens if t.startswith("$sucesso_dry_run$")), "")
    if _AVISO_FINAL not in aviso or "RAISE NOTICE" not in aviso:
        raise ArquivoDryRunInvalido("Aviso final do DRY RUN ausente.")
    # Impede inclusive SQL dinamico adulterado. LF/CRLF nao alteram a identidade.
    if hashlib.sha256(sql.encode("utf-8")).hexdigest() != _SHA256_REVISADO:
        raise ArquivoDryRunInvalido("Conteudo do DRY RUN diverge do artefato revisado.")
    return sql


def executar_dry_run(engine: Engine) -> dict[str, str | bool]:
    sql = _ler_sql_validado()
    # Usa o pool do backend sem deixar o SQLAlchemy envolver BEGIN/ROLLBACK.
    conexao = engine.raw_connection()
    driver = conexao.driver_connection
    try:
        driver.rollback()
        driver.autocommit = True
        with driver.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user")
            if cursor.fetchone() != ("smarttec_erp_staging", "smarttec_staging"):
                raise ArquivoDryRunInvalido("Banco ou usuario fora do destino staging autorizado.")
            driver.notices.clear()
            cursor.execute(sql)
            if (
                cursor.statusmessage != "ROLLBACK"
                or driver.get_transaction_status() != TRANSACTION_STATUS_IDLE
                or not any(_AVISO_FINAL in aviso for aviso in driver.notices)
            ):
                raise ReversaoDryRunInvalida("ERRO GRAVE: encerramento do DRY RUN nao confirmado.")

            driver.autocommit = False
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            cursor.execute("SET LOCAL statement_timeout = '15s'")
            cursor.execute("SET LOCAL lock_timeout = '3s'")
            cursor.execute(_SQL_POS_ROLLBACK)
            if cursor.fetchone() != (
                "smarttec_erp_staging", "smarttec_staging",
                False, False, False, 1, 0,
            ):
                raise ReversaoDryRunInvalida("ERRO GRAVE: estado pos-ROLLBACK diverge do baseline.")
        return {
            "ok": True,
            "database": "smarttec_erp_staging",
            "message": "DRY RUN FASE 1 concluido com sucesso e revertido",
        }
    finally:
        try:
            driver.rollback()
            driver.autocommit = False
        except Exception:
            # Nao devolver uma conexao com estado transacional desconhecido ao pool.
            conexao.invalidate()
            raise
        finally:
            conexao.close()
