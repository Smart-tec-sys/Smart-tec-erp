"""Produção isolada em SQLite/mocks: nunca conecta nem altera PostgreSQL."""
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models.cliente import ClienteDB  # noqa: F401
from app.models.funcionario import FuncionarioDB  # noqa: F401
from app.models.empresa import EmpresaDB
from app.models.pedido import PedidoDB, PedidoItemDB
from app.models.produto import ProdutoDB
from app.models.producao import OrdemProducaoDB, PecaProducaoDB
from app.routes.producao import router
from app.services import producao_service as service
from app.services.producao_documentos import etiqueta_da_peca, ficha_html
from app.tenant.context import LEGACY_UNSCOPED, TenantContext
from app.tenant.dependencies import get_current_tenant


@compiles(JSONB, "sqlite")
def _sqlite_jsonb(tipo, compiler, **kwargs):
    return "JSON"


@pytest.fixture
def contexto(monkeypatch):
    monkeypatch.setenv("PRODUCAO_V1_ENABLED", "true")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    @event.listens_for(engine, "connect")
    def habilitar_fk(conexao, _):
        conexao.execute("PRAGMA foreign_keys=ON")
    nomes = ("empresas", "clientes", "funcionarios", "produtos", "orcamentos", "orcamentos_itens",
             "parceiros_comerciais", "representantes", "pedidos", "pedidos_itens",
             "ordens_producao", "producao_pecas")
    Base.metadata.create_all(engine, tables=[Base.metadata.tables[n] for n in nomes])
    with Session(engine) as db:
        db.add_all([EmpresaDB(id=1, nome="Fábrica <Teste>", slug="teste"),
                    EmpresaDB(id=2, nome="Outra", slug="outra")])
        db.flush()
        db.add_all([
            ProdutoDB(id=i, empresa_id=1, nome=nome, custo_final=custo, situacao="Ativo",
                      estoque_atual=50, saldo_metros=80, modelo_tecnico=None,
                      grupo_tecnico="TECIDOS_CORTINA" if i == 1 else "COMPONENTES_CORTINAS")
            for i, nome, custo in ((1, "Tecido", 10), (2, "Trilho", 20),
                                    (3, "Rodízio", .5), (4, "Entretela", 1))
        ])
        db.add(ProdutoDB(id=20, empresa_id=2, nome="Alheio", custo_final=10, situacao="Ativo"))
        venda = PedidoDB(id=1, empresa_id=1, numero="VEN-1", status="ABERTO",
                         perfil_comercial="VAREJO", total=600, total_final=600)
        venda.itens = [PedidoItemDB(
            id=1, tipo_item="PRODUTO", produto_id=None, descricao="Cortina",
            modelo_tecnico="CORTINA", material="Tecido", cor="Branco", acionamento="Manual",
            largura=2, altura=2, quantidade=2, preco_unitario=300, subtotal=600, desconto=0,
            observacao_item="Conferir acabamento",
            dados_tecnicos={"cortina": {
                "tecidoProdutoId": 1, "trilhoProdutoId": 2, "rodizioProdutoId": 3,
                "entretelaProdutoId": 4, "fator": 2.5, "larguraTecido": 3, "modeloPrega": "PREGA",
            }},
        )]
        db.add(venda)
        db.commit()
        tenant = TenantContext(empresa_id=1, user_id=7)
        api = FastAPI()
        api.include_router(router, prefix="/producao")
        api.dependency_overrides[get_db] = lambda: db
        api.dependency_overrides[get_current_tenant] = lambda: tenant
        with TestClient(api) as client:
            yield db, tenant, venda, api, client
    engine.dispose()


def preparar(db, tenant):
    op = service.criar(db, 1, tenant, True)
    for peca in op.pecas:
        service.alterar_peca(db, op.id, peca.id, tenant, {"ambiente": "Sala", "observacoes": "Manual"})
    return op


@pytest.mark.parametrize("status", ["ABERTO", "CONCLUIDO", "FATURADO"])
def test_confirmacao_explicita_sem_alterar_comercial(contexto, status):
    db, tenant, venda, _, _ = contexto
    venda.status = status
    db.flush()
    op = service.criar(db, 1, tenant, True)
    assert venda.status == status
    assert op.confirmado_por == "7"
    assert isinstance(op.confirmado_em, datetime) and op.confirmado_em.tzinfo is not None
    assert op.liberado_em is None and len(op.pecas) == 2
    assert [(p.pedido_item_id, p.sequencia, p.status) for p in op.pecas] == [
        (1, 1, "AGUARDANDO"), (1, 2, "AGUARDANDO")]
    assert op.pecas[0].tecido == "Tecido" and op.pecas[0].cor == "Branco"
    assert db.get(ProdutoDB, 1).estoque_atual == 50
    assert venda.total_final == Decimal("600.00")


def test_bloqueios_confirmacao_e_usuario(contexto):
    db, tenant, *_ = contexto
    with pytest.raises(ValueError, match="explicitamente"):
        service.criar(db, 1, tenant, False)
    with pytest.raises(PermissionError, match="identificado"):
        service.criar(db, 1, TenantContext(empresa_id=1), True)
    assert db.query(OrdemProducaoDB).count() == 0


@pytest.mark.parametrize("status", ["CANCELADO", "DESCONHECIDO"])
def test_venda_bloqueada(contexto, status):
    db, tenant, venda, *_ = contexto
    venda.status = status
    db.flush()
    with pytest.raises(ValueError, match="cancelada"):
        service.criar(db, 1, tenant, True)


@pytest.mark.parametrize("quantidade", ["0", "-1", "1.25"])
def test_quantidades_invalidas(contexto, quantidade):
    db, tenant, venda, *_ = contexto
    venda.itens[0].quantidade = Decimal(quantidade)
    db.flush()
    with pytest.raises(ValueError, match="quantidade|peças"):
        service.criar(db, 1, tenant, True)
    assert db.query(OrdemProducaoDB).count() == 0


def test_servicos_nao_geram_pecas(contexto):
    db, tenant, venda, *_ = contexto
    venda.itens.append(PedidoItemDB(tipo_item="SERVICO", descricao="Instalação", quantidade=1,
                                   largura=0, altura=0, preco_unitario=50))
    db.flush()
    assert len(service.criar(db, 1, tenant, True).pecas) == 2


def test_servico_isolado_nao_gera_op(contexto):
    db, tenant, venda, *_ = contexto
    venda.itens[0].tipo_item = "SERVICO"
    db.flush()
    with pytest.raises(ValueError, match="sem produtos"):
        service.criar(db, 1, tenant, True)


def test_duplicidade_venda_e_restricao_concorrencia_peca(contexto):
    db, tenant, *_ = contexto
    op = preparar(db, tenant)
    with pytest.raises(ValueError, match="já possui"):
        service.criar(db, 1, tenant, True)
    db.commit()
    with pytest.raises(IntegrityError):
        db.add(PecaProducaoDB(ordem_id=op.id, pedido_item_id=1, sequencia=1, largura=2, altura=2))
        db.flush()
    db.rollback()
    assert db.query(PecaProducaoDB).count() == 2
    with pytest.raises(IntegrityError):
        db.add(OrdemProducaoDB(empresa_id=1, pedido_id=1, confirmado_por="9",
                              confirmado_em=service._agora(), snapshot={}))
        db.flush()
    db.rollback()


def test_isolamento_tenant_e_peca(contexto):
    db, tenant, *_ = contexto
    op = preparar(db, tenant)
    outro = TenantContext(empresa_id=2, user_id=7)
    assert service.listar(db, 1, outro) == []
    with pytest.raises(LookupError):
        service.criar(db, 1, outro, True)
    for acao in (
        lambda: service.obter(db, op.id, outro),
        lambda: service.liberar(db, op.id, outro, True),
        lambda: service.alterar_peca(db, op.id, op.pecas[0].id, outro, {"ambiente": "X", "observacoes": ""}),
        lambda: service.alterar_peca(db, op.id, 999, tenant, {"ambiente": "X", "observacoes": ""}),
    ):
        with pytest.raises(LookupError):
            acao()


def test_recupera_cortes_e_insumos_recalculados_por_peca(contexto):
    db, tenant, venda, *_ = contexto
    venda.itens[0].dados_tecnicos = {**venda.itens[0].dados_tecnicos, "result": {"custo_completo": True, "tecido": "FALSO"}}
    op = preparar(db, tenant)
    dados = service.serializar(db, op)
    assert dados["pendencias"] == []
    calculo = dados["calculos_por_peca"]["1"]
    assert calculo["quantidade_pecas"] == 1
    assert calculo["tecido"]["consumo_total_ml"] == 4.8
    assert calculo["tecido"]["quantidade_alturas"] == 2
    assert {c["produto_id"] for c in calculo["composicao"]} == {1, 2, 3, 4, None}
    service.liberar(db, op.id, tenant, True)
    assert op.liberado_por == "7" and op.liberado_em.tzinfo is not None
    congelado = deepcopy(op.snapshot["calculos_por_peca"])
    db.get(ProdutoDB, 1).custo_final = 100
    db.flush()
    assert service.serializar(db, op)["calculos_por_peca"] == congelado
    assert venda.status == "ABERTO" and venda.total_final == Decimal("600.00")
    with pytest.raises(ValueError, match="já liberada"):
        service.liberar(db, op.id, tenant, True)
    with pytest.raises(ValueError, match="imutável"):
        service.alterar_peca(db, op.id, op.pecas[0].id, tenant, {"ambiente": "Quarto", "observacoes": ""})


@pytest.mark.parametrize("mudanca", [
    "ausente", "inativo", "outro_tenant", "lista_livre", "custo_venda",
    "componente_incompativel", "prega_desconhecida", "fator_insuficiente",
])
def test_insumos_incompletos_bloqueiam(contexto, mudanca):
    db, tenant, venda, *_ = contexto
    config = deepcopy(venda.itens[0].dados_tecnicos)
    if mudanca == "ausente":
        config["cortina"].pop("trilhoProdutoId")
    elif mudanca == "inativo":
        db.get(ProdutoDB, 2).situacao = "Inativo"
    elif mudanca == "outro_tenant":
        config["cortina"]["tecidoProdutoId"] = 20
    elif mudanca == "lista_livre":
        config["cortina"]["componentes"] = []
    elif mudanca == "custo_venda":
        db.get(ProdutoDB, 2).custo_final = 0
        db.get(ProdutoDB, 2).valor_venda = 20
    elif mudanca == "componente_incompativel":
        db.get(ProdutoDB, 2).grupo_tecnico = "COMPONENTES_PERSIANAS"
    elif mudanca == "prega_desconhecida":
        config["cortina"]["modeloPrega"] = "DESCONHECIDA"
    else:
        config["cortina"]["fator"] = .5
    venda.itens[0].dados_tecnicos = config
    db.flush()
    op = preparar(db, tenant)
    with pytest.raises(ValueError, match="bloqueada"):
        service.liberar(db, op.id, tenant, True)
    assert op.liberado_em is None


@pytest.mark.parametrize("modelo", ["ROLO", "DOUBLE_VISION", "ROMANA", "OUTRO"])
def test_modelos_incompletos_bloqueados(contexto, modelo):
    db, tenant, venda, *_ = contexto
    venda.itens[0].modelo_tecnico = modelo
    venda.itens[0].produto_id = 1
    db.flush()
    op = preparar(db, tenant)
    assert service.serializar(db, op)["pendencias"]
    with pytest.raises(ValueError, match="bloqueada"):
        service.liberar(db, op.id, tenant, True)


def test_campos_basicos_ausentes_impedem_liberacao(contexto):
    db, tenant, venda, *_ = contexto
    venda.itens[0].cor = ""
    db.flush()
    op = service.criar(db, 1, tenant, True)
    pendencias = service.serializar(db, op)["pendencias"]
    assert any("ambiente" in p for p in pendencias)
    assert any("cor" in p for p in pendencias)
    with pytest.raises(ValueError, match="bloqueada"):
        service.liberar(db, op.id, tenant, True)


@pytest.mark.parametrize("dados", [None, [], {"cortina": "inválido"}, {"cortina": {"componentes": None}},
                                  {"cortina": {"componentes": [1]}}])
def test_parametros_tecnicos_invalidos_geram_pendencia_explicita(contexto, dados):
    db, tenant, venda, *_ = contexto
    venda.itens[0].dados_tecnicos = dados
    db.flush()
    op = preparar(db, tenant)
    assert service.serializar(db, op)["pendencias"]
    with pytest.raises(ValueError, match="bloqueada"):
        service.liberar(db, op.id, tenant, True)


def test_status_sequenciais_sem_saltos_e_dados_desatualizados(contexto):
    db, tenant, *_ = contexto
    op = preparar(db, tenant)
    peca = op.pecas[0]
    with pytest.raises(ValueError, match="Libere"):
        service.alterar_peca(db, op.id, peca.id, tenant, {"status_atual": "AGUARDANDO", "status": "CORTE"})
    service.liberar(db, op.id, tenant, True)
    with pytest.raises(ValueError, match="Transição"):
        service.alterar_peca(db, op.id, peca.id, tenant, {"status_atual": "AGUARDANDO", "status": "MONTAGEM"})
    for anterior, proximo in zip(service.STATUS, service.STATUS[1:]):
        data = {"status_atual": anterior, "status": proximo}
        service.alterar_peca(db, op.id, peca.id, tenant, data)
        with pytest.raises(ValueError, match="desatualizada"):
            service.alterar_peca(db, op.id, peca.id, tenant, data)
    assert peca.status == "CONCLUIDA"
    assert len(peca.historico) == 4
    assert all(h["usuario"] == "7" and datetime.fromisoformat(h["em"]).tzinfo for h in peca.historico)
    assert service.serializar(db, op)["status"] == "AGUARDANDO"


def test_cancelamento_posterior_bloqueia_liberacao_e_andamento(contexto):
    db, tenant, venda, *_ = contexto
    op = preparar(db, tenant)
    venda.status = "CANCELADO"
    db.flush()
    with pytest.raises(ValueError, match="cancelada"):
        service.liberar(db, op.id, tenant, True)
    venda.status = "CONCLUIDO"
    db.flush()
    service.liberar(db, op.id, tenant, True)
    venda.status = "CANCELADO"
    db.flush()
    with pytest.raises(ValueError, match="cancelada"):
        service.alterar_peca(db, op.id, op.pecas[0].id, tenant,
                            {"status_atual": "AGUARDANDO", "status": "CORTE"})


def test_rastreabilidade_snapshot_e_restricao_exclusao(contexto):
    db, tenant, venda, *_ = contexto
    op = preparar(db, tenant)
    dados = deepcopy(op.snapshot)
    venda.itens[0].material = "Alterado"
    db.commit()
    assert op.pecas[0].tecido == "Tecido" and op.snapshot == dados
    db.delete(venda.itens[0])
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
    db.delete(venda)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
    assert db.query(OrdemProducaoDB).count() == 1


def test_html_escapado_e_reuso_literal_do_gerador_etiquetas(contexto):
    db, tenant, *_ = contexto
    op = preparar(db, tenant)
    service.alterar_peca(db, op.id, op.pecas[0].id, tenant,
                       {"ambiente": '<img src=x onerror="alert(1)">', "observacoes": "<script>malicioso()</script>"})
    documento = ficha_html(db, op)
    assert "<script>malicioso()" not in documento
    assert "&lt;script&gt;" in documento and "NÃO LIBERADA" in documento
    service.liberar(db, op.id, tenant, True)
    from modulos.produtos_etiquetas import gerar_html_impressao
    with patch("modulos.produtos_etiquetas.gerar_html_impressao", wraps=gerar_html_impressao) as renderer:
        etiqueta = etiqueta_da_peca(op, op.pecas[0])
    renderer.assert_called_once()
    assert "etiqueta-grid-2" in etiqueta and "Imprimir etiqueta" in etiqueta
    assert "<img src=x" not in etiqueta and "&lt;img" in etiqueta
    assert "OP-000001-I1-P0001" in etiqueta
    assert "<div class=\"etiqueta-title\">Fábrica &lt;Teste&gt;</div>" in etiqueta


def test_api_fluxo_contrato_e_isolamento(contexto):
    db, tenant, venda, api, client = contexto
    url = "/producao/vendas/1"
    assert client.post(url, json={"confirmar_fabricacao": False}).status_code == 409
    assert client.post(url, json={"confirmar_fabricacao": True, "usuario": 999}).status_code == 422
    assert client.post(url, json={"confirmar_fabricacao": "true"}).status_code == 422
    api.dependency_overrides[get_current_tenant] = lambda: TenantContext(empresa_id=1)
    assert client.post(url, json={"confirmar_fabricacao": True}).status_code == 403
    api.dependency_overrides[get_current_tenant] = lambda: tenant
    response = client.post(url, json={"confirmar_fabricacao": True})
    assert response.status_code == 201, response.text
    op = response.json()
    assert op["confirmado_por"] == "7" and len(op["pecas"]) == 2
    assert client.post(url, json={"confirmar_fabricacao": True}).status_code == 409
    assert client.get("/producao/?pedido_id=1").json()[0]["id"] == op["id"]
    assert client.get("/producao/1/ficha").headers["content-type"].startswith("text/html")
    assert client.get("/producao/1/pecas/1/etiqueta").status_code == 409
    for peca in op["pecas"]:
        response = client.patch(f"/producao/1/pecas/{peca['id']}", json={"ambiente": "Sala", "observacoes": "Teste"})
        assert response.status_code == 200
    response = client.post("/producao/1/liberar", json={"confirmar_fabricacao": True})
    assert response.status_code == 200, response.text
    assert client.get("/producao/1/pecas/999/etiqueta").status_code == 404
    assert client.get("/producao/1/pecas/1/etiqueta").status_code == 200
    assert client.post("/producao/1/pecas/1/status",
                       json={"status_atual": "AGUARDANDO", "status": "CORTE"}).status_code == 200
    api.dependency_overrides[get_current_tenant] = lambda: TenantContext(empresa_id=2, user_id=7)
    assert client.get("/producao/?pedido_id=1").json() == []
    for path in ("/producao/1", "/producao/1/ficha", "/producao/1/pecas/1/etiqueta"):
        assert client.get(path).status_code == 404
    assert client.post("/producao/1/liberar", json={"confirmar_fabricacao": True}).status_code == 404
    assert client.post(url, json={"confirmar_fabricacao": True}).status_code == 404


def test_migration_ausente_retorna_503_sem_instalacao_automatica(contexto):
    db, _, _, _, client = contexto
    class ErroTabela(Exception):
        pgcode = "42P01"
    with patch.object(service, "listar", side_effect=ProgrammingError("SELECT", {}, ErroTabela())):
        response = client.get("/producao/?pedido_id=1")
    assert response.status_code == 503 and "pendente" in response.json()["detail"]
    assert db.query(OrdemProducaoDB).count() == 0


def test_contexto_legado_sem_empresa_bloqueado(contexto):
    _, _, _, api, client = contexto
    api.dependency_overrides[get_current_tenant] = lambda: LEGACY_UNSCOPED
    assert client.get("/producao/?pedido_id=1").status_code == 403
    assert client.post("/producao/vendas/1", json={"confirmar_fabricacao": True}).status_code == 403


def test_sem_escrita_estoque_financeiro_ou_status_comercial(contexto):
    db, tenant, venda, *_ = contexto
    escritas = []
    @event.listens_for(db.get_bind(), "before_cursor_execute")
    def registrar(_, __, sql, *args):
        if sql.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            escritas.append(sql)
    op = preparar(db, tenant)
    service.liberar(db, op.id, tenant, True)
    for anterior, proximo in zip(service.STATUS, service.STATUS[1:]):
        service.alterar_peca(db, op.id, op.pecas[0].id, tenant, {"status_atual": anterior, "status": proximo})
    db.commit()
    assert escritas
    assert all("ordens_producao" in sql or "producao_pecas" in sql for sql in escritas)
    assert venda.status == "ABERTO" and venda.total_final == Decimal("600.00")
    assert db.get(ProdutoDB, 1).estoque_atual == 50
    assert db.get(ProdutoDB, 1).saldo_metros == 80
