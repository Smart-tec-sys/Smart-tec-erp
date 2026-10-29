from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class DocumentoContabilInput(BaseModel):
    competencia: str
    tipo_documento: str
    numero: Optional[str] = None
    chave_acesso: Optional[str] = None
    data_emissao: date
    valor: Decimal
    pedido_id: Optional[int] = None
    compra_id: Optional[int] = None
    observacao: Optional[str] = None


class ObrigacaoContabilInput(BaseModel):
    competencia: str
    tipo_obrigacao: str
    descricao: str
    valor: Decimal
    vencimento: date
    fornecedor_id: Optional[int] = None
    observacao: Optional[str] = None


class MarcarObrigacaoPagaInput(BaseModel):
    pagamento: date


class FecharCompetenciaInput(BaseModel):
    observacao: Optional[str] = None