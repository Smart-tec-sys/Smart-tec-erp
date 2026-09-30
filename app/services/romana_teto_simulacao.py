"""Adaptador de simulação para Romana de Teto: não persiste nem calcula custo de composição."""
from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.services.romana_teto_calculo_producao import (
    RomanaTetoEntrada,
    calcular_romana_teto,
)
from app.services.area_faturavel import calcular_area_faturavel, AreaFaturavelResultado
from app.schemas.orcamento import RomanaTetoSimulacaoInput


FAMILIA_PIMPOINT = "ROMANA_TETO_BLACKOUT_PIMPOINT"
CORES_PIMPOINT_VALIDAS = ("BEGE", "BRANCO", "CINZA")

PIMPOINT_TECIDO_FONTES = {
    "BEGE": {
        1.83: {"codigo_fonte": "JPTEC-0090", "custo_m2": Decimal("29.98")},
        2.50: {"codigo_fonte": "JPTEC-0093", "custo_m2": Decimal("29.98")},
        3.00: {"codigo_fonte": "JPTEC-0096", "custo_m2": Decimal("32.98")},
    },
    "BRANCO": {
        1.83: {"codigo_fonte": "JPTEC-0089", "custo_m2": Decimal("29.98")},
        2.50: {"codigo_fonte": "JPTEC-0092", "custo_m2": Decimal("29.98")},
        3.00: {"codigo_fonte": "JPTEC-0095", "custo_m2": Decimal("32.98")},
    },
    "CINZA": {
        1.83: {"codigo_fonte": "JPTEC-0091", "custo_m2": Decimal("29.98")},
        2.50: {"codigo_fonte": "JPTEC-0094", "custo_m2": Decimal("29.98")},
        3.00: {"codigo_fonte": "JPTEC-0097", "custo_m2": Decimal("32.98")},
    },
}


@dataclass(frozen=True)
class TecidoCustoResolvido:
    familia: str
    cor: str
    largura_modulo_m: float
    largura_tecido_selecionada_m: float | None
    codigo_fonte: str | None
    produto_fonte_id: int | None
    custo_tecido_m2: Decimal | None
    status: str


STATUS_RESOLVIDO = "RESOLVIDO"
STATUS_AVALIACAO_NECESSARIA = "AVALIACAO_NECESSARIA"
STATUS_COR_INVALIDA = "COR_INVALIDA"
STATUS_FAMILIA_NAO_PIMPOINT = "FAMILIA_NAO_PIMPOINT"


def _eh_pimpoint(produto) -> bool:
    familia = getattr(produto, "familia_tecnica", None)
    return familia == FAMILIA_PIMPOINT


def _obter_cor_produto(produto) -> str | None:
    cor = getattr(produto, "cor", None)
    if cor:
        return cor.upper().strip()
    variacao_cor = getattr(produto, "variacao_cor", None)
    if variacao_cor:
        return variacao_cor.upper().strip()
    return None


def _resolver_cor_pimpoint(entrada_cor: str | None, produto) -> str | None:
    """Resolve a cor com prioridade: 1. entrada.cor (payload), 2. produto.cor, 3. produto.variacao_cor."""
    if entrada_cor:
        return entrada_cor.upper().strip()
    return _obter_cor_produto(produto)


def _selecionar_largura_tecido(largura_modulo_m: float) -> float | None:
    if largura_modulo_m <= 1.83:
        return 1.83
    if largura_modulo_m <= 2.50:
        return 2.50
    if largura_modulo_m <= 3.00:
        return 3.00
    return None


def resolver_tecido_pimpoint(produto, largura_modulo_m: float, entrada_cor: str | None = None) -> TecidoCustoResolvido:
    if not _eh_pimpoint(produto):
        return TecidoCustoResolvido(
            familia=FAMILIA_PIMPOINT,
            cor="",
            largura_modulo_m=largura_modulo_m,
            largura_tecido_selecionada_m=None,
            codigo_fonte=None,
            produto_fonte_id=None,
            custo_tecido_m2=None,
            status=STATUS_FAMILIA_NAO_PIMPOINT,
        )

    cor = _resolver_cor_pimpoint(entrada_cor, produto)
    if not cor or cor not in CORES_PIMPOINT_VALIDAS:
        return TecidoCustoResolvido(
            familia=FAMILIA_PIMPOINT,
            cor=cor or "",
            largura_modulo_m=largura_modulo_m,
            largura_tecido_selecionada_m=None,
            codigo_fonte=None,
            produto_fonte_id=None,
            custo_tecido_m2=None,
            status=STATUS_COR_INVALIDA,
        )

    largura_tecido_selecionada = _selecionar_largura_tecido(largura_modulo_m)
    if largura_tecido_selecionada is None:
        return TecidoCustoResolvido(
            familia=FAMILIA_PIMPOINT,
            cor=cor,
            largura_modulo_m=largura_modulo_m,
            largura_tecido_selecionada_m=None,
            codigo_fonte=None,
            produto_fonte_id=None,
            custo_tecido_m2=None,
            status=STATUS_AVALIACAO_NECESSARIA,
        )

    fonte_info = PIMPOINT_TECIDO_FONTES[cor][largura_tecido_selecionada]
    produto_fonte_id = getattr(produto, "id", None)

    return TecidoCustoResolvido(
        familia=FAMILIA_PIMPOINT,
        cor=cor,
        largura_modulo_m=largura_modulo_m,
        largura_tecido_selecionada_m=largura_tecido_selecionada,
        codigo_fonte=fonte_info["codigo_fonte"],
        produto_fonte_id=produto_fonte_id,
        custo_tecido_m2=fonte_info["custo_m2"],
        status=STATUS_RESOLVIDO,
    )


def simular_romana_teto(produto, entrada: RomanaTetoSimulacaoInput):
    parametros = RomanaTetoEntrada(
        largura_modulo_m=entrada.largura_modulo_m,
        comprimento_avanco_m=entrada.comprimento_avanco_m,
        quantidade_modulos=entrada.quantidade_modulos,
        acionamento=entrada.acionamento,
        lado_comando=entrada.lado_comando,
        comprimento_bastao_m=entrada.comprimento_bastao_m,
        comprimento_corrente_sem_fim_m=entrada.comprimento_corrente_sem_fim_m,
    )
    fabricacao = calcular_romana_teto(parametros)

    tecido_custo = resolver_tecido_pimpoint(produto, entrada.largura_modulo_m, entrada.cor)

    from app.services.orcamento_service import _preco_produto, _dinheiro, MULTIPLICADORES
    is_pimpoint_resolvido = _eh_pimpoint(produto) and tecido_custo.status == STATUS_RESOLVIDO
    is_pimpoint_avaliacao = _eh_pimpoint(produto) and tecido_custo.status == STATUS_AVALIACAO_NECESSARIA
    is_pimpoint_cor_invalida = _eh_pimpoint(produto) and tecido_custo.status == STATUS_COR_INVALIDA

    if is_pimpoint_resolvido:
        custo_base = tecido_custo.custo_tecido_m2
        multiplicador = MULTIPLICADORES[entrada.perfil_comercial]
        preco = (custo_base * multiplicador).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        custo = custo_base
        origem_preco = "CUSTO_TECIDO_POR_LARGURA"
    elif is_pimpoint_avaliacao or is_pimpoint_cor_invalida:
        preco = Decimal("0")
        custo = None
        origem_preco = "AVALIACAO_NECESSARIA"
    else:
        preco = _preco_produto(produto, entrada.perfil_comercial)
        custo = next(
            (
                Decimal(str(getattr(produto, campo, 0) or 0))
                for campo in ("custo_final", "valor_custo")
                if Decimal(str(getattr(produto, campo, 0) or 0)) > 0
            ),
            None,
        )
        origem_preco = "CUSTO_CADASTRADO" if custo is not None else "VALOR_VENDA_CADASTRADO"

    unidade_venda = getattr(produto, "unidade_venda", None)
    area_faturavel: AreaFaturavelResultado = calcular_area_faturavel(
        largura=entrada.largura_modulo_m,
        altura=entrada.comprimento_avanco_m,
        quantidade=entrada.quantidade_modulos,
        unidade_venda=unidade_venda,
    )
    subtotal = _dinheiro(
        max(Decimal("0"), area_faturavel.area_faturavel_m2 * preco - Decimal(str(entrada.desconto)))
    )
    avisos = list(fabricacao.alertas)
    if custo is None and not is_pimpoint_avaliacao and not is_pimpoint_cor_invalida:
        avisos.append("Sem custo cadastrado: usado valor de venda conforme o backend, sem novo acréscimo.")
    if preco <= 0 and not is_pimpoint_avaliacao and not is_pimpoint_cor_invalida:
        avisos.append("Preço indisponível: cadastro sem custo ou valor de venda positivo. Revise antes de salvar.")
    if tecido_custo.status == STATUS_COR_INVALIDA:
        avisos.append(f"Cor '{tecido_custo.cor}' não suportada para PIMPOINT. Cores válidas: {', '.join(CORES_PIMPOINT_VALIDAS)}.")
    if tecido_custo.status == STATUS_AVALIACAO_NECESSARIA:
        avisos.append(f"Largura do módulo {entrada.largura_modulo_m:.2f} m excede 3,00 m. Avaliação técnica necessária para definição de tecido.")

    tecido_custo_dict = {
        "familia": tecido_custo.familia,
        "cor": tecido_custo.cor,
        "largura_modulo_m": tecido_custo.largura_modulo_m,
        "largura_tecido_selecionada_m": tecido_custo.largura_tecido_selecionada_m,
        "codigo_fonte": tecido_custo.codigo_fonte,
        "produto_fonte_id": tecido_custo.produto_fonte_id,
        "custo_tecido_m2": float(tecido_custo.custo_tecido_m2) if tecido_custo.custo_tecido_m2 is not None else None,
        "status": tecido_custo.status,
    }

    preco_disponivel = preco > 0 and not is_pimpoint_avaliacao and not is_pimpoint_cor_invalida

    return dict(
        modelo="ROMANA_TETO",
        quantidade_modulos=entrada.quantidade_modulos,
        area_real_m2=float(area_faturavel.area_real_m2),
        area_faturavel_m2=float(area_faturavel.area_faturavel_m2),
        minimo_faturavel_aplicado=area_faturavel.minimo_faturavel_aplicado,
        fabricacao_por_modulo=asdict(fabricacao),
        custo_tecnico=None,
        custo_cadastrado=custo,
        preco_unitario=preco,
        subtotal=subtotal,
        preco_disponivel=preco_disponivel,
        alertas=avisos,
        origem_preco=origem_preco,
        aviso="Simulação recalculada, por módulo; não representa histórico nem composição integral precificada.",
        tecido_custo_resolvido=tecido_custo_dict,
    )