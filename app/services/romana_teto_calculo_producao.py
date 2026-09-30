"""Motor de cálculo para Romana de Teto Modular.

Este módulo implementa o cálculo técnico da Romana de teto modular conforme
decisões da Fase 8E.5C. Não calcula preços, não consulta banco, não estima
materiais além do especificado.
"""

from dataclasses import dataclass, field
from math import ceil
from typing import Literal


STATUS_PRODUCAO_LIBERADA = "PRODUCAO_LIBERADA"
STATUS_REQUER_AVALIACAO_PROFISSIONAL = "REQUER_AVALIACAO_PROFISSIONAL"

ACIONAMENTO_MANUAL_BASTAO = "MANUAL_BASTAO"
ACIONAMENTO_MANUAL_CORRENTE = "MANUAL_CORRENTE"
ACIONAMENTO_MOTORIZADA = "MOTORIZADA"

ACIONAMENTOS_VALIDOS = (
    ACIONAMENTO_MANUAL_BASTAO,
    ACIONAMENTO_MANUAL_CORRENTE,
    ACIONAMENTO_MOTORIZADA,
)

GOMO_REFERENCIA_CM = 30.0
LARGURA_LIMITE_TRILHO_CENTRAL_M = 1.20
AREA_MINIMA_FATURAVEL_M2 = 1.50

BASTAO_OPCOES_VALIDAS = (1.00, 1.25, 1.50, 1.75, 2.00, 2.25)
BASTAO_DEFAULT = 1.50

CORRENTE_SEM_FIM_OPCOES_VALIDAS = (0.75, 1.00, 1.25, 1.50, 1.75, 2.00, 2.50, 3.00, 4.00)
CORRENTE_SEM_FIM_DEFAULT = 1.50

LADO_COMANDO_VALIDOS = ("ESQUERDA", "DIREITA")

REFERENCIA_COMANDO_TETO = "COMANDO_E_ANEL_BORRACHA_TETO"


@dataclass(frozen=True)
class RomanaTetoEntrada:
    largura_modulo_m: float
    comprimento_avanco_m: float
    quantidade_modulos: int
    acionamento: str
    lado_comando: str | None = None
    comprimento_bastao_m: float | None = None
    comprimento_corrente_sem_fim_m: float | None = None


@dataclass(frozen=True)
class RomanaTetoResultado:
    largura_modulo_m: float
    comprimento_avanco_m: float
    quantidade_modulos: int
    area_real_m2: float
    quantidade_gomos: int
    passo_gomo_cm: float
    quantidade_varetas: int
    comprimento_vareta_m: float
    quantidade_deslizantes: int
    tipo_trilho: str
    quantidade_trilhos_base: int
    comprimento_trilho_m: float
    largura_tecido_m: float
    comprimento_tecido_m: float
    area_tecido_m2: float
    avaliacao_trilho_central: bool
    terceiro_trilho_confirmado: bool | None
    acionamento: str
    motores_por_modulo: int
    quantidade_motores: int
    motor_modelo: str | None
    motor_torque_nm: str | None
    motor_tensao: str | None
    status_motor: str | None
    tipo_acionamento_manual: str | None
    referencia_mecanismo_manual: str | None
    quantidade_tampas_vareta: int
    quantidade_bases_conicas: int
    comprimento_base_conica_m: float
    quantidade_tampas_base: int
    quantidade_guias_corda: int
    quantidade_argolas: int
    quantidade_puxadores: int
    quantidade_espaguete_2_5: int
    metragem_total_espaguete_2_5: float
    quantidade_espaguete_3: int
    metragem_total_espaguete_3: float
    quantidade_bastoes: int
    comprimento_bastao_m: float | None
    # MANUAL_CORRENTE specific fields
    quantidade_trilhos: int | None = None
    lado_comando: str | None = None
    trilho_comando: str | None = None
    quantidade_carrinho_master: int | None = None
    quantidade_tampas_cabeceira_teto: int | None = None
    metragem_corrente_tracao_m: float | None = None
    quantidade_correntes_sem_fim: int | None = None
    comprimento_corrente_sem_fim_m: float | None = None
    opcoes_corrente_sem_fim_m: tuple[float, ...] | None = None
    quantidade_pendulos: int | None = None
    referencia_comando_teto: str | None = None
    terceiro_trilho: bool | None = None
    alertas: tuple[str, ...] = field(default_factory=tuple)
    status_calculo: str = STATUS_PRODUCAO_LIBERADA


def _validar_entrada(entrada: RomanaTetoEntrada) -> None:
    if entrada.largura_modulo_m <= 0:
        raise ValueError("largura_modulo_m deve ser maior que zero")
    if entrada.comprimento_avanco_m <= 0:
        raise ValueError("comprimento_avanco_m deve ser maior que zero")
    if entrada.quantidade_modulos <= 0:
        raise ValueError("quantidade_modulos deve ser maior que zero")
    if entrada.acionamento.upper() not in ACIONAMENTOS_VALIDOS:
        raise ValueError(
            f"acionamento deve ser um de: {', '.join(ACIONAMENTOS_VALIDOS)}"
        )
    if entrada.acionamento.upper() == ACIONAMENTO_MOTORIZADA and entrada.lado_comando:
        raise ValueError("lado_comando não se aplica a acionamento MOTORIZADA")
    if entrada.acionamento.upper() == ACIONAMENTO_MANUAL_BASTAO and entrada.comprimento_bastao_m is not None:
        if entrada.comprimento_bastao_m not in BASTAO_OPCOES_VALIDAS:
            raise ValueError(
                f"comprimento_bastao_m deve ser um de: {', '.join(str(x) for x in BASTAO_OPCOES_VALIDAS)}"
            )
    if entrada.acionamento.upper() == ACIONAMENTO_MANUAL_CORRENTE:
        if entrada.lado_comando is None:
            raise ValueError("lado_comando é obrigatório para acionamento MANUAL_CORRENTE")
        if entrada.lado_comando not in LADO_COMANDO_VALIDOS:
            raise ValueError(
                f"lado_comando deve ser um de: {', '.join(LADO_COMANDO_VALIDOS)}"
            )
        if entrada.comprimento_corrente_sem_fim_m is not None:
            if entrada.comprimento_corrente_sem_fim_m not in CORRENTE_SEM_FIM_OPCOES_VALIDAS:
                raise ValueError(
                    f"comprimento_corrente_sem_fim_m deve ser um de: {', '.join(str(x) for x in CORRENTE_SEM_FIM_OPCOES_VALIDAS)}"
                )


def _calcular_gomos(comprimento_avanco_m: float) -> tuple[int, float]:
    """Calcula quantidade de gomos e passo baseado no comprimento de avanço.

    Regra: aproximadamente 30 cm por gomo. Arredonda para cima para garantir
    cobertura completa do comprimento.
    """
    comprimento_cm = comprimento_avanco_m * 100
    quantidade_gomos = max(1, ceil(comprimento_cm / GOMO_REFERENCIA_CM))
    passo_gomo_cm = comprimento_cm / quantidade_gomos
    return quantidade_gomos, passo_gomo_cm


def _calcular_trilho_central(largura_modulo_m: float) -> tuple[bool, bool | None, tuple[str, ...]]:
    """Define regra de trilho central conforme decisão Smart-tec.

    Retorna: (avaliacao_trilho_central, terceiro_trilho_confirmado, alertas)
    """
    if largura_modulo_m <= LARGURA_LIMITE_TRILHO_CENTRAL_M:
        return False, False, ()

    alerta = (
        'Avaliar" necessidade e possibilidade estrutural de trilho "central.',
    )
    return True, None, alerta


def _calcular_motores(acionamento: str, quantidade_modulos: int) -> int:
    if acionamento.upper() == ACIONAMENTO_MOTORIZADA:
        return 1
    return 0


def _calcular_motor_campos(acionamento: str, quantidade_modulos: int) -> dict:
    """Calcula campos do motor para acionamento MOTORIZADA.

    Retorna dicionário com:
    - quantidade_motores: total de motores (quantidade_modulos * motores_por_modulo)
    - motor_modelo: None / pendente
    - motor_torque_nm: None / pendente
    - motor_tensao: None / pendente
    - status_motor: PENDENTE_ESPECIFICACAO
    """
    if acionamento.upper() == ACIONAMENTO_MOTORIZADA:
        motores_por_modulo = 1
        quantidade_motores = quantidade_modulos * motores_por_modulo
        return {
            "quantidade_motores": quantidade_motores,
            "motor_modelo": None,
            "motor_torque_nm": None,
            "motor_tensao": None,
            "status_motor": "PENDENTE_ESPECIFICACAO",
        }
    return {
        "quantidade_motores": 0,
        "motor_modelo": None,
        "motor_torque_nm": None,
        "motor_tensao": None,
        "status_motor": None,
    }


TIPO_TRILHO = "TRILHO_MAX_SIMPLES_COM_ABA"
REFERENCIA_MECANISMO_MANUAL_BASTAO = "ROLETE_DOUBLE_VISION_COM_GANCHO"
SOBRA_TECIDO_COMPRIMENTO = 1.12


def _calcular_deslizantes(quantidade_varetas: int) -> int:
    return quantidade_varetas * 2


def _calcular_tecido(largura_modulo_m: float, comprimento_avanco_m: float) -> tuple[float, float, float]:
    largura_tecido_m = largura_modulo_m
    comprimento_tecido_m = comprimento_avanco_m * SOBRA_TECIDO_COMPRIMENTO
    area_tecido_m2 = largura_tecido_m * comprimento_tecido_m
    return largura_tecido_m, comprimento_tecido_m, area_tecido_m2


def _calcular_acionamento_manual(acionamento: str) -> tuple[str | None, str | None]:
    if acionamento == ACIONAMENTO_MANUAL_BASTAO:
        return ACIONAMENTO_MANUAL_BASTAO, REFERENCIA_MECANISMO_MANUAL_BASTAO
    return None, None


def _calcular_tampas_vareta(quantidade_varetas: int) -> int:
    """2 tampas por vareta."""
    return quantidade_varetas * 2


def _calcular_bases_conicas() -> tuple[int, float]:
    """2 bases cônicas por módulo: uma no início, uma no fim.

    Retorna: (quantidade, comprimento_de_cada_base_em_metros)
    O comprimento de cada base é igual à largura do módulo.
    """
    return 2, 0.0  # O comprimento será preenchido na função principal


def _calcular_tampas_base() -> int:
    """4 tampas de base por módulo."""
    return 4


def _calcular_guias_corda(quantidade_varetas: int) -> int:
    """2 guias de corda por vareta."""
    return quantidade_varetas * 2


def _calcular_argolas(quantidade_varetas: int) -> int:
    """2 argolas por vareta + 2 na base móvel."""
    return (quantidade_varetas * 2) + 2


def _calcular_puxadores() -> int:
    """1 puxador por módulo."""
    return 1


def _calcular_espaguete_2_5(quantidade_varetas: int, largura_modulo_m: float) -> tuple[int, float]:
    """1 comprimento por vareta. Comprimento = largura do módulo.

    Retorna: (quantidade, metragem_total)
    """
    quantidade = quantidade_varetas
    metragem_total = quantidade_varetas * largura_modulo_m
    return quantidade, metragem_total


def _calcular_espaguete_3(largura_modulo_m: float) -> tuple[int, float]:
    """1 comprimento por base cônica (2 bases). Comprimento = largura do módulo.

    Retorna: (quantidade, metragem_total)
    """
    quantidade = 2
    metragem_total = 2 * largura_modulo_m
    return quantidade, metragem_total


def _calcular_bastao(acionamento: str, comprimento_bastao_m: float | None) -> tuple[int, float | None]:
    """Calcula bastão para acionamento MANUAL_BASTAO.

    Retorna: (quantidade, comprimento)
    """
    if acionamento == ACIONAMENTO_MANUAL_BASTAO:
        comprimento = comprimento_bastao_m if comprimento_bastao_m is not None else BASTAO_DEFAULT
        return 1, comprimento
    return 0, None


def _calcular_manual_corrente(
    comprimento_avanco_m: float,
    lado_comando: str,
    comprimento_corrente_sem_fim_m: float | None,
) -> dict:
    """Calcula componentes técnicos do acionamento MANUAL_CORRENTE.

    Retorna dicionário com todos os campos específicos do MANUAL_CORRENTE.
    """
    # Trilhos: sempre 2 trilhos laterais, sem terceiro trilho
    quantidade_trilhos = 2
    terceiro_trilho = False
    avaliacao_trilho_central = False

    # Lado de comando define qual trilho recebe a corrente sem fim e o pêndulo
    trilho_comando = "ESQUERDO" if lado_comando == "ESQUERDA" else "DIREITO"

    # Carrinho Master: 1 por trilho
    quantidade_carrinho_master = quantidade_trilhos

    # Tampas de cabeceira: 2 por módulo
    quantidade_tampas_cabeceira_teto = 2

    # Corrente de tração: ida e volta ao longo do comprimento/avanço
    metragem_corrente_tracao_m = comprimento_avanco_m * 2

    # Corrente sem fim Bola 10: 1 por módulo, no trilho do lado de comando
    quantidade_correntes_sem_fim = 1
    comprimento_corrente_sem_fim = (
        comprimento_corrente_sem_fim_m
        if comprimento_corrente_sem_fim_m is not None
        else CORRENTE_SEM_FIM_DEFAULT
    )

    # Pêndulo: 1 por corrente sem fim, associado ao mesmo lado de comando
    quantidade_pendulos = 1

    return {
        "quantidade_trilhos": quantidade_trilhos,
        "lado_comando": lado_comando,
        "trilho_comando": trilho_comando,
        "quantidade_carrinho_master": quantidade_carrinho_master,
        "quantidade_tampas_cabeceira_teto": quantidade_tampas_cabeceira_teto,
        "metragem_corrente_tracao_m": metragem_corrente_tracao_m,
        "quantidade_correntes_sem_fim": quantidade_correntes_sem_fim,
        "comprimento_corrente_sem_fim_m": comprimento_corrente_sem_fim,
        "opcoes_corrente_sem_fim_m": CORRENTE_SEM_FIM_OPCOES_VALIDAS,
        "quantidade_pendulos": quantidade_pendulos,
        "referencia_comando_teto": REFERENCIA_COMANDO_TETO,
        "terceiro_trilho": terceiro_trilho,
        "avaliacao_trilho_central": avaliacao_trilho_central,
    }


def calcular_romana_teto(entrada: RomanaTetoEntrada) -> RomanaTetoResultado:
    """Calcula o motor técnico da Romana de Teto Modular."""
    _validar_entrada(entrada)

    acionamento = entrada.acionamento.upper()
    largura_modulo_m = entrada.largura_modulo_m
    comprimento_avanco_m = entrada.comprimento_avanco_m
    quantidade_modulos = entrada.quantidade_modulos

    quantidade_gomos, passo_gomo_cm = _calcular_gomos(comprimento_avanco_m)
    quantidade_varetas = max(0, quantidade_gomos - 1)
    comprimento_vareta_m = largura_modulo_m

    quantidade_deslizantes = _calcular_deslizantes(quantidade_varetas)

    tipo_trilho = TIPO_TRILHO
    quantidade_trilhos_base = 2
    comprimento_trilho_m = comprimento_avanco_m

    largura_tecido_m, comprimento_tecido_m, area_tecido_m2 = _calcular_tecido(
        largura_modulo_m, comprimento_avanco_m
    )

    tipo_acionamento_manual, referencia_mecanismo_manual = _calcular_acionamento_manual(acionamento)

    avaliacao_trilho_central, terceiro_trilho_confirmado, alertas_trilho = _calcular_trilho_central(
        largura_modulo_m
    )

    motores_por_modulo = _calcular_motores(acionamento, quantidade_modulos)
    motor_campos = _calcular_motor_campos(acionamento, quantidade_modulos)

    area_real_m2 = largura_modulo_m * comprimento_avanco_m

    # Novos componentes - Fase 8E.5D.1
    quantidade_tampas_vareta = _calcular_tampas_vareta(quantidade_varetas)
    quantidade_bases_conicas, _ = _calcular_bases_conicas()
    comprimento_base_conica_m = largura_modulo_m
    quantidade_tampas_base = _calcular_tampas_base()
    quantidade_guias_corda = _calcular_guias_corda(quantidade_varetas)
    quantidade_argolas = _calcular_argolas(quantidade_varetas)
    quantidade_puxadores = _calcular_puxadores()
    quantidade_espaguete_2_5, metragem_total_espaguete_2_5 = _calcular_espaguete_2_5(
        quantidade_varetas, largura_modulo_m
    )
    quantidade_espaguete_3, metragem_total_espaguete_3 = _calcular_espaguete_3(largura_modulo_m)
    quantidade_bastoes, comprimento_bastao_m = _calcular_bastao(acionamento, entrada.comprimento_bastao_m)

    # MANUAL_CORRENTE specific calculations
    manual_corrente_data = {}
    if acionamento == ACIONAMENTO_MANUAL_CORRENTE:
        manual_corrente_data = _calcular_manual_corrente(
            comprimento_avanco_m,
            entrada.lado_comando,
            entrada.comprimento_corrente_sem_fim_m,
        )
        # Override trilho central evaluation for MANUAL_CORRENTE (always 2 trilhos, no central)
        avaliacao_trilho_central = manual_corrente_data["avaliacao_trilho_central"]
        terceiro_trilho_confirmado = manual_corrente_data["terceiro_trilho"]

    alertas = list(alertas_trilho)

    # Add motor specification alert for MOTORIZADA
    if acionamento == ACIONAMENTO_MOTORIZADA:
        alertas.append(
            'Motorização: modelo e torque do motor ainda requerem especificação técnica.'
        )

    if largura_modulo_m <= LARGURA_LIMITE_TRILHO_CENTRAL_M:
        status_calculo = STATUS_PRODUCAO_LIBERADA
    else:
        status_calculo = STATUS_REQUER_AVALIACAO_PROFISSIONAL

    return RomanaTetoResultado(
        largura_modulo_m=largura_modulo_m,
        comprimento_avanco_m=comprimento_avanco_m,
        quantidade_modulos=quantidade_modulos,
        area_real_m2=area_real_m2,
        quantidade_gomos=quantidade_gomos,
        passo_gomo_cm=passo_gomo_cm,
        quantidade_varetas=quantidade_varetas,
        comprimento_vareta_m=comprimento_vareta_m,
        quantidade_deslizantes=quantidade_deslizantes,
        tipo_trilho=tipo_trilho,
        quantidade_trilhos_base=quantidade_trilhos_base,
        comprimento_trilho_m=comprimento_trilho_m,
        largura_tecido_m=largura_tecido_m,
        comprimento_tecido_m=comprimento_tecido_m,
        area_tecido_m2=area_tecido_m2,
        avaliacao_trilho_central=avaliacao_trilho_central,
        terceiro_trilho_confirmado=terceiro_trilho_confirmado,
        acionamento=acionamento,
        motores_por_modulo=motores_por_modulo,
        quantidade_motores=motor_campos["quantidade_motores"],
        motor_modelo=motor_campos["motor_modelo"],
        motor_torque_nm=motor_campos["motor_torque_nm"],
        motor_tensao=motor_campos["motor_tensao"],
        status_motor=motor_campos["status_motor"],
        tipo_acionamento_manual=tipo_acionamento_manual,
        referencia_mecanismo_manual=referencia_mecanismo_manual,
        quantidade_tampas_vareta=quantidade_tampas_vareta,
        quantidade_bases_conicas=quantidade_bases_conicas,
        comprimento_base_conica_m=comprimento_base_conica_m,
        quantidade_tampas_base=quantidade_tampas_base,
        quantidade_guias_corda=quantidade_guias_corda,
        quantidade_argolas=quantidade_argolas,
        quantidade_puxadores=quantidade_puxadores,
        quantidade_espaguete_2_5=quantidade_espaguete_2_5,
        metragem_total_espaguete_2_5=metragem_total_espaguete_2_5,
        quantidade_espaguete_3=quantidade_espaguete_3,
        metragem_total_espaguete_3=metragem_total_espaguete_3,
        quantidade_bastoes=quantidade_bastoes,
        comprimento_bastao_m=comprimento_bastao_m,
        # MANUAL_CORRENTE specific fields
        quantidade_trilhos=manual_corrente_data.get("quantidade_trilhos"),
        lado_comando=manual_corrente_data.get("lado_comando"),
        trilho_comando=manual_corrente_data.get("trilho_comando"),
        quantidade_carrinho_master=manual_corrente_data.get("quantidade_carrinho_master"),
        quantidade_tampas_cabeceira_teto=manual_corrente_data.get("quantidade_tampas_cabeceira_teto"),
        metragem_corrente_tracao_m=manual_corrente_data.get("metragem_corrente_tracao_m"),
        quantidade_correntes_sem_fim=manual_corrente_data.get("quantidade_correntes_sem_fim"),
        comprimento_corrente_sem_fim_m=manual_corrente_data.get("comprimento_corrente_sem_fim_m"),
        opcoes_corrente_sem_fim_m=manual_corrente_data.get("opcoes_corrente_sem_fim_m"),
        quantidade_pendulos=manual_corrente_data.get("quantidade_pendulos"),
        referencia_comando_teto=manual_corrente_data.get("referencia_comando_teto"),
        terceiro_trilho=manual_corrente_data.get("terceiro_trilho"),
        alertas=tuple(alertas),
        status_calculo=status_calculo,
    )


def calcular_area_faturavel(area_real_m2: float) -> float:
    """Regra comercial central da Fase 8F.1: área mínima faturável."""
    return max(area_real_m2, AREA_MINIMA_FATURAVEL_M2)