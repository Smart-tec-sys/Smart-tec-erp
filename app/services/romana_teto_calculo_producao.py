"""Motor independente de alinhamento para conjuntos de Romanas de teto.

A geometria da peça mestre é uma entrada explícita. Este módulo não presume que
a fórmula da Romana comum seja a fórmula produtiva da Romana de teto.
"""

from dataclasses import dataclass, field


INSTALACAO_FORA_VAO = "FORA_DO_VAO"
INSTALACAO_DENTRO_VAO = "DENTRO_DO_VAO"
ROMANA_TETO_V1_STATUS = "DIAGNOSTICA"
ROMANA_TETO_PRODUCAO_LIBERADA = False
STATUS_ALINHADO = "ALINHAMENTO_INTEGRAL_TETO"
STATUS_PARCIAL = "ALINHAMENTO_PARCIAL_TETO"
STATUS_REVISAR = "REVISAR_ALINHAMENTO_TETO"


@dataclass(frozen=True)
class RomanaTetoPecaEntrada:
    identificador: str
    largura_cm: float
    altura_cm: float


@dataclass(frozen=True)
class RomanaTetoGeometriaMestre:
    """Geometria previamente validada para a maior peça do conjunto."""

    quantidade_gomos: int
    posicoes_varetas_cm: tuple[float, ...]
    altura_cm: float
    origem: str


@dataclass(frozen=True)
class RomanaTetoGrupoEntrada:
    pecas: tuple[RomanaTetoPecaEntrada, ...]
    tipo_instalacao: str
    geometria_mestre: RomanaTetoGeometriaMestre


@dataclass(frozen=True)
class RomanaTetoPecaResultado:
    identificador: str
    peca_mestre: bool
    altura_original_cm: float
    altura_ajustada_cm: float
    diferenca_acrescentada_cm: float
    posicoes_varetas_cm: tuple[float, ...]
    quantidade_gomos: int
    quantidade_varetas: int
    varetas_com_passadores: tuple[int, ...]
    ultimo_gomo_cm: float
    status: str
    alertas: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RomanaTetoGrupoResultado:
    peca_mestre: str
    tipo_instalacao: str
    origem_geometria_mestre: str
    versao_status: str
    producao_liberada: bool
    pecas: tuple[RomanaTetoPecaResultado, ...]
    status: str


def calcular_grupo_romana_teto(
    entrada: RomanaTetoGrupoEntrada,
) -> RomanaTetoGrupoResultado:
    """Alinha peças de teto sem calcular ou importar a geometria da mestre."""
    _validar_entrada(entrada)
    maior_altura = max(peca.altura_cm for peca in entrada.pecas)
    if abs(entrada.geometria_mestre.altura_cm - maior_altura) > 1e-9:
        raise ValueError("geometria_mestre deve pertencer à peça de maior altura")

    indice_mestre = next(
        indice
        for indice, peca in enumerate(entrada.pecas)
        if abs(peca.altura_cm - maior_altura) <= 1e-9
    )
    resultados = []
    for indice, peca in enumerate(entrada.pecas):
        if abs(peca.altura_cm - maior_altura) <= 1e-9:
            resultados.append(_resultado_mestre(peca, indice == indice_mestre, entrada.geometria_mestre))
        elif entrada.tipo_instalacao == INSTALACAO_FORA_VAO:
            resultados.append(_resultado_fora_vao(peca, entrada.geometria_mestre))
        else:
            resultados.append(_resultado_dentro_vao(peca, entrada.geometria_mestre))

    status = STATUS_REVISAR if any(p.status == STATUS_REVISAR for p in resultados) else (
        STATUS_PARCIAL if any(p.status == STATUS_PARCIAL for p in resultados) else STATUS_ALINHADO
    )
    return RomanaTetoGrupoResultado(
        peca_mestre=entrada.pecas[indice_mestre].identificador,
        tipo_instalacao=entrada.tipo_instalacao,
        origem_geometria_mestre=entrada.geometria_mestre.origem,
        versao_status=ROMANA_TETO_V1_STATUS,
        producao_liberada=ROMANA_TETO_PRODUCAO_LIBERADA,
        pecas=tuple(resultados),
        status=status,
    )


def _validar_entrada(entrada: RomanaTetoGrupoEntrada) -> None:
    if not entrada.pecas:
        raise ValueError("grupo de Romana de teto deve conter pelo menos uma peça")
    if entrada.tipo_instalacao not in (INSTALACAO_FORA_VAO, INSTALACAO_DENTRO_VAO):
        raise ValueError("tipo_instalacao deve ser FORA_DO_VAO ou DENTRO_DO_VAO")
    if any(peca.largura_cm <= 0 or peca.altura_cm <= 0 for peca in entrada.pecas):
        raise ValueError("largura e altura devem ser positivas")
    geometria = entrada.geometria_mestre
    if geometria.altura_cm <= 0 or not geometria.origem.strip():
        raise ValueError("geometria da mestre deve possuir altura e origem")
    if geometria.quantidade_gomos < 1 or geometria.quantidade_gomos % 2 != 1:
        raise ValueError("a mestre deve possuir quantidade ímpar de gomos")
    if len(geometria.posicoes_varetas_cm) != geometria.quantidade_gomos - 1:
        raise ValueError("varetas da mestre devem ser iguais a gomos menos um")
    if len(geometria.posicoes_varetas_cm) % 2:
        raise ValueError("a mestre deve possuir quantidade par de varetas")
    if any(a >= b for a, b in zip(geometria.posicoes_varetas_cm, geometria.posicoes_varetas_cm[1:])):
        raise ValueError("posições das varetas devem ser estritamente crescentes")
    if geometria.posicoes_varetas_cm and (
        geometria.posicoes_varetas_cm[0] <= 0
        or geometria.posicoes_varetas_cm[-1] >= geometria.altura_cm
    ):
        raise ValueError("posição de vareta fora da peça mestre")


def _resultado_mestre(peca, mestre, geometria):
    return _montar_resultado(
        peca, mestre, peca.altura_cm, geometria.posicoes_varetas_cm, STATUS_ALINHADO, ()
    )


def _resultado_fora_vao(peca, geometria):
    return _montar_resultado(
        peca,
        False,
        geometria.altura_cm,
        geometria.posicoes_varetas_cm,
        STATUS_ALINHADO,
        ("altura aumentada para reproduzir integralmente a geometria da mestre",),
    )


def _resultado_dentro_vao(peca, geometria):
    compativeis = tuple(pos for pos in geometria.posicoes_varetas_cm if pos < peca.altura_cm)
    # A última vareta precisa ser par e receber passadores; remove-se a última
    # posição quando a quantidade compatível é ímpar.
    if len(compativeis) % 2:
        compativeis = compativeis[:-1]
    alertas = ["alinhamento integral inviável dentro da altura obrigatória"]
    status = STATUS_PARCIAL
    if not compativeis:
        alertas.append("nenhum par de varetas da mestre cabe na peça")
        status = STATUS_REVISAR
    ultimo_gomo = peca.altura_cm - compativeis[-1] if compativeis else peca.altura_cm
    if ultimo_gomo <= 0:
        alertas.append("último gomo não positivo")
        status = STATUS_REVISAR
    alertas.append("diferença visual do último gomo requer avaliação; não há limite percentual aprovado")
    return _montar_resultado(
        peca, False, peca.altura_cm, compativeis, status, tuple(alertas)
    )


def _montar_resultado(peca, mestre, altura_ajustada, posicoes, status, alertas):
    quantidade_varetas = len(posicoes)
    varetas_com_passadores = tuple(range(2, quantidade_varetas + 1, 2))
    ultimo_gomo = altura_ajustada - posicoes[-1] if posicoes else altura_ajustada
    if quantidade_varetas % 2 or (
        quantidade_varetas and varetas_com_passadores[-1] != quantidade_varetas
    ):
        status = STATUS_REVISAR
        alertas = (*alertas, "paridade mecânica ou última vareta incompatível")
    return RomanaTetoPecaResultado(
        identificador=peca.identificador,
        peca_mestre=mestre,
        altura_original_cm=peca.altura_cm,
        altura_ajustada_cm=altura_ajustada,
        diferenca_acrescentada_cm=altura_ajustada - peca.altura_cm,
        posicoes_varetas_cm=posicoes,
        quantidade_gomos=quantidade_varetas + 1,
        quantidade_varetas=quantidade_varetas,
        varetas_com_passadores=varetas_com_passadores,
        ultimo_gomo_cm=ultimo_gomo,
        status=status,
        alertas=alertas,
    )
