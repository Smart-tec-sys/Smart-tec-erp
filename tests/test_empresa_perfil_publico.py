"""Perfil público multiempresa: SQLite em memória, sem banco real."""
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from test_orcamento_cortina_pdf_local import db  # noqa: F401
from app.models.empresa import EmpresaDB
from app.routes.empresa import obter_empresa_atual, atualizar_empresa_atual
from app.schemas.empresa_perfil import EmpresaPerfilUpdate
from app.tenant.context import TenantContext


def entrada(**updates):
    return EmpresaPerfilUpdate.model_validate({
        "nome": "Razão Social Sintética Ltda", "nome_fantasia": "Empresa de Teste",
        "documento": "12.345.678/0001-95", "perfil_publico": {
            "logradouro": "Rua Sintética", "numero": "123", "complemento": "Sala 2",
            "bairro": "Centro", "cidade": "Cidade Teste", "estado": "sp", "cep": "01000-000",
            "telefone_comercial": "(11) 3333-4444", "telefone_celular": "(11) 99999-8888",
            "email": "vendas@example.invalid", "site": "empresa.example.invalid",
        }, **updates,
    })


def test_salvar_reabrir_perfil_sem_vazar_configuracoes_nem_alterar_outro_tenant(db):
    empresa = db.get(EmpresaDB, 1)
    empresa.configuracoes = {"segredo_interno": "não expor", "modulo": {"habilitado": True}}
    empresa.logo_url = "/media/empresas/logo-original.png"
    db.commit()
    resultado = atualizar_empresa_atual(entrada(), TenantContext(empresa_id=1), db)
    db.expire_all()
    reaberto = obter_empresa_atual(TenantContext(empresa_id=1), db)
    assert resultado == reaberto
    assert reaberto["nome"] == "Razão Social Sintética Ltda"
    assert reaberto["documento"] == "12.345.678/0001-95"
    assert reaberto["perfil_publico"]["estado"] == "SP"
    assert reaberto["perfil_publico"]["site"] == "https://empresa.example.invalid"
    assert reaberto["logo_url"] == "/media/empresas/logo-original.png"
    assert "segredo_interno" not in reaberto and "configuracoes" not in reaberto
    configuracoes = db.get(EmpresaDB, 1).configuracoes
    assert configuracoes["segredo_interno"] == "não expor"
    assert configuracoes["modulo"] == {"habilitado": True}
    outra = obter_empresa_atual(TenantContext(empresa_id=2), db)
    assert outra["nome"] == "Outra empresa" and outra["perfil_publico"] == {}


def test_limpar_opcionais_e_omitir_dados_legados_invalidos(db):
    empresa = db.get(EmpresaDB, 1)
    empresa.configuracoes = {"perfil_publico": {"email": "inválido", "telefone_comercial": "123",
                                               "cidade": " Cidade válida ", "senha": "não expor"}}
    db.commit()
    assert obter_empresa_atual(TenantContext(empresa_id=1), db)["perfil_publico"] == {"cidade": "Cidade válida"}
    resultado = atualizar_empresa_atual(entrada(nome_fantasia=" ", documento=" ", perfil_publico={"email": " "}), TenantContext(empresa_id=1), db)
    assert resultado["perfil_publico"] == {} and resultado["nome_fantasia"] is None and resultado["documento"] is None


@pytest.mark.parametrize("campo,valor", [("email", "sem-arroba"), ("site", "javascript:alert(1)"),
    ("telefone_comercial", "123"), ("cep", "1234"), ("estado", "1A"), ("cidade", 123), ("senha", "x")])
def test_validacao_dos_dados_publicos(campo, valor):
    with pytest.raises(ValidationError):
        entrada(perfil_publico={campo: valor})


def test_nome_documento_e_empresa_inativa(db):
    for mudanca in ({"nome": " "}, {"documento": "inválido"}, {"id": 2}, {"logo_url": "/outra-logo"}):
        with pytest.raises(ValidationError):
            entrada(**mudanca)
    db.get(EmpresaDB, 2).status = "INATIVA"
    db.flush()
    with pytest.raises(HTTPException) as exc:
        atualizar_empresa_atual(entrada(), TenantContext(empresa_id=2), db)
    assert exc.value.status_code == 404


def test_falha_de_gravacao_e_visivel_com_rollback(db):
    original = obter_empresa_atual(TenantContext(empresa_id=1), db)
    with patch.object(db, "commit", side_effect=SQLAlchemyError("falha sintética")):
        with pytest.raises(HTTPException) as exc:
            atualizar_empresa_atual(entrada(), TenantContext(empresa_id=1), db)
    assert exc.value.status_code == 500
    assert obter_empresa_atual(TenantContext(empresa_id=1), db) == original
