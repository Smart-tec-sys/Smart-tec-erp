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
from app.schemas.pedido import PedidoUpdate
from app.models.orcamento import OrcamentoDB, OrcamentoItemDB
from app.models.pedido import PedidoDB, PedidoItemDB
from app.models.produto import ProdutoDB
from app.models.producao import (
    ComponenteProducaoDB,
    OrdemProducaoDB,
    PecaProducaoDB,
    RevisaoFichaProducaoDB,
)
from app.routes.producao import router
from app.services import producao_service as service
from app.services import pedido_service
from app.services.producao_documentos import etiqueta_da_peca, etiquetas_lote_html, ficha_html
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
             "parceiros_comerciais", "representantes", "servicos", "pedidos", "pedidos_itens",
             "ordens_producao", "producao_pecas", "producao_componentes",
             "producao_revisoes_ficha")
    Base.metadata.create_all(engine, tables=[Base.metadata.tables[n] for n in nomes])
    with Session(engine) as db:
        db.add_all([EmpresaDB(id=1, nome="Fábrica <Teste>", slug="teste"),
                    EmpresaDB(id=2, nome="Outra", slug="outra")])
        db.flush()
        db.add(ClienteDB(id=1, empresa_id=1, nome="Cliente Teste", tipo="Pessoa Física"))
        db.add_all([
            ProdutoDB(id=i, empresa_id=1, nome=nome, descricao=nome, unidade="UN",
                      custo_final=custo, situacao="Ativo",
                      estoque_atual=50, saldo_metros=80, modelo_tecnico=None,
                      grupo_tecnico="TECIDOS_CORTINA" if i == 1 else "COMPONENTES_CORTINAS")
            for i, nome, custo in ((1, "Tecido", 10), (2, "Trilho", 20),
                                    (3, "Rodízio", .5), (4, "Entretela", 1))
        ])
        db.add(ProdutoDB(id=20, empresa_id=2, nome="Alheio", unidade="UN",
                         custo_final=10, situacao="Ativo"))
        venda = PedidoDB(id=1, empresa_id=1, numero="VEN-1", status="ABERTO",
                         cliente_id=1, perfil_comercial="VAREJO",
                         total=600, total_final=600)
        venda.itens = [PedidoItemDB(
            id=1, empresa_id=1, tipo_item="PRODUTO", produto_id=None, descricao="Cortina",
            modelo_tecnico="CORTINA", material="Tecido", cor="Branco", acionamento="Manual",
            largura=2, altura=2, quantidade=2, preco_unitario=300, subtotal=600, desconto=0,
            ambiente="Sala",
            observacao_item="Conferir acabamento",
            dados_tecnicos={"cortina": {
                "tecidoProdutoId": 1, "trilhoProdutoId": 2, "rodizioProdutoId": 3,
                "entretelaProdutoId": 4, "fator": 2.5, "larguraTecido": 3, "modeloPrega": "WAVE",
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


def autorizar(db, tenant):
    service.aprovar_fabricacao(db, 1, tenant)
    service.liberar_pedido_fabricacao(db, 1, tenant)


def preparar(db, tenant):
    autorizar(db, tenant)
    op = service.criar(db, 1, tenant, True)
    for peca in op.pecas:
        service.alterar_peca(db, op.id, peca.id, tenant, {
            "ambiente": "Sala", "observacoes": "Manual",
            "justificativa": "Conferência inicial da ficha",
        })
    return op


@pytest.mark.parametrize("status", ["ABERTO", "CONCLUIDO", "FATURADO"])
def test_confirmacao_explicita_sem_alterar_comercial(contexto, status):
    db, tenant, venda, _, _ = contexto
    venda.status = status
    db.flush()
    autorizar(db, tenant)
    op = service.criar(db, 1, tenant, True)
    assert venda.status == status
    assert op.confirmado_por == "7"
    assert isinstance(op.confirmado_em, datetime) and op.confirmado_em.tzinfo is not None
    assert op.liberado_em is None and len(op.pecas) == 2
    assert [(p.pedido_item_id, p.sequencia, p.status) for p in op.pecas] == [
        (1, 1, "AGUARDANDO"), (1, 2, "AGUARDANDO")]
    assert op.pecas[0].tecido == "Tecido" and op.pecas[0].cor == "Branco"
    assert op.snapshot["cliente"] == "Cliente Teste"
    assert op.pecas[0].ambiente == "Sala"
    assert db.get(ProdutoDB, 1).estoque_atual == 50
    assert venda.total_final == Decimal("600.00")


@pytest.mark.parametrize("status", ["ABERTO", "FATURADO", "CONCLUIDO"])
def test_status_comercial_nao_substitui_autorizacao_explicita(contexto, status):
    db, tenant, venda, *_ = contexto
    venda.status = status
    db.flush()
    with pytest.raises(ValueError, match="Aprovação explícita"):
        service.criar(db, venda.id, tenant, True)
    assert db.query(OrdemProducaoDB).count() == 0


def test_bloqueios_confirmacao_e_usuario(contexto):
    db, tenant, *_ = contexto
    with pytest.raises(ValueError, match="explicitamente"):
        service.criar(db, 1, tenant, False)
    with pytest.raises(PermissionError, match="identificado"):
        service.criar(db, 1, TenantContext(empresa_id=1), True)
    with pytest.raises(ValueError, match="Aprovação explícita"):
        service.criar(db, 1, tenant, True)
    assert db.query(OrdemProducaoDB).count() == 0


def test_aprovacao_e_liberacao_separadas_com_historico_e_rollback(contexto):
    db, tenant, venda, *_ = contexto
    with pytest.raises(ValueError, match="Aprovação explícita"):
        service.liberar_pedido_fabricacao(db, venda.id, tenant)
    autorizacao = service.aprovar_fabricacao(db, venda.id, tenant)
    assert autorizacao["aprovado_por"] == "7" and autorizacao["liberado_em"] is None
    db.rollback()
    db.expire_all()
    venda = db.get(PedidoDB, venda.id)
    assert venda.producao_aprovado_em is None and venda.producao_historico == []
    service.aprovar_fabricacao(db, venda.id, tenant)
    autorizacao = service.liberar_pedido_fabricacao(db, venda.id, tenant)
    assert autorizacao["liberado_por"] == "7"
    assert [evento["acao"] for evento in autorizacao["historico"]] == ["APROVADO", "LIBERADO"]


def test_alteracao_de_cabecalho_invalida_autorizacao_e_preserva_auditoria(contexto):
    db, tenant, venda, _, client = contexto
    op = preparar(db, tenant)
    service.liberar(db, op.id, tenant, True)
    resultado = pedido_service.atualizar(
        db, venda.id, tenant, PedidoUpdate(prazo_entrega="2026-12-01"),
    )
    assert resultado["producao_aprovado_em"] is None
    assert resultado["producao_liberado_em"] is None
    assert resultado["producao_historico"][-1]["acao"] == "AUTORIZACAO_INVALIDADA_POR_ALTERACAO"
    with pytest.raises(ValueError, match="Aprovação explícita"):
        service.alterar_peca(db, op.id, op.pecas[0].id, tenant,
                            {"status_atual": "AGUARDANDO", "status": "CORTE"})
    assert client.get(f"/producao/{op.id}/pecas/{op.pecas[0].id}/etiqueta").status_code == 409


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
    autorizar(db, tenant)
    with pytest.raises(ValueError, match="quantidade|peças"):
        service.criar(db, 1, tenant, True)
    assert db.query(OrdemProducaoDB).count() == 0


def test_servicos_nao_geram_pecas(contexto):
    db, tenant, venda, *_ = contexto
    venda.itens.append(PedidoItemDB(empresa_id=1, tipo_item="SERVICO", descricao="Instalação", quantidade=1,
                                   largura=0, altura=0, preco_unitario=50))
    db.flush()
    autorizar(db, tenant)
    assert len(service.criar(db, 1, tenant, True).pecas) == 2


def test_servico_isolado_nao_gera_op(contexto):
    db, tenant, venda, *_ = contexto
    venda.itens[0].tipo_item = "SERVICO"
    db.flush()
    autorizar(db, tenant)
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
        lambda: service.alterar_peca(db, op.id, op.pecas[0].id, outro, {
            "ambiente": "X", "observacoes": "", "justificativa": "Teste tenant",
        }),
        lambda: service.alterar_peca(db, op.id, 999, tenant, {
            "ambiente": "X", "observacoes": "", "justificativa": "Teste peça",
        }),
    ):
        with pytest.raises(LookupError):
            acao()


def test_edicao_manual_componentes_conferencia_e_separacao_comercial(contexto):
    db, tenant, venda, *_ = contexto
    op = preparar(db, tenant)
    db.commit()
    peca = db.get(PecaProducaoDB, op.pecas[0].id)
    item_original = {
        "largura": venda.itens[0].largura,
        "altura": venda.itens[0].altura,
        "quantidade": venda.itens[0].quantidade,
        "preco_unitario": venda.itens[0].preco_unitario,
        "total": venda.total_final,
    }

    service.alterar_peca(db, op.id, peca.id, tenant, {
        "modo_fabricacao": "MANUAL_SUPERVISIONADA",
        "ambiente": "Sala de estar",
        "largura": Decimal("2.150"),
        "altura": Decimal("2.400"),
        "quantidade": Decimal("1"),
        "especificacoes_fabricacao": {"acabamento": "Conferir tecido manualmente"},
        "justificativa": "Ajuste técnico aprovado",
    })
    service.adicionar_componente(db, op.id, peca.id, tenant, {
        "produto_id": 2, "quantidade": Decimal("2"), "unidade": "UN",
        "comprimento_corte": Decimal("2.15"), "custo_unitario": Decimal("22.50"),
        "observacoes": "Corte conforme ficha",
        "justificativa": "Inclusão do componente",
    })
    componente = peca.componentes[0]
    assert componente.empresa_id == 1 and componente.origem_custo == "INFORMADO"
    assert peca.conferido_em is None
    assert service.conferir_peca(
        db, op.id, peca.id, tenant, True, "Conferência da composição",
    ).pecas[0].conferido_por == "7"
    assert peca.versao_ficha == 5 and len(peca.revisoes) == 4
    assert service.serializar(db, op)["pendencias"] == []

    service.atualizar_componente(db, op.id, peca.id, componente.id, tenant, {
        "produto_id": 3, "quantidade": Decimal("4"), "unidade": "UN",
        "comprimento_corte": None, "custo_unitario": None,
        "observacoes": "Substituído pelo produto do catálogo",
        "justificativa": "Substituição autorizada",
    })
    assert peca.componentes[0].produto_id == 3
    assert peca.componentes[0].custo_unitario == Decimal("0.5000")
    assert peca.componentes[0].origem_custo == "CADASTRO"
    assert peca.conferido_em is None
    with pytest.raises(ValueError, match="Conferência técnica obrigatória"):
        service.liberar(db, op.id, tenant, True)

    service.conferir_peca(db, op.id, peca.id, tenant, True, "Revisão após substituição")
    assert service.serializar(db, op)["pendencias"] == []
    service.liberar(db, op.id, tenant, True)
    dados = service.serializar(db, op)
    assert dados["calculos_por_peca"][f"peca:{peca.id}"]["status_composicao"] == "MANUAL_NAO_HOMOLOGADA"
    etiqueta = etiqueta_da_peca(op, peca)
    lote = etiquetas_lote_html(op)
    assert "COMPOSIÇÃO MANUAL SUPERVISIONADA" in etiqueta
    assert "NÃO HOMOLOGADA" in etiqueta and "NÃO HOMOLOGADA" in lote
    assert f"OP-{op.id:06d}-I1-P0001" in lote
    assert venda.itens[0].largura == item_original["largura"]
    assert venda.itens[0].altura == item_original["altura"]
    assert venda.itens[0].quantidade == item_original["quantidade"]
    assert venda.itens[0].preco_unitario == item_original["preco_unitario"]
    assert venda.total_final == item_original["total"]
    with pytest.raises(ValueError, match="imutável"):
        service.alterar_peca(db, op.id, peca.id, tenant, {
            "ambiente": "Outro", "justificativa": "Mudança tardia",
        })


def test_catalogo_isolado_remocao_e_rollback_de_ficha(contexto):
    db, tenant, _, _, client = contexto
    op = preparar(db, tenant)
    db.commit()
    peca = db.get(PecaProducaoDB, op.pecas[0].id)
    resposta = client.get("/producao/catalogo-componentes?q=Trilho")
    assert resposta.status_code == 200 and [item["id"] for item in resposta.json()] == [2]
    resposta = client.patch(f"/producao/{op.id}/pecas/{peca.id}", json={
        "modo_fabricacao": "MANUAL_SUPERVISIONADA",
        "especificacoes_fabricacao": {"montagem": "manual"},
        "justificativa": "Edição de ficha manual",
    })
    assert resposta.status_code == 200
    resposta = client.post(f"/producao/{op.id}/pecas/{peca.id}/componentes", json={
        "produto_id": 20, "quantidade": 1, "unidade": "UN",
        "observacoes": "", "justificativa": "Tentativa de outro tenant",
    })
    assert resposta.status_code == 409
    assert db.query(ComponenteProducaoDB).count() == 0

    componente = service.adicionar_componente(db, op.id, peca.id, tenant, {
        "produto_id": 2, "quantidade": 1, "unidade": "UN",
        "custo_unitario": None, "observacoes": "",
        "justificativa": "Inclusão para testar rollback",
    }).pecas[0].componentes[0]
    db.commit()
    service.remover_componente(db, op.id, peca.id, componente.id, tenant, "Remoção de teste")
    assert db.query(ComponenteProducaoDB).count() == 0
    db.rollback()
    db.expire_all()
    assert db.query(ComponenteProducaoDB).count() == 1
    assert db.query(RevisaoFichaProducaoDB).filter_by(peca_id=peca.id).count() == 3
    assert db.get(ProdutoDB, 20).empresa_id == 2


def test_modo_automatico_exige_troca_para_manual_antes_de_editar_medidas(contexto):
    db, tenant, *_ = contexto
    op = preparar(db, tenant)
    peca = op.pecas[0]
    with pytest.raises(ValueError, match="modo manual supervisionado"):
        service.alterar_peca(db, op.id, peca.id, tenant, {
            "largura": Decimal("2.2"), "justificativa": "Ajuste de dimensão",
        })
    service.alterar_peca(db, op.id, peca.id, tenant, {
        "modo_fabricacao": "MANUAL_SUPERVISIONADA",
        "justificativa": "Modo manual habilitado",
    })
    with pytest.raises(ValueError, match="não pode voltar"):
        service.alterar_peca(db, op.id, peca.id, tenant, {
            "modo_fabricacao": "AUTOMATICA", "justificativa": "Tentativa de retorno",
        })


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
        service.alterar_peca(db, op.id, op.pecas[0].id, tenant, {
            "ambiente": "Quarto", "observacoes": "", "justificativa": "Alteração pós liberação",
        })


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


@pytest.mark.parametrize(("modelo", "pendencia"), [
    ("ROLO", "Rolô motorizado"),
    ("DOUBLE VISION", "Double Vision motorizado"),
    ("ROMANA", "Romana motorizada"),
])
def test_modelos_motorizados_nao_liberam_composicao_pendente(contexto, modelo, pendencia):
    db, tenant, venda, *_ = contexto
    venda.itens[0].produto_id = 1
    venda.itens[0].modelo_tecnico = modelo
    venda.itens[0].acionamento = "Motorizado"
    db.flush()
    op = preparar(db, tenant)
    assert any(pendencia in p for p in service.serializar(db, op)["pendencias"])
    with pytest.raises(ValueError, match="bloqueada"):
        service.liberar(db, op.id, tenant, True)


def test_ambiente_preservado_na_conversao_de_orcamento_e_na_op(contexto):
    db, tenant, *_ = contexto
    orcamento = OrcamentoDB(
        id=2, empresa_id=1, numero="ORC-2", cliente_id=1, status="APROVADO",
        total=300, desconto=0, total_final=300,
    )
    orcamento.itens = [OrcamentoItemDB(
        empresa_id=1, tipo_item="PRODUTO", produto_id=1, descricao="Cortina",
        modelo_tecnico="CORTINA", material="Tecido", cor="Branco",
        acionamento="Manual", quantidade=1, largura=2, altura=2, area=4,
        preco_unitario=300, desconto=0, subtotal=300, ambiente="Quarto",
        dados_tecnicos={"cortina": {
            "tecidoProdutoId": 1, "trilhoProdutoId": 2, "rodizioProdutoId": 3,
            "entretelaProdutoId": 4, "fator": 2.5, "larguraTecido": 3, "modeloPrega": "WAVE",
        }},
    )]
    db.add(orcamento)
    db.flush()
    pedido = pedido_service.converter_orcamento(db, orcamento.id, tenant)
    assert pedido["status"] == "ABERTO"
    assert pedido["itens"][0]["ambiente"] == "Quarto"
    pedido_id = pedido["id"]
    service.aprovar_fabricacao(db, pedido_id, tenant)
    service.liberar_pedido_fabricacao(db, pedido_id, tenant)
    ordem = service.criar(db, pedido_id, tenant, True)
    assert ordem.snapshot["itens"][0]["ambiente"] == "Quarto"
    assert ordem.pecas[0].ambiente == "Quarto"


def test_campos_basicos_ausentes_impedem_liberacao(contexto):
    db, tenant, venda, *_ = contexto
    venda.itens[0].cor = ""
    venda.itens[0].ambiente = ""
    db.flush()
    autorizar(db, tenant)
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
    service.alterar_peca(db, op.id, op.pecas[0].id, tenant, {
        "ambiente": '<img src=x onerror="alert(1)">',
        "observacoes": "<script>malicioso()</script>",
        "justificativa": "Teste de segurança HTML",
    })
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
    assert "Cliente Teste" in etiqueta and "OBS:" in etiqueta
    assert "<div class=\"etiqueta-title\">Fábrica &lt;Teste&gt;</div>" in etiqueta
    from app.services.producao_documentos import etiquetas_lote_html
    lote = etiquetas_lote_html(op)
    assert "OP-000001-I1-P0001" in lote and "OP-000001-I1-P0002" in lote


def test_api_fluxo_contrato_e_isolamento(contexto):
    db, tenant, venda, api, client = contexto
    url = "/producao/vendas/1"
    assert client.post(url, json={"confirmar_fabricacao": False}).status_code == 409
    assert client.post(url, json={"confirmar_fabricacao": True, "usuario": 999}).status_code == 422
    assert client.post(url, json={"confirmar_fabricacao": "true"}).status_code == 422
    api.dependency_overrides[get_current_tenant] = lambda: TenantContext(empresa_id=1)
    assert client.post(url, json={"confirmar_fabricacao": True}).status_code == 403
    api.dependency_overrides[get_current_tenant] = lambda: tenant
    autorizacao_url = "/producao/vendas/1/autorizacao"
    assert client.get(autorizacao_url).json()["aprovado_em"] is None
    assert client.post("/producao/vendas/1/liberar-fabricacao").status_code == 409
    aprovado = client.post("/producao/vendas/1/aprovar")
    assert aprovado.status_code == 200 and aprovado.json()["aprovado_por"] == "7"
    assert client.post("/producao/vendas/1/aprovar").status_code == 409
    response = client.post(url, json={"confirmar_fabricacao": True})
    assert response.status_code == 409
    liberado = client.post("/producao/vendas/1/liberar-fabricacao")
    assert liberado.status_code == 200 and liberado.json()["liberado_por"] == "7"
    assert client.post("/producao/vendas/1/liberar-fabricacao").status_code == 409
    response = client.post(url, json={"confirmar_fabricacao": True})
    assert response.status_code == 201, response.text
    op = response.json()
    assert op["confirmado_por"] == "7" and len(op["pecas"]) == 2
    assert client.post(url, json={"confirmar_fabricacao": True}).status_code == 409
    assert client.get("/producao/?pedido_id=1").json()[0]["id"] == op["id"]
    assert client.get("/producao/1/ficha").headers["content-type"].startswith("text/html")
    assert client.get("/producao/1/pecas/1/etiqueta").status_code == 409
    for peca in op["pecas"]:
        response = client.patch(f"/producao/1/pecas/{peca['id']}", json={
            "ambiente": "Sala", "observacoes": "Teste", "justificativa": "Teste de edição",
        })
        assert response.status_code == 200
    response = client.post("/producao/1/liberar", json={"confirmar_fabricacao": True})
    assert response.status_code == 200, response.text
    assert client.get("/producao/1/pecas/999/etiqueta").status_code == 404
    assert client.get("/producao/1/pecas/1/etiqueta").status_code == 200
    lote = client.get("/producao/1/etiquetas")
    assert lote.status_code == 200 and "OP-000001-I1-P0002" in lote.text
    assert client.post("/producao/1/pecas/1/status",
                       json={"status_atual": "AGUARDANDO", "status": "CORTE"}).status_code == 200
    api.dependency_overrides[get_current_tenant] = lambda: TenantContext(empresa_id=2, user_id=7)
    assert client.get("/producao/?pedido_id=1").json() == []
    for path in ("/producao/1", "/producao/1/ficha", "/producao/1/pecas/1/etiqueta",
                 "/producao/1/etiquetas", autorizacao_url):
        assert client.get(path).status_code == 404
    assert client.post("/producao/1/liberar", json={"confirmar_fabricacao": True}).status_code == 404
    assert client.post(url, json={"confirmar_fabricacao": True}).status_code == 404
    assert client.post("/producao/vendas/1/aprovar").status_code == 404


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
    escritas.clear()
    service.liberar(db, op.id, tenant, True)
    for anterior, proximo in zip(service.STATUS, service.STATUS[1:]):
        service.alterar_peca(db, op.id, op.pecas[0].id, tenant, {"status_atual": anterior, "status": proximo})
    db.commit()
    assert escritas
    assert all("ordens_producao" in sql or "producao_pecas" in sql for sql in escritas)
    assert venda.status == "ABERTO" and venda.total_final == Decimal("600.00")
    assert db.get(ProdutoDB, 1).estoque_atual == 50
    assert db.get(ProdutoDB, 1).saldo_metros == 80
