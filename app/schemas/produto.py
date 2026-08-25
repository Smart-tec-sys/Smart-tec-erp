from typing import Optional

from pydantic import BaseModel, ConfigDict


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


class Produto(ProdutoBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
