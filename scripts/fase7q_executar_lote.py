import csv
import json
from datetime import datetime
from sqlalchemy import text
from app.database import engine

PLANO = "fase7q_plano_estrito.csv"

with open(PLANO, encoding="utf-8-sig") as f:
    linhas = list(csv.DictReader(f, delimiter=";"))

ids_plano = sorted({int(x["legado"]) for x in linhas})

if len(ids_plano) != len(linhas):
    raise RuntimeError("ABORTADO: existem IDs legados repetidos no plano.")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = f"fase7q_backup_lote_{timestamp}.json"

with engine.begin() as conn:

    db = conn.execute(
        text("SELECT current_database()")
    ).scalar()

    if db != "smarttec_erp_dev":
        raise RuntimeError(f"ABORTADO: banco incorreto = {db}")

    registros = list(conn.execute(
        text("""
            SELECT *
            FROM produtos
            WHERE empresa_id = 1
              AND id = ANY(:ids)
            ORDER BY id
        """),
        {"ids": ids_plano},
    ).mappings())

    if len(registros) != len(ids_plano):
        raise RuntimeError(
            f"ABORTADO: plano possui {len(ids_plano)} IDs, "
            f"mas apenas {len(registros)} foram encontrados."
        )

    # Backup integral antes da escrita
    serializaveis = []
    for r in registros:
        item = {}
        for k, v in dict(r).items():
            item[k] = v.isoformat() if hasattr(v, "isoformat") else v
        serializaveis.append(item)

    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(
            serializaveis,
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    ids_ativos = sorted(
        int(r["id"])
        for r in registros
        if bool(r["ativo"])
    )

    ids_ja_inativos = sorted(
        int(r["id"])
        for r in registros
        if not bool(r["ativo"])
    )

    print("Plano total:", len(ids_plano))
    print("Ainda ativos:", len(ids_ativos))
    print("Já inativos:", len(ids_ja_inativos))
    print("IDs já inativos:", ids_ja_inativos)

    if not ids_ativos:
        raise RuntimeError("ABORTADO: nenhum produto ativo restante no lote.")

    # Nenhum dos que serão inativados pode possuir dependência
    for tabela in (
        "orcamentos_itens",
        "pedidos_itens",
        "compras_itens",
        "estoque_movimentacoes",
        "empresa_equivalencias_tecnicas",
    ):
        qtd = conn.execute(
            text(f"""
                SELECT COUNT(*)
                FROM {tabela}
                WHERE produto_id = ANY(:ids)
            """),
            {"ids": ids_ativos},
        ).scalar()

        if qtd != 0:
            raise RuntimeError(
                f"ABORTADO: {qtd} dependência(s) em {tabela}."
            )

    total_antes = conn.execute(text("""
        SELECT COUNT(*) FROM produtos WHERE empresa_id = 1
    """)).scalar()

    ativos_antes = conn.execute(text("""
        SELECT COUNT(*)
        FROM produtos
        WHERE empresa_id = 1 AND ativo = true
    """)).scalar()

    equiv_antes = conn.execute(text("""
        SELECT COUNT(*)
        FROM empresa_equivalencias_tecnicas
        WHERE empresa_id = 1
    """)).scalar()

    resultado = conn.execute(
        text("""
            UPDATE produtos
            SET
                ativo = false,
                situacao = 'Inativo',
                status_comercial = 'INATIVO'
            WHERE empresa_id = 1
              AND id = ANY(:ids)
              AND ativo = true
        """),
        {"ids": ids_ativos},
    )

    if resultado.rowcount != len(ids_ativos):
        raise RuntimeError(
            f"ABORTADO: UPDATE parcial "
            f"{resultado.rowcount}/{len(ids_ativos)}."
        )

    ativos_restantes_lote = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM produtos
            WHERE empresa_id = 1
              AND id = ANY(:ids)
              AND ativo = true
        """),
        {"ids": ids_ativos},
    ).scalar()

    if ativos_restantes_lote != 0:
        raise RuntimeError(
            f"ABORTADO: {ativos_restantes_lote} registros "
            f"continuaram ativos."
        )

    total_depois = conn.execute(text("""
        SELECT COUNT(*) FROM produtos WHERE empresa_id = 1
    """)).scalar()

    ativos_depois = conn.execute(text("""
        SELECT COUNT(*)
        FROM produtos
        WHERE empresa_id = 1 AND ativo = true
    """)).scalar()

    equiv_depois = conn.execute(text("""
        SELECT COUNT(*)
        FROM empresa_equivalencias_tecnicas
        WHERE empresa_id = 1
    """)).scalar()

    if total_depois != total_antes:
        raise RuntimeError("ABORTADO: total de produtos mudou.")

    if ativos_depois != ativos_antes - len(ids_ativos):
        raise RuntimeError("ABORTADO: total final de ativos divergiu.")

    if equiv_depois != equiv_antes:
        raise RuntimeError("ABORTADO: equivalências foram alteradas.")

print()
print("====================================================")
print(" FASE 7Q - LOTE ESTRITO CONCLUÍDO")
print("====================================================")
print("Plano:", len(ids_plano))
print("Já estavam inativos:", len(ids_ja_inativos))
print("Inativados agora:", len(ids_ativos))
print("Backup:", backup_path)
print("Total de produtos:", total_depois)
print("Ativos antes:", ativos_antes)
print("Ativos depois:", ativos_depois)
print("Equivalências preservadas:", equiv_depois)
