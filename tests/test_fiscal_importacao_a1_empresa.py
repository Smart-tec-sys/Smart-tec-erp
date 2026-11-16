from base64 import b64encode
from json import dumps
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.services import fiscal_importacao_a1_empresa as cadastro
from app.services.fiscal_certificado_a1 import CertificadoA1Invalido
from app.services.fiscal_cofre_a1 import CofreIndisponivel
from app.tenant.context import TenantContext


TENANT = TenantContext(empresa_id=42, user_id=7)


def corpo(*, pfx=b"fixture", senha="senha-de-teste"):
    return bytearray(dumps({"pfx": b64encode(pfx).decode("ascii"), "senha": senha}), "utf-8")


@pytest.fixture
def dependencias(monkeypatch):
    monkeypatch.setenv("SMARTTEC_FISCAL_A1_IMPORTACAO_EMPRESA", "1")
    mocks = {
        "situacao_kms_aws": Mock(return_value="CONFIGURACAO_OIDC_DETECTADA_NAO_VERIFICADA"),
        "exigir_admin": Mock(),
        "_empresa": Mock(return_value=SimpleNamespace(id=42, documento="12345678000123")),
        "conferir_pfx_a1_local": Mock(return_value={"validade_ate": "2027-01-01T00:00:00+00:00"}),
        "criar_provedor_kms_staging": Mock(),
        "proteger_a1": Mock(),
        "guardar_envelope_cifrado": Mock(),
    }
    for nome, mock in mocks.items():
        monkeypatch.setattr(cadastro, nome, mock)
    return mocks


def test_grava_apenas_o_envelope_e_nao_libera_emissao(dependencias):
    db = object()
    resposta = cadastro.importar_certificado_empresa(db, TENANT, corpo())
    dependencias["exigir_admin"].assert_called_once_with(db, TENANT)
    dependencias["_empresa"].assert_called_once_with(db, TENANT, bloquear=True)
    dependencias["conferir_pfx_a1_local"].assert_called_once_with(
        b"fixture", b"senha-de-teste", cnpj_emitente="12345678000123",
    )
    dependencias["proteger_a1"].assert_called_once_with(
        42, b"fixture", b"senha-de-teste", dependencias["criar_provedor_kms_staging"].return_value,
    )
    dependencias["guardar_envelope_cifrado"].assert_called_once_with(
        db, TENANT, dependencias["proteger_a1"].return_value,
    )
    assert resposta == {
        "certificado_armazenado": True,
        "validade_ate": "2027-01-01T00:00:00+00:00",
        "emissao_habilitada": False,
    }


def test_importacao_desabilitada_por_padrao(monkeypatch, dependencias):
    monkeypatch.delenv("SMARTTEC_FISCAL_A1_IMPORTACAO_EMPRESA")
    with pytest.raises(HTTPException) as erro:
        cadastro.importar_certificado_empresa(object(), TENANT, corpo())
    assert erro.value.status_code == 404
    dependencias["exigir_admin"].assert_not_called()


def test_empresa_de_laboratorio_nao_pode_importar_a1_real(dependencias):
    with pytest.raises(HTTPException) as erro:
        cadastro.importar_certificado_empresa(
            object(), TenantContext(empresa_id=cadastro.EMPRESA_LAB, user_id=7), corpo(),
        )
    assert erro.value.status_code == 404
    dependencias["proteger_a1"].assert_not_called()


def test_nega_permissao_antes_de_processar_o_arquivo(dependencias):
    dependencias["exigir_admin"].side_effect = HTTPException(403)
    with pytest.raises(HTTPException) as erro:
        cadastro.importar_certificado_empresa(object(), TENANT, corpo())
    assert erro.value.status_code == 403
    dependencias["conferir_pfx_a1_local"].assert_not_called()


def test_certificado_invalido_nao_chega_ao_cofre(dependencias):
    dependencias["conferir_pfx_a1_local"].side_effect = CertificadoA1Invalido("CNPJ divergente")
    with pytest.raises(HTTPException) as erro:
        cadastro.importar_certificado_empresa(object(), TENANT, corpo())
    assert erro.value.status_code == 422
    dependencias["proteger_a1"].assert_not_called()
    dependencias["guardar_envelope_cifrado"].assert_not_called()


def test_cofre_indisponivel_nao_substitui_o_certificado(dependencias):
    dependencias["proteger_a1"].side_effect = CofreIndisponivel()
    with pytest.raises(HTTPException) as erro:
        cadastro.importar_certificado_empresa(object(), TENANT, corpo())
    assert erro.value.status_code == 503
    dependencias["guardar_envelope_cifrado"].assert_not_called()
