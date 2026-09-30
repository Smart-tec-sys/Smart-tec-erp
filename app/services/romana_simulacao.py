"""Adaptador de simulação: não persiste nem calcula custo de composição."""
from dataclasses import asdict
from decimal import Decimal
import unicodedata

from pydantic import BaseModel, Field, conint
from app.services.romana_calculo_producao import (
    RomanaCalculoEntrada, calcular_distribuicao_fabricacao_romana,
)
from typing import Literal
from app.services.area_faturavel import calcular_area_faturavel, AreaFaturavelResultado


class RomanaSimulacaoInput(BaseModel):
    produto_id: int = Field(gt=0)
    largura: float = Field(gt=0, allow_inf_nan=False)
    altura: float = Field(gt=0, allow_inf_nan=False)
    quantidade: conint(strict=True, gt=0)
    perfil_comercial: Literal['DECORADOR', 'VAREJO', 'CONSUMIDOR_FINAL'] = 'VAREJO'
    desconto: float = Field(default=0, ge=0, allow_inf_nan=False)


def tipo_romana(produto):
    def normalizar(value):
        return ''.join(c for c in unicodedata.normalize('NFD', str(value or ''))
                       if not unicodedata.combining(c)).upper().replace('_', ' ')
    modelo = normalizar(getattr(produto, 'modelo_tecnico', ''))
    texto = ' '.join(normalizar(getattr(produto, campo, ''))
                     for campo in ('modelo_tecnico', 'modelo', 'nome'))
    if 'ROMANA' not in texto or 'TETO' in texto:
        return None
    if 'MOTORIZ' in texto:
        return 'MOTORIZADA'
    if modelo in ('ROMANA', 'ROMANA MANUAL'):
        return 'MANUAL'
    return None


def simular_romana(produto, entrada):
    if tipo_romana(produto) != 'MANUAL':
        raise ValueError('Simulação disponível somente para Romana manual; motorizada não liberada.')
    # Conversão de unidade apenas; geometria e defaults pertencem ao motor.
    parametros = RomanaCalculoEntrada(entrada.largura * 100, entrada.altura * 100, entrada.quantidade)
    fabricacao = calcular_distribuicao_fabricacao_romana(parametros)
    if min(fabricacao.largura_vareta_cm, fabricacao.largura_base_cm,
           fabricacao.tamanho_gomo_padrao_cm) <= 0:
        raise ValueError('Medidas produzem cortes não positivos; revise largura e altura.')
    # Importação local evita ciclo com o serviço que revalida no salvamento.
    from app.services.orcamento_service import _preco_produto, _dinheiro
    preco = _preco_produto(produto, entrada.perfil_comercial)
    custo = next((Decimal(str(getattr(produto, campo, 0) or 0))
                  for campo in ('custo_final', 'valor_custo')
                  if Decimal(str(getattr(produto, campo, 0) or 0)) > 0), None)

    # Área faturável (regra central: mínimo 1,50 m² apenas para produtos vendidos em M²)
    unidade_venda = getattr(produto, 'unidade_venda', None)
    area_faturavel: AreaFaturavelResultado = calcular_area_faturavel(
        largura=entrada.largura,
        altura=entrada.altura,
        quantidade=entrada.quantidade,
        unidade_venda=unidade_venda,
    )
    subtotal = _dinheiro(max(Decimal('0'), area_faturavel.area_faturavel_m2 * preco - Decimal(str(entrada.desconto))))
    avisos = list(fabricacao.alertas)
    if custo is None:
        avisos.append('Sem custo cadastrado: usado valor de venda conforme o backend, sem novo acréscimo.')
    if preco <= 0:
        avisos.append('Preço indisponível: cadastro sem custo ou valor de venda positivo. Revise antes de salvar.')
    return dict(
        modelo='ROMANA',
        quantidade_pecas=entrada.quantidade,
        area_real_m2=area_faturavel.area_real_m2,
        area_faturavel_m2=area_faturavel.area_faturavel_m2,
        minimo_faturavel_aplicado=area_faturavel.minimo_faturavel_aplicado,
        fabricacao_por_peca=asdict(fabricacao),
        defaults_utilizados=dict(tipo_corrente=parametros.tipo_corrente, tipo_comando=parametros.tipo_comando),
        custo_tecnico=None,
        custo_cadastrado=custo,
        preco_unitario=preco,
        subtotal=subtotal,
        preco_disponivel=preco > 0,
        alertas=avisos,
        origem_preco='CUSTO_CADASTRADO' if custo is not None else 'VALOR_VENDA_CADASTRADO',
        aviso='Simulação recalculada, por peça; não representa histórico nem composição integral precificada.',
    )
