"""Importação GestãoClick com mapeamento explícito, isolamento e lote atômico.

Complementa apenas campos vazios após correspondência segura e opção explícita.
O arquivo é reprocessado na confirmação;
nenhuma linha normalizada recebida do navegador é usada para persistência.
"""
import csv
import hashlib
import io
import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.cliente import ClienteDB
from app.schemas.cliente import ClienteCreate
from app.schemas.cliente_importacao import (
    ImportacaoConfiguracao, ImportacaoLinha, ImportacaoPrevia,
    ImportacaoRelatorio, ImportacaoTabela,
)
from app.schemas.consultas_cadastro import cnpj_valido, normalizar_cnpj
from app.tenant.context import TenantContext
from app.tenant.isolation import require_tenant

MAX_BYTES = 5 * 1024 * 1024
MAX_LINHAS = 2000
MAX_COLUNAS = 80
MAX_CELULA = 4000
UFS = set("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split())
logger = logging.getLogger(__name__)


@dataclass
class Tabela:
    colunas: list[str]
    linhas: list[tuple[int, list[str]]]
    abas: list[str]
    aba: str | None = None
    separador: str | None = None

    def resumo(self):
        return dict(colunas=self.colunas, abas=self.abas, aba=self.aba,
                    separador=self.separador, total=len(self.linhas),
                    amostra=[values for _, values in self.linhas[:5]])


def _texto_celula(cell):
    if cell.data_type == "f":
        raise ValueError("A planilha contém fórmulas. Exporte os valores antes de importar.")
    value = cell.value
    if value is None:
        return ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and not value.is_integer():
            return str(value)
        result = str(int(value))
        # Respeita zeros explicitamente formatados, sem fabricar CPF/CNPJ.
        if re.fullmatch(r"0+", cell.number_format or ""):
            result = result.zfill(len(cell.number_format))
        return result
    return str(value)


def _montar_tabela(rows, config, abas, aba=None, separador=None):
    colunas = None
    linhas = []
    for numero, row in enumerate(rows, 1):
        if numero > config.linha_cabecalho + MAX_LINHAS + 100:
            raise ValueError("Arquivo com excesso de linhas vazias. Divida o lote ou remova as linhas vazias.")
        if numero < config.linha_cabecalho:
            continue
        values = [str(value).strip() for value in row]
        if len(values) > MAX_COLUNAS or any(len(value) > MAX_CELULA for value in values):
            raise ValueError(f"Linha {numero}: limite de {MAX_COLUNAS} colunas ou {MAX_CELULA} caracteres por célula excedido.")
        if colunas is None:
            # Não elimina células vazias entre colunas nem confunde cabeçalhos repetidos.
            colunas = [value or f"Coluna {index + 1}" for index, value in enumerate(values)]
            if not colunas or not any(value.strip() for value in row):
                raise ValueError("Cabeçalho vazio. Escolha a linha de cabeçalho correta.")
            continue
        if not any(values):
            continue
        if len(values) > len(colunas) and any(values[len(colunas):]):
            raise ValueError(f"Linha {numero}: há mais valores que colunas no cabeçalho.")
        values = values[:len(colunas)] + [""] * max(0, len(colunas) - len(values))
        linhas.append((numero, values))
        if len(linhas) > MAX_LINHAS:
            raise ValueError(f"Importe no máximo {MAX_LINHAS} clientes por lote.")
    if colunas is None:
        raise ValueError("A linha de cabeçalho não existe no arquivo.")
    if not linhas:
        raise ValueError("Arquivo sem clientes após o cabeçalho.")
    return Tabela(colunas, linhas, abas, aba, separador)


def ler_tabela(content: bytes, filename: str, config: ImportacaoConfiguracao):
    if not content or len(content) > MAX_BYTES:
        raise ValueError("Envie um arquivo não vazio de até 5 MB.")
    extension = Path(filename or "").suffix.lower()
    if extension == ".csv":
        encodings = ("utf-8-sig", "cp1252") if config.encoding == "auto" else (config.encoding,)
        decoded = None
        for encoding in encodings:
            try:
                decoded = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if decoded is None or "\x00" in decoded:
            raise ValueError("CSV com codificação inválida. Selecione UTF-8 ou Windows-1252.")
        separator = config.separador
        if separator == "auto":
            try:
                separator = csv.Sniffer().sniff(decoded[:16384], delimiters=";,\t|").delimiter
            except csv.Error:
                separator = ";"
        try:
            return _montar_tabela(csv.reader(io.StringIO(decoded, newline=""), delimiter=separator, strict=True),
                                  config, [], separador=separator)
        except csv.Error as exc:
            raise ValueError("CSV inválido. Confira separador e aspas do arquivo.") from exc
    if extension != ".xlsx":
        raise ValueError("Formato não suportado. Envie CSV ou XLSX; converta arquivos XLS antes de importar.")
    try:
        from openpyxl import load_workbook
        with ZipFile(io.BytesIO(content)) as package:
            entries = package.infolist()
            if len(entries) > 1000 or sum(entry.file_size for entry in entries) > 40 * 1024 * 1024:
                raise ValueError("Planilha excede o limite de conteúdo descompactado.")
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=False, keep_links=False)
        try:
            names = workbook.sheetnames
            selected = config.aba or names[0]
            if selected not in names:
                raise ValueError("A aba selecionada não existe na planilha.")
            sheet = workbook[selected]
            if sheet.max_column and sheet.max_column > MAX_COLUNAS:
                raise ValueError(f"Planilha excede o limite de {MAX_COLUNAS} colunas.")
            rows = ([_texto_celula(cell) for cell in row] for row in sheet.iter_rows())
            return _montar_tabela(rows, config, names, aba=selected)
        finally:
            workbook.close()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("XLSX inválido ou corrompido. Exporte a planilha novamente.") from exc


def inspecionar(content, filename, config, tenant):
    require_tenant(tenant)
    return ImportacaoTabela(**ler_tabela(content, filename, config).resumo())


def _chave_nome(value):
    plain = unicodedata.normalize("NFKD", value or "")
    return " ".join("".join(char for char in plain if not unicodedata.combining(char)).casefold().split())


def _cpf_valido(value):
    if not re.fullmatch(r"\d{11}", value) or len(set(value)) == 1:
        return False
    for tamanho in (9, 10):
        result = (sum(int(digit) * (tamanho + 1 - index) for index, digit in enumerate(value[:tamanho])) * 10) % 11
        if (0 if result == 10 else result) != int(value[tamanho]):
            return False
    return True


def _normalizar_dados(values, config, dados_preparados=None):
    dados = dict(dados_preparados) if dados_preparados is not None else {
        field: " ".join(values[index].split()) or None for field, index in config.mapeamento.items()}
    erros, avisos = [], []
    documents = [value for value in (dados.get("documento"), dados.pop("cpf", None), dados.pop("cnpj", None)) if value]
    if len({normalizar_cnpj(value) for value in documents}) > 1:
        erros.append("CPF e CNPJ/documento conflitantes na mesma linha. Revise as colunas de documento.")
    if documents:
        dados["documento"] = documents[0]
    nome = dados.get("nome") or ""
    if len(nome) < 2 or not any(char.isalpha() for char in nome):
        erros.append("Nome obrigatório, com pelo menos dois caracteres e uma letra.")
    limits = {"nome": 255, "email": 255, "logradouro": 255, "complemento": 255,
              "bairro": 100, "cidade": 150, "numero": 30, "site": 255,
              "vendedor_responsavel": 255, "observacoes": 4000}
    for campo, value in dados.items():
        if value and (len(value) > limits.get(campo, 100) or any(ord(char) < 32 for char in value)):
            erros.append(f"Campo {campo} contém caracteres inválidos ou excede o tamanho permitido.")
    document = dados.get("documento")
    if document:
        normalized = normalizar_cnpj(document)
        if not (_cpf_valido(normalized) or cnpj_valido(normalized)):
            erros.append("CPF/CNPJ inválido. Confira dígitos verificadores e zeros à esquerda; use texto no XLSX.")
        dados["documento"] = normalized or document
    else:
        avisos.append("Sem CPF/CNPJ: duplicidade será conferida por nome e e-mail ou telefone.")
    raw_tipo = _chave_nome(dados.get("tipo")).replace(" ", "")
    tipos = {"pf": "Física", "fisica": "Física", "pessoafisica": "Física",
             "pj": "Jurídica", "juridica": "Jurídica", "pessoajuridica": "Jurídica"}
    if raw_tipo and raw_tipo not in tipos:
        erros.append("Tipo inválido: use Física/PF ou Jurídica/PJ, ou desmapeie a coluna.")
    inferred = "Jurídica" if len(dados.get("documento") or "") == 14 else "Física"
    dados["tipo"] = tipos.get(raw_tipo) or (inferred if document else config.tipo_padrao)
    if document and raw_tipo in tipos and dados["tipo"] != inferred:
        erros.append("Tipo de cliente incompatível com CPF/CNPJ.")
    email = dados.get("email")
    if email:
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            erros.append("E-mail inválido; informe um único endereço.")
    for field in ("telefone_comercial", "telefone_celular"):
        phone = dados.get(field)
        if phone:
            digits = re.sub(r"\D", "", phone)
            if not re.fullmatch(r"[0-9+().\-\s]+", phone) or not 10 <= len(digits) <= 15:
                erros.append(f"{field}: informe um telefone com DDD e 10 a 15 dígitos.")
            else:
                dados[field] = ("+" if phone.startswith("+") else "") + digits
    if dados.get("cep"):
        cep = re.sub(r"[.\-\s]", "", dados["cep"])
        if not re.fullmatch(r"\d{8}", cep):
            erros.append("CEP inválido: informe oito dígitos.")
        dados["cep"] = cep
    if dados.get("estado"):
        dados["estado"] = dados["estado"].upper()
        if dados["estado"] not in UFS:
            erros.append("UF inválida: informe a sigla do estado brasileiro.")
    address_fields = ("cep", "logradouro", "numero", "complemento", "bairro", "cidade", "estado")
    if any(dados.get(field) for field in address_fields) and not all(dados.get(field) for field in ("logradouro", "cidade", "estado")):
        avisos.append("Endereço incompleto: revise logradouro, cidade e UF antes de confirmar.")
    if not email and not any(dados.get(field) for field in ("telefone_comercial", "telefone_celular")):
        avisos.append("Cliente sem e-mail nem telefone.")
    return dados, erros, avisos


def _chaves_contato(dados):
    name = _chave_nome(dados.get("nome"))
    keys = set()
    if name and dados.get("email"):
        keys.add(("email", name, dados["email"].strip().casefold()))
    for field in ("telefone_comercial", "telefone_celular"):
        phone = re.sub(r"\D", "", dados.get(field) or "")
        if name and phone:
            # Os números brasileiros com/sem +55 representam o mesmo contato.
            if len(phone) in (12, 13) and phone.startswith("55"):
                phone = phone[2:]
            keys.add(("telefone", name, phone))
    return keys


ENDERECO_CAMPOS = {"cep", "logradouro", "numero", "complemento", "bairro", "cidade", "estado"}
CONTATO_CAMPOS = {"email", "telefone_comercial", "telefone_celular", "contato", "nome_contato", "tipo_contato", "cargo", "observacao_contato"}
CLIENTE_CAMPOS = set(ClienteCreate.model_fields) - {"parceiro_id", "representante_id", "limite_credito", "permitir_exceder", "situacao"}


def _vazio(value):
    return value is None or (isinstance(value, str) and not value.strip())


def _mapear(values, mapping):
    return {field: " ".join(values[index].split()) or None for field, index in mapping.items()}


def _validar_colunas(tabela, config, allowed):
    if set(config.mapeamento) - allowed:
        raise ValueError("Mapeamento contém campo incompatível com esta fonte.")
    indices = list(config.mapeamento.values()) + ([] if config.codigo_cliente is None else [config.codigo_cliente])
    if any(index >= len(tabela.colunas) for index in indices):
        raise ValueError("Mapeamento aponta para coluna inexistente.")
    if config.codigo_cliente is not None and config.codigo_cliente in config.mapeamento.values():
        raise ValueError("A coluna de código do cliente não pode ser usada como outro campo.")


def _fontes_auxiliares(principal, config, enderecos, contatos):
    fontes, groups, ocorrencias = {}, {}, []
    codigos = {values[config.codigo_cliente].strip() for _, values in principal.linhas} if config.codigo_cliente is not None else set()
    for nome, arquivo, fonte_config, allowed in (
        ("enderecos", enderecos, config.enderecos, ENDERECO_CAMPOS | {"tipo_endereco"}),
        ("contatos", contatos, config.contatos, CONTATO_CAMPOS),
    ):
        if arquivo is None and fonte_config is None:
            continue
        if arquivo is None or fonte_config is None or fonte_config.codigo_cliente is None or config.codigo_cliente is None:
            raise ValueError(f"Configure o código do cliente no arquivo principal e na fonte {nome}, e envie os dois arquivos.")
        tabela = ler_tabela(arquivo[0], arquivo[1], fonte_config)
        _validar_colunas(tabela, fonte_config, allowed)
        fontes[nome] = ImportacaoTabela(**tabela.resumo())
        groups[nome] = {}
        for numero, values in tabela.linhas:
            codigo = values[fonte_config.codigo_cliente].strip()
            if not codigo or codigo not in codigos:
                fontes[nome].sem_vinculo += 1
                ocorrencias.append(f"{nome}, linha {numero}: código de cliente ausente ou sem correspondência no arquivo principal.")
                continue
            fontes[nome].vinculados += 1
            groups[nome].setdefault(codigo, []).append((numero, _mapear(values, fonte_config.mapeamento)))
    return fontes, groups, ocorrencias


def _agregar_auxiliares(dados, codigo, groups):
    dados, conflitos, avisos = dict(dados), [], []
    enderecos = groups.get("enderecos", {}).get(codigo, [])
    diferentes = {tuple((campo, values.get(campo)) for campo in sorted(ENDERECO_CAMPOS)) for _, values in enderecos}
    if len(diferentes) > 1:
        conflitos.append("Mais de um endereço distinto para o mesmo código. Escolha o endereço principal no arquivo antes de importar.")
    elif enderecos:
        for campo, value in enderecos[0][1].items():
            if campo not in ENDERECO_CAMPOS or _vazio(value):
                continue
            if _vazio(dados.get(campo)):
                dados[campo] = value
            elif _chave_nome(dados[campo]) != _chave_nome(value):
                conflitos.append(f"{campo}: valor do arquivo de endereços diverge do arquivo principal.")
    notas = []
    for numero, contato in groups.get("contatos", {}).get(codigo, []):
        values = {field: contato.get(field) for field in ("email", "telefone_comercial", "telefone_celular")}
        generic = contato.get("contato")
        if generic:
            if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", generic):
                values["email"] = generic
            elif re.fullmatch(r"[0-9+().\-\s]+", generic) and 10 <= len(re.sub(r"\D", "", generic)) <= 15:
                tipo = _chave_nome(contato.get("tipo_contato"))
                field = "telefone_celular" if any(word in tipo for word in ("whats", "celular")) else "telefone_comercial"
                values[field] = generic
            else:
                conflitos.append(f"Contatos, linha {numero}: contato não é e-mail ou telefone válido.")
        for campo, value in values.items():
            if _vazio(value):
                continue
            if _vazio(dados.get(campo)):
                dados[campo] = value
            elif not _campo_igual(campo, dados[campo], value):
                avisos.append(f"Contato adicional, linha {numero}: {campo} principal foi preservado; veja observações.")
        detail = "; ".join(f"{label}: {contato[key]}" for key, label in (
            ("nome_contato", "Nome"), ("tipo_contato", "Tipo"), ("contato", "Contato"),
            ("cargo", "Cargo"), ("observacao_contato", "Observação"),
        ) if contato.get(key))
        if detail:
            notas.append("Contato adicional — " + detail)
    if notas:
        dados["observacoes"] = " | ".join(([dados["observacoes"]] if dados.get("observacoes") else []) + notas)
    return dados, conflitos, avisos


def _campo_igual(campo, first, second):
    if campo == "documento":
        return normalizar_cnpj(first or "") == normalizar_cnpj(second or "")
    if campo.startswith("telefone"):
        def phone(value):
            digits = re.sub(r"\D", "", value or "")
            return digits[2:] if len(digits) in (12, 13) and digits.startswith("55") else digits
        return phone(first) == phone(second)
    return _chave_nome(first) == _chave_nome(second)


def _documento(dados):
    return normalizar_cnpj(dados.get("documento") or "")


def _documentos_compativeis(first, second):
    first_doc, second_doc = _documento(first), _documento(second)
    return not first_doc or not second_doc or first_doc == second_doc


def _match_forte(first, second):
    if _documento(first) and _documento(first) == _documento(second):
        return True
    return _documentos_compativeis(first, second) and bool(_chaves_contato(first) & _chaves_contato(second))


def _snapshot(cliente):
    return {"id": cliente.id, "empresa_id": cliente.empresa_id,
            **{field: getattr(cliente, field) for field in sorted(CLIENTE_CAMPOS)}}


def _previa_hash(content, filename, config, empresa_id, enderecos=None, contatos=None, plano=None):
    metadata = {"config": config.model_dump(), "empresa_id": empresa_id,
                "extensao": Path(filename or "").suffix.lower(), "plano": plano}
    digest = hashlib.sha256(json.dumps(metadata, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    for arquivo in ((content, filename), enderecos, contatos):
        if arquivo is None:
            digest.update(b"\0ausente")
        else:
            digest.update(Path(arquivo[1] or "").suffix.lower().encode("utf-8") + b"\0" + arquivo[0])
    return digest.hexdigest()


def previa(db: Session, content, filename, config, tenant: TenantContext, enderecos=None, contatos=None, bloquear=False):
    empresa_id = require_tenant(tenant)
    tabela = ler_tabela(content, filename, config)
    if "nome" not in config.mapeamento:
        raise ValueError("Mapeie a coluna Nome antes de gerar a prévia.")
    _validar_colunas(tabela, config, CLIENTE_CAMPOS | {"cpf", "cnpj"})
    fontes, groups, ocorrencias = _fontes_auxiliares(tabela, config, enderecos, contatos)
    fontes["clientes"] = ImportacaoTabela(**tabela.resumo())
    # get_all() legado esconde falhas retornando []; aqui uma falha bloqueia a importação.
    query = db.query(ClienteDB).filter(ClienteDB.empresa_id == empresa_id).populate_existing()
    if bloquear:
        query = query.with_for_update()
    existentes = query.all()
    registros = [(cliente, _snapshot(cliente)) for cliente in existentes]
    preparados = []
    for numero, values in tabela.linhas:
        codigo = values[config.codigo_cliente].strip() if config.codigo_cliente is not None else None
        dados, conflitos, avisos_aux = _agregar_auxiliares(_mapear(values, config.mapeamento), codigo, groups)
        dados, erros, avisos = _normalizar_dados(values, config, dados)
        if groups and not codigo:
            conflitos.append("Código do cliente ausente: não é possível relacionar os arquivos auxiliares.")
        preparados.append((numero, codigo, dados, erros, conflitos, avisos + avisos_aux))
    linhas, vistos, snapshots = [], [], []
    for index, (numero, codigo, dados, erros, conflitos, avisos) in enumerate(preparados):
        conflitos = list(conflitos)
        nome = _chave_nome(dados.get("nome"))
        outros_mesmo_nome = [other[2] for other_index, other in enumerate(preparados)
                             if other_index != index and _chave_nome(other[2].get("nome")) == nome]
        if any(not _match_forte(dados, other) for other in outros_mesmo_nome):
            conflitos.append("Nome exato repetido no arquivo sem documento ou contato forte compatível. Revise os registros separadamente.")
        if codigo and sum(other[1] == codigo for other in preparados) > 1:
            conflitos.append("Código do cliente repetido no arquivo principal.")
        por_documento = [(cliente, snap) for cliente, snap in registros if _documento(dados) and _documento(dados) == _documento(snap)]
        por_contato = [(cliente, snap) for cliente, snap in registros if bool(_chaves_contato(dados) & _chaves_contato(snap))]
        matches = por_documento or [(cliente, snap) for cliente, snap in por_contato if _documentos_compativeis(dados, snap)]
        mesmo_nome = [snap for _, snap in registros if _chave_nome(snap["nome"]) == nome]
        if len(matches) > 1:
            conflitos.append("Mais de um cliente existente corresponde ao documento/contato. Não é seguro escolher um ID automaticamente.")
        if not por_documento and any(not _documentos_compativeis(dados, snap) for _, snap in por_contato):
            conflitos.append("Nome e contato coincidem com cliente de documento diferente. Documentos conflitantes exigem revisão.")
        if not matches and mesmo_nome:
            conflitos.append("Já existe cliente com este nome exato, mas sem correspondência segura de documento ou contato. Nome sozinho não autoriza vinculação.")
        target = matches[0] if len(matches) == 1 and not conflitos else None
        patch_values = {}
        preserved = []
        if target:
            cliente, snap = target
            for campo, value in dados.items():
                if campo not in CLIENTE_CAMPOS or _vazio(value):
                    continue
                current = snap[campo]
                if _vazio(current):
                    patch_values[campo] = value
                elif not _campo_igual(campo, current, value):
                    preserved.append(f"{campo}: valor já preenchido no ERP será preservado.")
            snapshots.append(snap)
        if erros:
            status, motivos = "erro", erros
        elif conflitos:
            status, motivos = "revisar", conflitos
        elif target:
            status = "complementar" if config.complementar_vazios and patch_values else "ignorado"
            motivos = ["Correspondência única por documento ou nome exato e contato forte."]
            if patch_values and not config.complementar_vazios:
                avisos.append("Há campos vazios que poderiam ser complementados. Habilite a opção e gere nova prévia para revisar.")
        elif any(_match_forte(dados, previous) for previous in vistos):
            status, motivos = "ignorado", ["Duplicado no arquivo por documento ou nome exato e contato forte compatível."]
        else:
            status, motivos = "inserir", []
            vistos.append(dados)
        linhas.append(ImportacaoLinha(linha=numero, codigo_cliente=codigo, dados=dados, status=status,
            motivos=motivos, avisos=avisos, conflitos=conflitos + preserved,
            cliente_existente_id=target[0].id if target else None,
            campos_complementar=patch_values if target and config.complementar_vazios else {}))
    por_id = {}
    for row in linhas:
        if row.status == "complementar":
            por_id.setdefault(row.cliente_existente_id, []).append(row)
    for candidates in por_id.values():
        if len(candidates) > 1:
            for row in candidates:
                row.status = "revisar"
                row.motivos = ["Mais de uma linha propõe complementar o mesmo ID. Consolide os dados e gere nova prévia."]
                row.conflitos.extend(row.motivos)
    # O hash inclui a decisão e o snapshot dos candidatos; alteração concorrente exige outra prévia.
    plano = {"linhas": [{"linha": row.linha, "status": row.status, "id": row.cliente_existente_id,
                         "campos": row.campos_complementar} for row in linhas], "candidatos": snapshots,
             "ocorrencias": ocorrencias}
    return ImportacaoPrevia(**tabela.resumo(),
        previa_hash=_previa_hash(content, filename, config, empresa_id, enderecos, contatos, plano),
        inserir=sum(row.status == "inserir" for row in linhas),
        complementar=sum(row.status == "complementar" for row in linhas),
        ignorados=sum(row.status == "ignorado" for row in linhas), erros=sum(row.status == "erro" for row in linhas),
        inconsistencias=sum(row.status in ("erro", "revisar") for row in linhas) + len(ocorrencias),
        linhas=linhas, fontes=fontes, ocorrencias=ocorrencias)


def _relatorio(preview, concluido, mensagem):
    linhas = preview.linhas
    return ImportacaoRelatorio(concluido=concluido, mensagem=mensagem, total=len(linhas),
        inseridos=sum(row.status == "inserido" for row in linhas), complementados=sum(row.status == "complementado" for row in linhas),
        ignorados=sum(row.status == "ignorado" for row in linhas), erros=sum(row.status == "erro" for row in linhas),
        nao_importados=sum(row.status in ("inserir", "complementar", "nao_importado", "revisar") for row in linhas),
        inconsistencias=preview.inconsistencias, linhas=linhas, fontes=preview.fontes, ocorrencias=preview.ocorrencias)


def confirmar(db: Session, content, filename, config, tenant, previa_hash, confirmado, enderecos=None, contatos=None):
    empresa_id = require_tenant(tenant)
    if not confirmado:
        raise ValueError("Confirmação inválida ou prévia desatualizada. Gere a prévia novamente.")
    try:
        if db.get_bind().dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(:namespace, :empresa_id)"),
                       {"namespace": 1398031169, "empresa_id": empresa_id})
        preview = previa(db, content, filename, config, tenant, enderecos, contatos, bloquear=True)
        if previa_hash != preview.previa_hash:
            raise ValueError("Confirmação inválida ou prévia desatualizada: arquivo, configuração ou cadastros candidatos mudaram. Gere a prévia novamente.")
        if preview.inconsistencias and not config.ignorar_inconsistencias:
            db.rollback()
            for row in preview.linhas:
                if row.status in ("inserir", "complementar"):
                    row.status = "nao_importado"
            return _relatorio(preview, False, "Corrija as inconsistências ou autorize explicitamente ignorá-las em uma nova prévia. Nenhum cliente foi alterado.")
        candidatos = [row for row in preview.linhas if row.status in ("inserir", "complementar")]
        try:
            for row in candidatos:
                if row.status == "inserir":
                    data = ClienteCreate(**row.dados)
                    db.add(ClienteDB(**data.model_dump(), empresa_id=empresa_id))
                else:
                    cliente = db.query(ClienteDB).filter(ClienteDB.id == row.cliente_existente_id,
                        ClienteDB.empresa_id == empresa_id).with_for_update().one()
                    for campo, value in row.campos_complementar.items():
                        if campo not in CLIENTE_CAMPOS or not _vazio(getattr(cliente, campo)):
                            raise ValueError("Campo de complementação mudou; gere outra prévia.")
                        setattr(cliente, campo, value)
                db.flush()
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.warning("Lote de clientes revertido; tipo de falha: %s", type(exc).__name__)
            for row in candidatos:
                row.status = "erro"
                row.motivos = ["Lote cancelado por falha na gravação. Todas as inserções e complementações foram revertidas."]
            return _relatorio(preview, False, "Falha ao gravar o lote. A transação inteira foi revertida; nenhum cadastro foi alterado.")
        for row in candidatos:
            row.status = "inserido" if row.status == "inserir" else "complementado"
        mensagem = "Importação concluída. IDs e campos já preenchidos foram preservados; duplicados foram ignorados."
        if preview.inconsistencias:
            mensagem += " Inconsistências foram excluídas conforme autorização explícita e permanecem no relatório."
        return _relatorio(preview, True, mensagem)
    except Exception:
        db.rollback()
        raise
