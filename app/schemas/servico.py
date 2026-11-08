from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, root_validator, validator


UnidadeServico = Literal["UN", "ML", "M2", "HORA", "SERVICO"]
TipoCalculoServico = Literal["POR_UNIDADE", "FAIXA_ALTURA"]


class FaixaAlturaServico(BaseModel):
    altura_max_cm: Decimal = Field(gt=0, max_digits=7, decimal_places=2)
    preco_unitario: Decimal = Field(ge=0, max_digits=14, decimal_places=4)


class ServicoInput(BaseModel):
    codigo: str = Field(min_length=1, max_length=50)
    descricao: str = Field(min_length=1, max_length=500)
    categoria: str = Field(min_length=1, max_length=80)
    unidade: UnidadeServico
    tipo_calculo: TipoCalculoServico = "POR_UNIDADE"
    custo: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=4)
    preco_venda: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=4)
    comissao: Optional[Decimal] = Field(default=None, ge=0, le=100, max_digits=8, decimal_places=4)
    observacoes: Optional[str] = Field(default=None, max_length=5000)
    situacao: Literal["ATIVO", "INATIVO"] = "ATIVO"
    faixas_altura: list[FaixaAlturaServico] = Field(default_factory=list)

    @validator("codigo")
    def normalizar_codigo(cls, value):
        value = value.strip().upper()
        if not value:
            raise ValueError("Informe o código do serviço.")
        return value

    @validator("descricao", "categoria")
    def normalizar_textos_obrigatorios(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Campo obrigatório não pode ficar vazio.")
        return value

    @validator("observacoes")
    def normalizar_observacoes(cls, value):
        value = value.strip() if value is not None else None
        return value or None

    @root_validator(skip_on_failure=True)
    def validar_regra_altura(cls, values):
        faixas = values.get("faixas_altura") or []
        if values.get("tipo_calculo") == "FAIXA_ALTURA":
            if values.get("categoria", "").strip().upper() != "LAVAGEM":
                raise ValueError("Cálculo por faixa de altura está disponível para serviços da categoria Lavagem.")
            if values.get("unidade") != "UN":
                raise ValueError("Lavagem por altura deve usar unidade UN.")
            if not faixas:
                raise ValueError("Cadastre pelo menos uma faixa de altura e seu preço.")
            limites = [faixa.altura_max_cm for faixa in faixas]
            if limites != sorted(set(limites)):
                raise ValueError("As alturas máximas devem ser únicas e estar em ordem crescente.")
        elif faixas:
            raise ValueError("Faixas de altura só podem ser informadas no cálculo por faixa de altura.")
        return values


class ServicoOut(ServicoInput):
    id: int
    empresa_id: int
    criado_em: Optional[str] = None
    atualizado_em: Optional[str] = None
