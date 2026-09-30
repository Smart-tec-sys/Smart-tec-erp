"""Simula??o t?cnica de Cortina sob medida.

N?o persiste dados e n?o calcula pre?o comercial nesta fase.
Implementa apenas regras t?cnicas j? confirmadas.
"""

from decimal import Decimal
from math import ceil
from typing import Literal, Optional

from pydantic import BaseModel, Field, conint


class CortinaSimulacaoInput(BaseModel):
    produto_id: int = Field(gt=0)

    largura: float = Field(gt=0, allow_inf_nan=False)
    altura: float = Field(gt=0, allow_inf_nan=False)
    quantidade: conint(strict=True, gt=0) = 1
    perfil_comercial: Literal["DECORADOR", "VAREJO", "CONSUMIDOR_FINAL"] = "VAREJO"
    desconto: float = Field(default=0, ge=0, allow_inf_nan=False)

    fator: float = Field(gt=0, allow_inf_nan=False)
    largura_tecido: float = Field(gt=0, allow_inf_nan=False)

    modelo_prega: str

    possui_forro: bool = False
    tipo_forro: Optional[str] = None

    trilho_linha: Optional[Literal["MINI", "MAX", "MASTER"]] = None
    trilho_modelo: Optional[str] = None

    rodizio_tipo: Optional[Literal["MINI", "MAX", "BOTAO"]] = None
    possui_gancho: bool = True

    valor_mao_obra_por_altura: float = Field(default=35.0, ge=0, allow_inf_nan=False)

    cabeca_cm: float = Field(default=10.0, ge=0, allow_inf_nan=False)
    barra_cm: float = Field(default=15.0, ge=0, allow_inf_nan=False)
    barra_dupla: bool = True

    usa_entretela: bool = True
    tipo_entretela: str = "TNT"

    fixacao_cortina: Literal["RODIZIO", "GANCHO"] = "RODIZIO"
    trilho_com_cordas: bool = False

    sistema_wave: Literal["PREGA_PRONTA", "BOTAO"] = "PREGA_PRONTA"
    espacamento_botao_cm: Literal[7, 10] = 10
    abertura_cortina: Literal[
        "LATERAL_ESQUERDA",
        "LATERAL_DIREITA",
        "CENTRAL",
        "DUAS_LATERAIS",
    ] = "LATERAL_ESQUERDA"


def _normalizar(valor) -> str:
    import unicodedata

    texto = "" if valor is None else str(valor)
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )

    return texto.strip().upper()


def _produto_cortina_fabricada(produto) -> bool:
    modelo = _normalizar(getattr(produto, "modelo_tecnico", None))
    grupo_tecnico = _normalizar(getattr(produto, "grupo_tecnico", None))
    tipo_produto = _normalizar(getattr(produto, "tipo_produto", None))

    if modelo != "CORTINA":
        return False

    # Classificacao atual das Cortinas finais.
    if grupo_tecnico == "TECIDOS_CORTINA":
        return True

    # Compatibilidade com cadastros historicos.
    return tipo_produto == "PRODUTO FABRICADO"


def _proximo_par(valor: int) -> int:
    return valor if valor % 2 == 0 else valor + 1


def _quantidade_wave_por_largura(
    largura_m: float,
    passo_m: float,
) -> int:
    return _proximo_par(ceil(largura_m / passo_m))


def simular_cortina(produto, entrada: CortinaSimulacaoInput) -> dict:
    """Executa a primeira etapa da simula??o t?cnica de Cortina."""

    if not _produto_cortina_fabricada(produto):
        raise ValueError(
            "Simula??o dispon?vel somente para produto fabricado de Cortina."
        )

    from app.services.orcamento_service import _preco_produto, _dinheiro

    preco = _preco_produto(produto, entrada.perfil_comercial)

    custo = next(
        (
            Decimal(str(getattr(produto, campo, 0) or 0))
            for campo in ("custo_final", "valor_custo")
            if Decimal(str(getattr(produto, campo, 0) or 0)) > 0
        ),
        None,
    )

    subtotal = _dinheiro(
        max(
            Decimal("0"),
            Decimal(str(entrada.quantidade)) * preco
            - Decimal(str(entrada.desconto)),
        )
    )

    avisos_preco = []

    if custo is None:
        avisos_preco.append(
            "Sem custo cadastrado: usado valor de venda conforme a regra comercial do backend."
        )

    if preco <= 0:
        avisos_preco.append(
            "Preço indisponível: cadastro sem custo ou valor de venda positivo."
        )

    desenvolvimento = entrada.largura * entrada.fator

    quantidade_alturas = ceil(
        desenvolvimento / entrada.largura_tecido
    )

    # Regra confirmada:
    # 1 rod?zio a cada 10 cm da largura da cortina.
    quantidade_rodizios = ceil(entrada.largura / 0.10)

    modelo_prega_norm = entrada.modelo_prega.strip().upper()

    if modelo_prega_norm == "WAVE":
        abertura_central = entrada.abertura_cortina == "CENTRAL"

        if entrada.sistema_wave == "BOTAO":
            passo_wave_m = entrada.espacamento_botao_cm / 100.0
        else:
            passo_wave_m = 0.12

        if abertura_central:
            largura_folha_m = entrada.largura / 2.0

            pontos_por_folha = _quantidade_wave_por_largura(
                largura_folha_m,
                passo_wave_m,
            )

            quantidade_pontos_wave = pontos_por_folha * 2
            folhas_wave = 2
        else:
            pontos_por_folha = _quantidade_wave_por_largura(
                entrada.largura,
                passo_wave_m,
            )

            quantidade_pontos_wave = pontos_por_folha
            folhas_wave = 1

        if entrada.sistema_wave == "BOTAO":
            botoes_wave = quantidade_pontos_wave
            rodizios_cortina = quantidade_pontos_wave
            ganchos_cortina = 0
        elif entrada.fixacao_cortina == "RODIZIO":
            botoes_wave = 0
            rodizios_cortina = quantidade_pontos_wave * 2
            ganchos_cortina = 0
        else:
            botoes_wave = 0
            rodizios_cortina = 0
            ganchos_cortina = quantidade_pontos_wave
    else:
        quantidade_pontos_wave = 0
        pontos_por_folha = 0
        folhas_wave = 0
        botoes_wave = 0

        quantidade_comum = ceil(entrada.largura / 0.10)

        if entrada.fixacao_cortina == "RODIZIO":
            rodizios_cortina = quantidade_comum
            ganchos_cortina = 0
        else:
            rodizios_cortina = 0
            ganchos_cortina = quantidade_comum

    rodizios_trilho = (
        ganchos_cortina
        if entrada.fixacao_cortina == "GANCHO" and entrada.trilho_com_cordas
        else 0
    )

    consumo_entretela_ml = (
        desenvolvimento * entrada.quantidade
        if entrada.usa_entretela
        else 0.0
    )

    trilho_ml = entrada.largura

    cabeca_m = entrada.cabeca_cm / 100.0
    barra_m = entrada.barra_cm / 100.0

    consumo_barra_m = barra_m * 2 if entrada.barra_dupla else barra_m

    consumo_por_altura_m = (
        entrada.altura
        + cabeca_m
        + consumo_barra_m
    )

    consumo_tecido_total_ml = (
        consumo_por_altura_m
        * quantidade_alturas
        * entrada.quantidade
    )

    return {
        "modelo": "CORTINA",
        "quantidade_pecas": entrada.quantidade,

        "largura_m": round(entrada.largura, 4),
        "altura_m": round(entrada.altura, 4),

        "modelo_prega": entrada.modelo_prega,
        "fator": round(entrada.fator, 4),

        "largura_tecido_m": round(entrada.largura_tecido, 4),

        "desenvolvimento_m": round(desenvolvimento, 4),
        "quantidade_alturas": quantidade_alturas,

        "mao_de_obra": {
            "quantidade_alturas": quantidade_alturas,
            "valor_por_altura": round(entrada.valor_mao_obra_por_altura, 2),
            "total": round(
                quantidade_alturas * entrada.valor_mao_obra_por_altura,
                2,
            ),
        },

        "forro": {
            "possui": entrada.possui_forro,
            "tipo": entrada.tipo_forro if entrada.possui_forro else None,
        },

        "trilho": {
            "linha": entrada.trilho_linha,
            "modelo": entrada.trilho_modelo,
            "quantidade_ml": round(trilho_ml, 4),
        },

        "fixacao": {
            "tipo": entrada.fixacao_cortina,
            "trilho_com_cordas": entrada.trilho_com_cordas,
        },

        "wave": {
            "aplicavel": modelo_prega_norm == "WAVE",
            "sistema": entrada.sistema_wave if modelo_prega_norm == "WAVE" else None,
            "abertura": entrada.abertura_cortina if modelo_prega_norm == "WAVE" else None,
            "quantidade_folhas": folhas_wave if modelo_prega_norm == "WAVE" else 0,
            "pontos_por_folha": pontos_por_folha if modelo_prega_norm == "WAVE" else 0,
            "quantidade_pontos_total": quantidade_pontos_wave if modelo_prega_norm == "WAVE" else 0,
            "espacamento_cm": (
                entrada.espacamento_botao_cm
                if modelo_prega_norm == "WAVE" and entrada.sistema_wave == "BOTAO"
                else (12 if modelo_prega_norm == "WAVE" else None)
            ),
            "quantidade_botoes": botoes_wave if modelo_prega_norm == "WAVE" else 0,
            "paridade_por_folha": "PAR" if modelo_prega_norm == "WAVE" else None,
        },


        "rodizios": {
            "tipo": entrada.rodizio_tipo,
            "quantidade_cortina_un": rodizios_cortina,
            "quantidade_trilho_un": rodizios_trilho,
            "quantidade_total_un": rodizios_cortina + rodizios_trilho,
            "regra": (
                (
                    f"Wave bot?o: 1 rod?zio de bot?o a cada {entrada.espacamento_botao_cm} cm"
                    if entrada.sistema_wave == "BOTAO"
                    else "Wave prega pronta: 2 rod?zios a cada 12 cm"
                )
                if modelo_prega_norm == "WAVE"
                else "Cortina comum: 1 rod?zio a cada 10 cm"
            ),
        },

        "ganchos": {
            "quantidade_cortina_un": ganchos_cortina,
            "regra": (
                (
                    "Wave bot?o: n?o usa gancho"
                    if entrada.sistema_wave == "BOTAO"
                    else "Wave prega pronta: 1 gancho a cada 12 cm"
                )
                if modelo_prega_norm == "WAVE"
                else "Cortina comum: 1 gancho a cada 10 cm"
            ),
        },

        "tecido": {
            "quantidade_alturas": quantidade_alturas,
            "cabeca_cm": round(entrada.cabeca_cm, 2),
            "barra_cm": round(entrada.barra_cm, 2),
            "barra_dupla": entrada.barra_dupla,
            "tipo_barra": (
                "LENCO_MORRENDO"
                if entrada.barra_cm == 0
                else ("DUPLA" if entrada.barra_dupla else "SIMPLES")
            ),
            "consumo_barra_m": round(consumo_barra_m, 4),
            "consumo_por_altura_m": round(consumo_por_altura_m, 4),
            "consumo_total_ml": round(consumo_tecido_total_ml, 4),
            "status_calculo": "CALCULADO",
        },

        "entretela": {
            "usa": entrada.usa_entretela,
            "tipo": entrada.tipo_entretela,
            "quantidade_ml": round(consumo_entretela_ml, 4),
            "status_calculo": "CALCULADO",
        },

        "custo_cadastrado": float(custo) if custo is not None else None,
        "preco_unitario": float(preco),
        "subtotal": float(subtotal),
        "preco_disponivel": preco > 0,
        "origem_preco": (
            "CUSTO_CADASTRADO"
            if custo is not None
            else "VALOR_VENDA_CADASTRADO"
        ),

        "avisos": avisos_preco,
    }
