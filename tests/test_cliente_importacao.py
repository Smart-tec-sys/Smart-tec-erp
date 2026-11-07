"""Importação de clientes: exclusivamente SQLite em memória e dados sintéticos."""
from io import BytesIO
from unittest.mock import patch

import pytest
from openpyxl import Workbook
from sqlalchemy.exc import SQLAlchemyError

from test_orcamento_cortina_pdf_local import db  # noqa: F401
from app.models.cliente import ClienteDB
from app.models.orcamento import OrcamentoDB
from app.schemas.cliente_importacao import ImportacaoConfiguracao
from app.services import cliente_importacao_service as service
from app.tenant.context import TenantContext


TENANT = TenantContext(empresa_id=1)
CONFIG = ImportacaoConfiguracao(
    mapeamento={"nome": 0, "documento": 1, "email": 2, "telefone_celular": 3},
    separador=";",
)
CONTENT = (
    "Nome;Documento;Email;Telefone\n"
    "Novo;529.982.247-25;novo@example.test;11999998888\n"
    "Duplicado;52998224725;outro@example.test;11999997777\n"
    "Contato;;contato@example.test;11999996666\n"
    "Contato;;CONTATO@example.test;+5511999996666\n"
).encode()


def test_duplicidades_no_lote_reimportacao_e_isolamento(db):
    db.add(ClienteDB(empresa_id=2, tipo="Física", nome="Outro tenant",
                    documento="52998224725"))
    db.commit()
    preview = service.previa(db, CONTENT, "clientes.csv", CONFIG, TENANT)
    assert (preview.inserir, preview.ignorados, preview.erros) == (2, 2, 0)
    report = service.confirmar(db, CONTENT, "clientes.csv", CONFIG, TENANT,
                               preview.previa_hash, True)
    assert report.concluido and report.inseridos == 2
    assert db.query(ClienteDB).filter(ClienteDB.empresa_id == 2).count() == 1
    existing = db.query(ClienteDB).filter(ClienteDB.empresa_id == 2).one()
    assert existing.nome == "Outro tenant"
    repeated = service.previa(db, CONTENT, "clientes.csv", CONFIG, TENANT)
    assert (repeated.inserir, repeated.ignorados, repeated.erros) == (0, 4, 0)


@pytest.mark.parametrize("change", ["empresa", "arquivo", "configuracao", "confirmacao"])
def test_confirmacao_exige_previa_do_mesmo_arquivo_configuracao_e_empresa(db, change):
    preview = service.previa(db, CONTENT, "clientes.csv", CONFIG, TENANT)
    tenant = TenantContext(empresa_id=2) if change == "empresa" else TENANT
    content = CONTENT + b"Mais;;mais@example.test;11999995555\n" if change == "arquivo" else CONTENT
    config = CONFIG.model_copy(update={"tipo_padrao": "Jurídica"}) if change == "configuracao" else CONFIG
    before = db.query(ClienteDB).count()
    with pytest.raises(ValueError, match="Confirmação inválida"):
        service.confirmar(db, content, "clientes.csv", config, tenant,
                          preview.previa_hash, change != "confirmacao")
    assert db.query(ClienteDB).count() == before


def test_dados_invalidos_impedem_gravacao_do_lote_inteiro(db):
    content = CONTENT + b"Erro;123;email-invalido;1\n"
    preview = service.previa(db, content, "clientes.csv", CONFIG, TENANT)
    assert preview.erros == 1
    before = db.query(ClienteDB).count()
    report = service.confirmar(db, content, "clientes.csv", CONFIG, TENANT,
                               preview.previa_hash, True)
    assert not report.concluido and report.inseridos == 0
    assert report.nao_importados == 2
    assert db.query(ClienteDB).count() == before


def test_falha_de_commit_reverte_todas_as_insercoes(db):
    preview = service.previa(db, CONTENT, "clientes.csv", CONFIG, TENANT)
    before = db.query(ClienteDB).count()
    with patch.object(db, "commit", side_effect=SQLAlchemyError("falha sintética")):
        report = service.confirmar(db, CONTENT, "clientes.csv", CONFIG, TENANT,
                                   preview.previa_hash, True)
    assert not report.concluido and report.inseridos == 0
    assert db.query(ClienteDB).count() == before


def test_csv_com_separador_tabulacao_real(db):
    config = CONFIG.model_copy(update={"separador": "\t"})
    content = CONTENT.replace(b";", b"\t")
    preview = service.previa(db, content, "clientes.csv", config, TENANT)
    assert preview.separador == "\t"
    assert (preview.inserir, preview.ignorados, preview.erros) == (2, 2, 0)


def planilha(documento):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Clientes"
    sheet.append(["Nome", "Documento", "Email", "Telefone"])
    sheet.append(["Cliente XLSX", documento, "xlsx@example.test", "11999998888"])
    sheet.cell(2, 2).number_format = "00000000000"
    stream = BytesIO()
    workbook.save(stream)
    workbook.close()
    return stream.getvalue()


def test_xlsx_documento_numerico_e_aba_selecionada(db):
    config = CONFIG.model_copy(update={"aba": "Clientes"})
    content = planilha(52998224725)
    preview = service.previa(db, content, "clientes.xlsx", config, TENANT)
    assert preview.abas == ["Clientes"] and preview.aba == "Clientes"
    assert (preview.inserir, preview.erros) == (1, 0)
    assert preview.linhas[0].dados["documento"] == "52998224725"
    report = service.confirmar(db, content, "clientes.xlsx", config, TENANT,
                               preview.previa_hash, True)
    assert report.concluido and report.inseridos == 1


def test_xlsx_com_formula_e_recusado_sem_inserir(db):
    before = db.query(ClienteDB).count()
    with pytest.raises(ValueError, match="fórmulas"):
        service.previa(db, planilha("=1+1"), "clientes.xlsx", CONFIG, TENANT)
    assert db.query(ClienteDB).count() == before


def fonte(rows, formato):
    if formato == "csv":
        import csv
        from io import StringIO
        stream = StringIO()
        csv.writer(stream, delimiter=";").writerows(rows)
        return stream.getvalue().encode(), "fonte.csv"
    workbook = Workbook()
    for row in rows:
        workbook.active.append(row)
    stream = BytesIO()
    workbook.save(stream)
    workbook.close()
    return stream.getvalue(), "fonte.xlsx"


def configuracao_relacionada(**updates):
    return ImportacaoConfiguracao(
        codigo_cliente=0,
        mapeamento={"nome": 1, "documento": 2, "email": 3},
        enderecos={"codigo_cliente": 0, "separador": ";",
                   "mapeamento": {"logradouro": 1, "cidade": 2, "estado": 3, "cep": 4}},
        contatos={"codigo_cliente": 0, "separador": ";",
                  "mapeamento": {"nome_contato": 1, "tipo_contato": 2, "contato": 3}},
        separador=";", **updates,
    )


@pytest.mark.parametrize("formato", ["csv", "xlsx"])
@pytest.mark.parametrize("nome", ["Fátima Zanetti", "Gillian"])
def test_complementar_preserva_id_orcamento_e_campos_preenchidos(db, formato, nome):
    cliente = ClienteDB(empresa_id=1, nome=nome, tipo="Física", documento="52998224725",
                        email="Original@Example.test", logradouro="Rua Original")
    db.add(cliente)
    db.flush()
    oid = cliente.id
    orcamento = OrcamentoDB(empresa_id=1, numero="PROTECAO", cliente_id=oid, total=321, total_final=321)
    db.add(orcamento)
    db.commit()
    principal = fonte([["Código", "Nome", "Documento", "Email"],
                       ["GC-007", nome, "529.982.247-25", "Outro@Example.test"]], formato)
    enderecos = fonte([["Código", "Rua", "Cidade", "UF", "CEP"],
                      ["GC-007", "Rua Nova", "São Paulo", "SP", "01001000"]], formato)
    contatos = fonte([["Código", "Nome", "Tipo", "Contato"],
                     ["GC-007", "Contato adicional", "WhatsApp", "+5511999998888"]], formato)
    config = configuracao_relacionada(complementar_vazios=True)
    preview = service.previa(db, *principal, config, TENANT, enderecos, contatos)
    assert (preview.inserir, preview.complementar, preview.erros) == (0, 1, 0)
    row = preview.linhas[0]
    assert row.cliente_existente_id == oid
    assert "nome" not in row.campos_complementar and "email" not in row.campos_complementar
    assert "logradouro" not in row.campos_complementar
    assert row.campos_complementar["cidade"] == "São Paulo"
    assert preview.fontes["enderecos"].vinculados == preview.fontes["contatos"].vinculados == 1
    assert db.get(ClienteDB, oid).cidade is None
    report = service.confirmar(db, *principal, config, TENANT, preview.previa_hash, True, enderecos, contatos)
    db.expire_all()
    assert report.concluido and report.complementados == 1
    atual = db.get(ClienteDB, oid)
    assert atual.nome == nome and atual.email == "Original@Example.test" and atual.logradouro == "Rua Original"
    assert atual.cidade == "São Paulo" and atual.telefone_celular == "+5511999998888"
    assert "Contato adicional" in atual.observacoes
    assert db.get(OrcamentoDB, orcamento.id).cliente_id == oid
    assert db.get(OrcamentoDB, orcamento.id).total_final == 321


@pytest.mark.parametrize("nome", ["Fátima Zanetti", "Fátima Zaneti"])
def test_nome_sem_correspondencia_forte_nao_substitui_fatima(db, nome):
    cliente = ClienteDB(empresa_id=1, nome="Fátima Zanetti", tipo="Física")
    db.add(cliente)
    db.flush()
    db.add(OrcamentoDB(empresa_id=1, numero="FATIMA", cliente_id=cliente.id))
    db.commit()
    content = fonte([["Nome", "Documento", "Email", "Telefone"],
                     [nome, "", "nova@example.test", "11999998888"]], "csv")
    preview = service.previa(db, *content, CONFIG.model_copy(update={"complementar_vazios": True}), TENANT)
    assert preview.complementar == 0
    assert preview.linhas[0].cliente_existente_id is None
    assert preview.linhas[0].status == ("revisar" if nome == cliente.nome else "inserir")
    assert cliente.email is None
    assert db.query(OrcamentoDB).one().cliente_id == cliente.id


def test_auxiliares_sem_vinculo_e_enderecos_conflitantes_bloqueiam_lote(db):
    config = configuracao_relacionada()
    principal = fonte([["Código", "Nome", "Documento", "Email"],
                       ["GC-1", "Novo cliente", "52998224725", "novo@example.test"]], "csv")
    enderecos = fonte([["Código", "Rua", "Cidade", "UF", "CEP"],
                      ["GC-1", "Rua A", "São Paulo", "SP", "01001000"],
                      ["GC-1", "Rua B", "São Paulo", "SP", "01001000"],
                      ["GC-999", "Rua C", "São Paulo", "SP", "01001000"]], "csv")
    contatos = fonte([["Código", "Nome", "Tipo", "Contato"],
                     ["GC-1", "Contato", "Email", "Contato@Example.test"]], "csv")
    preview = service.previa(db, *principal, config, TENANT, enderecos, contatos)
    assert preview.linhas[0].status == "revisar"
    assert preview.fontes["enderecos"].vinculados == 2
    assert preview.fontes["enderecos"].sem_vinculo == 1
    assert len(preview.ocorrencias) == 1
    before = db.query(ClienteDB).count()
    result = service.confirmar(db, *principal, config, TENANT, preview.previa_hash, True, enderecos, contatos)
    assert not result.concluido and db.query(ClienteDB).count() == before


def test_rollback_reverte_complementacao_e_insercao_sem_perder_vinculo(db):
    db.add(ClienteDB(empresa_id=1, nome="Fátima Zanetti", tipo="Física", documento="52998224725"))
    db.commit()
    cliente = db.query(ClienteDB).filter(ClienteDB.nome == "Fátima Zanetti").one()
    db.add(OrcamentoDB(empresa_id=1, numero="ROLLBACK", cliente_id=cliente.id))
    db.commit()
    content = fonte([["Nome", "Documento", "Email", "Telefone"],
                     ["Fátima Zanetti", "52998224725", "Fatima@Example.test", ""],
                     ["Novo cliente", "", "novo@example.test", ""]], "csv")
    config = CONFIG.model_copy(update={"complementar_vazios": True})
    preview = service.previa(db, *content, config, TENANT)
    assert (preview.complementar, preview.inserir) == (1, 1)
    before = db.query(ClienteDB).count()
    with patch.object(db, "commit", side_effect=SQLAlchemyError("falha sintética")):
        report = service.confirmar(db, *content, config, TENANT, preview.previa_hash, True)
    db.expire_all()
    assert not report.concluido and report.complementados == report.inseridos == 0
    assert db.query(ClienteDB).count() == before
    assert db.get(ClienteDB, cliente.id).email is None
    assert db.query(OrcamentoDB).one().cliente_id == cliente.id


def test_multiplas_complementacoes_do_mesmo_id_exigem_revisao(db):
    db.add(ClienteDB(empresa_id=1, nome="Fátima Zanetti", tipo="Física", documento="52998224725"))
    db.commit()
    content = fonte([["Nome", "Documento", "Email", "Telefone"],
                     ["Fátima Zanetti", "52998224725", "Primeiro@Example.test", ""],
                     ["Fátima Zanetti", "52998224725", "Segundo@Example.test", ""]], "csv")
    preview = service.previa(db, *content, CONFIG.model_copy(update={"complementar_vazios": True}), TENANT)
    assert preview.complementar == 0 and preview.inconsistencias == 2
    assert all(row.status == "revisar" for row in preview.linhas)


def test_snapshot_impede_complementar_cadastro_alterado_apos_previa(db):
    db.add(ClienteDB(empresa_id=1, nome="Fátima Zanetti", tipo="Física", documento="52998224725"))
    db.commit()
    cliente = db.query(ClienteDB).filter(ClienteDB.nome == "Fátima Zanetti").one()
    content = fonte([["Nome", "Documento", "Email", "Telefone"],
                     ["Fátima Zanetti", "52998224725", "Fatima@Example.test", ""]], "csv")
    config = CONFIG.model_copy(update={"complementar_vazios": True})
    preview = service.previa(db, *content, config, TENANT)
    cliente.email = "Preenchido@Example.test"
    db.commit()
    with pytest.raises(ValueError, match="cadastros candidatos mudaram"):
        service.confirmar(db, *content, config, TENANT, preview.previa_hash, True)
    assert db.get(ClienteDB, cliente.id).email == "Preenchido@Example.test"


def test_complementacao_nunca_consulta_ou_altera_outro_tenant(db):
    cliente = ClienteDB(empresa_id=2, nome="Fátima Zanetti", tipo="Física", documento="52998224725")
    db.add(cliente)
    db.commit()
    content = fonte([["Nome", "Documento", "Email", "Telefone"],
                     ["Fátima Zanetti", "52998224725", "Fatima@Example.test", ""]], "csv")
    config = CONFIG.model_copy(update={"complementar_vazios": True})
    preview = service.previa(db, *content, config, TENANT)
    assert (preview.inserir, preview.complementar) == (1, 0)
    assert preview.linhas[0].cliente_existente_id is None
    report = service.confirmar(db, *content, config, TENANT, preview.previa_hash, True)
    assert report.concluido and report.inseridos == 1
    assert db.get(ClienteDB, cliente.id).email is None
    assert db.query(ClienteDB).filter(ClienteDB.empresa_id == 1, ClienteDB.documento == "52998224725").one().id != cliente.id
