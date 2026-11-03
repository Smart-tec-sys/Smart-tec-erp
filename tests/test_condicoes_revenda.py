"""Regras aprovadas de acrescimo e pagamento; nunca acessa PostgreSQL."""
from datetime import datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException

from test_orcamento_cortina_pdf_local import db  # noqa: F401
from app.models.orcamento import OrcamentoDB, OrcamentoItemDB
from app.routes.orcamento import atualizar_condicoes_revenda as rota_condicoes
from app.schemas.orcamento import OrcamentoCondicoesRevendaInput
from app.services import orcamento_service
from app.services.condicoes_revenda import calcular_condicoes_revenda, textos_condicoes_revenda
from app.tenant.context import TenantContext


def calcular(base="1000", **kw):
    return calcular_condicoes_revenda(base, kw.get("percentual", 50),
                                      kw.get("desconto", 5), kw.get("taxa", "7.2"),
                                      kw.get("parcelas", 3))


def test_exemplo_obrigatorio():
    c = calcular()
    assert c["base_smarttec"] == 1000 and c["acrescimo_parceiro"] == 500
    assert c["preco_cliente"] == 1500
    assert c["total_cartao"] == 1608 and c["acrescimo_cartao"] == 108
    assert c["parcelas"] == [536, 536, 536]
    assert c["total_descontado"] == 1425
    assert c["smarttec_descontado"] == 950 and c["parceiro_descontado"] == 475


def test_cenario_base_real_sem_dividir_recebido_ou_reduzir_base():
    c = calcular("2854.21")
    assert c["acrescimo_parceiro"] == Decimal("1427.11")
    assert c["preco_cliente"] == Decimal("4281.32")
    assert c["total_cartao"] == Decimal("4589.58")
    assert c["acrescimo_cartao"] == Decimal("308.26")
    assert c["parcelas"] == [Decimal("1529.86")] * 3
    assert c["total_descontado"] == Decimal("4067.25")
    assert c["smarttec_descontado"] == Decimal("2711.50")
    assert c["parceiro_descontado"] == Decimal("1355.75")
    assert c["entrada"] == Decimal("2033.63") and c["saldo"] == Decimal("2033.62")
    assert c["total_cartao"] - c["acrescimo_cartao"] - c["acrescimo_parceiro"] == c["base_smarttec"]
    publico, interno = textos_condicoes_revenda(c)
    for valor in ("50%", "7.2%", "7,2%", "Smart-tec", "parceira", "taxa", "lucro"):
        assert valor not in publico
    for valor in ("4.281,32", "4.067,25", "4.589,58", "2.033,63", "2.033,62"):
        assert valor in publico
    for valor in ("50%", "7,2%", "1.427,11", "2.854,21", "308,26", "nao lucro"):
        assert valor in interno


@pytest.mark.parametrize("base", ["0.01", "0.03", "19.99", "1000", "2854.21"])
def test_centavos_fecham_distribuicao_e_parcelas(base):
    c = calcular(base)
    assert c["smarttec_descontado"] + c["parceiro_descontado"] == c["total_descontado"]
    assert c["entrada"] + c["saldo"] == c["total_descontado"]
    assert sum(c["parcelas"]) == c["total_cartao"]
    assert c["base_smarttec"] + c["acrescimo_parceiro"] == c["preco_cliente"]


@pytest.mark.parametrize("base,kw", [
    ("0", {}), ("0.001", {}), ("-1", {}), ("nan", {}), ("inf", {}),
    ("1000", {"percentual": -1}), ("1000", {"desconto": 100}),
    ("1000", {"taxa": 100}), ("1000", {"parcelas": 0}),
    ("1000", {"parcelas": 3.5}), ("1000", {"parcelas": True}),
])
def test_entradas_invalidas(base, kw):
    with pytest.raises(ValueError):
        calcular(base, **kw)


def inserir_orcamento(db):
    o = OrcamentoDB(empresa_id=1, numero="TESTE-REVENDA", parceiro_id=1,
                    cliente_final_nome="Cliente ficticio", total=2854.21, total_final=2854.21,
                    base_protegida=2854.21, total_cliente_final=2854.21,
                    observacao="Texto antigo", observacao_interna="Interno anterior")
    o.itens = [OrcamentoItemDB(tipo_item="SERVICO", descricao="Instalacao teste",
                               quantidade=Decimal("8.43"), preco_unitario=45, subtotal=379.35)]
    db.add(o)
    db.commit()
    return o


def entrada(o, **kw):
    valores = dict(base_smarttec_esperada=float(o.total_final),
                   total_cliente_esperado=float(o.total_cliente_final),
                   atualizado_em_esperado=o.atualizado_em, percentual_parceiro=50,
                   desconto_pagamento_percentual=5, acrescimo_cartao_percentual=7.2,
                   parcelas_cartao=3, observacao_comercial="Prazo e garantia aprovados.",
                   observacao_interna="Custos industriais privados.")
    return OrcamentoCondicoesRevendaInput(**(valores | kw))


def test_atualizar_somente_composicao_e_observacoes_reabrir_sem_recriar_itens(db):
    o = inserir_orcamento(db)
    outro = OrcamentoDB(empresa_id=1, numero="OUTRO", total=42, total_final=42,
                        total_cliente_final=42)
    db.add(outro)
    db.commit()
    item_id = o.itens[0].id
    data = entrada(o, observacoes_itens={item_id: "Instalacao de 8,43 metros lineares."})
    result = orcamento_service.atualizar_condicoes_revenda(db, o.id, data, TenantContext(empresa_id=1))
    db.expire_all()
    salvo = orcamento_service.obter(db, o.id, TenantContext(empresa_id=1))
    assert salvo["total_final"] == result["total_final"] == 2854.21
    assert salvo["percentual_parceiro"] == 50 and salvo["valor_parceiro"] == 1427.11
    assert salvo["base_protegida"] == salvo["total_cliente_final"] == 4281.32
    assert salvo["incluir_taxa_bancaria"] is False and salvo["valor_taxa_bancaria"] == 0
    assert salvo["itens"][0]["id"] == item_id
    assert salvo["itens"][0]["subtotal"] == 379.35
    assert salvo["itens"][0]["quantidade"] == 8.43
    assert salvo["itens"][0]["observacao_item"] == "Instalacao de 8,43 metros lineares."
    assert "50%" not in salvo["observacao"] and "7,2%" not in salvo["observacao"]
    assert "50%" in salvo["observacao_interna"] and "7,2%" in salvo["observacao_interna"]
    assert db.get(OrcamentoDB, outro.id).total_cliente_final == 42


@pytest.mark.parametrize("mudanca", [
    {"base_smarttec_esperada": 1}, {"total_cliente_esperado": 1},
    {"atualizado_em_esperado": datetime(2000, 1, 1)}, {"observacoes_itens": {9999: "indevido"}},
])
def test_concorrencia_e_item_invalido_nao_alteram_orcamento(db, mudanca):
    o = inserir_orcamento(db)
    with pytest.raises(ValueError):
        orcamento_service.atualizar_condicoes_revenda(db, o.id, entrada(o, **mudanca), TenantContext(empresa_id=1))
    db.refresh(o)
    assert o.total_cliente_final == Decimal("2854.21")
    assert o.percentual_parceiro == 0 and o.observacao == "Texto antigo"


@pytest.mark.parametrize("campo,valor", [
    ("status", "APROVADO"), ("parceiro_id", None), ("incluir_rt", True),
    ("incluir_taxa_bancaria", True),
])
def test_rejeita_documento_incompativel(db, campo, valor):
    o = inserir_orcamento(db)
    setattr(o, campo, valor)
    db.commit()
    with pytest.raises(ValueError, match="somente para revenda"):
        orcamento_service.atualizar_condicoes_revenda(db, o.id, entrada(o), TenantContext(empresa_id=1))


def test_rota_respeita_empresa_e_expoe_conflito(db):
    o = inserir_orcamento(db)
    with pytest.raises(HTTPException) as exc:
        rota_condicoes(o.id, entrada(o), db, TenantContext(empresa_id=2))
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        rota_condicoes(o.id, entrada(o, base_smarttec_esperada=1), db, TenantContext(empresa_id=1))
    assert exc.value.status_code == 422
