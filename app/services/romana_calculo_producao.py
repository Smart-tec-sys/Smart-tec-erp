"""Motor geométrico puro para a Romana padrão manual.

Este módulo não consulta banco, não calcula preço e não estima materiais.
"""

from dataclasses import dataclass, field
from math import ceil, floor


STATUS_CALCULO = "CALCULO_GEOMETRICO_CONCLUIDO"
STATUS_PENDENTE = "PENDENTE_CONFIRMACAO"
TIPO_SUPORTADO = "ROMANA"
ACIONAMENTO_SUPORTADO = "MANUAL"

# Parâmetros mecânicos V2 centralizados para calibração física.
GOMO_PADRAO_MINIMO_CM = 25.0
GOMO_PADRAO_MAXIMO_CM = 35.0
AJUSTE_PRIMEIRO_GOMO_MINIMO_CM = 2.0
AJUSTE_PRIMEIRO_GOMO_MAXIMO_CM = 6.0
REFERENCIA_BASE_INTEGRADA_CM = 2.5
DOBRA_CABECEIRA_CORTE_CM = 2.5
DOBRA_TECIDO_POR_VARETA_CM = 0.5
RESERVA_FITA_PLASTICA_CORTE_CM = 1.5
TOLERANCIA_FECHAMENTO_CM = 0.01
# Diagnóstico amplo e calibrável; não representa limite industrial definitivo.
RAZAO_MINIMA_ULTIMO_INTERMEDIARIO = 0.75
RAZAO_MAXIMA_ULTIMO_INTERMEDIARIO = 1.75


@dataclass(frozen=True)
class RomanaCalculoEntrada:
    largura_cm: float
    altura_cm: float
    quantidade: int
    tipo: str = TIPO_SUPORTADO
    acionamento: str = ACIONAMENTO_SUPORTADO


@dataclass(frozen=True)
class RomanaCalculoResultado:
    largura_cm: float
    altura_cm: float
    quantidade: int
    quantidade_gomos: int
    quantidade_gomos_inteiros: int
    tamanho_gomo_cm: float
    tamanho_base_cm: float
    alertas: tuple[str, ...] = field(default_factory=tuple)
    status_calculo: str = STATUS_CALCULO
    regra_varetas_status: str = STATUS_PENDENTE
    calculo_tecido_producao: str = "PENDENTE"
    cabeceira_referencia_cm: float | None = None
    base_referencia_cm: float | None = None
    cordoes_carreteis_comando_status: str = STATUS_PENDENTE


@dataclass(frozen=True)
class RomanaPosicaoVareta:
    vareta: int
    posicao_cm: float


@dataclass(frozen=True)
class RomanaFabricacaoResultado:
    altura_pronta_cm: float
    quantidade_gomos: int
    quantidade_varetas: int
    tamanho_gomo_padrao_cm: float
    primeiro_gomo_pronto_cm: float
    gomos_intermediarios_prontos_cm: tuple[float, ...]
    ultimo_gomo_pronto_cm: float
    referencia_base_integrada_cm: float
    soma_altura_pronta_cm: float
    diferenca_altura_pronta_cm: float
    dobra_cabeceira_cm: float
    primeiro_gomo_corte_cm: float
    intermediarios_corte_cm: tuple[float, ...]
    ultimo_gomo_corte_cm: float
    reserva_fita_plastica_cm: float
    quantidade_dobras_varetas: int
    sobra_total_fabricacao_cm: float
    comprimento_total_tecido_cm: float
    compensacao_aplicada_em: str
    ajuste_primeiro_gomo_cm: float
    ajuste_ultimo_gomo_cm: float
    posicoes_varetas: tuple[RomanaPosicaoVareta, ...]
    status_fabricacao: str
    alertas: tuple[str, ...] = field(default_factory=tuple)


def _arredondar_comercial_positivo(valor: float) -> int:
    """Arredonda valor positivo para o inteiro mais próximo, com 0,5 para cima."""
    return floor(valor + 0.5)


def calcular_producao_romana(
    entrada: RomanaCalculoEntrada,
) -> RomanaCalculoResultado:
    """Calcula somente a geometria dos gomos da Romana padrão manual V1."""
    if entrada.largura_cm <= 0:
        raise ValueError("largura_cm deve ser maior que zero")
    if entrada.altura_cm <= 0:
        raise ValueError("altura_cm deve ser maior que zero")
    if entrada.quantidade <= 0:
        raise ValueError("quantidade deve ser maior que zero")
    if entrada.tipo.upper() != TIPO_SUPORTADO:
        raise ValueError("somente o tipo ROMANA possui regra produtiva V1")
    if entrada.acionamento.upper() != ACIONAMENTO_SUPORTADO:
        raise ValueError("somente o acionamento MANUAL possui regra produtiva V1")

    quantidade_gomos = max(1, _arredondar_comercial_positivo(entrada.altura_cm / 25))
    tamanho_gomo_cm = entrada.altura_cm / (quantidade_gomos - 0.5)
    tamanho_base_cm = tamanho_gomo_cm / 2

    return RomanaCalculoResultado(
        largura_cm=float(entrada.largura_cm),
        altura_cm=float(entrada.altura_cm),
        quantidade=int(entrada.quantidade),
        quantidade_gomos=quantidade_gomos,
        quantidade_gomos_inteiros=max(0, quantidade_gomos - 1),
        tamanho_gomo_cm=tamanho_gomo_cm,
        tamanho_base_cm=tamanho_base_cm,
        alertas=(
            "Altura informada representa a altura pronta; consumo de tecido pendente.",
            "Varetas, cordões, carretéis e comando dependem de confirmação da produção.",
        ),
        cabeceira_referencia_cm=float(entrada.largura_cm),
        base_referencia_cm=float(entrada.largura_cm),
    )


def calcular_distribuicao_fabricacao_romana(
    entrada: RomanaCalculoEntrada,
) -> RomanaFabricacaoResultado:
    """Separa altura pronta e corte V2; os gomos são pares e as varetas ímpares."""
    geometria = calcular_producao_romana(entrada)  # valida entrada e bloqueios da V1
    quantidade_gomos, gomo_padrao_cm = _selecionar_gomos_fabricacao_v2(
        geometria.altura_cm, geometria.quantidade_gomos
    )
    quantidade_varetas = quantidade_gomos - 1
    quantidade_intermediarios = quantidade_gomos - 2

    diferenca_para_distribuir_cm = (
        geometria.altura_cm - (quantidade_gomos * gomo_padrao_cm)
    )
    ajuste_primeiro_gomo_cm = min(
        AJUSTE_PRIMEIRO_GOMO_MAXIMO_CM,
        max(AJUSTE_PRIMEIRO_GOMO_MINIMO_CM, diferenca_para_distribuir_cm),
    )
    ajuste_ultimo_gomo_cm = diferenca_para_distribuir_cm - ajuste_primeiro_gomo_cm
    primeiro_gomo_pronto_cm = gomo_padrao_cm + ajuste_primeiro_gomo_cm
    gomos_intermediarios_prontos = (gomo_padrao_cm,) * quantidade_intermediarios
    ultimo_gomo_pronto_cm = geometria.altura_cm - (
        primeiro_gomo_pronto_cm + sum(gomos_intermediarios_prontos)
    )
    soma_altura_pronta_cm = (
        primeiro_gomo_pronto_cm
        + sum(gomos_intermediarios_prontos)
        + ultimo_gomo_pronto_cm
    )
    diferenca_altura_pronta_cm = geometria.altura_cm - soma_altura_pronta_cm

    primeiro_gomo_corte_cm = (
        primeiro_gomo_pronto_cm + DOBRA_TECIDO_POR_VARETA_CM
    )
    intermediarios_corte = tuple(
        gomo + DOBRA_TECIDO_POR_VARETA_CM
        for gomo in gomos_intermediarios_prontos
    )
    # A base de 2,5 cm já está integrada ao último gomo; não é um trecho extra.
    ultimo_gomo_corte_cm = ultimo_gomo_pronto_cm
    sobra_total_fabricacao_cm = (
        DOBRA_CABECEIRA_CORTE_CM
        + (quantidade_varetas * DOBRA_TECIDO_POR_VARETA_CM)
        + RESERVA_FITA_PLASTICA_CORTE_CM
    )
    comprimento_total_tecido_cm = geometria.altura_cm + sobra_total_fabricacao_cm
    comprimento_por_trechos_cm = (
        DOBRA_CABECEIRA_CORTE_CM
        + primeiro_gomo_corte_cm
        + sum(intermediarios_corte)
        + ultimo_gomo_corte_cm
        + RESERVA_FITA_PLASTICA_CORTE_CM
    )

    # Saída auxiliar: cada vareta fica após um gomo, exceto o último.
    posicoes_varetas = []
    posicao_acumulada_cm = 0.0
    for numero_vareta, tamanho_gomo_cm in enumerate(
        (primeiro_gomo_pronto_cm, *gomos_intermediarios_prontos), start=1
    ):
        posicao_acumulada_cm += tamanho_gomo_cm
        posicoes_varetas.append(
            RomanaPosicaoVareta(
                vareta=numero_vareta,
                posicao_cm=posicao_acumulada_cm,
            )
        )

    alertas = []
    if ultimo_gomo_pronto_cm <= 0:
        alertas.append("Último gomo não positivo; revisar a distribuição.")
    if gomos_intermediarios_prontos:
        razao = ultimo_gomo_pronto_cm / gomo_padrao_cm
        if not (
            RAZAO_MINIMA_ULTIMO_INTERMEDIARIO
            <= razao
            <= RAZAO_MAXIMA_ULTIMO_INTERMEDIARIO
        ):
            alertas.append(
                "Último gomo muito diferente dos intermediários; "
                "limiar diagnóstico pendente de calibração física."
            )
    if abs(diferenca_altura_pronta_cm) > TOLERANCIA_FECHAMENTO_CM:
        alertas.append("Altura pronta fora da tolerância matemática de 0,01 cm.")
    if quantidade_gomos % 2 or quantidade_varetas % 2 != 1:
        alertas.append("Paridade mecânica inválida: revisar gomos e varetas.")
    if len((primeiro_gomo_corte_cm, *intermediarios_corte)) != quantidade_varetas:
        alertas.append("Quantidade de dobras de tecido difere da quantidade de varetas.")
    if abs(comprimento_por_trechos_cm - comprimento_total_tecido_cm) > TOLERANCIA_FECHAMENTO_CM:
        alertas.append("Marcação por trechos diverge da fórmula total do corte de tecido.")

    return RomanaFabricacaoResultado(
        altura_pronta_cm=geometria.altura_cm,
        quantidade_gomos=quantidade_gomos,
        quantidade_varetas=quantidade_varetas,
        tamanho_gomo_padrao_cm=gomo_padrao_cm,
        primeiro_gomo_pronto_cm=primeiro_gomo_pronto_cm,
        gomos_intermediarios_prontos_cm=gomos_intermediarios_prontos,
        ultimo_gomo_pronto_cm=ultimo_gomo_pronto_cm,
        referencia_base_integrada_cm=REFERENCIA_BASE_INTEGRADA_CM,
        soma_altura_pronta_cm=soma_altura_pronta_cm,
        diferenca_altura_pronta_cm=diferenca_altura_pronta_cm,
        dobra_cabeceira_cm=DOBRA_CABECEIRA_CORTE_CM,
        primeiro_gomo_corte_cm=primeiro_gomo_corte_cm,
        intermediarios_corte_cm=intermediarios_corte,
        ultimo_gomo_corte_cm=ultimo_gomo_corte_cm,
        reserva_fita_plastica_cm=RESERVA_FITA_PLASTICA_CORTE_CM,
        quantidade_dobras_varetas=quantidade_varetas,
        sobra_total_fabricacao_cm=sobra_total_fabricacao_cm,
        comprimento_total_tecido_cm=comprimento_total_tecido_cm,
        compensacao_aplicada_em=(
            "PRIMEIRO"
            if abs(ajuste_ultimo_gomo_cm) <= TOLERANCIA_FECHAMENTO_CM
            else "ULTIMO"
        ),
        ajuste_primeiro_gomo_cm=ajuste_primeiro_gomo_cm,
        ajuste_ultimo_gomo_cm=ajuste_ultimo_gomo_cm,
        posicoes_varetas=tuple(posicoes_varetas),
        status_fabricacao="REVISAR_DISTRIBUICAO" if alertas else "DISTRIBUICAO_V2_CALCULADA",
        alertas=tuple(alertas),
    )


def _selecionar_gomos_fabricacao_v2(
    altura_pronta_cm: float, quantidade_aproximada_v1: int
) -> tuple[int, float]:
    """Ajusta a aproximação V1 para par e valida o conforto da distribuição.

    A paridade é mecânica: gomos pares produzem varetas ímpares e mantêm
    correta a alternância do conjunto durante o recolhimento. Quando a
    aproximação V1 é ímpar, o par inferior é preferido para manter gomos
    maiores. Quando já é par, a referência V1 é preservada.
    """
    candidato_inicial = max(
        4,
        quantidade_aproximada_v1
        if quantidade_aproximada_v1 % 2 == 0
        else quantidade_aproximada_v1 - 1,
    )
    limite_busca = max(candidato_inicial + 6, ceil(altura_pronta_cm / 20) + 4)
    candidatos = [candidato_inicial]
    candidatos.extend(range(candidato_inicial - 2, 3, -2))
    candidatos.extend(range(candidato_inicial + 2, limite_busca + 1, 2))

    for quantidade_gomos in candidatos:
        gomo_padrao_cm = max(
            GOMO_PADRAO_MINIMO_CM,
            float(
                ceil(
                    (altura_pronta_cm - AJUSTE_PRIMEIRO_GOMO_MAXIMO_CM)
                    / quantidade_gomos
                )
            ),
        )
        diferenca = altura_pronta_cm - (quantidade_gomos * gomo_padrao_cm)
        ajuste_primeiro = min(
            AJUSTE_PRIMEIRO_GOMO_MAXIMO_CM,
            max(AJUSTE_PRIMEIRO_GOMO_MINIMO_CM, diferenca),
        )
        ultimo_gomo = gomo_padrao_cm + (diferenca - ajuste_primeiro)
        razao_ultimo = ultimo_gomo / gomo_padrao_cm
        if (
            gomo_padrao_cm <= GOMO_PADRAO_MAXIMO_CM
            and RAZAO_MINIMA_ULTIMO_INTERMEDIARIO
            <= razao_ultimo
            <= RAZAO_MAXIMA_ULTIMO_INTERMEDIARIO
        ):
            return quantidade_gomos, gomo_padrao_cm
    # Mantém um resultado diagnosticável para dimensões positivas fora da faixa,
    # permitindo que o chamador receba REVISAR_DISTRIBUICAO em vez de inventar
    # uma configuração industrial alternativa.
    gomo_fallback = max(
        GOMO_PADRAO_MINIMO_CM,
        min(
            GOMO_PADRAO_MAXIMO_CM,
            float(
                ceil(
                    (altura_pronta_cm - AJUSTE_PRIMEIRO_GOMO_MAXIMO_CM)
                    / candidato_inicial
                )
            ),
        ),
    )
    return candidato_inicial, gomo_fallback
