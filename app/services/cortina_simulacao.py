"""Composição técnica e preço da Cortina montada; não persiste dados."""

from decimal import Decimal
from math import ceil
from typing import Literal, Optional

from pydantic import BaseModel, Field, conint


class CortinaComponenteInput(BaseModel):
    produto_id: int = Field(gt=0)
    quantidade: float = Field(ge=0, allow_inf_nan=False)


class CortinaSimulacaoInput(BaseModel):
    produto_id: Optional[int] = Field(default=None, gt=0)  # compatibilidade de contrato; nunca base de preço
    componentes: Optional[list[CortinaComponenteInput]] = None
    tecido_produto_id: Optional[int] = Field(default=None, gt=0)
    forro_produto_id: Optional[int] = Field(default=None, gt=0)
    largura_forro: Optional[float] = Field(default=None, gt=0, allow_inf_nan=False)
    trilho_produto_id: Optional[int] = Field(default=None, gt=0)
    rodizio_produto_id: Optional[int] = Field(default=None, gt=0)
    gancho_produto_id: Optional[int] = Field(default=None, gt=0)
    botao_produto_id: Optional[int] = Field(default=None, gt=0)
    entretela_produto_id: Optional[int] = Field(default=None, gt=0)

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


def componente_cortina_elegivel(produto):
    """Catálogo exclusivo; classificação de cortina não sobrepõe indícios de persiana."""
    import re
    if _normalizar(getattr(produto, 'grupo_tecnico', None)) != 'COMPONENTES_CORTINAS':
        return False
    if _normalizar(getattr(produto, 'situacao', None)) != 'ATIVO':
        return False
    texto = ' '.join(_normalizar(getattr(produto, campo, None)) for campo in
                     ('nome', 'grupo_produto', 'modelo_tecnico', 'familia_tecnica', 'tipo_cortina_persiana'))
    return not re.search(r'PERSIANA|ROLO|ROMANA|DOUBLE[ _-]?VISION|\bDV\b|\bTUBOS?\b|\bCOMANDOS?\b|\bBASES?\b', texto)


def _proximo_par(valor: int) -> int:
    return valor if valor % 2 == 0 else valor + 1


def _quantidade_wave_por_largura(
    largura_m: float,
    passo_m: float,
) -> int:
    return _proximo_par(ceil(largura_m / passo_m))


def simular_cortina(produto, entrada: CortinaSimulacaoInput, componentes=None) -> dict:
    """Consumos e custos por peça; produto é o tecido real, nunca a cortina final."""
    from types import SimpleNamespace
    from app.services.composicao_comercial import _preco_produto, _dinheiro
    if _normalizar(getattr(produto, "modelo_tecnico", None)) == "CORTINA":
        raise ValueError("Produto final histórico não pode ser usado como tecido/base de custo.")
    componentes = componentes or {}
    avisos_preco = []
    pendencias = []
    composicao = []

    def adicionar(papel, quantidade, componente):
        if quantidade <= 0:
            return Decimal('0')
        if componente is None:
            pendencias.append(papel)
            avisos_preco.append(f'{papel}: custo pendente; nenhum produto real vinculado.')
            return Decimal('0')
        custo = next((Decimal(str(getattr(componente, c, 0) or 0))
                      for c in ('custo_final', 'valor_custo')
                      if Decimal(str(getattr(componente, c, 0) or 0)) > 0), None)
        origem = 'CUSTO_CADASTRADO'
        if custo is None:
            custo = Decimal(str(getattr(componente, 'valor_venda', 0) or 0))
            origem = 'VALOR_VENDA_CADASTRADO'
            avisos_preco.append(f'{papel}: usado fallback de valor de venda cadastrado.')
        if custo <= 0:
            pendencias.append(papel)
            avisos_preco.append(f'{papel}: produto sem custo ou fallback positivo.')
        total = Decimal(str(quantidade)) * custo
        composicao.append(dict(componente=papel, produto_id=componente.id,
                               quantidade=round(quantidade, 4), custo_unitario=float(custo),
                               custo_total=float(_dinheiro(total)), origem_custo=origem))
        return total

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

    # O consumo técnico acima inclui todas as peças; o custo comercial é unitário.
    consumo_tecido_unitario = consumo_tecido_total_ml / entrada.quantidade
    custo_tecido = adicionar('tecido', consumo_tecido_unitario, produto)
    forro = componentes.get('forro') if entrada.possui_forro else None
    largura_forro = entrada.largura_forro or getattr(forro, 'largura', None)
    consumo_forro = 0.0
    if entrada.possui_forro:
        if largura_forro and float(largura_forro) > 0:
            consumo_forro = consumo_por_altura_m * ceil(entrada.largura * 2 / float(largura_forro))
        else:
            pendencias.append('largura_forro')
            avisos_preco.append('Forro: informe a largura real do produto para calcular o consumo.')
        if forro is None:
            pendencias.append('forro')
            avisos_preco.append('Forro: selecione um produto real do catálogo.')
    custo_forro = adicionar('forro', consumo_forro, forro)
    custo_componentes = Decimal('0')
    if entrada.componentes is not None:
        # Lista explícita: nenhuma associação automática a prega/Wave e nenhum custo legado duplicado.
        livres = componentes.get('livres', [])
        if len(livres) != len(entrada.componentes):
            raise ValueError('Componentes da cortina: vínculos reais incompletos.')
        for linha, componente in zip(entrada.componentes, livres):
            if not componente_cortina_elegivel(componente):
                raise ValueError('Selecione somente componentes ativos de cortina.')
            custo_componentes += adicionar(componente.nome, linha.quantidade, componente)
    else:
        # Compatibilidade com documentos anteriores, que já armazenavam IDs explícitos por papel.
        custo_trilho = adicionar('trilho', trilho_ml, componentes.get('trilho'))
        custo_rodizios = adicionar('rodizios', rodizios_cortina + rodizios_trilho, componentes.get('rodizio'))
        custo_ganchos = adicionar('ganchos', ganchos_cortina, componentes.get('gancho'))
        custo_botoes = adicionar('botoes', botoes_wave, componentes.get('botao'))
        custo_entretela = adicionar('entretela', consumo_entretela_ml / entrada.quantidade, componentes.get('entretela'))
        custo_componentes = custo_trilho + custo_rodizios + custo_ganchos + custo_botoes + custo_entretela
    alturas_costureira = ceil(Decimal(str(entrada.altura)) / Decimal('1.50'))
    custo_mao_obra = Decimal(alturas_costureira) * Decimal('35.00')
    composicao.append(dict(componente='mao_de_obra', produto_id=None,
                           quantidade=alturas_costureira, custo_unitario=35.0, custo_total=float(custo_mao_obra)))
    custo_total = _dinheiro(custo_tecido + custo_forro + custo_componentes + custo_mao_obra)
    preco = _preco_produto(SimpleNamespace(custo_final=custo_total, valor_custo=0, valor_venda=0), entrada.perfil_comercial)
    subtotal = _dinheiro(max(Decimal('0'), Decimal(entrada.quantidade) * preco - Decimal(str(entrada.desconto))))
    if pendencias:
        avisos_preco.append('Preço parcial: inclui somente custos vinculados e mão de obra; revise as pendências da composição.')

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
            "quantidade_alturas": alturas_costureira,
            "valor_por_altura": 35.0,
            "total": float(custo_mao_obra),
        },
        "forro": {
            "possui": entrada.possui_forro, "tipo": entrada.tipo_forro,
            "produto_id": getattr(forro, 'id', None), "fator": 2,
            "consumo_unitario_ml": round(consumo_forro, 4),
            "consumo_total_ml": round(consumo_forro * entrada.quantidade, 4),
            "custo_total": float(_dinheiro(custo_forro)),
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

        "custo_cadastrado": None,
        "custo_total": float(custo_total),
        "composicao": composicao,
        "custo_completo": not pendencias,
        "pendencias_custo": pendencias,
        "preco_unitario": float(preco),
        "subtotal": float(subtotal),
        "preco_disponivel": preco > 0 and 'tecido' not in pendencias and
                            (not entrada.possui_forro or (forro is not None and consumo_forro > 0 and 'forro' not in pendencias)),
        "origem_preco": "COMPOSICAO_TECNICA" if not pendencias else "COMPOSICAO_TECNICA_PARCIAL",

        "avisos": avisos_preco,
    }


def simular_cortina_catalogo(db, entrada, empresa_id):
    """Resolve exclusivamente IDs explícitos no tenant, sem inferir componentes por nome."""
    from app.models.produto import ProdutoDB
    def obter(produto_id, papel):
        if produto_id is None:
            return None
        produto = db.query(ProdutoDB).filter(ProdutoDB.id == produto_id, ProdutoDB.empresa_id == empresa_id).first()
        if produto is None:
            raise ValueError(f'{papel}: produto não encontrado para a empresa ativa.')
        return produto
    tecido = obter(entrada.tecido_produto_id, 'tecido')
    if tecido is None or _produto_cortina_fabricada(tecido):
        raise ValueError('Selecione o tecido real da Cortina; produto final histórico não é base de preço.')
    papeis = ('forro',) if entrada.componentes is not None else ('forro', 'trilho', 'rodizio', 'gancho', 'botao', 'entretela')
    componentes = {papel: obter(getattr(entrada, f'{papel}_produto_id'), papel) for papel in papeis}
    if entrada.componentes is not None:
        componentes['livres'] = [obter(linha.produto_id, 'componente') for linha in entrada.componentes]
        if any(not componente_cortina_elegivel(p) for p in componentes['livres']):
            raise ValueError('Selecione somente componentes ativos de cortina.')
    if entrada.possui_forro and componentes['forro'] is not None and _normalizar(getattr(componentes['forro'], 'modelo_tecnico', None)) == 'CORTINA':
        raise ValueError('Forro: selecione o tecido real, não um produto final histórico.')
    return simular_cortina(tecido, entrada, componentes)


def entrada_cortina_item(item, perfil):
    config = (item.dados_tecnicos or {}).get('cortina') or {}
    campos = {
        'componentes': 'componentes', 'tecidoProdutoId': 'tecido_produto_id', 'forroProdutoId': 'forro_produto_id', 'larguraForro': 'largura_forro',
        'trilhoProdutoId': 'trilho_produto_id', 'rodizioProdutoId': 'rodizio_produto_id',
        'ganchoProdutoId': 'gancho_produto_id', 'botaoProdutoId': 'botao_produto_id', 'entretelaProdutoId': 'entretela_produto_id',
        'fator': 'fator', 'larguraTecido': 'largura_tecido', 'modeloPrega': 'modelo_prega',
        'possuiForro': 'possui_forro', 'tipoForro': 'tipo_forro', 'trilhoLinha': 'trilho_linha',
        'trilhoModelo': 'trilho_modelo', 'rodizioTipo': 'rodizio_tipo', 'cabecaCm': 'cabeca_cm',
        'barraCm': 'barra_cm', 'barraDupla': 'barra_dupla', 'usaEntretela': 'usa_entretela',
        'tipoEntretela': 'tipo_entretela', 'fixacaoCortina': 'fixacao_cortina', 'trilhoComCordas': 'trilho_com_cordas',
        'sistemaWave': 'sistema_wave', 'espacamentoBotaoCm': 'espacamento_botao_cm', 'aberturaCortina': 'abertura_cortina'}
    if 'componentes' in config:
        config = {**config, 'componentes': [linha for linha in config['componentes'] if linha.get('produto_id')]}
    if not float(item.quantidade).is_integer():
        raise ValueError('Cortina exige quantidade inteira de peças.')
    return CortinaSimulacaoInput(largura=item.largura, altura=item.altura, quantidade=int(item.quantidade),
                                perfil_comercial=perfil, desconto=item.desconto,
                                **{destino: config[origem] for origem, destino in campos.items() if origem in config})
