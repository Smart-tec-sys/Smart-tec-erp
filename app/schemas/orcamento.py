from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, conint, root_validator


class RomanaTetoSimulacaoInput(BaseModel):
    produto_id: int = Field(gt=0)
    largura_modulo_m: float = Field(gt=0, allow_inf_nan=False)
    comprimento_avanco_m: float = Field(gt=0, allow_inf_nan=False)
    quantidade_modulos: conint(strict=True, gt=0)
    acionamento: Literal["MANUAL_BASTAO", "MANUAL_CORRENTE", "MOTORIZADA"]
    lado_comando: Optional[Literal["ESQUERDA", "DIREITA"]] = None
    comprimento_bastao_m: Optional[float] = Field(default=None, allow_inf_nan=False)
    comprimento_corrente_sem_fim_m: Optional[float] = Field(default=None, allow_inf_nan=False)
    perfil_comercial: Literal["DECORADOR", "VAREJO", "CONSUMIDOR_FINAL"] = "VAREJO"
    desconto: float = Field(default=0, ge=0, allow_inf_nan=False)
    cor: Optional[str] = None


class OrcamentoItemInput(BaseModel):
    tipo_item: Literal["PRODUTO", "SERVICO"] = "PRODUTO"
    produto_id: Optional[int] = None
    servico_id: Optional[int] = Field(default=None, gt=0)
    descricao: str
    codigo_interno: Optional[str] = None
    grupo_tecnico: Optional[str] = None
    modelo_tecnico: Optional[str] = None
    unidade: Optional[str] = None
    quantidade: float = Field(default=1, gt=0, allow_inf_nan=False)
    largura: float = Field(default=0, ge=0, allow_inf_nan=False)
    altura: float = Field(default=0, ge=0, allow_inf_nan=False)
    area: float = Field(default=0, ge=0, allow_inf_nan=False)
    preco_unitario: float = Field(default=0, ge=0, allow_inf_nan=False)
    preco_unitario_manual: bool = False
    desconto: float = Field(default=0, ge=0, allow_inf_nan=False)
    subtotal: float = Field(default=0, ge=0, allow_inf_nan=False)
    observacao_item: Optional[str] = None
    material: Optional[str] = None
    cor: Optional[str] = None
    acionamento: Optional[str] = None
    lado_comando: Optional[str] = None
    ambiente: Optional[str] = Field(default=None, max_length=200)
    calculo_producao_status: Optional[str] = None
    dados_tecnicos: Optional[dict] = None
    largura_modulo_m: Optional[float] = Field(default=None, allow_inf_nan=False)
    comprimento_avanco_m: Optional[float] = Field(default=None, allow_inf_nan=False)
    quantidade_modulos: Optional[int] = Field(default=None, gt=0)
    acionamento_romana_teto: Optional[str] = None
    comprimento_bastao_m: Optional[float] = Field(default=None, allow_inf_nan=False)
    comprimento_corrente_sem_fim_m: Optional[float] = Field(default=None, allow_inf_nan=False)

    @root_validator(skip_on_failure=True)
    def validar_referencias_item(cls, values):
        tipo = values.get("tipo_item")
        if tipo == "SERVICO" and values.get("produto_id") is not None:
            raise ValueError("Serviço não deve informar produto.")
        if tipo == "PRODUTO" and values.get("servico_id") is not None:
            raise ValueError("Produto não deve informar serviço.")
        return values


class OrcamentoParcelaInput(BaseModel):
    numero: conint(strict=True, ge=1, le=24)
    tipo: Literal["PARCELA", "ENTRADA", "SALDO"] = "PARCELA"
    valor: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    vencimento: date
    forma_pagamento_id: int = Field(gt=0)

class OrcamentoInput(BaseModel):
    cliente_final_nome: Optional[str] = None
    cliente_final_documento: Optional[str] = None
    cliente_final_telefone: Optional[str] = None
    cliente_final_email: Optional[str] = None
    cliente_final_endereco: Optional[str] = None

    cliente_id: Optional[int] = None
    perfil_comercial: Literal["DECORADOR", "VAREJO", "CONSUMIDOR_FINAL"] = "VAREJO"
    status: str = "EM_ABERTO"
    validade: Optional[date] = None
    observacao: Optional[str] = None
    observacao_interna: Optional[str] = None
    desconto: float = Field(default=0, ge=0, allow_inf_nan=False)
    total: float = Field(default=0, ge=0, allow_inf_nan=False)
    total_final: float = Field(default=0, ge=0, allow_inf_nan=False)

    parceiro_id: Optional[int] = None
    percentual_parceiro: float = Field(
        default=0,
        ge=0,
        le=1000,
    )

    representante_id: Optional[int] = None
    vendedor_id: Optional[int] = None
    incluir_rt: bool = False
    tipo_rt: Optional[
        Literal["VALOR_FIXO", "PERCENTUAL"]
    ] = None
    percentual_rt: float = Field(
        default=0,
        ge=0,
        le=100,
    )
    valor_rt: float = Field(
        default=0,
        ge=0,
    )

    incluir_taxa_bancaria: bool = False
    taxa_bancaria_percentual: float = Field(
        default=0,
        ge=0,
        lt=100,
    )

    pagamento_modalidade: Optional[Literal["AVISTA", "PARCELADO", "ENTRADA_SALDO"]] = None
    pagamento_numero_parcelas: Optional[conint(strict=True, ge=1, le=24)] = None
    pagamento_intervalo_dias: Optional[conint(strict=True, ge=0, le=365)] = None
    pagamento_primeiro_vencimento: Optional[date] = None
    pagamento_parcelas: Optional[List[OrcamentoParcelaInput]] = None

    itens: List[OrcamentoItemInput] = Field(default_factory=list)

class OrcamentoUpdate(OrcamentoInput):
    pass


class OrcamentoCondicoesRevendaInput(BaseModel):
    base_smarttec_esperada: float = Field(gt=0, allow_inf_nan=False)
    total_cliente_esperado: float = Field(ge=0, allow_inf_nan=False)
    atualizado_em_esperado: Optional[datetime] = Field(...)
    percentual_parceiro: float = Field(ge=0, le=1000, allow_inf_nan=False)
    desconto_pagamento_percentual: float = Field(ge=0, lt=100, allow_inf_nan=False)
    acrescimo_cartao_percentual: float = Field(ge=0, lt=100, allow_inf_nan=False)
    parcelas_cartao: conint(strict=True, ge=1, le=12)
    observacao_comercial: str
    observacao_interna: str
    observacoes_itens: dict[int, str] = Field(default_factory=dict)
