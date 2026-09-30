"""Cálculo puro de grupos de Romanas alinhadas por uma peça mestre."""

from dataclasses import dataclass, field

from app.services.romana_calculo_producao import (
    RomanaCalculoEntrada,
    RomanaPosicaoVareta,
    calcular_distribuicao_fabricacao_romana,
)


STATUS_OK = "GRUPO_ALINHADO_CALCULADO"
STATUS_REVISAR = "REVISAR_GRUPO_ALINHADO"
RAZAO_DIAGNOSTICA_ULTIMO_GOMO_MINIMO = 0.5


@dataclass(frozen=True)
class RomanaGrupoPecaEntrada:
    identificador: str
    largura_cm: float
    altura_cm: float
    quantidade: int = 1
    posicao_conjunto: str | None = None


@dataclass(frozen=True)
class RomanaGrupoAlinhadoEntrada:
    pecas: tuple[RomanaGrupoPecaEntrada, ...]
    identificador: str | None = None


@dataclass(frozen=True)
class RomanaGrupoPecaResultado:
    identificador: str
    peca_mestre: bool
    largura_cm: float
    altura_cm: float
    quantidade_gomos: int
    quantidade_varetas: int
    posicoes_varetas: tuple[RomanaPosicaoVareta, ...]
    varetas_com_passadores: tuple[int, ...]
    quantidade_cavaletes: int | None
    quantidade_total_passadores: int | None
    ultimo_gomo_cm: float
    diferenca_ultimo_para_padrao_mestre_cm: float
    comprimento_total_tecido_cm: float
    status: str
    alertas: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RomanaGrupoAlinhadoResultado:
    identificador: str | None
    peca_mestre: str
    pecas: tuple[RomanaGrupoPecaResultado, ...]
    posicoes_compartilhadas_cm: tuple[float, ...]
    status: str
    alertas: tuple[str, ...] = field(default_factory=tuple)


def calcular_grupo_alinhado_romana(
    entrada: RomanaGrupoAlinhadoEntrada,
) -> RomanaGrupoAlinhadoResultado:
    """Usa sempre a maior peça como referência única para todo o grupo."""
    if len(entrada.pecas) < 2:
        raise ValueError("grupo alinhado deve conter pelo menos duas peças")
    for peca in entrada.pecas:
        if peca.largura_cm <= 0 or peca.altura_cm <= 0 or peca.quantidade <= 0:
            raise ValueError("largura, altura e quantidade das peças devem ser positivas")

    indice_mestre = max(range(len(entrada.pecas)), key=lambda i: entrada.pecas[i].altura_cm)
    entrada_mestre = entrada.pecas[indice_mestre]
    calculo_mestre = calcular_distribuicao_fabricacao_romana(
        RomanaCalculoEntrada(
            largura_cm=entrada_mestre.largura_cm,
            altura_cm=entrada_mestre.altura_cm,
            quantidade=entrada_mestre.quantidade,
        )
    )
    posicoes_mestre = tuple(v.posicao_cm for v in calculo_mestre.posicoes_varetas)

    resultados = []
    for indice, peca in enumerate(entrada.pecas):
        if indice == indice_mestre or abs(peca.altura_cm - entrada_mestre.altura_cm) <= 1e-9:
            individual = calcular_distribuicao_fabricacao_romana(
                RomanaCalculoEntrada(peca.largura_cm, peca.altura_cm, peca.quantidade)
            )
            resultados.append(_resultado_individual(peca, individual, indice == indice_mestre))
        else:
            resultados.append(_resultado_menor(peca, calculo_mestre, posicoes_mestre))

    alertas_grupo = tuple(
        f"{peca.identificador}: {alerta}"
        for peca in resultados
        for alerta in peca.alertas
    )
    return RomanaGrupoAlinhadoResultado(
        identificador=entrada.identificador,
        peca_mestre=entrada_mestre.identificador,
        pecas=tuple(resultados),
        posicoes_compartilhadas_cm=posicoes_mestre,
        status=STATUS_REVISAR if alertas_grupo else STATUS_OK,
        alertas=alertas_grupo,
    )


def _resultado_individual(peca, calculo, mestre):
    return RomanaGrupoPecaResultado(
        identificador=peca.identificador,
        peca_mestre=mestre,
        largura_cm=peca.largura_cm,
        altura_cm=peca.altura_cm,
        quantidade_gomos=calculo.quantidade_gomos,
        quantidade_varetas=calculo.quantidade_varetas,
        posicoes_varetas=calculo.posicoes_varetas,
        varetas_com_passadores=calculo.varetas_com_passadores,
        quantidade_cavaletes=calculo.quantidade_cavaletes,
        quantidade_total_passadores=calculo.quantidade_total_passadores,
        ultimo_gomo_cm=calculo.ultimo_gomo_pronto_cm,
        diferenca_ultimo_para_padrao_mestre_cm=0.0,
        comprimento_total_tecido_cm=calculo.comprimento_total_tecido_cm,
        status=STATUS_OK,
    )


def _resultado_menor(peca, mestre, posicoes_mestre):
    posicoes_herdadas = tuple(pos for pos in posicoes_mestre if pos < peca.altura_cm)
    quantidade_varetas = len(posicoes_herdadas)
    quantidade_gomos = quantidade_varetas + 1
    ultimo_gomo = (
        peca.altura_cm - posicoes_herdadas[-1]
        if posicoes_herdadas
        else peca.altura_cm
    )
    alertas = list(_alertas_ultimo_gomo(ultimo_gomo, mestre.tamanho_gomo_padrao_cm))
    if not posicoes_herdadas:
        alertas.append("nenhuma posição de vareta da mestre cabe na peça")
    if quantidade_varetas % 2:
        alertas.append("quantidade herdada de varetas é ímpar")

    varetas_com_passadores = tuple(range(2, quantidade_varetas + 1, 2))
    if quantidade_varetas == 0 or not varetas_com_passadores:
        alertas.append("peça não possui última vareta par com passadores")
    elif varetas_com_passadores[-1] != quantidade_varetas:
        alertas.append("última vareta herdada não recebe passadores")

    referencia_individual = calcular_distribuicao_fabricacao_romana(
        RomanaCalculoEntrada(peca.largura_cm, peca.altura_cm, peca.quantidade)
    )
    total_passadores = (
        len(varetas_com_passadores) * referencia_individual.quantidade_cavaletes
        if referencia_individual.quantidade_cavaletes is not None
        else None
    )
    posicoes = tuple(
        RomanaPosicaoVareta(vareta=i, posicao_cm=posicao)
        for i, posicao in enumerate(posicoes_herdadas, start=1)
    )
    corte = peca.altura_cm + 2.5 + (quantidade_varetas * 0.5) + 1.5
    return RomanaGrupoPecaResultado(
        identificador=peca.identificador,
        peca_mestre=False,
        largura_cm=peca.largura_cm,
        altura_cm=peca.altura_cm,
        quantidade_gomos=quantidade_gomos,
        quantidade_varetas=quantidade_varetas,
        posicoes_varetas=posicoes,
        varetas_com_passadores=varetas_com_passadores,
        quantidade_cavaletes=referencia_individual.quantidade_cavaletes,
        quantidade_total_passadores=total_passadores,
        ultimo_gomo_cm=ultimo_gomo,
        diferenca_ultimo_para_padrao_mestre_cm=(
            ultimo_gomo - mestre.tamanho_gomo_padrao_cm
        ),
        comprimento_total_tecido_cm=corte,
        status=STATUS_REVISAR if alertas else STATUS_OK,
        alertas=tuple(alertas),
    )


def _alertas_ultimo_gomo(ultimo_gomo_cm, padrao_mestre_cm):
    if ultimo_gomo_cm <= 0:
        return ("último gomo não positivo",)
    if ultimo_gomo_cm < padrao_mestre_cm * RAZAO_DIAGNOSTICA_ULTIMO_GOMO_MINIMO:
        return (
            "último gomo menor que 50% do padrão da mestre; "
            "limiar apenas diagnóstico, pendente de validação física",
        )
    return ()
