"""Catálogo de serviços isolado em SQLite; nunca acessa PostgreSQL real."""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.cliente import ClienteDB  # noqa: F401
from app.models.empresa import EmpresaDB
from app.models.funcionario import FuncionarioDB  # noqa: F401
from app.models.orcamento import OrcamentoItemDB
from app.models.pedido import PedidoItemDB
from app.models.servico import ServicoDB
from app.routes import servico as routes
from app.schemas.orcamento import OrcamentoItemInput
from app.schemas.pedido import PedidoItemCreate
from app.schemas.servico import ServicoInput
from app.services import servico_service
from app.services.composicao_comercial import calcular_itens
from app.tenant.context import TenantContext


@compiles(JSONB, "sqlite")
def _sqlite_jsonb(tipo, compiler, **kwargs):
    return "JSON"


@pytest.fixture
def contexto():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def habilitar_fk(conexao, _):
        conexao.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine, tables=[
        Base.metadata.tables["empresas"],
        Base.metadata.tables["servicos"],
    ])
    with Session(engine) as db:
        db.add_all([
            EmpresaDB(id=1, nome="Empresa A", slug="empresa-a"),
            EmpresaDB(id=2, nome="Empresa B", slug="empresa-b"),
        ])
        db.commit()
        tenant = TenantContext(empresa_id=1)
        yield db, tenant
    engine.dispose()


def payload(**changes):
    values = {
        "codigo": "SRV-001",
        "descricao": "Instalação",
        "categoria": "Instalação",
        "unidade": "UN",
        "tipo_calculo": "POR_UNIDADE",
        "custo": 10,
        "preco_venda": 50,
        "comissao": None,
        "observacoes": None,
        "situacao": "ATIVO",
        "faixas_altura": [],
    }
    return ServicoInput(**{**values, **changes})


def criar_servico(db, empresa_id, dados):
    servico = ServicoDB(
        empresa_id=empresa_id,
        codigo=dados["codigo"],
        descricao=dados["descricao"],
        categoria=dados["categoria"],
        unidade=dados["unidade"],
        tipo_calculo=dados["tipo_calculo"],
        custo=dados["custo"],
        preco_venda=dados["preco_venda"],
        comissao=dados["comissao"],
        observacoes=dados["observacoes"],
        situacao=dados["situacao"],
        faixas_altura=dados["faixas_altura"],
    )
    db.add(servico)
    db.commit()
    return servico


def test_crud_busca_e_isolamento_por_empresa(contexto):
    db, tenant = contexto
    forged_payload = ServicoInput(**{**payload().dict(), "empresa_id": 2})
    criado = routes.criar(forged_payload, db, tenant)
    servico_id = criado["id"]
    assert criado["empresa_id"] == 1
    assert routes.listar("instala", True, db, tenant)[0]["id"] == servico_id

    atualizado = payload(descricao="Instalação técnica", situacao="INATIVO")
    resposta = routes.atualizar(servico_id, atualizado, db, tenant)
    assert resposta["situacao"] == "INATIVO"
    assert routes.listar(None, False, db, tenant) == []

    outra_empresa = TenantContext(empresa_id=2)
    with pytest.raises(HTTPException) as erro:
        routes.obter(servico_id, db, outra_empresa)
    assert erro.value.status_code == 404
    with pytest.raises(HTTPException) as erro:
        routes.atualizar(servico_id, payload(), db, outra_empresa)
    assert erro.value.status_code == 404


def test_validacao_de_faixas_de_lavagem_sem_tarifa_inventada():
    with pytest.raises(ValueError, match="pelo menos uma faixa"):
        payload(categoria="Lavagem", tipo_calculo="FAIXA_ALTURA")
    servico = payload(
        categoria="Lavagem",
        tipo_calculo="FAIXA_ALTURA",
        unidade="UN",
        faixas_altura=[
            {"altura_max_cm": 100, "preco_unitario": 12},
            {"altura_max_cm": 200, "preco_unitario": 19},
        ],
    )
    assert [str(faixa.preco_unitario) for faixa in servico.faixas_altura] == ["12", "19"]
    registro = SimpleNamespace(tipo_calculo=servico.tipo_calculo, preco_venda=0, faixas_altura=[
        {"altura_max_cm": "100", "preco_unitario": "12"},
        {"altura_max_cm": "200", "preco_unitario": "19"},
    ])
    assert servico_service.calcular_preco_altura(registro, 100) == Decimal("12.0000")
    assert servico_service.calcular_preco_altura(registro, 100.01) == Decimal("19.0000")
    with pytest.raises(ValueError, match="não possui faixa"):
        servico_service.calcular_preco_altura(registro, 201)


@pytest.mark.parametrize("item_model,item_schema", [
    (OrcamentoItemDB, OrcamentoItemInput),
    (PedidoItemDB, PedidoItemCreate),
])
def test_integracao_orcamento_pedido_preco_negociado_e_snapshot(contexto, item_model, item_schema):
    db, tenant, *_ = contexto
    servico = criar_servico(db, 1, payload().dict())
    documento = SimpleNamespace(itens=[])
    data_item = item_schema(
        tipo_item="SERVICO",
        servico_id=servico.id,
        descricao="Instalação negociada",
        unidade="UN",
        quantidade=2,
        preco_unitario=30,
        preco_unitario_manual=True,
        desconto=5,
    )
    data = SimpleNamespace(perfil_comercial="VAREJO", itens=[data_item])
    calcular_itens(db, documento, data, 1, item_model)
    item = documento.itens[0]
    assert item.servico_id == servico.id
    assert item.descricao == "Instalação negociada"
    assert item.preco_unitario == Decimal("30")
    assert item.subtotal == Decimal("55.00")
    assert item.unidade == "UN"
    assert item.empresa_id == tenant.empresa_id


def test_preco_padrao_do_catalogo_e_servico_livre_historico(contexto):
    db, *_ = contexto
    servico = criar_servico(db, 1, payload(preco_venda=50).dict())
    catalogo = OrcamentoItemInput(
        tipo_item="SERVICO", servico_id=servico.id, descricao="Instalação",
        unidade="UN", quantidade=3, preco_unitario=5, preco_unitario_manual=False, desconto=5,
    )
    livre_antigo = OrcamentoItemInput(
        tipo_item="SERVICO", descricao="Serviço antigo", unidade="HORA",
        quantidade=2, preco_unitario=12, desconto=2,
    )
    documento = SimpleNamespace(itens=[])
    calcular_itens(
        db, documento, SimpleNamespace(perfil_comercial="VAREJO", itens=[catalogo, livre_antigo]),
        1, OrcamentoItemDB,
    )
    assert documento.itens[0].preco_unitario == Decimal("50")
    assert documento.itens[0].subtotal == Decimal("145.00")
    assert documento.itens[1].servico_id is None
    assert documento.itens[1].descricao == "Serviço antigo"
    assert documento.itens[1].preco_unitario == Decimal("12")
    assert documento.itens[1].subtotal == Decimal("22.00")
    assert documento.itens[1].empresa_id == 1


def test_preco_padrao_lavagem_calculado_por_altura(contexto):
    from app.models.servico import ServicoDB

    service = ServicoDB(
        id=1, empresa_id=1, codigo="LAV-1", descricao="Lavagem", categoria="Lavagem",
        unidade="UN", tipo_calculo="FAIXA_ALTURA", custo=0, preco_venda=0, situacao="ATIVO",
        faixas_altura=[
            {"altura_max_cm": "100", "preco_unitario": "12.5"},
            {"altura_max_cm": "200", "preco_unitario": "22"},
        ],
    )
    class Item:
        def __init__(self, **values):
            self.__dict__.update(values)
        def dict(self, include=None):
            return {key: value for key, value in self.__dict__.items() if include is None or key in include}

    item = Item(
        tipo_item="SERVICO", produto_id=None, servico_id=1, descricao="Lavagem",
        codigo_interno=None, grupo_tecnico=None, modelo_tecnico=None, unidade="UN",
        quantidade=2, largura=0, altura=1.5, area=0, preco_unitario=0, desconto=0,
        subtotal=0, observacao_item=None, material=None, cor=None, acionamento=None,
        lado_comando=None, calculo_producao_status=None, dados_tecnicos=None,
        preco_unitario_manual=False,
    )
    db, *_ = contexto
    db.add(service)
    db.commit()
    documento = SimpleNamespace(itens=[])
    calcular_itens(db, documento, SimpleNamespace(perfil_comercial="VAREJO", itens=[item]), 1, OrcamentoItemDB)
    assert Decimal(str(documento.itens[0].preco_unitario)) == Decimal("22.0000")
    assert Decimal(str(documento.itens[0].subtotal)) == Decimal("44.00")


@pytest.mark.parametrize("item_model,item_schema", [
    (OrcamentoItemDB, OrcamentoItemInput),
    (PedidoItemDB, PedidoItemCreate),
])
def test_servico_de_outra_empresa_e_rejeitado(contexto, item_model, item_schema):
    db, *_ = contexto
    foreign = criar_servico(db, 2, payload(codigo="SRV-OUTRO").dict())
    item = item_schema(
        tipo_item="SERVICO", servico_id=foreign.id, descricao="Alheio",
        quantidade=1, preco_unitario=10,
    )
    with pytest.raises(ValueError, match="empresa ativa"):
        calcular_itens(
            db, SimpleNamespace(itens=[]),
            SimpleNamespace(perfil_comercial="VAREJO", itens=[item]),
            1, item_model,
        )


def test_migration_declara_relacoes_compostas_por_empresa():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    migration = (root / "migrations" / "20261107_servicos_v1_up.sql").read_text(
        encoding="utf-8"
    )
    rollback = (root / "migrations" / "20261107_servicos_v1_down.sql").read_text(
        encoding="utf-8"
    )
    for constraint in (
        "fk_orcamentos_itens_documento_empresa_servicos_v1",
        "fk_orcamentos_itens_servico_empresa_v1",
        "fk_pedidos_itens_documento_empresa_servicos_v1",
        "fk_pedidos_itens_servico_empresa_v1",
    ):
        assert constraint in migration
        assert constraint in rollback
    assert "NEW.empresa_id := v_empresa_id" in migration
    assert "FOREIGN KEY (servico_id, empresa_id)" in migration
    assert "ON DELETE SET NULL" in migration
    assert migration.count("FROM pg_index i") == 2
    assert migration.count("i.indisunique") == 2
    assert migration.count("i.indisvalid") == 2
    assert migration.count("i.indpred IS NULL") == 2
    assert migration.count("i.indkey[0]") == 2
    assert migration.count("i.indkey[1]") == 2
    assert "preco_unitario" not in migration.lower()
    assert "descricao =" not in migration.lower()


def test_rollback_em_falha_de_persistencia(contexto):
    db, tenant, *_ = contexto
    data = payload()
    with patch.object(db, "commit", side_effect=RuntimeError("falha simulada")):
        with pytest.raises(RuntimeError, match="falha simulada"):
            servico_service.criar(db, tenant, data)
    assert db.query(ServicoDB).filter(ServicoDB.empresa_id == 1).count() == 0
