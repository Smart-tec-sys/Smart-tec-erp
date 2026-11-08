"""Edicao do catalogo em SQLite isolado; nunca acessa banco operacional."""
from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models.empresa import EmpresaDB
from app.models.empresa_usuario import EmpresaUsuarioDB
from app.models.classificacao_tecnica_produto import ClassificacaoTecnicaProdutoDB
from app.models.equivalencia_tecnica import EmpresaEquivalenciaTecnicaDB
from app.models.cliente import ClienteDB  # noqa: F401
from app.models.funcionario import FuncionarioDB  # noqa: F401
from app.models.fornecedor import FornecedorDB
from app.models.orcamento import OrcamentoDB, OrcamentoItemDB
from app.models.opcao_auxiliar import OpcaoAuxiliarDB
from app.models.pedido import PedidoDB, PedidoItemDB
from app.models.produto import ProdutoDB
from app.models.produto_historico import ProdutoHistoricoAlteracaoDB
from app.models.producao import ComponenteProducaoDB, OrdemProducaoDB, PecaProducaoDB
from app.routes.produto import router
from app.models.servico import ServicoDB  # noqa: F401
from app.models.usuario import UsuarioDB
from app.tenant.context import TenantContext
from app.tenant.dependencies import get_current_tenant


@compiles(JSONB, "sqlite")
def _sqlite_jsonb(tipo, compiler, **kwargs):
    return "JSON"


@pytest.fixture
def catalogo():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def habilitar_fk(conexao, _):
        conexao.execute("PRAGMA foreign_keys=ON")

    nomes = (
        "empresas", "usuarios", "empresa_usuarios", "clientes", "funcionarios", "parceiros_comerciais",
        "representantes", "servicos", "orcamentos", "orcamentos_itens",
        "pedidos", "pedidos_itens", "ordens_producao", "producao_pecas",
        "producao_componentes", "fornecedores", "produtos",
        "opcoes_auxiliares", "empresa_equivalencias_tecnicas",
        "classificacoes_tecnicas_produtos", "produtos_historico_alteracoes",
    )
    Base.metadata.create_all(engine, tables=[Base.metadata.tables[name] for name in nomes])
    with Session(engine) as db:
        db.add_all([
            EmpresaDB(id=1, nome="Empresa A", slug="empresa-a"),
            EmpresaDB(id=2, nome="Empresa B", slug="empresa-b"),
            UsuarioDB(id=7, nome="Usuário Teste", email="teste@example.com", status="ATIVO"),
            UsuarioDB(id=8, nome="Usuário Empresa B", email="empresa-b@example.com", status="ATIVO"),
            FornecedorDB(id=1, empresa_id=1, nome="Fornecedor A", tipo="FABRICANTE"),
        ])
        db.flush()
        db.add_all([
            EmpresaUsuarioDB(
                id=1, empresa_id=1, usuario_id=7, papel="ADMIN", ativo=True,
            ),
            EmpresaUsuarioDB(
                id=2, empresa_id=2, usuario_id=8, papel="ADMIN", ativo=True,
            ),
        ])
        db.flush()
        db.add_all([
            ClassificacaoTecnicaProdutoDB(
                empresa_id=1, tipo=tipo, nome=nome, nome_normalizado=nome.lower(),
            )
            for tipo, nome in (
                ("grupo_tecnico", "TUBO"),
                ("grupo_tecnico", "TUBO_REFORCADO"),
                ("familia_tecnica", "ROLO"),
                ("modelo_tecnico", "ROLO 32"),
                ("modelo_tecnico", "ROLO 38"),
            )
        ])
        db.add_all([
            ProdutoDB(
                id=10, empresa_id=1, nome="Tubo antigo", descricao="Descricao antiga",
                grupo_produto="Acessorios", grupo_tecnico="TUBO",
                familia_tecnica="ROLO", modelo_tecnico="ROLO 32",
                unidade="UN", unidade_venda="UN", unidade_compra="RL",
                unidade_controle="UN", nome_fornecedor="Fornecedor A",
                codigo_fornecedor="A-32", fornecedores="Fornecedor A",
                valor_custo=10, despesas_acessorias=1, outras_despesas=0,
                custo_final=11, valor_venda=20, situacao="Ativo",
            ),
            ProdutoDB(
                id=11, empresa_id=1, nome="Tubo candidato",
                grupo_tecnico="TUBO_REFORCADO", familia_tecnica="ROLO",
                modelo_tecnico="ROLO 38", unidade="UN", unidade_venda="M2",
                unidade_compra="RL", unidade_controle="UN",
                valor_custo=15, custo_final=15, situacao="Ativo",
            ),
            ProdutoDB(
                id=20, empresa_id=2, nome="Produto privado",
                grupo_tecnico="TUBO", familia_tecnica="ROLO",
                modelo_tecnico="ROLO 32", unidade="UN", unidade_venda="UN",
                valor_custo=5, custo_final=5, situacao="Ativo",
            ),
        ])
        db.flush()
        db.add_all([
            OpcaoAuxiliarDB(
                empresa_id=1, categoria="grupo_produto", nome="Acessorios",
                situacao="Ativo",
            ),
            OpcaoAuxiliarDB(
                empresa_id=1, categoria="unidade_venda", nome="UN", situacao="Ativo",
            ),
            OpcaoAuxiliarDB(
                empresa_id=1, categoria="unidade_venda", nome="M2", situacao="Ativo",
            ),
        ])
        db.add(EmpresaEquivalenciaTecnicaDB(
            id=5, empresa_id=1, funcao_tecnica="ROLO_TUBO_32",
            produto_id=10, fornecedor_id=1, prioridade=10,
            preferencial=True, ativo=True, configuracoes_locais={},
        ))
        db.add(OrcamentoDB(
            id=1, empresa_id=1, numero="ORC-1", perfil_comercial="VAREJO",
            status="APROVADO", total=20, desconto=0, total_final=20,
            itens=[OrcamentoItemDB(
                id=1, empresa_id=1, tipo_item="PRODUTO", produto_id=10,
                descricao="Tubo antigo", grupo_tecnico="TUBO",
                modelo_tecnico="ROLO 32", unidade="UN", quantidade=1,
                largura=0, altura=0, area=0, preco_unitario=20,
                desconto=0, subtotal=20,
            )],
        ))
        db.add(PedidoDB(
            id=1, empresa_id=1, numero="VEN-1", status="ABERTO",
            perfil_comercial="VAREJO", total=20, desconto=0, total_final=20,
            itens=[PedidoItemDB(
                id=1, empresa_id=1, tipo_item="PRODUTO", produto_id=10,
                descricao="Tubo antigo", grupo_tecnico="TUBO",
                modelo_tecnico="ROLO 32", unidade="UN", quantidade=1,
                largura=0, altura=0, area=0, preco_unitario=20,
                desconto=0, subtotal=20,
            )],
        ))
        db.flush()
        liberado_em = datetime.now(timezone.utc)
        db.add(OrdemProducaoDB(
            id=1, empresa_id=1, pedido_id=1, confirmado_por="7",
            confirmado_em=liberado_em, liberado_por="7", liberado_em=liberado_em,
            snapshot={"itens": [{"produto_id": 10, "descricao": "Tubo antigo", "custo": 10}]},
            pecas=[PecaProducaoDB(
                id=1, pedido_item_id=1, sequencia=1, largura=1, altura=1,
                quantidade=1, ambiente="Sala", observacoes="", status="AGUARDANDO",
                especificacoes_fabricacao={}, historico=[],
                componentes=[ComponenteProducaoDB(
                    id=1, empresa_id=1, ordem_id=1, produto_id=10,
                    descricao="Tubo antigo", codigo_interno="T-1", quantidade=1,
                    unidade="UN", custo_unitario=10, origem_custo="CADASTRO",
                    observacoes="",
                )],
            )],
        ))
        db.commit()
        tenant = TenantContext(empresa_id=1, user_id=7)
        api = FastAPI()
        api.include_router(router, prefix="/produtos")
        api.dependency_overrides[get_db] = lambda: db
        api.dependency_overrides[get_current_tenant] = lambda: tenant
        with TestClient(api) as client:
            yield db, api, tenant, client
    engine.dispose()


def test_edita_produto_no_mesmo_id_preservando_equivalencia_e_valores(catalogo):
    db, _, _, client = catalogo
    ordem = db.get(OrdemProducaoDB, 1)
    snapshot_op = deepcopy(ordem.snapshot)
    componente_op = db.query(ComponenteProducaoDB).filter(
        ComponenteProducaoDB.ordem_id == ordem.id,
    ).one()
    snapshot_componente = (
        componente_op.produto_id, componente_op.descricao, componente_op.unidade,
        float(componente_op.quantidade), float(componente_op.custo_unitario),
        componente_op.codigo_interno,
    )
    response = client.put("/produtos/10", json={
        "nome": "Tubo revisado",
        "descricao": "Descricao conferida manualmente",
        "grupo_tecnico": "  tubo_reforcado ",
        "familia_tecnica": "ROLO",
        "modelo_tecnico": "ROLO 38",
        "unidade_venda": "M2",
        "nome_fornecedor": "Fornecedor revisado",
        "codigo_fornecedor": "B-38",
        "fornecedores": "Fornecedor revisado",
        "valor_custo": 12.5,
    })
    assert response.status_code == 200, response.text
    assert response.json()["id"] == 10
    assert response.json()["custo_final"] == 13.5
    assert response.json()["grupo_tecnico"] == "TUBO_REFORCADO"
    assert db.get(ProdutoDB, 10).nome == "Tubo revisado"
    equivalencia = db.get(EmpresaEquivalenciaTecnicaDB, 5)
    assert equivalencia.produto_id == 10 and equivalencia.ativo is True
    orcamento_item = db.get(OrcamentoItemDB, 1)
    pedido_item = db.get(PedidoItemDB, 1)
    for item in (orcamento_item, pedido_item):
        assert item.produto_id == 10
        assert item.descricao == "Tubo antigo"
        assert item.grupo_tecnico == "TUBO" and item.modelo_tecnico == "ROLO 32"
        assert item.unidade == "UN" and float(item.preco_unitario) == 20
    db.expire_all()
    ordem = db.get(OrdemProducaoDB, 1)
    componente_op = db.query(ComponenteProducaoDB).filter(
        ComponenteProducaoDB.ordem_id == ordem.id,
    ).one()
    assert ordem.liberado_em is not None
    assert ordem.snapshot == snapshot_op
    assert (
        componente_op.produto_id, componente_op.descricao, componente_op.unidade,
        float(componente_op.quantidade), float(componente_op.custo_unitario),
        componente_op.codigo_interno,
    ) == snapshot_componente

    history = client.get("/produtos/10/historico")
    assert history.status_code == 200
    entries = history.json()
    assert len(entries) == 1
    assert entries[0]["usuario_id"] == 7
    assert entries[0]["alteracoes"]["grupo_tecnico"] == {
        "antes": "TUBO", "depois": "TUBO_REFORCADO",
    }
    assert entries[0]["alteracoes"]["custo_final"] == {"antes": 11.0, "depois": 13.5}


def test_classificacoes_tecnicas_sao_canonicas_e_isoladas_por_empresa(catalogo):
    _, api, _, client = catalogo
    response = client.get("/produtos/classificacoes-tecnicas")
    assert response.status_code == 200
    assert response.json() == {
        "grupo_tecnico": ["TUBO", "TUBO_REFORCADO"],
        "familia_tecnica": ["ROLO"],
        "modelo_tecnico": ["ROLO 32", "ROLO 38"],
    }
    criado = client.post("/produtos/", json={
        "nome": "Produto com classificação existente",
        "grupo_tecnico": " tubo ",
    })
    assert criado.status_code == 200, criado.text
    assert criado.json()["grupo_tecnico"] == "TUBO"
    invalido = client.post("/produtos/", json={
        "nome": "Produto com classificação arbitrária",
        "grupo_tecnico": "Grupo novo",
    })
    assert invalido.status_code == 422

    api.dependency_overrides[get_current_tenant] = lambda: TenantContext(
        empresa_id=2, user_id=8,
    )
    assert client.get("/produtos/classificacoes-tecnicas").json() == {
        "grupo_tecnico": [], "familia_tecnica": [], "modelo_tecnico": [],
    }


def test_historico_permanece_apos_desativacao_e_impede_exclusao_fisica(catalogo):
    db, _, _, client = catalogo
    response = client.put("/produtos/10", json={"situacao": "Inativo"})
    assert response.status_code == 200
    assert client.get("/produtos/10/historico").status_code == 200

    response = client.delete("/produtos/10")
    assert response.status_code == 409
    assert db.get(ProdutoDB, 10) is not None


def test_historico_rejeita_empresa_produto_ou_usuario_desalinhados(catalogo):
    db, *_ = catalogo
    db.add(ProdutoHistoricoAlteracaoDB(
        empresa_id=1, produto_id=20, usuario_id=7, alteracoes={"nome": {}},
    ))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()

    db.add(ProdutoHistoricoAlteracaoDB(
        empresa_id=1, produto_id=10, usuario_id=8, alteracoes={"nome": {}},
    ))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


@pytest.mark.parametrize(("payload", "message"), [
    ({"grupo_tecnico": "CLASSIFICACAO_INEXISTENTE"}, "classificação"),
    ({"unidade_venda": "UNIDADE_INEXISTENTE"}, "unidade"),
    ({"valor_custo": -1}, "greater than or equal to 0"),
    ({"nome": "   "}, "Nome do produto é obrigatório"),
])
def test_valida_classificacoes_unidades_e_custos(catalogo, payload, message):
    _, _, _, client = catalogo
    response = client.put("/produtos/10", json=payload)
    assert response.status_code == (422 if message == "greater than or equal to 0" else 422)
    assert message.casefold() in response.text.casefold()


def test_historico_e_edicao_isolados_por_empresa_e_usuario(catalogo):
    _, api, tenant, client = catalogo
    assert client.get("/produtos/10/historico").json() == []
    api.dependency_overrides[get_current_tenant] = lambda: TenantContext(empresa_id=2, user_id=8)
    assert client.get("/produtos/10/historico").status_code == 404
    assert client.put("/produtos/10", json={"descricao": "Tentativa cruzada"}).status_code == 404
    assert client.get("/produtos/20/historico").json() == []

    api.dependency_overrides[get_current_tenant] = lambda: TenantContext(empresa_id=1)
    response = client.put("/produtos/10", json={"descricao": "Sem ator"})
    assert response.status_code == 403
    assert "identidade de usuário" in response.json()["detail"]
    assert tenant.user_id == 7


def test_falha_ao_gravar_historico_reverte_edicao(catalogo):
    db, _, _, client = catalogo

    def falhar_antes_do_flush(session, _context, _instances):
        if any(isinstance(obj, ProdutoHistoricoAlteracaoDB) for obj in session.new):
            raise RuntimeError("falha simulada")

    event.listen(db, "before_flush", falhar_antes_do_flush)
    try:
        response = client.put("/produtos/10", json={"descricao": "Nao persistir"})
    finally:
        event.remove(db, "before_flush", falhar_antes_do_flush)
    assert response.status_code == 500
    db.expire_all()
    assert db.get(ProdutoDB, 10).descricao == "Descricao antiga"
    assert db.query(ProdutoHistoricoAlteracaoDB).count() == 0
