"""Condições de pagamento de orçamento em SQLite; nunca acessa produção."""
from datetime import date
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"

from app.database import Base
from app.models.cliente import ClienteDB
from app.models.empresa import EmpresaDB
from app.models.financeiro_cadastros import FormaPagamentoDB
from app.models.orcamento import OrcamentoParcelaDB  # noqa: F401
from app.schemas.orcamento import OrcamentoInput
from app.services import orcamento_service
from app.tenant.context import TenantContext


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    names = ("empresas", "clientes", "funcionarios", "produtos", "formas_pagamento",
             "orcamentos", "orcamentos_itens", "orcamento_parcelas")
    Base.metadata.create_all(engine, tables=[Base.metadata.tables[name] for name in names])
    with Session(engine) as session:
        session.add_all([
            EmpresaDB(id=1, nome="Empresa 1", slug="empresa-1"),
            EmpresaDB(id=2, nome="Empresa 2", slug="empresa-2"),
            ClienteDB(id=1, empresa_id=1, tipo="Pessoa Física", nome="Cliente"),
            FormaPagamentoDB(id=1, empresa_id=1, nome="Pix", tipo="PIX", disponivel_para="AMBOS", ativo=True),
            FormaPagamentoDB(id=2, empresa_id=1, nome="Cartão", tipo="CARTAO", disponivel_para="RECEBER", ativo=True),
            FormaPagamentoDB(id=3, empresa_id=2, nome="Forma alheia", tipo="PIX", disponivel_para="AMBOS", ativo=True),
        ])
        session.commit()
        yield session
    engine.dispose()


def entrada(**changes):
    values = {
        "cliente_id": 1,
        "perfil_comercial": "VAREJO",
        "itens": [{"tipo_item": "SERVICO", "descricao": "Serviço", "quantidade": 1,
                   "preco_unitario": 100, "subtotal": 100}],
    }
    values.update(changes)
    return OrcamentoInput(**values)


def salvar(db, data):
    with patch.object(orcamento_service, "_numero", return_value="PAG-LOCAL"):
        return orcamento_service.criar(db, data, TenantContext(empresa_id=1))


def test_parcelado_fecha_centavos_e_persiste(db):
    data = entrada(
        pagamento_modalidade="PARCELADO", pagamento_numero_parcelas=3,
        pagamento_intervalo_dias=30, pagamento_primeiro_vencimento=date(2026, 11, 10),
        pagamento_parcelas=[
            {"numero": 1, "valor": "33.33", "vencimento": "2026-11-10", "forma_pagamento_id": 2},
            {"numero": 2, "valor": "33.33", "vencimento": "2026-12-10", "forma_pagamento_id": 2},
            {"numero": 3, "valor": "33.34", "vencimento": "2027-01-09", "forma_pagamento_id": 2},
        ],
    )
    result = salvar(db, data)
    assert result["pagamento_total"] == 100
    assert [item["valor"] for item in result["pagamento_parcelas"]] == [33.33, 33.33, 33.34]
    assert result["pagamento_parcelas"][0]["forma_pagamento_nome"] == "Cartão"
    assert orcamento_service.obter(db, result["id"], TenantContext(empresa_id=2)) is None


@pytest.mark.parametrize("mode,count,parcels", [
    ("AVISTA", 1, [{"numero": 1, "tipo": "PARCELA", "valor": "90.00", "vencimento": "2026-11-10", "forma_pagamento_id": 1}]),
    ("ENTRADA_SALDO", 2, [
        {"numero": 1, "tipo": "ENTRADA", "valor": "40.00", "vencimento": "2026-11-10", "forma_pagamento_id": 1},
        {"numero": 2, "tipo": "SALDO", "valor": "50.00", "vencimento": "2026-12-10", "forma_pagamento_id": 2},
    ]),
])
def test_desconto_avista_e_entrada_saldo(mode, count, parcels, db):
    result = salvar(db, entrada(
        desconto=10, pagamento_modalidade=mode, pagamento_numero_parcelas=count,
        pagamento_intervalo_dias=30, pagamento_primeiro_vencimento=date(2026, 11, 10),
        pagamento_parcelas=parcels,
    ))
    assert result["total_cliente_final"] == 90
    assert result["pagamento_total"] == 90


def test_taxa_bancaria_aplicada_uma_vez(db):
    result = salvar(db, entrada(
        incluir_taxa_bancaria=True, taxa_bancaria_percentual=10,
        pagamento_modalidade="AVISTA", pagamento_numero_parcelas=1,
        pagamento_intervalo_dias=0, pagamento_primeiro_vencimento=date(2026, 11, 10),
        pagamento_parcelas=[{"numero": 1, "valor": "111.11", "vencimento": "2026-11-10", "forma_pagamento_id": 1}],
    ))
    assert result["total_cliente_final"] == 111.11
    assert result["pagamento_total"] == 111.11


def test_quantidade_comercial_maior_que_um(db):
    result = salvar(db, entrada(
        itens=[{"tipo_item": "SERVICO", "descricao": "Serviço", "quantidade": 2,
                "preco_unitario": 100, "subtotal": 200}],
        pagamento_modalidade="PARCELADO", pagamento_numero_parcelas=2,
        pagamento_intervalo_dias=30, pagamento_primeiro_vencimento=date(2026, 11, 10),
        pagamento_parcelas=[
            {"numero": 1, "valor": "100.00", "vencimento": "2026-11-10", "forma_pagamento_id": 2},
            {"numero": 2, "valor": "100.00", "vencimento": "2026-12-10", "forma_pagamento_id": 2},
        ],
    ))
    assert result["total_cliente_final"] == 200
    assert result["pagamento_total"] == 200


def test_bloqueia_soma_incorreta_e_forma_de_outra_empresa(db):
    base = dict(pagamento_modalidade="AVISTA", pagamento_numero_parcelas=1,
                pagamento_intervalo_dias=0, pagamento_primeiro_vencimento=date(2026, 11, 10))
    with pytest.raises(ValueError, match="soma das parcelas"):
        salvar(db, entrada(**base, pagamento_parcelas=[{"numero": 1, "valor": "99.99", "vencimento": "2026-11-10", "forma_pagamento_id": 1}]))
    with pytest.raises(ValueError, match="empresa ativa"):
        salvar(db, entrada(**base, pagamento_parcelas=[{"numero": 1, "valor": "100.00", "vencimento": "2026-11-10", "forma_pagamento_id": 3}]))


def test_orcamento_antigo_sem_plano_continua_compativel(db):
    result = salvar(db, entrada())
    assert result["pagamento_modalidade"] is None
    assert result["pagamento_parcelas"] == []
