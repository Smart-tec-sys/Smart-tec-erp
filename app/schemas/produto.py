from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProdutoBase(BaseModel):
    nome: str

    codigo_interno: Optional[str] = None
    codigo_barras: Optional[str] = None
    grupo_produto: Optional[str] = None

    # Arquitetura técnica SmartTec
    modelo_tecnico: Optional[str] = None
    grupo_tecnico: Optional[str] = None
    familia_tecnica: Optional[str] = None

    produto_base: Optional[str] = None
    variacao_cor: Optional[str] = None
    variacao_lado: Optional[str] = None
    variacao_tamanho: Optional[str] = None

    varia_cor: Optional[bool] = False
    cor_componente: Optional[str] = None

    status_comercial: Optional[str] = "Ativo"

    # Fornecedor
    fornecedores: Optional[str] = None
    nome_fornecedor: Optional[str] = None
    codigo_fornecedor: Optional[str] = None

    # Compra / controle
    unidade_compra: Optional[str] = None
    unidade_controle: Optional[str] = None
    comprimento_compra: Optional[float] = 0
    saldo_metros: Optional[float] = 0

    tipo_produto: Optional[str] = None
    unidade_venda: Optional[str] = None
    movimenta_estoque: Optional[str] = "Sim"
    habilitar_nota_fiscal: Optional[str] = "Sim"
    possui_variacoes: Optional[str] = "Não"
    possui_composicao: Optional[str] = "Não"
    situacao: Optional[str] = "Ativo"

    linha: Optional[str] = None
    modelo: Optional[str] = None
    tipo_cortina_persiana: Optional[str] = None
    material_tecido: Optional[str] = None
    cor: Optional[str] = None

    largura: Optional[float] = 0
    altura: Optional[float] = 0
    comprimento: Optional[float] = 0
    peso: Optional[float] = 0

    descricao: Optional[str] = None
    observacoes: Optional[str] = None

    valor_custo: Optional[float] = 0
    despesas_acessorias: Optional[float] = 0
    outras_despesas: Optional[float] = 0
    custo_final: Optional[float] = 0
    margem_lucro: Optional[float] = 0
    valor_venda: Optional[float] = 0

    estoque_minimo: Optional[float] = 0
    estoque_maximo: Optional[float] = 0
    estoque_atual: Optional[float] = 0

    ncm: Optional[str] = None
    cest: Optional[str] = None
    origem: Optional[str] = None


class ProdutoCreate(ProdutoBase):
    pass


class ProdutoUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    descricao: str | None = Field(default=None, max_length=5000)
    grupo_produto: str | None = Field(default=None, max_length=150)
    grupo_tecnico: str | None = Field(default=None, max_length=150)
    familia_tecnica: str | None = Field(default=None, max_length=100)
    modelo_tecnico: str | None = Field(default=None, max_length=100)
    unidade: str | None = Field(default=None, max_length=50)
    unidade_venda: str | None = Field(default=None, max_length=50)
    unidade_compra: str | None = Field(default=None, max_length=50)
    unidade_controle: str | None = Field(default=None, max_length=50)
    nome_fornecedor: str | None = Field(default=None, max_length=255)
    fornecedores: str | None = Field(default=None, max_length=5000)
    codigo_fornecedor: str | None = Field(default=None, max_length=100)
    valor_custo: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    despesas_acessorias: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    outras_despesas: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    margem_lucro: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    valor_venda: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    cor: str | None = Field(default=None, max_length=100)
    cor_componente: str | None = Field(default=None, max_length=100)
    variacao_cor: str | None = Field(default=None, max_length=100)
    situacao: str | None = Field(default=None, max_length=20)
    status_comercial: str | None = Field(default=None, max_length=50)
    varia_cor: bool | None = None

    model_config = ConfigDict(extra="forbid")


class Produto(ProdutoBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
