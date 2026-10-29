from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional, Literal

from pydantic import BaseModel, Field, root_validator


class ConverterOrcamentoInput(BaseModel):
    prazo_entrega: Optional[date] = None
    canal_venda: Optional[str] = None


class PedidoItemOut(BaseModel):
    id: int
    tipo_item: str
    produto_id: Optional[int] = None
    descricao: Optional[str] = None
    codigo_interno: Optional[str] = None
    grupo_tecnico: Optional[str] = None
    modelo_tecnico: Optional[str] = None
    unidade: Optional[str] = None

    quantidade: Decimal
    largura: Decimal
    altura: Decimal
    area: Decimal

    preco_unitario: Decimal
    desconto: Decimal
    subtotal: Decimal

    observacao_item: Optional[str] = None
    material: Optional[str] = None
    cor: Optional[str] = None
    acionamento: Optional[str] = None
    lado_comando: Optional[str] = None
    calculo_producao_status: Optional[str] = None
    dados_tecnicos: Optional[Any] = None


class ClienteFinalRevenda(BaseModel):
    cliente_final_nome: Optional[str] = None
    cliente_final_documento: Optional[str] = None
    cliente_final_telefone: Optional[str] = None
    cliente_final_email: Optional[str] = None
    cliente_final_endereco: Optional[str] = None


class PedidoOut(ClienteFinalRevenda):
    id: int
    numero: Optional[str] = None
    empresa_id: Optional[int] = None
    cliente_id: Optional[int] = None
    orcamento_id: Optional[int] = None
    vendedor_id: Optional[int] = None
    parceiro_id: Optional[int] = None
    representante_id: Optional[int] = None

    status: Optional[str] = None
    perfil_comercial: str

    data_venda: Optional[date] = None
    prazo_entrega: Optional[date] = None
    canal_venda: Optional[str] = None

    total: Decimal
    desconto: Decimal
    total_final: Decimal

    percentual_parceiro: Optional[Decimal] = None
    incluir_rt: Optional[bool] = None
    tipo_rt: Optional[str] = None
    percentual_rt: Optional[Decimal] = None
    valor_rt: Optional[Decimal] = None
    incluir_taxa_bancaria: Optional[bool] = None
    taxa_bancaria_percentual: Optional[Decimal] = None
    valor_parceiro: Optional[Decimal] = None
    valor_taxa_bancaria: Optional[Decimal] = None
    total_cliente_final: Optional[Decimal] = None

    observacao: Optional[str] = None
    observacao_interna: Optional[str] = None

    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None

    itens: list[PedidoItemOut] = []

class GerarContaReceberInput(BaseModel):
    vencimento: date
    categoria: Optional[str] = "VENDAS"
    observacao: Optional[str] = None


class ContaReceberOut(BaseModel):
    id: int
    pedido_id: int
    cliente_id: Optional[int] = None
    descricao: str
    valor: Decimal
    vencimento: date
    status: str
    categoria: Optional[str] = None
    observacao: Optional[str] = None

class PedidoUpdate(ClienteFinalRevenda):
    percentual_parceiro: Optional[Decimal] = None
    incluir_rt: Optional[bool] = None
    tipo_rt: Optional[str] = None
    percentual_rt: Optional[Decimal] = None
    valor_rt: Optional[Decimal] = None
    incluir_taxa_bancaria: Optional[bool] = None
    taxa_bancaria_percentual: Optional[Decimal] = None
    valor_parceiro: Optional[Decimal] = None
    valor_taxa_bancaria: Optional[Decimal] = None
    total_cliente_final: Optional[Decimal] = None
    # Campos omitidos permanecem intactos; null explícito remove o vínculo.
    class Config:
        extra = "forbid"
    cliente_id: Optional[int] = None
    vendedor_id: Optional[int] = None
    parceiro_id: Optional[int] = None
    representante_id: Optional[int] = None
    status: Optional[str] = None
    perfil_comercial: Optional[str] = None
    data_venda: Optional[date] = None
    prazo_entrega: Optional[date] = None
    canal_venda: Optional[str] = None
    observacao: Optional[str] = None
    observacao_interna: Optional[str] = None


class PedidoItemCreate(BaseModel):
    class Config:
        extra = "forbid"
    tipo_item: Literal["PRODUTO", "SERVICO"] = "PRODUTO"
    produto_id: Optional[int] = Field(default=None, gt=0)
    descricao: str = Field(min_length=1)
    codigo_interno: Optional[str] = None
    grupo_tecnico: Optional[str] = None
    modelo_tecnico: Optional[str] = None
    unidade: Optional[str] = None
    quantidade: Decimal = Field(default=1, gt=0)
    largura: Decimal = Field(default=0, ge=0)
    altura: Decimal = Field(default=0, ge=0)
    area: Decimal = Field(default=0, ge=0)
    preco_unitario: Decimal = Field(default=0, ge=0)
    desconto: Decimal = Field(default=0, ge=0)
    subtotal: Decimal = Field(default=0, ge=0)
    observacao_item: Optional[str] = None
    material: Optional[str] = None
    cor: Optional[str] = None
    acionamento: Optional[str] = None
    lado_comando: Optional[str] = None
    calculo_producao_status: Optional[str] = None
    dados_tecnicos: Optional[dict] = None

    @root_validator
    def validar_item(cls, values):
        if values.get("tipo_item") == "PRODUTO" and values.get("produto_id") is None:
            config = (values.get("dados_tecnicos") or {}).get("cortina") or {}
            tecido_id = config.get("tecidoProdutoId") if isinstance(config, dict) else None
            cortina_virtual = (values.get("modelo_tecnico") == "CORTINA" and
                               type(tecido_id) is int and tecido_id > 0)
            if not cortina_virtual:
                raise ValueError("Selecione o produto.")
        if values.get("tipo_item") == "SERVICO" and values.get("produto_id") is not None:
            raise ValueError("Serviço não deve informar produto.")
        return values


class PedidoCreate(ClienteFinalRevenda):
    class Config:
        extra = "forbid"
    cliente_id: Optional[int] = Field(default=None, gt=0)
    vendedor_id: Optional[int] = Field(default=None, gt=0)
    parceiro_id: Optional[int] = Field(default=None, gt=0)
    representante_id: Optional[int] = Field(default=None, gt=0)
    perfil_comercial: Literal["VAREJO", "DECORADOR", "CONSUMIDOR_FINAL"] = "VAREJO"
    status: Literal["ABERTO"] = "ABERTO"
    data_venda: Optional[date] = None
    prazo_entrega: Optional[date] = None
    canal_venda: Optional[str] = None
    observacao: Optional[str] = None
    observacao_interna: Optional[str] = None
    desconto: Decimal = Field(default=0, ge=0)
    percentual_parceiro: Decimal = Field(default=0, ge=0, le=1000)
    incluir_rt: bool = False
    tipo_rt: Optional[Literal["PERCENTUAL", "VALOR_FIXO"]] = None
    percentual_rt: Decimal = Field(default=0, ge=0, le=100)
    valor_rt: Decimal = Field(default=0, ge=0)
    incluir_taxa_bancaria: bool = False
    taxa_bancaria_percentual: Decimal = Field(default=0, ge=0, lt=100)
    itens: list[PedidoItemCreate] = Field(min_items=1)
