from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.financeiro_cadastros import (
    CentroCustoDB,
    ContaFinanceiraDB,
    FormaPagamentoDB,
    PlanoContaDB,
    SituacaoFinanceiraDB,
)
from app.services import financeiro_cadastros_service as svc

EMPRESA_A = SimpleNamespace(empresa_id=1)
EMPRESA_B = SimpleNamespace(empresa_id=2)

PAYLOADS = {
    "contas-financeiras": {"nome": "Caixa", "tipo": "CAIXA", "saldo_inicial": 0, "ativo": True},
    "formas-pagamento": {"nome": "PIX", "tipo": "PIX", "conta_financeira_id": None, "disponivel_para": "AMBOS", "ativo": True},
    "plano-contas": {"codigo": "1.01", "nome": "Receitas", "tipo": "RECEITA", "pai_id": None, "ativo": True},
    "situacoes": {"nome": "Aberto", "tipo": "AMBOS", "quitado": False, "padrao": False, "ativo": True},
    "centros-custo": {"nome": "Showroom", "observacao": None, "ativo": True},
}


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    tabelas = [
        m.__table__
        for m in (ContaFinanceiraDB, FormaPagamentoDB, PlanoContaDB, SituacaoFinanceiraDB, CentroCustoDB)
    ]
    for tabela in tabelas:
        tabela.create(engine)
    sessao = sessionmaker(bind=engine)()
    yield sessao
    sessao.close()


@pytest.mark.parametrize("recurso", list(PAYLOADS))
def test_crud_completo(db, recurso):
    item = svc.criar(db, recurso, EMPRESA_A, dict(PAYLOADS[recurso]))
    assert item.id and item.empresa_id == 1
    assert [i.id for i in svc.listar(db, recurso, EMPRESA_A)] == [item.id]

    atualizado = svc.atualizar(db, recurso, item.id, EMPRESA_A, {"ativo": False})
    assert atualizado.ativo is False
    assert svc.listar(db, recurso, EMPRESA_A, apenas_ativos=True) == []

    svc.remover(db, recurso, item.id, EMPRESA_A)
    with pytest.raises(svc.CadastroNaoEncontrado):
        svc.obter(db, recurso, item.id, EMPRESA_A)


@pytest.mark.parametrize("recurso", list(PAYLOADS))
def test_isolamento_por_empresa(db, recurso):
    item = svc.criar(db, recurso, EMPRESA_A, dict(PAYLOADS[recurso]))
    assert svc.listar(db, recurso, EMPRESA_B) == []
    with pytest.raises(svc.CadastroNaoEncontrado):
        svc.obter(db, recurso, item.id, EMPRESA_B)
    with pytest.raises(svc.CadastroNaoEncontrado):
        svc.atualizar(db, recurso, item.id, EMPRESA_B, {"ativo": False})
    with pytest.raises(svc.CadastroNaoEncontrado):
        svc.remover(db, recurso, item.id, EMPRESA_B)
    # Mesmo nome em outra empresa e permitido.
    outro = svc.criar(db, recurso, EMPRESA_B, dict(PAYLOADS[recurso]))
    assert outro.empresa_id == 2


@pytest.mark.parametrize("recurso", list(PAYLOADS))
def test_unicidade_por_empresa_sem_diferenciar_caixa(db, recurso):
    svc.criar(db, recurso, EMPRESA_A, dict(PAYLOADS[recurso]))
    duplicado = dict(PAYLOADS[recurso])
    duplicado["nome"] = duplicado["nome"].upper()
    if recurso == "plano-contas":
        duplicado["codigo"] = "9.99"
    with pytest.raises(svc.CadastroConflito):
        svc.criar(db, recurso, EMPRESA_A, duplicado)


def test_plano_contas_codigo_unico_e_hierarquia(db):
    raiz = svc.criar(db, "plano-contas", EMPRESA_A, dict(PAYLOADS["plano-contas"]))
    with pytest.raises(svc.CadastroConflito):
        svc.criar(db, "plano-contas", EMPRESA_A,
                  {"codigo": "1.01", "nome": "Outro", "tipo": "RECEITA", "pai_id": None, "ativo": True})
    filho = svc.criar(db, "plano-contas", EMPRESA_A,
                      {"codigo": "1.01.01", "nome": "Filho", "tipo": "RECEITA", "pai_id": raiz.id, "ativo": True})

    with pytest.raises(svc.CadastroConflito):
        svc.atualizar(db, "plano-contas", raiz.id, EMPRESA_A, {"pai_id": raiz.id})
    with pytest.raises(svc.CadastroConflito):
        svc.atualizar(db, "plano-contas", raiz.id, EMPRESA_A, {"pai_id": filho.id})
    with pytest.raises(svc.CadastroConflito):
        svc.remover(db, "plano-contas", raiz.id, EMPRESA_A)
    with pytest.raises(svc.CadastroNaoEncontrado):
        svc.criar(db, "plano-contas", EMPRESA_B,
                  {"codigo": "x", "nome": "x", "tipo": "RECEITA", "pai_id": raiz.id, "ativo": True})


def test_atualizar_mantendo_proprio_nome_nao_conflita(db):
    item = svc.criar(db, "centros-custo", EMPRESA_A, dict(PAYLOADS["centros-custo"]))
    atualizado = svc.atualizar(db, "centros-custo", item.id, EMPRESA_A, {"nome": "SHOWROOM"})
    assert atualizado.nome == "SHOWROOM"


def test_forma_pagamento_conta_padrao_e_disponibilidade(db):
    conta = svc.criar(db, "contas-financeiras", EMPRESA_A, dict(PAYLOADS["contas-financeiras"]))
    forma = svc.criar(db, "formas-pagamento", EMPRESA_A,
                      {"nome": "PIX", "tipo": "PIX", "conta_financeira_id": conta.id, "disponivel_para": "RECEBER", "ativo": True})
    assert forma.conta_financeira_id == conta.id and forma.disponivel_para == "RECEBER"

    limpa = svc.atualizar(db, "formas-pagamento", forma.id, EMPRESA_A, {"conta_financeira_id": None})
    assert limpa.conta_financeira_id is None

    # Conta de outra empresa nao pode ser usada como padrao.
    with pytest.raises(svc.CadastroNaoEncontrado):
        svc.criar(db, "formas-pagamento", EMPRESA_B,
                  {"nome": "Boleto", "tipo": "BOLETO", "conta_financeira_id": conta.id, "disponivel_para": "AMBOS", "ativo": True})


def test_schema_forma_pagamento_valida_disponivel_para():
    from pydantic import ValidationError
    from app.schemas.financeiro_cadastros import FormaPagamentoCreate

    assert FormaPagamentoCreate(nome="PIX", disponivel_para="pagar").disponivel_para == "PAGAR"
    assert FormaPagamentoCreate(nome="PIX").disponivel_para == "AMBOS"
    with pytest.raises(ValidationError):
        FormaPagamentoCreate(nome="PIX", disponivel_para="TODOS")


def test_situacao_padrao_unica_por_empresa_e_tipo(db):
    aberto = svc.criar(db, "situacoes", EMPRESA_A,
                       {"nome": "Aberto", "tipo": "AMBOS", "quitado": False, "padrao": True, "ativo": True})
    outra = svc.criar(db, "situacoes", EMPRESA_A,
                      {"nome": "Em análise", "tipo": "AMBOS", "quitado": False, "padrao": True, "ativo": True})
    db.refresh(aberto)
    assert aberto.padrao is False and outra.padrao is True

    outra_empresa = svc.criar(db, "situacoes", EMPRESA_B,
                              {"nome": "Aberto", "tipo": "AMBOS", "quitado": False, "padrao": True, "ativo": True})
    db.refresh(outra)
    assert outra.padrao is True and outra_empresa.padrao is True


def test_situacao_quitada_nao_pode_ser_padrao(db):
    with pytest.raises(svc.CadastroConflito):
        svc.criar(db, "situacoes", EMPRESA_A,
                  {"nome": "Pago", "tipo": "AMBOS", "quitado": True, "padrao": True, "ativo": True})
    pago = svc.criar(db, "situacoes", EMPRESA_A,
                     {"nome": "Pago", "tipo": "AMBOS", "quitado": True, "padrao": False, "ativo": True})
    with pytest.raises(svc.CadastroConflito):
        svc.atualizar(db, "situacoes", pago.id, EMPRESA_A, {"padrao": True})
    cancelado = svc.criar(db, "situacoes", EMPRESA_A,
                          {"nome": "Cancelado", "tipo": "AMBOS", "quitado": False, "padrao": False, "ativo": True})
    with pytest.raises(svc.CadastroConflito):
        svc.atualizar(db, "situacoes", cancelado.id, EMPRESA_A, {"padrao": True, "ativo": False})