from datetime import date
from decimal import Decimal
import re
from typing import Literal, Optional

from pydantic import BaseModel, PositiveInt, root_validator, validator


class ParceiroDadosBase(BaseModel):
    nome: str
    documento: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    percentual_padrao: Decimal
    observacao: Optional[str] = None
    tipo_pessoa: Optional[Literal["FISICA", "JURIDICA"]] = None
    nome_fantasia: Optional[str] = None
    razao_social: Optional[str] = None
    situacao_cadastral: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    inscricao_municipal: Optional[str] = None
    tipo_contribuinte: Optional[Literal["CONTRIBUINTE", "ISENTO", "NAO_CONTRIBUINTE"]] = None
    isento_ie: bool
    telefone_celular: Optional[str] = None
    responsavel: Optional[str] = None
    site: Optional[str] = None
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    vendedor_responsavel_id: Optional[PositiveInt] = None
    limite_credito: Optional[Decimal] = None
    permitir_exceder_limite: bool

    @validator("estado")
    def validar_estado(cls, value):
        if value is None:
            return None
        estado = value.strip().upper()
        if estado not in {
            "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
            "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
            "RS", "RO", "RR", "SC", "SP", "SE", "TO",
        }:
            raise ValueError("Estado deve ser uma UF brasileira válida.")
        return estado

    @validator("cep")
    def validar_cep(cls, value):
        if value is None:
            return None
        cep = value.strip()
        if not cep:
            return None
        if not re.fullmatch(r"[0-9.\-/\s]+", cep):
            raise ValueError("CEP deve conter somente números e separadores.")
        digitos = re.sub(r"\D", "", cep)
        if len(digitos) != 8:
            raise ValueError("CEP deve conter oito dígitos.")
        return digitos

    @root_validator(skip_on_failure=True)
    def validar_tamanhos(cls, values):
        limites = {
            "nome": 255,
            "documento": 30,
            "email": 255,
            "telefone": 50,
            "tipo_pessoa": 8,
            "nome_fantasia": 255,
            "razao_social": 255,
            "situacao_cadastral": 100,
            "inscricao_estadual": 80,
            "inscricao_municipal": 80,
            "tipo_contribuinte": 30,
            "telefone_celular": 50,
            "responsavel": 120,
            "site": 500,
            "cep": 8,
            "logradouro": 255,
            "numero": 30,
            "complemento": 255,
            "bairro": 100,
            "cidade": 150,
            "estado": 2,
        }
        for campo, limite in limites.items():
            valor = values.get(campo)
            if isinstance(valor, str) and len(valor.strip()) > limite:
                raise ValueError(f"{campo} excede o limite de {limite} caracteres.")
        return values

    class Config:
        extra = "forbid"


class ParceiroCreateFiscal(ParceiroDadosBase):
    @root_validator(skip_on_failure=True)
    def validar_consistencia_fiscal(cls, values):
        ie = (values.get("inscricao_estadual") or "").strip()
        isento_ie = values.get("isento_ie", False)
        tipo_contribuinte = values.get("tipo_contribuinte")
        if isento_ie and ie:
            raise ValueError("Inscrição Estadual não pode ser informada quando isento_ie é verdadeiro.")
        if isento_ie and tipo_contribuinte not in (None, "ISENTO"):
            raise ValueError("isento_ie verdadeiro exige tipo_contribuinte ISENTO.")
        if tipo_contribuinte == "ISENTO" and not isento_ie:
            raise ValueError("tipo_contribuinte ISENTO exige isento_ie verdadeiro.")
        return values


class ParceiroCreate(ParceiroCreateFiscal):
    nome: str
    percentual_padrao: Decimal = Decimal("0")
    ativo: bool = True
    isento_ie: bool = False
    permitir_exceder_limite: bool = False


class ParceiroUpdate(ParceiroDadosBase):
    nome: Optional[str] = None
    percentual_padrao: Optional[Decimal] = None
    ativo: Optional[bool] = None
    isento_ie: Optional[bool] = None
    permitir_exceder_limite: Optional[bool] = None

    @root_validator(pre=True)
    def rejeitar_null_em_campos_nao_nulos(cls, values):
        for campo in (
            "nome", "percentual_padrao", "ativo", "isento_ie",
            "permitir_exceder_limite",
        ):
            if campo in values and values[campo] is None:
                raise ValueError(f"{campo} não pode ser null.")
        return values


class RepresentanteCreate(BaseModel):
    nome: str
    parceiro_id: Optional[int] = None

    documento: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None

    tipo_rt_padrao: str = "PERCENTUAL"
    percentual_rt_padrao: Decimal = Decimal("0")
    valor_rt_padrao: Decimal = Decimal("0")

    observacao: Optional[str] = None


class RTCreate(BaseModel):
    pedido_id: int
    representante_id: int

    competencia: str
    vencimento: Optional[date] = None

    tipo_calculo: Optional[str] = None
    percentual: Optional[Decimal] = None
    valor_fixo: Optional[Decimal] = None

    observacao: Optional[str] = None


class RTPagamentoInput(BaseModel):
    pagamento: date

# ============================================================
# CARTEIRA DO PARCEIRO
# ============================================================

class ParceiroRepresentanteCreate(BaseModel):
    nome: str

    documento: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None


class ParceiroClienteCreate(BaseModel):
    nome: str

    representante_parceiro_id: Optional[int] = None

    documento: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None

    cadastro_completo: bool = False