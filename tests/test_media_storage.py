"""Armazenamento de logo/avatar: sem rede, sem Supabase real e sem banco real."""
import asyncio
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import requests
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from starlette.datastructures import Headers, UploadFile

from app import media_storage as ms
from app.auth.service import ExternalIdentity
from app.database import Base
from app.models.empresa import EmpresaDB
from app.models.usuario import UsuarioDB
from app.routes.auth import delete_auth_me_photo, upload_auth_me_photo
from app.routes.empresa import delete_empresa_logo, upload_empresa_logo
from app.tenant.context import TenantContext

ROOT = Path(__file__).resolve().parents[1]
JPEG = b"\xff\xd8\xff\xe0" + b"jpeg-sintetico"
PNG = b"\x89PNG\r\n\x1a\n" + b"png-sintetico"
WEBP = b"RIFF\x10\x00\x00\x00WEBPVP8 " + b"webp"
LOGO_LEGADA_1 = "empresas/empresa-1-6fec7bc9c6734e3280faafb7c8ca6af6.jpg"
FOTO_LEGADA_1 = "usuarios/user-1-a90781f45ea54e2bbcaa0220b83381b4.jpg"


class StorageFalso:
    def __init__(self):
        self.objetos = {}
        self.removidos = []
        self.falhar_gravacao = False
        self.falhar_leitura = False

    def salvar(self, chave, conteudo, content_type):
        if self.falhar_gravacao:
            raise ms.MediaStorageError("indisponível")
        assert chave not in self.objetos, "nunca sobrescrever"
        self.objetos[chave] = (conteudo, content_type)

    def ler(self, chave):
        if self.falhar_leitura:
            raise ms.MediaStorageError("indisponível")
        if chave not in self.objetos:
            raise ms.MediaNaoEncontrada(chave)
        return self.objetos[chave][0]

    def remover(self, chave):
        self.removidos.append(chave)
        self.objetos.pop(chave, None)


@pytest.fixture
def storage():
    falso = StorageFalso()
    with patch.object(ms, "obter_media_storage", return_value=falso):
        yield falso


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[Base.metadata.tables[n] for n in ("empresas", "usuarios")])
    with Session(engine) as session:
        session.add_all([
            EmpresaDB(id=1, nome="Empresa Teste", slug="teste", logo_url="/media/" + LOGO_LEGADA_1),
            EmpresaDB(id=2, nome="Outra Empresa", slug="outra", logo_url="/media/empresas/empresa-2-aa.jpg"),
            EmpresaDB(id=11, nome="Empresa Onze", slug="onze"),
            UsuarioDB(id=1, nome="Usuário Um", email="um@example.invalid", provedor="supabase",
                      provedor_subject="sub-1", foto_url="/media/" + FOTO_LEGADA_1),
            UsuarioDB(id=2, nome="Usuário Dois", email="dois@example.invalid", provedor="supabase",
                      provedor_subject="sub-2", foto_url="/media/usuarios/user-2-bb.png"),
        ])
        session.commit()
        yield session
    engine.dispose()


def arquivo(conteudo=JPEG, tipo="image/jpeg"):
    return UploadFile(file=io.BytesIO(conteudo), filename="x", headers=Headers({"content-type": tipo}))


def enviar_logo(db, empresa_id, conteudo=JPEG, tipo="image/jpeg"):
    return asyncio.run(upload_empresa_logo(arquivo(conteudo, tipo), TenantContext(empresa_id=empresa_id), db))


def enviar_foto(db, subject, conteudo=PNG, tipo="image/png"):
    return asyncio.run(upload_auth_me_photo(arquivo(conteudo, tipo), ExternalIdentity("supabase", subject), db))


# ---------------------------------------------------------------- validações

@pytest.mark.parametrize("chave", [
    LOGO_LEGADA_1, FOTO_LEGADA_1, "empresas/1/logo-abc.png", "usuarios/7/avatar-abc.webp",
    "empresas/logo-original.png",
])
def test_chaves_aceitas_incluem_referencias_existentes(chave):
    assert ms.chave_valida(chave)


@pytest.mark.parametrize("chave", [
    "", "../app/main.py", "empresas/../../.env", "empresas/1/../2/x.jpg", "outros/x.jpg",
    "empresas/x.txt", "empresas/a/b.jpg", "empresas/1/2/x.jpg", "/empresas/x.jpg", "empresas/.x.jpg",
    "empresas\\x.jpg", "empresas/x.jpg/", "empresas/x .jpg",
])
def test_chaves_recusadas(chave):
    assert not ms.chave_valida(chave)


def test_validacao_de_imagem_por_tipo_assinatura_e_tamanho():
    assert ms.validar_imagem("image/jpeg", JPEG) == ".jpg"
    assert ms.validar_imagem("image/png", PNG) == ".png"
    assert ms.validar_imagem("image/webp", WEBP) == ".webp"
    casos = [("image/gif", JPEG, "formato"), ("image/jpeg", b"", "vazio"), ("image/png", JPEG, "não corresponde"),
             ("image/jpeg", b"<svg onload=alert(1)>", "não corresponde"),
             ("image/jpeg", JPEG + b"0" * (5 * 1024 * 1024), "5 MB")]
    for tipo, conteudo, mensagem in casos:
        with pytest.raises(ms.ImagemInvalida, match=mensagem):
            ms.validar_imagem(tipo, conteudo)


def test_dono_formato_novo_e_legado_sem_confundir_ids():
    assert ms.pertence_ao_dono("empresas/1/logo-a.jpg", "empresas", 1, "empresa")
    assert ms.pertence_ao_dono(LOGO_LEGADA_1, "empresas", 1, "empresa")
    assert not ms.pertence_ao_dono("empresas/empresa-11-a.jpg", "empresas", 1, "empresa")
    assert not ms.pertence_ao_dono("empresas/11/logo-a.jpg", "empresas", 1, "empresa")
    assert not ms.pertence_ao_dono("empresas/empresa-2-a.jpg", "empresas", 1, "empresa")
    assert not ms.pertence_ao_dono("usuarios/1/avatar-a.jpg", "empresas", 1, "empresa")
    assert not ms.pertence_ao_dono(None, "empresas", 1, "empresa")


# ---------------------------------------------------------------- logo

def test_upload_logo_grava_por_empresa_e_remove_somente_a_antiga_da_mesma_empresa(db, storage):
    resultado = enviar_logo(db, 1)
    chave = resultado["logo_url"].removeprefix("/media/")
    assert chave.startswith("empresas/1/logo-") and chave.endswith(".jpg")
    assert storage.objetos[chave] == (JPEG, "image/jpeg")
    assert db.get(EmpresaDB, 1).logo_url == resultado["logo_url"]
    assert storage.removidos == [LOGO_LEGADA_1]
    assert db.get(EmpresaDB, 2).logo_url == "/media/empresas/empresa-2-aa.jpg"


def test_referencia_inconsistente_de_outra_empresa_nunca_e_apagada(db, storage):
    db.get(EmpresaDB, 11).logo_url = "/media/empresas/empresa-1-zz.jpg"
    db.commit()
    enviar_logo(db, 11, PNG, "image/png")
    assert storage.removidos == []


def test_tenant_so_altera_a_propria_logo_e_empresa_inativa_e_recusada(db, storage):
    enviar_logo(db, 2)
    assert db.get(EmpresaDB, 1).logo_url == "/media/" + LOGO_LEGADA_1
    assert storage.removidos == ["empresas/empresa-2-aa.jpg"]
    db.get(EmpresaDB, 2).status = "INATIVA"
    db.commit()
    with pytest.raises(HTTPException) as exc:
        enviar_logo(db, 2)
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        delete_empresa_logo(TenantContext(empresa_id=2), db)
    assert exc.value.status_code == 404


def test_imagem_invalida_nao_grava_nada(db, storage):
    with pytest.raises(HTTPException) as exc:
        enviar_logo(db, 1, b"texto", "image/jpeg")
    assert exc.value.status_code == 400
    assert storage.objetos == {} and storage.removidos == []
    assert db.get(EmpresaDB, 1).logo_url == "/media/" + LOGO_LEGADA_1


def test_falha_no_storage_nao_altera_banco(db, storage):
    storage.falhar_gravacao = True
    with pytest.raises(HTTPException) as exc:
        enviar_logo(db, 1)
    assert exc.value.status_code == 503
    db.expire_all()
    assert db.get(EmpresaDB, 1).logo_url == "/media/" + LOGO_LEGADA_1


def test_falha_no_banco_faz_rollback_e_remove_objeto_novo(db, storage):
    with patch.object(db, "commit", side_effect=SQLAlchemyError("falha sintética")):
        with pytest.raises(HTTPException) as exc:
            enviar_logo(db, 1)
    assert exc.value.status_code == 500
    assert storage.objetos == {}
    assert len(storage.removidos) == 1 and storage.removidos[0].startswith("empresas/1/logo-")
    db.expire_all()
    assert db.get(EmpresaDB, 1).logo_url == "/media/" + LOGO_LEGADA_1


def test_remover_logo_com_arquivo_ja_ausente_preserva_fluxo(db, storage):
    assert delete_empresa_logo(TenantContext(empresa_id=1), db) == {"logo_url": None}
    assert db.get(EmpresaDB, 1).logo_url is None
    assert storage.removidos == [LOGO_LEGADA_1]
    assert db.get(EmpresaDB, 2).logo_url == "/media/empresas/empresa-2-aa.jpg"


def test_falha_no_banco_ao_remover_logo_mantem_referencia(db, storage):
    with patch.object(db, "commit", side_effect=SQLAlchemyError("falha sintética")):
        with pytest.raises(HTTPException) as exc:
            delete_empresa_logo(TenantContext(empresa_id=1), db)
    assert exc.value.status_code == 500 and storage.removidos == []
    db.expire_all()
    assert db.get(EmpresaDB, 1).logo_url == "/media/" + LOGO_LEGADA_1


# ---------------------------------------------------------------- avatar

def test_avatar_isolado_por_usuario(db, storage):
    resultado = enviar_foto(db, "sub-1")
    chave = resultado["foto_url"].removeprefix("/media/")
    assert chave.startswith("usuarios/1/avatar-") and chave.endswith(".png")
    assert storage.removidos == [FOTO_LEGADA_1]
    assert db.get(UsuarioDB, 2).foto_url == "/media/usuarios/user-2-bb.png"
    db.get(UsuarioDB, 2).foto_url = "/media/usuarios/user-1-cc.png"
    db.commit()
    storage.removidos.clear()
    assert delete_auth_me_photo(ExternalIdentity("supabase", "sub-2"), db) == {"foto_url": None}
    assert storage.removidos == []


def test_avatar_usuario_inativo_ou_desconhecido(db, storage):
    db.get(UsuarioDB, 2).status = "INATIVO"
    db.commit()
    with pytest.raises(HTTPException) as exc:
        enviar_foto(db, "sub-2")
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException) as exc:
        delete_auth_me_photo(ExternalIdentity("supabase", "inexistente"), db)
    assert exc.value.status_code == 404
    assert storage.objetos == {}


def test_avatar_falha_no_banco_faz_rollback(db, storage):
    with patch.object(db, "commit", side_effect=SQLAlchemyError("falha sintética")):
        with pytest.raises(HTTPException) as exc:
            enviar_foto(db, "sub-1")
    assert exc.value.status_code == 500 and storage.objetos == {}
    db.expire_all()
    assert db.get(UsuarioDB, 1).foto_url == "/media/" + FOTO_LEGADA_1


# ---------------------------------------------------------------- rota /media

@pytest.fixture
def cliente(storage):
    import app.main
    return TestClient(app.main.app)


def test_media_serve_referencias_existentes_sem_alterar_url(cliente, storage):
    storage.objetos[LOGO_LEGADA_1] = (JPEG, "image/jpeg")
    resposta = cliente.get("/media/" + LOGO_LEGADA_1)
    assert resposta.status_code == 200 and resposta.content == JPEG
    assert resposta.headers["content-type"] == "image/jpeg"
    assert resposta.headers["x-content-type-options"] == "nosniff"
    assert "max-age" in resposta.headers["cache-control"]
    assert cliente.head("/media/" + LOGO_LEGADA_1).status_code == 200


def test_media_ausente_invalida_e_indisponivel(cliente, storage):
    assert cliente.get("/media/" + FOTO_LEGADA_1).status_code == 404
    for caminho in ("/media/..%2Fapp%2Fmain.py", "/media/empresas/x.txt", "/media/outros/x.jpg", "/media/"):
        assert cliente.get(caminho).status_code == 404, caminho
    storage.falhar_leitura = True
    storage.objetos[LOGO_LEGADA_1] = (JPEG, "image/jpeg")
    assert cliente.get("/media/" + LOGO_LEGADA_1).status_code == 503


def test_media_cors_para_pdf_do_orcamento(cliente, storage):
    storage.objetos["empresas/1/logo-a.png"] = (PNG, "image/png")
    resposta = cliente.get("/media/empresas/1/logo-a.png", headers={"Origin": "https://smart-tec-persianas-web.onrender.com"})
    assert resposta.status_code == 200 and resposta.headers["content-type"] == "image/png"
    assert resposta.headers.get("access-control-allow-origin")


# ---------------------------------------------------------------- local

def test_storage_local_configuravel_sem_sobrescrever(tmp_path, monkeypatch):
    monkeypatch.setenv("SMARTTEC_MEDIA_STORAGE", "local")
    monkeypatch.setenv("SMARTTEC_MEDIA_DIR", str(tmp_path))
    local = ms.obter_media_storage()
    assert isinstance(local, ms.LocalMediaStorage)
    local.salvar("empresas/1/logo-a.jpg", JPEG, "image/jpeg")
    assert (tmp_path / "empresas" / "1" / "logo-a.jpg").read_bytes() == JPEG
    assert local.ler("empresas/1/logo-a.jpg") == JPEG
    with pytest.raises(ms.MediaStorageError):
        local.salvar("empresas/1/logo-a.jpg", PNG, "image/png")
    with pytest.raises(ms.MediaNaoEncontrada):
        local.ler("../segredo.jpg")
    local.remover("empresas/1/logo-a.jpg")
    local.remover("empresas/1/logo-a.jpg")
    with pytest.raises(ms.MediaNaoEncontrada):
        local.ler("empresas/1/logo-a.jpg")


def test_modo_padrao_continua_local_na_pasta_media(monkeypatch):
    monkeypatch.delenv("SMARTTEC_MEDIA_STORAGE", raising=False)
    monkeypatch.delenv("SMARTTEC_MEDIA_DIR", raising=False)
    local = ms.obter_media_storage()
    assert isinstance(local, ms.LocalMediaStorage) and local.raiz == Path("media")


# ---------------------------------------------------------------- Supabase

class Resposta:
    def __init__(self, status_code, content=b"", corpo=None):
        self.status_code = status_code
        self.content = content
        self.corpo = corpo

    def json(self):
        if self.corpo is None:
            raise ValueError("sem JSON")
        return self.corpo


NAO_ENCONTRADO = {"statusCode": "404", "error": "not_found", "message": "Object not found"}
CHAVE_INVALIDA = {"statusCode": "403", "error": "Unauthorized", "message": "Invalid Compact JWS", "code": "AccessDenied"}


class SessaoFalsa:
    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.chamadas = []

    def request(self, metodo, url, **kwargs):
        self.chamadas.append((metodo, url, kwargs))
        resposta = self.respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


def test_cliente_supabase_bucket_privado_sem_upsert_e_sem_expor_chave():
    sessao = SessaoFalsa([Resposta(200), Resposta(200, JPEG), Resposta(400, corpo=NAO_ENCONTRADO), Resposta(200), Resposta(500)])
    supa = ms.SupabaseMediaStorage("https://proj.supabase.co/", "sb_secret_FAKE", "smarttec-media", sessao=sessao)
    supa.salvar(LOGO_LEGADA_1, JPEG, "image/jpeg")
    metodo, url, kw = sessao.chamadas[0]
    assert metodo == "POST" and url == f"https://proj.supabase.co/storage/v1/object/smarttec-media/{LOGO_LEGADA_1}"
    assert kw["headers"]["x-upsert"] == "false" and kw["headers"]["Content-Type"] == "image/jpeg"
    assert kw["headers"]["apikey"] == "sb_secret_FAKE" and kw["timeout"] == 15
    assert supa.ler(LOGO_LEGADA_1) == JPEG
    assert sessao.chamadas[1][1].endswith(f"/storage/v1/object/authenticated/smarttec-media/{LOGO_LEGADA_1}")
    with pytest.raises(ms.MediaNaoEncontrada):
        supa.ler(FOTO_LEGADA_1)
    supa.remover(LOGO_LEGADA_1)
    assert sessao.chamadas[3][0] == "DELETE" and sessao.chamadas[3][2]["json"] == {"prefixes": [LOGO_LEGADA_1]}
    with pytest.raises(ms.MediaStorageError) as exc:
        supa.salvar("empresas/1/logo-b.jpg", JPEG, "image/jpeg")
    assert "sb_secret_FAKE" not in str(exc.value) and "sb_secret_FAKE" not in repr(supa)
    supa.remover("../tudo")
    assert len(sessao.chamadas) == 5


def test_cliente_supabase_falha_de_rede_vira_indisponivel():
    supa = ms.SupabaseMediaStorage("https://proj.supabase.co", "k", "b",
                                   sessao=SessaoFalsa([requests.ConnectionError("x"), requests.Timeout("x")]))
    with pytest.raises(ms.MediaStorageError):
        supa.ler(LOGO_LEGADA_1)
    supa.remover(LOGO_LEGADA_1)


@pytest.mark.parametrize("resposta", [
    Resposta(400, corpo=CHAVE_INVALIDA), Resposta(400), Resposta(400, corpo={"statusCode": "abc"}),
    Resposta(401), Resposta(403),
])
def test_cliente_supabase_chave_invalida_nao_vira_imagem_inexistente(resposta):
    supa = ms.SupabaseMediaStorage("https://proj.supabase.co", "sb_secret_FAKE", "b", sessao=SessaoFalsa([resposta]))
    with pytest.raises(ms.MediaStorageError) as exc:
        supa.ler(LOGO_LEGADA_1)
    assert not isinstance(exc.value, ms.MediaNaoEncontrada) and "sb_secret_FAKE" not in str(exc.value)


def test_cliente_supabase_objeto_ausente_vira_404():
    for resposta in (Resposta(400, corpo=NAO_ENCONTRADO), Resposta(404)):
        supa = ms.SupabaseMediaStorage("https://proj.supabase.co", "k", "b", sessao=SessaoFalsa([resposta]))
        with pytest.raises(ms.MediaNaoEncontrada):
            supa.ler(LOGO_LEGADA_1)


@pytest.mark.parametrize("ambiente,mensagem", [
    ({"SMARTTEC_MEDIA_STORAGE": "s3"}, "SMARTTEC_MEDIA_STORAGE inválido"),
    ({"SMARTTEC_MEDIA_STORAGE": "supabase", "SUPABASE_STORAGE_SECRET_KEY": "sb_secret_NAO_VAZAR"},
     "SUPABASE_STORAGE_URL, SUPABASE_STORAGE_BUCKET"),
    ({"SMARTTEC_MEDIA_STORAGE": "supabase", "SUPABASE_STORAGE_URL": "http://inseguro.invalid",
      "SUPABASE_STORAGE_SECRET_KEY": "sb_secret_NAO_VAZAR", "SUPABASE_STORAGE_BUCKET": "b"}, "https"),
])
def test_inicializacao_falha_com_configuracao_incompleta_sem_vazar_chave(tmp_path, ambiente, mensagem):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("SUPABASE_", "SMARTTEC_", "DB_", "DATABASE_URL"))}
    env.update({"DATABASE_URL": "postgresql://test_user@localhost/test_database", **ambiente})
    codigo = (f"import sys; sys.path.insert(0, {str(ROOT)!r}); import app.settings as s; "
              f"s.PROJECT_ROOT = __import__('pathlib').Path({str(tmp_path)!r}); import app.main")
    resultado = subprocess.run([sys.executable, "-c", codigo], env=env, cwd=ROOT,
                               capture_output=True, text=True, timeout=60)
    assert resultado.returncode != 0
    assert mensagem in resultado.stderr
    assert "sb_secret_NAO_VAZAR" not in resultado.stderr + resultado.stdout


def test_inicializacao_supabase_completa(tmp_path):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("SUPABASE_", "SMARTTEC_", "DB_", "DATABASE_URL"))}
    env.update({"DATABASE_URL": "postgresql://test_user@localhost/test_database", "SMARTTEC_MEDIA_STORAGE": "supabase",
                "SUPABASE_STORAGE_URL": "https://proj.supabase.co", "SUPABASE_STORAGE_SECRET_KEY": "k",
                "SUPABASE_STORAGE_BUCKET": "smarttec-media"})
    codigo = (f"import sys,json; sys.path.insert(0, {str(ROOT)!r}); import app.settings as s; "
              f"s.PROJECT_ROOT = __import__('pathlib').Path({str(tmp_path)!r}); import app.main; "
              "from app.media_storage import obter_media_storage as o; print(json.dumps(type(o()).__name__))")
    resultado = subprocess.run([sys.executable, "-c", codigo], env=env, cwd=ROOT,
                               capture_output=True, text=True, timeout=60)
    assert resultado.returncode == 0, resultado.stderr
    assert json.loads(resultado.stdout.strip().splitlines()[-1]) == "SupabaseMediaStorage"
