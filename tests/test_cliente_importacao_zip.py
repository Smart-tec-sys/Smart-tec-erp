"""Backup GestãoClick: arquivos sintéticos e SQLite em memória, sem banco real."""
import os
import stat
import warnings
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import pytest
from fastapi import HTTPException, UploadFile
from openpyxl import Workbook
from sqlalchemy.exc import SQLAlchemyError

from test_orcamento_cortina_pdf_local import db  # noqa: F401
from app.models.cliente import ClienteDB
from app.models.orcamento import OrcamentoDB
from app.routes.cliente_importacao import confirmar as confirmar_rota, previa as previa_rota
from app.schemas.cliente_importacao import ImportacaoConfiguracao
from app.services import cliente_importacao_service as service
from app.tenant.context import TenantContext

TENANT = TenantContext(empresa_id=1)


def xlsx(rows):
    workbook = Workbook()
    for row in rows:
        workbook.active.append(row)
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def arquivos():
    clientes = [["Codigo", "Tipo de pessoa", "Nome", "CPF", "RG", "Data de nascimento",
                 "Razão social", "Nome social", "CNPJ", "Inscrição estadual", "Inscrição municipal",
                 "Ativo", "Telefone", "Celular", "E-mail", "Cadastrado em"]]
    for code, name, document, email in (
        ("GC-1", "Fátima Zanetti", "52998224725", "Fatima@Example.test"),
        ("GC-2", "Gillian", "11144477735", "Gillian@Example.test"),
        ("GC-3", "Novo cliente", "", "Novo@Example.test"),
    ):
        clientes.append([code, "PF", name, document, "", "", "", "", "", "", "", "Sim", "", "", email, ""])
    return {
        "clientes/clientes.xlsx": xlsx(clientes),
        "clientes/clientes_enderecos.xlsx": xlsx([
            ["C\uFFFDdigo", "Tipo", "CEP", "Logradouro", "N\uFFFDmero", "Complemento", "Bairro", "Cidade", "UF"],
            ["GC-1", "Principal", "01001000", "Rua das Flores", "1", "", "Centro", "São Paulo", "SP"],
            ["GC-2", "Principal", "01001000", "Rua dos Testes", "2", "", "Centro", "São Paulo", "SP"],
            ["GC-3", "Principal", "01001000", "Rua Nova", "3", "", "Centro", "São Paulo", "SP"],
        ]),
        "clientes/clientes_contatos.xlsx": xlsx([
            ["C\uFFFDdigo", "Tipo de contato", "Nome", "Contato", "Cargo", "Observa\uFFFD\uFFFDo"],
            ["GC-1", "WhatsApp", "Contato de teste", "+5511999998888", "", "Texto original"],
        ]),
    }


def zip_bytes(entries):
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as package:
        for name, data in entries.items():
            package.writestr(name, data)
    return output.getvalue()


def upload(content):
    return UploadFile(filename="backup_gestaoclick_original.zip", file=BytesIO(content))


def preview(db, content, config):
    return previa_rota(file=upload(content), configuracao=config.model_dump_json(),
                      db=db, tenant=TENANT, enderecos_file=None, contatos_file=None)


def confirm(db, content, config, hash_value, accepted=True):
    return confirmar_rota(file=upload(content), configuracao=config.model_dump_json(),
                          previa_hash=hash_value, confirmado=accepted, db=db, tenant=TENANT,
                          enderecos_file=None, contatos_file=None)


def test_zip_rota_automatica_preserva_ids_orcamentos_e_reimportacao(db):
    for name, document in (("Fátima Zanetti", "52998224725"), ("Gillian", "11144477735")):
        cliente = ClienteDB(empresa_id=1, nome=name, documento=document, tipo="Física")
        db.add(cliente)
        db.flush()
        db.add(OrcamentoDB(empresa_id=1, numero=name, cliente_id=cliente.id, total_final=123))
    db.commit()
    before = {row.nome: row.id for row in db.query(ClienteDB).all()}
    unauthorized = preview(db, zip_bytes(arquivos()), ImportacaoConfiguracao())
    assert unauthorized.complementar == 0
    assert sum(bool(row.campos_disponiveis) for row in unauthorized.linhas) == 2
    assert all(not row.campos_complementar for row in unauthorized.linhas)
    config = ImportacaoConfiguracao(complementar_vazios=True)
    content = zip_bytes(arquivos())
    result = preview(db, content, config)
    assert (result.inserir, result.complementar, result.erros) == (1, 2, 0)
    assert result.fontes["enderecos"].vinculados == 3
    assert result.fontes["contatos"].vinculados == 1
    assert db.query(ClienteDB).count() == len(before)
    with pytest.raises(HTTPException) as exc:
        confirm(db, content, config, result.previa_hash, accepted=False)
    assert exc.value.status_code == 422
    report = confirm(db, content, config, result.previa_hash)
    assert report.concluido and (report.inseridos, report.complementados) == (1, 2)
    for order in db.query(OrcamentoDB).all():
        assert order.cliente_id == before[order.numero] and order.total_final == 123
    second = preview(db, content, config)
    assert (second.inserir, second.complementar, second.ignorados) == (0, 0, 3)
    count = db.query(ClienteDB).count()
    confirm(db, content, config, second.previa_hash)
    assert db.query(ClienteDB).count() == count
    assert db.get(ClienteDB, before["Fátima Zanetti"]).logradouro == "Rua das Flores"


def test_zip_rollback_integral(db):
    db.add(ClienteDB(empresa_id=1, nome="Fátima Zanetti", documento="52998224725", tipo="Física"))
    db.commit()
    config = ImportacaoConfiguracao(complementar_vazios=True)
    content = zip_bytes(arquivos())
    result = preview(db, content, config)
    count = db.query(ClienteDB).count()
    with patch.object(db, "commit", side_effect=SQLAlchemyError("falha sintética")):
        report = confirm(db, content, config, result.previa_hash)
    assert not report.concluido and report.inseridos == report.complementados == 0
    assert db.query(ClienteDB).count() == count
    assert db.query(ClienteDB).filter(ClienteDB.nome == "Fátima Zanetti").one().logradouro is None


@pytest.mark.parametrize("unsafe", ["../fora.xlsx", "/absoluto.xlsx", "C:/fora.xlsx", "clientes\\fora.xlsx"])
def test_zip_caminhos_inseguros_recusados(unsafe):
    content = zip_bytes({unsafe.replace("\\", "/"): b"teste"})
    if "\\" in unsafe:
        content = content.replace(unsafe.replace("\\", "/").encode(), unsafe.encode())
    with pytest.raises(ValueError, match="insegura"):
        service.preparar_backup(content, ImportacaoConfiguracao())


def test_zip_symlink_duplicado_criptografado_e_bomba_recusados():
    link = ZipInfo("clientes/link")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with pytest.raises(ValueError, match="insegura"):
        service.preparar_backup(zip_bytes({link: b"destino"}), ImportacaoConfiguracao())
    output = BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with ZipFile(output, "w") as package:
            package.writestr("repetido", b"1")
            package.writestr("repetido", b"2")
    with pytest.raises(ValueError, match="duplicada"):
        service.preparar_backup(output.getvalue(), ImportacaoConfiguracao())
    encrypted = bytearray(zip_bytes({"entrada": b"dados"}))
    for signature, offset in ((b"PK\x03\x04", 6), (b"PK\x01\x02", 8)):
        index = encrypted.index(signature)
        encrypted[index + offset] |= 1
    with pytest.raises(ValueError, match="criptografada"):
        service.preparar_backup(bytes(encrypted), ImportacaoConfiguracao())
    with pytest.raises(ValueError, match="compressão excessiva"):
        service.preparar_backup(zip_bytes({"bomba": b"0" * (2 * 1024 * 1024)}), ImportacaoConfiguracao())


def test_zip_limites_estrutura_e_cabecalhos():
    config = ImportacaoConfiguracao()
    with pytest.raises(ValueError, match="10 MB"):
        service.preparar_backup(b"x" * (service.MAX_ZIP_BYTES + 1), config)
    with pytest.raises(ValueError, match="incompleto"):
        service.preparar_backup(zip_bytes({"outra.xlsx": b"x"}), config)
    with pytest.raises(ValueError, match="corrompido"):
        service.preparar_backup(b"arquivo nao ZIP", config)
    with pytest.raises(ValueError, match="1.000 entradas"):
        service.preparar_backup(zip_bytes({str(i): b"" for i in range(1001)}), config)
    entries = arquivos()
    entries["clientes/clientes.xlsx"] = xlsx([["Formato desconhecido"], ["Nome"]])
    with pytest.raises(ValueError, match="não reconhecida"):
        service.preparar_backup(zip_bytes(entries), config)
    with patch.object(service, "MAX_ZIP_DESCOMPACTADO", 100):
        with pytest.raises(ValueError, match="descompactados"):
            service.preparar_backup(zip_bytes(arquivos()), config)


def test_zip_auxiliar_separado_recusado(db):
    with pytest.raises(HTTPException) as exc:
        previa_rota(file=upload(zip_bytes(arquivos())), configuracao="{}", db=db, tenant=TENANT,
                    enderecos_file=UploadFile(filename="extra.xlsx", file=BytesIO(b"x")), contatos_file=None)
    assert exc.value.status_code == 422


def test_zip_preview_hash_isolado_por_empresa(db):
    config = ImportacaoConfiguracao()
    content = zip_bytes(arquivos())
    result = preview(db, content, config)
    with pytest.raises(HTTPException) as exc:
        confirmar_rota(file=upload(content), configuracao="{}", previa_hash=result.previa_hash,
                       confirmado=True, db=db, tenant=TenantContext(empresa_id=2),
                       enderecos_file=None, contatos_file=None)
    assert exc.value.status_code == 422
    assert db.query(ClienteDB).count() == 1


def test_zip_pendentes_preservam_originais_e_nao_sao_importados(db):
    entries = arquivos()
    from openpyxl import load_workbook
    workbook = load_workbook(BytesIO(entries["clientes/clientes.xlsx"]))
    workbook.active.cell(4, 4).value = "123.456.789-"
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    entries["clientes/clientes.xlsx"] = output.getvalue()
    content = zip_bytes(entries)
    config = ImportacaoConfiguracao(ignorar_inconsistencias=True)
    result = preview(db, content, config)
    assert result.erros == 1
    pending = next(row for row in result.linhas if row.status == "erro")
    assert pending.dados_originais["cpf"] == "123.456.789-"
    report = confirm(db, content, config, result.previa_hash)
    assert report.concluido and report.inseridos == 2 and report.erros == 1
    assert any(row.dados_originais.get("cpf") == "123.456.789-" for row in report.linhas)
    assert db.query(ClienteDB).filter(ClienteDB.nome == "Novo cliente").count() == 0


def test_zip_alterado_apos_previa_exige_nova_confirmacao(db):
    config = ImportacaoConfiguracao()
    content = zip_bytes(arquivos())
    result = preview(db, content, config)
    changed = arquivos()
    changed["clientes/clientes_contatos.xlsx"] = xlsx([
        ["Código", "Tipo de contato", "Nome", "Contato", "Cargo", "Observação"],
        ["GC-1", "WhatsApp", "Contato novo", "+5511999997777", "", ""],
    ])
    before = db.query(ClienteDB).count()
    with pytest.raises(HTTPException) as exc:
        confirm(db, zip_bytes(changed), config, result.previa_hash)
    assert exc.value.status_code == 422
    assert db.query(ClienteDB).count() == before


def test_zip_fontes_sem_correspondencia_mantidas_no_relatorio(db):
    entries = arquivos()
    entries["clientes/clientes_contatos.xlsx"] = xlsx([
        ["Código", "Tipo de contato", "Nome", "Contato", "Cargo", "Observação"],
        ["GC-AUSENTE", "WhatsApp", "Contato sem vínculo", "+5511999997777", "", ""],
    ])
    config = ImportacaoConfiguracao()
    content = zip_bytes(entries)
    result = preview(db, content, config)
    assert result.fontes["contatos"].sem_vinculo == 1
    assert result.inconsistencias == 1 and result.ocorrencias
    before = db.query(ClienteDB).count()
    report = confirm(db, content, config, result.previa_hash)
    assert not report.concluido and report.ocorrencias == result.ocorrencias
    assert db.query(ClienteDB).count() == before


@pytest.mark.skipif(not os.getenv("GESTAOCLICK_BACKUP_TEST_PATH"), reason="Backup privado não faz parte do repositório")
def test_backup_real_somente_previa_em_memoria(db):
    content = Path(os.environ["GESTAOCLICK_BACKUP_TEST_PATH"]).read_bytes()
    before = db.query(ClienteDB).count()
    result = preview(db, content, ImportacaoConfiguracao())
    assert result.total == 670
    assert (result.inserir, result.ignorados, result.erros) == (259, 7, 384)
    assert sum(row.status == "revisar" for row in result.linhas) == 20
    assert result.fontes["enderecos"].total == result.fontes["enderecos"].vinculados == 541
    assert result.fontes["contatos"].total == result.fontes["contatos"].vinculados == 7
    assert db.query(ClienteDB).count() == before
