"""Cortina -> calculo -> salvar/reabrir, somente SQLite em memoria."""
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.database import Base
from app.models.cliente import ClienteDB
from app.models.funcionario import FuncionarioDB  # noqa: F401
from app.models.empresa import EmpresaDB
from app.models.produto import ProdutoDB
from app.routes.empresa import obter_empresa_atual
from app.schemas.orcamento import OrcamentoInput
from app.services import orcamento_service
from app.tenant.context import TenantContext


@compiles(JSONB, "sqlite")
def _jsonb_sqlite(tipo, compiler, **kwargs):
    return "JSON"


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    tables = [Base.metadata.tables[n] for n in (
        "empresas", "clientes", "funcionarios", "produtos", "orcamentos", "orcamentos_itens",
    )]
    Base.metadata.create_all(engine, tables=tables)
    with Session(engine) as session:
        session.add_all([
            EmpresaDB(id=1, nome="Empresa Ficticia - TESTE", slug="teste"),
            EmpresaDB(id=2, nome="Outra empresa", slug="outra"),
            ClienteDB(id=1, empresa_id=1, tipo="Pessoa Física", nome="Cliente Ficticia - NAO COMERCIAL"),
            ProdutoDB(id=1, empresa_id=1, nome="Tecido de teste", custo_final=10,
                      grupo_tecnico="TECIDOS_CORTINA", largura=3, situacao="Ativo"),
            ProdutoDB(id=2, empresa_id=1, nome="Trilho cortina", custo_final=20,
                      grupo_tecnico="COMPONENTES_CORTINAS", situacao="Ativo"),
            ProdutoDB(id=3, empresa_id=1, nome="Rodizio cortina", custo_final=.5,
                      grupo_tecnico="COMPONENTES_CORTINAS", situacao="Ativo"),
            ProdutoDB(id=4, empresa_id=1, nome="Entretela", custo_final=1,
                      grupo_tecnico="COMPONENTES_CORTINAS", situacao="Ativo"),
        ])
        session.commit()
        yield session
    engine.dispose()


@pytest.mark.parametrize("perfil,unitario,total", [
    ("DECORADOR", 259.5, 519), ("VAREJO", 346, 692), ("CONSUMIDOR_FINAL", 432.5, 865),
])
def test_salvar_reabrir_cortina_tres_tabelas(db, perfil, unitario, total):
    entrada = OrcamentoInput(
        cliente_id=1, perfil_comercial=perfil,
        observacao="TESTE FICTICIO - NAO ENVIAR COMO ORCAMENTO REAL.",
        observacao_interna="CUSTOS INTERNOS NAO DEVEM SAIR NO PDF.",
        validade="2026-11-10",
        itens=[{
            "tipo_item": "PRODUTO", "produto_id": None, "descricao": "Cortina Wave - Sala de teste",
            "modelo_tecnico": "CORTINA", "grupo_tecnico": "TECIDOS_CORTINA", "unidade": "UN",
            "material": "Tecido sintetico de teste", "cor": "Branco", "acionamento": "Manual",
            "largura": 2, "altura": 2, "quantidade": 2, "preco_unitario": 99999,
            "observacao_item": "Ambiente: Sala. Wave prega pronta. Abertura lateral esquerda.",
            "dados_tecnicos": {"cortina": {
                "tecidoProdutoId": 1, "fator": 2.5, "larguraTecido": 3, "modeloPrega": "WAVE",
                "componentes": [{"produto_id": 2, "quantidade": 2},
                                {"produto_id": 3, "quantidade": 20},
                                {"produto_id": 4, "quantidade": 5}],
                "result": {"preco_unitario": 99999, "subtotal": 99999},
            }},
        }],
    )
    tenant = TenantContext(empresa_id=1)
    with patch.object(orcamento_service, "_numero", return_value="TESTE-LOCAL"):
        salvo = orcamento_service.criar(db, entrada, tenant)
    db.expire_all()
    reaberto = orcamento_service.obter(db, salvo["id"], tenant)
    assert reaberto["perfil_comercial"] == perfil
    assert reaberto["total_final"] == total
    item = reaberto["itens"][0]
    assert item["preco_unitario"] == unitario
    assert item["subtotal"] == total and item["quantidade"] == 2
    assert item["material"] == "Tecido sintetico de teste" and item["cor"] == "Branco"
    assert item["largura"] == item["altura"] == 2
    resultado = item["dados_tecnicos"]["cortina"]["result"]
    assert resultado["custo_total"] == 173
    assert resultado["tecido"]["consumo_total_ml"] == 9.6
    assert resultado["tecido"]["consumo_por_altura_m"] == 2.4
    assert resultado["quantidade_alturas"] == 2
    assert orcamento_service.obter(db, salvo["id"], TenantContext(empresa_id=2)) is None
    if os.getenv("CURTAIN_PDF_FIXTURE_OUTPUT"):
        destino = Path(os.environ["CURTAIN_PDF_FIXTURE_OUTPUT"])
        destino.mkdir(parents=True, exist_ok=True)
        empresa = obter_empresa_atual(tenant, db)
        cliente = {"id": 1, "nome": "Cliente Ficticia - NAO COMERCIAL"}
        (destino / f"cortina-{perfil}.json").write_text(json.dumps(jsonable_encoder({
            "budget": reaberto, "context": {"companyName": empresa["nome"], "client": cliente},
        }), ensure_ascii=False), encoding="utf-8")
    alterado = orcamento_service.atualizar(
        db, salvo["id"], entrada.model_copy(update={"perfil_comercial": "DECORADOR"}), tenant,
    )
    assert alterado["perfil_comercial"] == "DECORADOR"
    assert alterado["total_final"] == 519
    assert orcamento_service.obter(db, salvo["id"], tenant)["perfil_comercial"] == "DECORADOR"


def test_empresa_pdf_respeita_empresa_ativa(db):
    atual = obter_empresa_atual(TenantContext(empresa_id=1), db)
    assert atual["id"] == 1 and atual["nome"] == "Empresa Ficticia - TESTE"
    assert set(atual) == {"id", "nome", "nome_fantasia", "documento", "logo_url"}
    db.get(EmpresaDB, 2).status = "INATIVA"
    db.flush()
    with pytest.raises(HTTPException) as exc:
        obter_empresa_atual(TenantContext(empresa_id=2), db)
    assert exc.value.status_code == 404


@pytest.mark.parametrize("base,largura,alturas,total", [
    ("ALTURA_VERTICAL_150",2,2,186.6),("ALTURAS_TECIDO",3.63,4,363.6),
])
def test_salvar_reabrir_conversao_embalagem_sem_alterar_produto(db,base,largura,alturas,total):
    produto=db.get(ProdutoDB,3)
    produto.custo_final=50
    db.commit()
    entrada=OrcamentoInput(cliente_id=1,perfil_comercial="DECORADOR",itens=[{
        "tipo_item":"PRODUTO","descricao":"Cortina teste embalagem","modelo_tecnico":"CORTINA",
        "grupo_tecnico":"TECIDOS_CORTINA","unidade":"UN","quantidade":1,"largura":largura,"altura":2,
        "dados_tecnicos":{"cortina":{"tecidoProdutoId":1,"fator":2.5,"larguraTecido":3,
            "modeloPrega":"WAVE","baseMaoObra":base,"componentes":[{"produto_id":3,"quantidade":64,
                                                "unidades_por_embalagem":500}]}}
    }])
    tenant=TenantContext(empresa_id=1)
    with patch.object(orcamento_service,"_numero",return_value="TESTE-EMBALAGEM"):
        salvo=orcamento_service.criar(db,entrada,tenant)
    db.expire_all()
    reaberto=orcamento_service.obter(db,salvo["id"],tenant)
    cortina=reaberto["itens"][0]["dados_tecnicos"]["cortina"]
    assert cortina["componentes"][0]["unidades_por_embalagem"]==500
    assert cortina["componentes"][0]["quantidade"]==64
    assert cortina["result"]["composicao"][1]["custo_total"]==6.4
    assert cortina["baseMaoObra"]==base
    assert cortina["result"]["mao_de_obra"]["quantidade_alturas"]==alturas
    assert reaberto["total_final"]==total
    assert db.get(ProdutoDB,3).custo_final==50
