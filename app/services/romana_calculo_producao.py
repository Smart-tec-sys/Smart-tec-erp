"""Motor geométrico puro para a Romana padrão manual.

Este módulo não consulta banco, não calcula preço e não estima materiais.
"""

from dataclasses import dataclass, field
from math import floor


STATUS_CALCULO = "CALCULO_GEOMETRICO_CONCLUIDO"
STATUS_PENDENTE = "PENDENTE_CONFIRMACAO"
TIPO_SUPORTADO = "ROMANA"
ACIONAMENTO_SUPORTADO = "MANUAL"

# Parâmetros mecânicos V2 centralizados para calibração física.
GOMO_PADRAO_MAXIMO_CM = 35.0
AJUSTE_PRIMEIRO_GOMO_MINIMO_CM = 2.0
AJUSTE_PRIMEIRO_GOMO_MAXIMO_CM = 5.0
REFERENCIA_BASE_INTEGRADA_CM = 2.5
DOBRA_CABECEIRA_CORTE_CM = 2.5
DOBRA_TECIDO_POR_VARETA_CM = 0.5
RESERVA_FITA_PLASTICA_CORTE_CM = 1.5
TOLERANCIA_FECHAMENTO_CM = 0.01
CATEGORIA_TAMPA_VARETA_ROMANA = "TAMPA_VARETA_ROMANA"
IDS_COMERCIAIS_TAMPA_VARETA_ROMANA = (292, 294, 920, 921, 922, 923, 2598)
TAMPAS_POR_VARETA = 2
CATEGORIA_GUIA_CORDA_ROMANA = "GUIA_CORDA_ROMANA"
IDS_COMERCIAIS_GUIA_CORDA_ROMANA = (667, 668)
CATEGORIA_ESPAGUETE_ROMANA_2_5MM = "ESPAGUETE_ROMANA_2_5MM"
ID_COMERCIAL_ESPAGUETE_ROMANA_2_5MM = 660
CATEGORIA_ESPAGUETE_BASE_ROMANA_3MM = "ESPAGUETE_BASE_ROMANA_3MM"
ID_COMERCIAL_ESPAGUETE_BASE_ROMANA_3MM = 661
RECUO_LARGURA_VARETA_CM = 1.5
RECUO_LARGURA_BASE_CM = 1.0
CATEGORIA_CORDA_ROMANA_1MM = "CORDA_ROMANA_1MM"
CORDA_ROMANA_1MM_PRODUTO = "PENDENTE"
EXTENSAO_CORDA_APOS_ULTIMA_VARETA_CM = 5.0
TIPO_CORRENTE_SEM_FIM_PRONTA = "SEM_FIM_PRONTA"
TIPO_CORRENTE_JUTA_BOLA10_PERSONALIZADA = "JUTA_BOLA10_PERSONALIZADA"
CATEGORIA_CORRENTE_JUTA_BOLA10_PERSONALIZADA = (
    "CORRENTE_JUTA_BOLA10_PERSONALIZADA"
)
TIPO_COMANDO_NORMAL = "NORMAL"
TIPO_COMANDO_REDUCAO = "REDUCAO"
CATEGORIA_COMANDO_NORMAL_ROMANA = "COMANDO_NORMAL_ROMANA"
CATEGORIA_COMANDO_REDUCAO_ROMANA = "COMANDO_REDUCAO_ROMANA"
ID_COMERCIAL_COMANDO_NORMAL_ROMANA = 273
ID_COMERCIAL_COMANDO_REDUCAO_ROMANA = 272
LARGURA_RECOMENDACAO_COMANDO_REDUCAO_CM = 220.0
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
    tipo_corrente: str = TIPO_CORRENTE_SEM_FIM_PRONTA
    medida_personalizada_m: float | None = None
    tipo_comando: str = TIPO_COMANDO_NORMAL


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
    categoria_tampa_vareta: str
    ids_comerciais_tampa_vareta: tuple[int, ...]
    quantidade_tampas_varetas: int
    tamanho_gomo_padrao_cm: float
    regra_primeiro_gomo_status: str
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
    quantidade_cavaletes: int | None
    varetas_com_passadores: tuple[int, ...]
    passadores_por_vareta: int | None
    quantidade_total_passadores: int | None
    categoria_guia_corda: str
    ids_comerciais_guia_corda: tuple[int, ...]
    quantidade_guias_corda: int | None
    largura_vareta_cm: float
    categoria_espaguete_romana_2_5mm: str
    id_comercial_espaguete_romana_2_5mm: int
    espaguete_romana_2_5_total_cm: float
    espaguete_romana_2_5_total_m: float
    largura_base_cm: float
    categoria_espaguete_base_romana_3mm: str
    id_comercial_espaguete_base_romana_3mm: int
    espaguete_base_romana_3mm_total_cm: float
    espaguete_base_romana_3mm_total_m: float
    categoria_corda_romana_1mm: str
    produto_comercial_corda_romana_1mm: str
    posicao_ultima_vareta_cm: float
    corda_por_linha_cm: float
    corda_total_cm: float | None
    corda_total_m: float | None
    tipo_corrente: str
    corrente_pronta_referencia_m: float
    corrente_pronta_referencia_status: str
    categoria_corrente_personalizada: str
    medida_personalizada_m: float | None
    medida_corrente_selecionada_m: float
    quantidade_correntes: int
    tipos_comando_permitidos: tuple[str, ...]
    tipo_comando: str
    comando_reducao_recomendado: bool
    categoria_comando_selecionado: str
    id_comercial_comando_selecionado: int
    categoria_comando_normal: str
    id_comercial_comando_normal: int
    categoria_comando_reducao: str
    id_comercial_comando_reducao: int
    quantidade_comando: int
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
    tipo_corrente = str(entrada.tipo_corrente or "").strip().upper()
    tipos_corrente_suportados = {
        TIPO_CORRENTE_SEM_FIM_PRONTA,
        TIPO_CORRENTE_JUTA_BOLA10_PERSONALIZADA,
    }
    if tipo_corrente not in tipos_corrente_suportados:
        raise ValueError("tipo_corrente deve ser SEM_FIM_PRONTA ou JUTA_BOLA10_PERSONALIZADA")

    corrente_pronta_referencia_m, corrente_pronta_referencia_status = (
        _corrente_pronta_referencia(geometria.altura_cm)
    )
    medida_personalizada_m = entrada.medida_personalizada_m
    if tipo_corrente == TIPO_CORRENTE_JUTA_BOLA10_PERSONALIZADA:
        if medida_personalizada_m is None or medida_personalizada_m <= 0:
            raise ValueError(
                "medida_personalizada_m deve ser informada e maior que zero "
                "para JUTA_BOLA10_PERSONALIZADA"
            )
        medida_corrente_selecionada_m = float(medida_personalizada_m)
    else:
        medida_personalizada_m = None
        medida_corrente_selecionada_m = corrente_pronta_referencia_m

    tipo_comando = str(entrada.tipo_comando or "").strip().upper()
    tipos_comando_permitidos = (TIPO_COMANDO_NORMAL, TIPO_COMANDO_REDUCAO)
    if tipo_comando not in tipos_comando_permitidos:
        raise ValueError("tipo_comando deve ser NORMAL ou REDUCAO")
    comando_reducao_recomendado = (
        geometria.largura_cm > LARGURA_RECOMENDACAO_COMANDO_REDUCAO_CM
    )
    if tipo_comando == TIPO_COMANDO_REDUCAO:
        categoria_comando_selecionado = CATEGORIA_COMANDO_REDUCAO_ROMANA
        id_comercial_comando_selecionado = ID_COMERCIAL_COMANDO_REDUCAO_ROMANA
    else:
        categoria_comando_selecionado = CATEGORIA_COMANDO_NORMAL_ROMANA
        id_comercial_comando_selecionado = ID_COMERCIAL_COMANDO_NORMAL_ROMANA
    quantidade_gomos, diferenca_primeiro_cm, gomo_restante_cm = (
        _selecionar_gomos_fabricacao_v2(geometria.altura_cm)
    )
    quantidade_varetas = quantidade_gomos - 1
    quantidade_intermediarios = quantidade_gomos - 2

    primeiro_gomo_pronto_cm = gomo_restante_cm + diferenca_primeiro_cm
    regra_primeiro_gomo_status = "FORMULA_GERAL_DISTRIBUICAO_IGUAL"
    gomos_intermediarios_prontos = (gomo_restante_cm,) * quantidade_intermediarios
    ultimo_gomo_pronto_cm = gomo_restante_cm
    ajuste_primeiro_gomo_cm = diferenca_primeiro_cm
    ajuste_ultimo_gomo_cm = 0.0
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

    quantidade_cavaletes = _quantidade_cavaletes_por_largura(geometria.largura_cm)
    varetas_com_passadores = tuple(range(2, quantidade_varetas + 1, 2))
    quantidade_total_passadores = (
        len(varetas_com_passadores) * quantidade_cavaletes
        if quantidade_cavaletes is not None
        else None
    )
    largura_vareta_cm = geometria.largura_cm - RECUO_LARGURA_VARETA_CM
    espaguete_romana_2_5_total_cm = (
        quantidade_varetas + 1
    ) * largura_vareta_cm
    largura_base_cm = geometria.largura_cm - RECUO_LARGURA_BASE_CM
    espaguete_base_romana_3mm_total_cm = largura_base_cm
    posicao_ultima_vareta_cm = posicoes_varetas[-1].posicao_cm
    corda_por_linha_cm = (
        posicao_ultima_vareta_cm + EXTENSAO_CORDA_APOS_ULTIMA_VARETA_CM
    )
    corda_total_cm = (
        corda_por_linha_cm * quantidade_cavaletes
        if quantidade_cavaletes is not None
        else None
    )

    alertas = []
    if ultimo_gomo_pronto_cm <= 0:
        alertas.append("Último gomo não positivo; revisar a distribuição.")
    if gomos_intermediarios_prontos:
        razao = ultimo_gomo_pronto_cm / gomo_restante_cm
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
    if quantidade_gomos % 2 != 1 or quantidade_varetas % 2:
        alertas.append("Paridade mecânica inválida: gomos devem ser ímpares e varetas pares.")
    if not varetas_com_passadores or varetas_com_passadores[-1] != quantidade_varetas:
        alertas.append("A última vareta deve ser par e receber passadores.")
    if any(vareta % 2 for vareta in varetas_com_passadores):
        alertas.append("Passadores só podem ser instalados em varetas pares.")
    if quantidade_cavaletes is None:
        alertas.append("Quantidade de cavaletes pendente para largura acima de 300 cm.")
    if gomo_restante_cm > GOMO_PADRAO_MAXIMO_CM:
        alertas.append("Tamanho dos gomos acima do máximo confortável aproximado de 35 cm.")
    if len((primeiro_gomo_corte_cm, *intermediarios_corte)) != quantidade_varetas:
        alertas.append("Quantidade de dobras de tecido difere da quantidade de varetas.")
    if abs(comprimento_por_trechos_cm - comprimento_total_tecido_cm) > TOLERANCIA_FECHAMENTO_CM:
        alertas.append("Marcação por trechos diverge da fórmula total do corte de tecido.")

    return RomanaFabricacaoResultado(
        altura_pronta_cm=geometria.altura_cm,
        quantidade_gomos=quantidade_gomos,
        quantidade_varetas=quantidade_varetas,
        categoria_tampa_vareta=CATEGORIA_TAMPA_VARETA_ROMANA,
        ids_comerciais_tampa_vareta=IDS_COMERCIAIS_TAMPA_VARETA_ROMANA,
        quantidade_tampas_varetas=calcular_quantidade_tampas_varetas(
            quantidade_varetas
        ),
        tamanho_gomo_padrao_cm=gomo_restante_cm,
        regra_primeiro_gomo_status=regra_primeiro_gomo_status,
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
        compensacao_aplicada_em="NENHUMA_DIVISAO_IGUAL",
        ajuste_primeiro_gomo_cm=ajuste_primeiro_gomo_cm,
        ajuste_ultimo_gomo_cm=ajuste_ultimo_gomo_cm,
        posicoes_varetas=tuple(posicoes_varetas),
        quantidade_cavaletes=quantidade_cavaletes,
        varetas_com_passadores=varetas_com_passadores,
        passadores_por_vareta=quantidade_cavaletes,
        quantidade_total_passadores=quantidade_total_passadores,
        categoria_guia_corda=CATEGORIA_GUIA_CORDA_ROMANA,
        ids_comerciais_guia_corda=IDS_COMERCIAIS_GUIA_CORDA_ROMANA,
        quantidade_guias_corda=quantidade_total_passadores,
        largura_vareta_cm=largura_vareta_cm,
        categoria_espaguete_romana_2_5mm=CATEGORIA_ESPAGUETE_ROMANA_2_5MM,
        id_comercial_espaguete_romana_2_5mm=ID_COMERCIAL_ESPAGUETE_ROMANA_2_5MM,
        espaguete_romana_2_5_total_cm=espaguete_romana_2_5_total_cm,
        espaguete_romana_2_5_total_m=espaguete_romana_2_5_total_cm / 100,
        largura_base_cm=largura_base_cm,
        categoria_espaguete_base_romana_3mm=CATEGORIA_ESPAGUETE_BASE_ROMANA_3MM,
        id_comercial_espaguete_base_romana_3mm=ID_COMERCIAL_ESPAGUETE_BASE_ROMANA_3MM,
        espaguete_base_romana_3mm_total_cm=espaguete_base_romana_3mm_total_cm,
        espaguete_base_romana_3mm_total_m=(
            espaguete_base_romana_3mm_total_cm / 100
        ),
        categoria_corda_romana_1mm=CATEGORIA_CORDA_ROMANA_1MM,
        produto_comercial_corda_romana_1mm=CORDA_ROMANA_1MM_PRODUTO,
        posicao_ultima_vareta_cm=posicao_ultima_vareta_cm,
        corda_por_linha_cm=corda_por_linha_cm,
        corda_total_cm=corda_total_cm,
        corda_total_m=corda_total_cm / 100 if corda_total_cm is not None else None,
        tipo_corrente=tipo_corrente,
        corrente_pronta_referencia_m=corrente_pronta_referencia_m,
        corrente_pronta_referencia_status=corrente_pronta_referencia_status,
        categoria_corrente_personalizada=(
            CATEGORIA_CORRENTE_JUTA_BOLA10_PERSONALIZADA
        ),
        medida_personalizada_m=medida_personalizada_m,
        medida_corrente_selecionada_m=medida_corrente_selecionada_m,
        quantidade_correntes=1,
        tipos_comando_permitidos=tipos_comando_permitidos,
        tipo_comando=tipo_comando,
        comando_reducao_recomendado=comando_reducao_recomendado,
        categoria_comando_selecionado=categoria_comando_selecionado,
        id_comercial_comando_selecionado=id_comercial_comando_selecionado,
        categoria_comando_normal=CATEGORIA_COMANDO_NORMAL_ROMANA,
        id_comercial_comando_normal=ID_COMERCIAL_COMANDO_NORMAL_ROMANA,
        categoria_comando_reducao=CATEGORIA_COMANDO_REDUCAO_ROMANA,
        id_comercial_comando_reducao=ID_COMERCIAL_COMANDO_REDUCAO_ROMANA,
        quantidade_comando=1,
        status_fabricacao="REVISAR_DISTRIBUICAO" if alertas else "DISTRIBUICAO_V2_CALCULADA",
        alertas=tuple(alertas),
    )


def _selecionar_gomos_fabricacao_v2(
    altura_pronta_cm: float,
) -> tuple[int, float, float]:
    """Inicia com 5 gomos e só aumenta N quando G ultrapassa 35 cm.

    A paridade é mecânica: gomos ímpares produzem varetas pares. Os
    passadores ficam nas varetas 2, 4, 6... e precisam alcançar naturalmente
    a última vareta. Não há limite inferior rígido para G: peças menores
    podem ter gomos menores. D começa em 2 cm e permanece parametrizado até 5.
    """
    quantidade_gomos = 5
    diferenca_primeiro = AJUSTE_PRIMEIRO_GOMO_MINIMO_CM
    gomo = (altura_pronta_cm - diferenca_primeiro) / quantidade_gomos
    while gomo > GOMO_PADRAO_MAXIMO_CM:
        quantidade_gomos += 2
        gomo = (altura_pronta_cm - diferenca_primeiro) / quantidade_gomos
    return quantidade_gomos, diferenca_primeiro, gomo


def calcular_quantidade_tampas_varetas(quantidade_varetas: int) -> int:
    """Calcula duas tampas por vareta, uma em cada extremidade."""
    if quantidade_varetas < 0:
        raise ValueError("quantidade_varetas não pode ser negativa")
    return quantidade_varetas * TAMPAS_POR_VARETA


def _corrente_pronta_referencia(altura_cm: float) -> tuple[float, str]:
    """Retorna referência comercial; a corrente personalizada pode substituí-la."""
    if altura_cm < 150:
        return 1.25, "REFERENCIA_PRONTA"
    if altura_cm <= 260:
        return 1.50, "REFERENCIA_PRONTA"
    return 1.75, "REFERENCIA_INICIAL_SUPERIOR_PROVISORIA"


def _quantidade_cavaletes_por_largura(largura_cm: float) -> int | None:
    if largura_cm <= 140:
        return 2
    if largura_cm <= 220:
        return 3
    if largura_cm <= 260:
        return 4
    if largura_cm <= 300:
        return 5
    return None
