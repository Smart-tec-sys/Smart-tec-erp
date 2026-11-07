"""Contrato da importação configurável; nenhum formato de exportação é presumido."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator


CAMPOS_IMPORTACAO = {
    "nome", "tipo", "documento", "email", "telefone_comercial", "telefone_celular",
    "site", "vendedor_responsavel", "cep", "logradouro", "numero", "complemento",
    "bairro", "cidade", "estado", "observacoes", "cpf", "cnpj", "tipo_endereco",
    "contato", "nome_contato", "tipo_contato", "cargo", "observacao_contato",
}


class ImportacaoFonteConfiguracao(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Índices de coluna começam em zero. Cabeçalhos podem se repetir no exportador.
    mapeamento: dict[str, StrictInt] = Field(default_factory=dict, max_length=24)
    codigo_cliente: StrictInt | None = Field(default=None, ge=0, lt=80)
    linha_cabecalho: int = Field(default=1, ge=1, le=100)
    aba: str | None = Field(default=None, max_length=100)
    separador: Literal["auto", ";", ",", "\t", "|"] = "auto"
    encoding: Literal["auto", "utf-8-sig", "cp1252"] = "auto"

    @field_validator("mapeamento")
    @classmethod
    def validar_mapeamento(cls, value):
        if set(value) - CAMPOS_IMPORTACAO:
            raise ValueError("Mapeamento contém campo de cliente não permitido.")
        if any(isinstance(index, bool) or index < 0 or index >= 80 for index in value.values()):
            raise ValueError("Índice de coluna inválido.")
        if len(set(value.values())) != len(value):
            raise ValueError("Mapeie cada coluna para um único campo.")
        return value


class ImportacaoConfiguracao(ImportacaoFonteConfiguracao):
    tipo_padrao: Literal["Física", "Jurídica"] = "Física"
    enderecos: ImportacaoFonteConfiguracao | None = None
    contatos: ImportacaoFonteConfiguracao | None = None
    complementar_vazios: bool = False
    ignorar_inconsistencias: bool = False


class ImportacaoTabela(BaseModel):
    colunas: list[str]
    abas: list[str]
    aba: str | None
    separador: str | None
    total: int
    amostra: list[list[str]]
    vinculados: int = 0
    sem_vinculo: int = 0


class ImportacaoLinha(BaseModel):
    linha: int
    dados: dict[str, str | None]
    status: Literal["inserir", "ignorado", "erro", "inserido", "nao_importado", "complementar", "complementado", "revisar"]
    motivos: list[str] = Field(default_factory=list)
    avisos: list[str] = Field(default_factory=list)
    codigo_cliente: str | None = None
    cliente_existente_id: int | None = None
    campos_complementar: dict[str, str | None] = Field(default_factory=dict)
    conflitos: list[str] = Field(default_factory=list)


class ImportacaoPrevia(ImportacaoTabela):
    previa_hash: str
    inserir: int
    ignorados: int
    erros: int
    linhas: list[ImportacaoLinha]
    complementar: int = 0
    inconsistencias: int = 0
    fontes: dict[str, ImportacaoTabela] = Field(default_factory=dict)
    ocorrencias: list[str] = Field(default_factory=list)


class ImportacaoRelatorio(BaseModel):
    concluido: bool
    mensagem: str
    total: int
    inseridos: int
    ignorados: int
    erros: int
    nao_importados: int
    linhas: list[ImportacaoLinha]
    complementados: int = 0
    inconsistencias: int = 0
    fontes: dict[str, ImportacaoTabela] = Field(default_factory=dict)
    ocorrencias: list[str] = Field(default_factory=list)
