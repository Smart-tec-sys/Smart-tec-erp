"""Receitas configurÃ¡veis por empresa; catÃ¡logo/fornecedor nÃ£o vivem no motor."""
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
import re
import unicodedata

from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.empresa import EmpresaDB
from app.models.equivalencia_tecnica import EmpresaEquivalenciaTecnicaDB
from app.models.produto import ProdutoDB
from app.schemas.rolo_receita import FaixaTuboRolo, InsumoReceitaRolo, ReceitaRolo
from app.services.area_faturavel import calcular_area_faturavel
from app.services.composicao_comercial import MULTIPLICADORES, _dinheiro, _preco_produto, _custo_referencia_comercial
from app.services.motor_calculo_produtos import calcular_produto_sob_medida
from app.services.rolo_simulacao import (
    RoloSimulacaoInput, _extrair_componentes_rolo, _tipo_rolo, simular_rolo,
)
from app.technical.rules.rolo import (
    AcionamentoPermitido, MotorObrigatorioErro, TuboRoloDiametro, TuboRoloSelecao,
    selecionar_tubo_rolo,
)


COMPONENTES = {
    "fita_tubo": "ML", "base": "ML", "fita_base": "ML", "espaguete_base": "ML",
    "corrente": "ML", "emenda_corrente": "UN", "tampa_base": "UN",
}
CORES_SCREEN_IMPORTADO = {"BRANCO", "BEGE", "CINZA", "PRETO"}
EMTECO_ROLO_REFERENCES = (
    "Tabela-referencial-para-persianas-2022.pdf, p. 1",
    "Tabelas-gerais-ATUALIZADA.pptx_21-08-2024.pdf, pp. 1-3",
)
EMTECO_ROLO_PROFILES = (
    {"perfil": "1740", "diametro": 43, "torque": 6, "tipo_motor": "PLUG",
     "familia": "628/1014NM", "largura": 2.50, "altura": 4.00, "peso": 17.0,
     "peso_barra": 1.00, "altura_operacao": 5.0, "kits": {"KIT 43 IMP", "KIT 43 BR"}},
    {"perfil": "3268", "diametro": 53, "torque": 6, "tipo_motor": "PLUG",
     "familia": "628/1014NM", "largura": 2.80, "altura": 5.00, "peso": 12.0,
     "peso_barra": 1.12, "altura_operacao": 7.0, "kits": {"KIT 53 IMP", "KIT 53 BR"}},
    {"perfil": "3268", "diametro": 53, "torque": 6, "tipo_motor": "ELETRONICO",
     "familia": "628/1014NM", "largura": 2.80, "altura": 6.00, "peso": 12.0,
     "peso_barra": 1.12, "altura_operacao": 17.0, "kits": {"KIT 53 IMP", "KIT 53 BR"}},
    {"perfil": "3810", "diametro": 70, "torque": 6, "tipo_motor": "PLUG",
     "familia": "628/1014NM", "largura": 3.20, "altura": 6.00, "peso": 11.0,
     "peso_barra": 1.28, "altura_operacao": 8.0, "kits": {"KIT KR 70"}},
    {"perfil": "3810", "diametro": 70, "torque": 20, "tipo_motor": "PLUG",
     "familia": "2017/5012NM", "largura": 4.00, "altura": 6.50, "peso": 36.0,
     "peso_barra": 1.60, "altura_operacao": 10.0, "kits": {"KIT KR 70"}},
)
def _normalizar_cor(valor):
    return ''.join(c for c in unicodedata.normalize('NFKD', valor or '')
                   if not unicodedata.combining(c)).strip().upper()


def _equivalencias_tecnicas(db, empresa_id, funcao):
    criterio_funcao = (
        EmpresaEquivalenciaTecnicaDB.funcao_tecnica == funcao
        if isinstance(funcao, str)
        else EmpresaEquivalenciaTecnicaDB.funcao_tecnica.in_(funcao)
    )
    return db.query(EmpresaEquivalenciaTecnicaDB).filter(
        EmpresaEquivalenciaTecnicaDB.empresa_id == empresa_id,
        criterio_funcao,
        EmpresaEquivalenciaTecnicaDB.ativo.is_(True),
    ).order_by(
        EmpresaEquivalenciaTecnicaDB.prioridade,
        EmpresaEquivalenciaTecnicaDB.id,
    ).all()


def _custos_positivos_produto(produto):
    custos = []
    for valor in (produto.custo_final, produto.valor_custo):
        if valor is None:
            continue
        try:
            custo = Decimal(str(valor))
        except (InvalidOperation, TypeError, ValueError):
            continue
        if custo.is_finite() and custo > 0:
            custos.append(custo)
    return custos


def _produto_equivalencia(db, empresa_id, equivalencia, unidade=None, exigir_custo=True):
    produto = db.query(ProdutoDB).filter(
        ProdutoDB.id == equivalencia.produto_id,
        ProdutoDB.empresa_id == empresa_id,
    ).one_or_none()
    if (
        produto is None
        or str(produto.situacao or "").strip().casefold() != "ativo"
        or str(produto.tipo_produto or "").strip().casefold() not in {"componente", "insumo"}
        or (
            unidade
            and _unidade_tecnica_produto(produto)
            != {"M": "ML", "M2": "M2"}.get(unidade, unidade)
        )
    ):
        return None
    custos = _custos_positivos_produto(produto)
    if exigir_custo and not custos:
        return None
    return produto, (custos[0] if custos else None)


def _configuracao_equivalencia(equivalencia):
    configuracao = equivalencia.configuracoes_locais
    return configuracao if isinstance(configuracao, dict) else {}


def _valores_textuais(configuracao, chave, normalizar=False):
    valores = configuracao.get(chave)
    if not isinstance(valores, (list, tuple, set)):
        return set()
    if normalizar:
        return {_normalizar_cor(str(valor)) for valor in valores if isinstance(valor, str)}
    return {str(valor).strip().upper() for valor in valores if isinstance(valor, str)}


def _fabricante_emteco(configuracao):
    return _normalizar_cor(str(configuracao.get("fabricante") or "")) == "EMTECO"


def _fabricante(configuracao):
    return _normalizar_cor(str(configuracao.get("fabricante") or ""))


def _motor_vinculado(configuracao, motor_id):
    motores = configuracao.get("motores_compativeis")
    return isinstance(motores, list) and any(
        isinstance(item, int) and not isinstance(item, bool) and item == motor_id
        for item in motores
    )


def _torque_compativel_rolo(torque, diametro):
    return (torque == Decimal("0.5") and diametro == 38) or torque >= 6


def _perfil_emteco_motor(configuracao, largura, altura, diametro=None):
    try:
        torque = Decimal(str(configuracao.get("torque_nm")))
    except (InvalidOperation, TypeError, ValueError):
        return None
    tipo_motor = _normalizar_cor(str(configuracao.get("tipo_motor") or ""))
    familia = _normalizar_cor(str(configuracao.get("familia_instalacao") or ""))
    tecnologia = str(configuracao.get("tecnologia") or "").strip().upper()
    if tecnologia not in {"RF", "WIFI_RF", "CONTATO_SECO"}:
        return None
    area = Decimal(str(largura)) * Decimal(str(altura))
    for perfil in EMTECO_ROLO_PROFILES:
        if (
            torque == Decimal(str(perfil["torque"]))
            and (diametro is None or perfil["diametro"] == diametro)
            and tipo_motor == perfil["tipo_motor"]
            and familia == perfil["familia"]
            and largura <= perfil["largura"]
            and altura <= min(perfil["altura"], perfil["altura_operacao"])
            and area * Decimal("0.5") + Decimal(str(perfil["peso_barra"]))
            <= Decimal(str(perfil["peso"]))
        ):
            return perfil
    return None


def _perfil_motor_configurado(configuracao, largura, altura):
    dados = configuracao.get("perfil_rolo")
    if not isinstance(dados, dict):
        return None
    try:
        torque = Decimal(str(configuracao.get("torque_nm")))
        diametro_decimal = Decimal(str(dados.get("diametro_mm")))
        limite_largura = Decimal(str(dados.get("largura_max_m")))
        limite_altura = Decimal(str(dados.get("altura_max_m")))
        capacidade, peso_barra, peso_area = (
            Decimal(str(dados[chave]))
            if dados.get(chave) is not None else None
            for chave in (
                "capacidade_kg",
                "peso_barra_kg",
                "peso_estimado_kg_m2",
            )
        )

        carga = (
            Decimal(str(largura)) * Decimal(str(altura))
            * peso_area + peso_barra
            if peso_area is not None and peso_barra is not None
            else None
        )

        carga_pendente = carga is None or capacidade is None

        if (
            carga_pendente
            and dados.get("permitir_orcamento_sem_carga") is not True
        ):
            return None
    except (InvalidOperation, TypeError, ValueError):
        return None
    tecnologia = str(configuracao.get("tecnologia") or "").strip().upper()
    familia = _normalizar_cor(str(dados.get("familia_instalacao") or ""))
    perfil_tubo = _normalizar_cor(str(dados.get("perfil_tubo") or ""))
    origem = dados.get("origem")
    codigos_kit = dados.get("codigos_kit")
    if not isinstance(codigos_kit, list):
        return None
    kits = {
        _normalizar_cor(codigo) for codigo in codigos_kit
        if isinstance(codigo, str) and codigo.strip()
    }
    numeros = (
        torque, diametro_decimal, limite_largura, limite_altura,
        capacidade, peso_barra, peso_area, carga,
    )
    if (
        not all(numero.is_finite() for numero in numeros if numero is not None)
        or diametro_decimal != diametro_decimal.to_integral_value()
        or torque <= 0 or diametro_decimal <= 0
        or limite_largura <= 0 or limite_altura <= 0
        or (capacidade is not None and capacidade <= 0)
        or (peso_barra is not None and peso_barra < 0)
        or (peso_area is not None and peso_area < 0)
        or tecnologia not in {"RF", "WIFI_RF", "CONTATO_SECO"}
        or not familia or not perfil_tubo or not kits
        or not isinstance(origem, str) or len(origem.strip()) < 5
        or diametro_decimal not in {32, 38, 41, 43, 53, 56, 70}
        or Decimal(str(largura)) > limite_largura
        or Decimal(str(altura)) > limite_altura
        or (carga is not None and capacidade is not None and carga > capacidade)
        or not _torque_compativel_rolo(torque, int(diametro_decimal))
    ):
        return None
    torques_permitidos = dados.get("torques_permitidos_nm")

    if torques_permitidos is not None:
        if not isinstance(torques_permitidos, list):
            return None

        try:
            permitidos = {
                Decimal(str(valor))
                for valor in torques_permitidos
            }
        except (InvalidOperation, TypeError, ValueError):
            return None

        if not permitidos or any(
            not valor.is_finite() or valor <= 0
            for valor in permitidos
        ):
            return None

        if torque not in permitidos:
            return None

    diametro = int(diametro_decimal)
    return {
        "perfil": perfil_tubo,
        "diametro": diametro,
        "torque": float(torque),
        "familia": familia,
        "largura": float(limite_largura),
        "altura": float(limite_altura),
        "peso": float(capacidade) if capacidade is not None else None,
        "peso_barra": float(peso_barra) if peso_barra is not None else None,
        "peso_estimado_kg_m2": float(peso_area) if peso_area is not None else None,
        "carga_pendente": carga_pendente,
        "altura_operacao": float(limite_altura),
        "kits": kits,
        "origem": origem.strip(),
    }


def _perfil_motor_rolo(configuracao, largura, altura, diametro=None):
    perfis = configuracao.get("perfis_rolo")
    if perfis is not None:
        if not isinstance(perfis, list):
            return None

        compativeis = []

        for dados in perfis:
            if not isinstance(dados, dict):
                continue

            perfil = _perfil_motor_configurado(
                {**configuracao, "perfil_rolo": dados},
                largura,
                altura,
            )

            if perfil is not None and (
                diametro is None
                or perfil["diametro"] == diametro
            ):
                compativeis.append(
                    {**perfil, "explicito": True}
                )

        return compativeis[0] if len(compativeis) == 1 else None

    fabricante = _fabricante(configuracao)
    if fabricante == "EMTECO" and "perfil_rolo" not in configuracao:
        perfil = _perfil_emteco_motor(configuracao, largura, altura, diametro)
        if perfil is not None:
            perfil = {
                **perfil, "peso_estimado_kg_m2": 0.5, "explicito": False,
                "origem": "; ".join(EMTECO_ROLO_REFERENCES),
            }
            return perfil
    perfil = _perfil_motor_configurado(configuracao, largura, altura)
    if perfil is not None and (diametro is None or perfil["diametro"] == diametro):
        return {**perfil, "explicito": True}
    return None


def _unidade_tecnica_produto(produto):
    unidade = str(produto.unidade_venda or "").strip().upper()
    return {"M": "ML", "ML": "ML", "M²": "M2", "M2": "M2", "UN": "UN", "KIT": "KIT"}.get(unidade)


def _itens_bom_kit(db, empresa_id, kit_equivalencia, perfil):
    settings = _configuracao_equivalencia(kit_equivalencia)
    bom = settings.get("componentes_incluidos")
    itens = {}
    if bom is None:
        return itens
    if not isinstance(bom, list):
        return None
    for item in bom:
        if not isinstance(item, dict):
            return None
        papel = _normalizar_cor(str(item.get("papel") or ""))
        produto_id = item.get("produto_id")
        try:
            quantidade = Decimal(str(item.get("quantidade_por_persiana")))
        except (InvalidOperation, TypeError, ValueError):
            return None
        produto = db.query(ProdutoDB).filter(
            ProdutoDB.id == produto_id,
            ProdutoDB.empresa_id == empresa_id,
        ).one_or_none()
        if (
            papel not in {"SUPORTE", "ADAPTADOR", "PONTEIRA"}
            or produto is None
            or str(produto.situacao or "").strip().casefold() != "ativo"
            or str(produto.tipo_produto or "").strip().casefold() not in {"componente", "insumo"}
            or not quantidade.is_finite()
            or quantidade <= 0
        ):
            return None
        unidade = _unidade_tecnica_produto(produto)
        if papel in itens or unidade is None:
            return None
        itens[papel] = {
            "papel": papel, "produto": produto, "quantidade": quantidade,
            "incluido_no_kit": True, "unidade": unidade,
        }
    return itens


def _resolver_acessorios_motor(
    db, empresa_id, perfil, motor_equivalencia, kit_equivalencia, fabricante,
):
    incluidos = _itens_bom_kit(db, empresa_id, kit_equivalencia, perfil)
    if incluidos is None:
        return None
    config_kit = _configuracao_equivalencia(kit_equivalencia)

    if config_kit.get("kit_completo_confirmado") is True:
        conteudo = _valores_textuais(
            config_kit, "conteudo_confirmado"
        )

        obrigatorios = {
            "SUPORTE", "COROA", "ADAPTADOR", "PONTEIRA"
        }

        origem = config_kit.get("origem_confirmacao")

        if (
            obrigatorios.issubset(conteudo)
            and config_kit.get("cobranca_acessorios_separada") is False
            and isinstance(origem, str)
            and len(origem.strip()) >= 5
        ):
            return list(incluidos.values())

        return None

    faltantes = {"SUPORTE", "ADAPTADOR", "PONTEIRA"} - set(incluidos)
    disponiveis = {}
    motor_cfg = _configuracao_equivalencia(motor_equivalencia)
    tecnologia = str(motor_cfg.get("tecnologia") or "").strip().upper()
    familia = perfil["familia"]
    for equivalencia in _equivalencias_tecnicas(db, empresa_id, "ACESSORIO_MOTOR"):
        config = _configuracao_equivalencia(equivalencia)
        papel = _normalizar_cor(str(config.get("papel") or ""))
        try:
            diametro = int(config.get("diametro_mm"))
            quantidade = Decimal(str(config.get("quantidade_por_persiana")))
        except (InvalidOperation, TypeError, ValueError):
            continue
        if (
            papel not in faltantes
            or _fabricante(config) != fabricante
            or (
                (fabricante != "EMTECO" or perfil["explicito"])
                and not _motor_vinculado(config, motor_equivalencia.produto_id)
            )
            or diametro != perfil["diametro"]
            or _normalizar_cor(str(config.get("perfil_tubo") or "")) != perfil["perfil"]
            or _normalizar_cor(str(config.get("familia_instalacao") or "")) != familia
            or tecnologia not in _valores_textuais(config, "tecnologias_compativeis")
            or not quantidade.is_finite()
            or quantidade <= 0
        ):
            continue
        cadastro = _produto_equivalencia(db, empresa_id, equivalencia)
        if cadastro is None:
            continue
        produto, _ = cadastro
        unidade = _unidade_tecnica_produto(produto)
        if unidade is None:
            continue
        disponiveis.setdefault(papel, {
            "papel": papel, "produto": produto, "quantidade": quantidade, "incluido_no_kit": False,
            "unidade": unidade,
        })
    if not faltantes.issubset(disponiveis):
        return None
    incluidos.update(disponiveis)
    return list(incluidos.values())


def _resolver_conjunto_dinamico(db, empresa_id, motor_equivalencia, largura, altura, tubo_receita, kit_produto_id):
    motor_cfg = _configuracao_equivalencia(motor_equivalencia)
    fabricante = _fabricante(motor_cfg)
    if not fabricante or _normalizar_cor(str(motor_cfg.get("familia") or "")) != "ROLO":
        return None
    perfil = _perfil_motor_rolo(motor_cfg, largura, altura, tubo_receita.diametro_mm)
    if perfil is None:
        return None
    motor_db = _produto_equivalencia(db, empresa_id, motor_equivalencia, "UN")
    if motor_db is None:
        return None
    tubo_funcao = f"TUBO_ROLO_{perfil['diametro']}MM"
    tubos = _equivalencias_tecnicas(db, empresa_id, tubo_funcao)
    tubo_equivalencia = next((
        item for item in tubos
        if item.produto_id == tubo_receita.produto_id
        and (
            _fabricante(_configuracao_equivalencia(item)) == fabricante
            or (perfil["explicito"] and _fabricante(_configuracao_equivalencia(item)))
        )
        and _normalizar_cor(str(_configuracao_equivalencia(item).get("perfil_tubo") or "")) == perfil["perfil"]
        and _configuracao_equivalencia(item).get("diametro_mm") == perfil["diametro"]
        and (
            (fabricante == "EMTECO" and not perfil["explicito"])
            or (
                _normalizar_cor(str(_configuracao_equivalencia(item).get("familia_instalacao") or ""))
                == perfil["familia"]
                and _motor_vinculado(
                    _configuracao_equivalencia(item), motor_equivalencia.produto_id,
                )
            )
        )
    ), None)
    if tubo_equivalencia is None:
        return None
    tubo_db = _produto_equivalencia(db, empresa_id, tubo_equivalencia, "ML")
    if tubo_db is None or tubo_db[0].codigo_interno != tubo_receita.codigo_interno:
        return None
    kits = _equivalencias_tecnicas(
        db, empresa_id, ("KIT_INSTALACAO_MOTOR_ROLO", "ACESSORIO_MOTOR"),
    )
    kits_compativeis = [
        item for item in kits
        if (kit_produto_id is None or item.produto_id == kit_produto_id)
        and _fabricante(_configuracao_equivalencia(item)) == fabricante
        and _normalizar_cor(str(_configuracao_equivalencia(item).get("papel") or "")).replace("_", " ") == "KIT INSTALACAO"
        and _normalizar_cor(str(_configuracao_equivalencia(item).get("perfil_tubo") or "")) == perfil["perfil"]
        and _configuracao_equivalencia(item).get("diametro_mm") == perfil["diametro"]
        and _normalizar_cor(str(_configuracao_equivalencia(item).get("familia_instalacao") or ""))
        == _normalizar_cor(perfil["familia"])
        and _normalizar_cor(str(_configuracao_equivalencia(item).get("codigo_kit") or ""))
        in {_normalizar_cor(codigo) for codigo in perfil["kits"]}
        and (
            (fabricante == "EMTECO" and not perfil["explicito"])
            or _motor_vinculado(
                _configuracao_equivalencia(item), motor_equivalencia.produto_id,
            )
        )
    ]
    if len(kits_compativeis) != 1:
        return None
    kit_equivalencia = kits_compativeis[0]
    kit_db = _produto_equivalencia(db, empresa_id, kit_equivalencia, "KIT")
    if kit_db is None:
        return None
    accessories = _resolver_acessorios_motor(
        db, empresa_id, perfil, motor_equivalencia, kit_equivalencia, fabricante,
    )
    if accessories is None:
        return None
    return {
        "perfil": perfil,
        "motor_equivalencia": motor_equivalencia,
        "motor": motor_db[0],
        "tubo": tubo_db[0],
        "kit": kit_db[0],
        "kit_equivalencia": kit_equivalencia,
        "acessorios": accessories,
        "tecnologia": str(motor_cfg["tecnologia"]).strip().upper(),
    }


def _diagnosticar_produto_equivalencia(db, empresa_id, equivalencia, unidade=None):
    produto = db.query(ProdutoDB).filter(
        ProdutoDB.id == equivalencia.produto_id,
        ProdutoDB.empresa_id == empresa_id,
    ).one_or_none()
    if produto is None:
        return f"produto {equivalencia.produto_id} ausente na empresa"
    if str(produto.situacao or "").strip().casefold() != "ativo":
        return f"produto {produto.id} ({produto.nome}) inativo"
    if str(produto.tipo_produto or "").strip().casefold() not in {"componente", "insumo"}:
        return f"produto {produto.id} ({produto.nome}) não é componente/insumo"
    if _unidade_tecnica_produto(produto) is None:
        return f"produto {produto.id} ({produto.nome}) com unidade comercial não suportada"
    unidade_esperada = {"M": "ML", "M2": "M2"}.get(unidade, unidade)
    if unidade_esperada and _unidade_tecnica_produto(produto) != unidade_esperada:
        return f"produto {produto.id} ({produto.nome}) deve ter unidade {unidade_esperada}"
    if not _custos_positivos_produto(produto):
        return f"produto {produto.id} ({produto.nome}) sem custo positivo cadastrado"
    return None


def _diagnosticar_conjunto_dinamico(db, empresa_id, motor_equivalencia, largura, altura, tubo_receita,
                                   kit_produto_id=None):
    config = _configuracao_equivalencia(motor_equivalencia)
    motor_id = motor_equivalencia.produto_id
    fabricante = _fabricante(config)
    if not fabricante or _normalizar_cor(str(config.get("familia") or "")) != "ROLO":
        return f"motor {motor_id} sem fabricante e família ROLO explícitos"
    perfil = _perfil_motor_rolo(config, largura, altura, tubo_receita.diametro_mm)
    if perfil is None:
        if fabricante == "EMTECO":
            return (f"motor {motor_id}: largura, altura, peso estimado, torque ou tipo fora "
                    f"dos limites documentados para o tubo {tubo_receita.diametro_mm} mm")
        return (
            f"motor {motor_id} ({fabricante}): perfil_rolo ausente/inválido "
            "ou largura, altura, carga, torque ou tecnologia incompatível"
        )
    pendencias = []
    motor_pendencia = _diagnosticar_produto_equivalencia(db, empresa_id, motor_equivalencia, "UN")
    if motor_pendencia:
        pendencias.append(f"motor: {motor_pendencia}")
    tubo_fn = f"TUBO_ROLO_{perfil['diametro']}MM"
    tubo = next((
        item for item in _equivalencias_tecnicas(db, empresa_id, tubo_fn)
        if item.produto_id == tubo_receita.produto_id
        and (
            _fabricante(_configuracao_equivalencia(item)) == fabricante
            or (perfil["explicito"] and _fabricante(_configuracao_equivalencia(item)))
        )
        and _normalizar_cor(str(_configuracao_equivalencia(item).get("perfil_tubo") or "")) == perfil["perfil"]
        and _configuracao_equivalencia(item).get("diametro_mm") == perfil["diametro"]
        and (
            (fabricante == "EMTECO" and not perfil["explicito"])
            or (
                _normalizar_cor(str(_configuracao_equivalencia(item).get("familia_instalacao") or ""))
                == perfil["familia"]
                and _motor_vinculado(
                    _configuracao_equivalencia(item), motor_equivalencia.produto_id,
                )
            )
        )
    ), None)
    if tubo is None:
        pendencias.append(
            f"{tubo_fn} do fabricante {fabricante}, perfil {perfil['perfil']} / "
            f"{perfil['diametro']} mm sem vínculo compatível com o motor {motor_id}"
        )
    else:
        tubo_pendencia = _diagnosticar_produto_equivalencia(db, empresa_id, tubo, "ML")
        if tubo_pendencia:
            pendencias.append(f"tubo: {tubo_pendencia}")
    codigo_kit = {_normalizar_cor(codigo) for codigo in perfil["kits"]}
    kit = next((
        item for item in _equivalencias_tecnicas(
            db, empresa_id, ("KIT_INSTALACAO_MOTOR_ROLO", "ACESSORIO_MOTOR"),
        )
        if (kit_produto_id is None or item.produto_id == kit_produto_id)
        and _fabricante(_configuracao_equivalencia(item)) == fabricante
        and _normalizar_cor(str(_configuracao_equivalencia(item).get("papel") or "")).replace("_", " ") == "KIT INSTALACAO"
        and _normalizar_cor(str(_configuracao_equivalencia(item).get("perfil_tubo") or "")) == perfil["perfil"]
        and _configuracao_equivalencia(item).get("diametro_mm") == perfil["diametro"]
        and _normalizar_cor(str(_configuracao_equivalencia(item).get("familia_instalacao") or ""))
        == _normalizar_cor(perfil["familia"])
        and _normalizar_cor(str(_configuracao_equivalencia(item).get("codigo_kit") or "")) in codigo_kit
        and (
            (fabricante == "EMTECO" and not perfil["explicito"])
            or _motor_vinculado(
                _configuracao_equivalencia(item), motor_equivalencia.produto_id,
            )
        )
    ), None)
    if kit is None:
        pendencias.append(
            f"kit de instalação {', '.join(sorted(perfil['kits']))} do fabricante "
            f"{fabricante}, perfil {perfil['perfil']} / {perfil['diametro']} mm "
            f"sem vínculo compatível com o motor {motor_id}"
        )
    else:
        kit_pendencia = _diagnosticar_produto_equivalencia(db, empresa_id, kit, "KIT")
        if kit_pendencia:
            pendencias.append(f"kit: {kit_pendencia}")
        incluidos = _itens_bom_kit(db, empresa_id, kit, perfil)
        if incluidos is None:
            pendencias.append(f"kit {kit.produto_id} com lista componentes_incluidos inválida")
        else:
            roles_incluidos = set(incluidos)
            for papel in {"SUPORTE", "ADAPTADOR", "PONTEIRA"} - roles_incluidos:
                acessorio = next((
                    item for item in _equivalencias_tecnicas(db, empresa_id, "ACESSORIO_MOTOR")
                    if _normalizar_cor(str(_configuracao_equivalencia(item).get("papel") or "")) == papel
                    and _fabricante(_configuracao_equivalencia(item)) == fabricante
                    and _normalizar_cor(str(_configuracao_equivalencia(item).get("perfil_tubo") or "")) == perfil["perfil"]
                    and _configuracao_equivalencia(item).get("diametro_mm") == perfil["diametro"]
                    and _normalizar_cor(str(_configuracao_equivalencia(item).get("familia_instalacao") or ""))
                    == _normalizar_cor(perfil["familia"])
                    and str(config.get("tecnologia") or "").strip().upper()
                    in _valores_textuais(
                        _configuracao_equivalencia(item), "tecnologias_compativeis",
                    )
                    and (
                        (fabricante == "EMTECO" and not perfil["explicito"])
                        or _motor_vinculado(
                            _configuracao_equivalencia(item), motor_equivalencia.produto_id,
                        )
                    )
                ), None)
                if acessorio is None:
                    pendencias.append(
                        f"sem vínculo/custo de {papel.lower()} compatível com perfil {perfil['perfil']} "
                        f"/ {perfil['diametro']} mm"
                    )
                else:
                    try:
                        quantidade = Decimal(str(
                            _configuracao_equivalencia(acessorio).get("quantidade_por_persiana")
                        ))
                    except (InvalidOperation, TypeError, ValueError):
                        quantidade = Decimal(0)
                    if not quantidade.is_finite() or quantidade <= 0:
                        pendencias.append(
                            f"{papel.lower()} {acessorio.produto_id} sem quantidade por persiana válida"
                        )
                    acessorio_pendencia = _diagnosticar_produto_equivalencia(
                        db, empresa_id, acessorio,
                    )
                    if acessorio_pendencia:
                        pendencias.append(f"{papel.lower()}: {acessorio_pendencia}")
    return "; ".join(pendencias) or "vínculos técnicos incompatíveis"


def _insumo_dinamico(produto, unidade, diametro=None):
    return InsumoReceitaRolo.model_validate({
        "produto_id": produto.id,
        "codigo_interno": produto.codigo_interno,
        "unidade_tecnica": unidade,
        "preco_compra": float(produto.custo_final or produto.valor_custo or 0),
        "ipi_percentual": None,
        "unidades_por_compra": 1.0,
        "origem": "Custo cadastrado; vínculo técnico individual da empresa.",
        "base_preco": "CUSTO_CADASTRADO",
        "diametro_mm": diametro,
    })


def _conjunto_dinamico_selecionado(db, empresa_id, entrada, tubo_receita):
    motores = [
        item for item in _equivalencias_tecnicas(db, empresa_id, "MOTOR_PERSIANA")
        if item.produto_id == entrada.motor_produto_id
    ]
    if not motores:
        raise ValueError(
            f"Motor {entrada.motor_produto_id} sem vínculo ativo MOTOR_PERSIANA na empresa."
        )
    if entrada.kit_produto_id is None:
        conjuntos = {}

        for motor in motores:
            for vinculo in _equivalencias_tecnicas(
                db, empresa_id,
                ("KIT_INSTALACAO_MOTOR_ROLO", "ACESSORIO_MOTOR"),
            ):
                conjunto = _resolver_conjunto_dinamico(
                    db, empresa_id, motor,
                    entrada.largura, entrada.altura,
                    tubo_receita, vinculo.produto_id,
                )

                if conjunto is not None:
                    conjuntos[
                        (motor.id, vinculo.produto_id)
                    ] = conjunto

        if len(conjuntos) == 1:
            return next(iter(conjuntos.values()))

        if len(conjuntos) > 1:
            raise ValueError(
                "Mais de um conjunto tecnico compativel. "
                "Corrija a duplicidade na configuracao tecnica."
            )

        raise ValueError(
            "Motor sem conjunto tecnico compativel aprovado."
        )

    pendencias = []
    for motor in motores:
        conjunto = _resolver_conjunto_dinamico(
            db, empresa_id, motor, entrada.largura, entrada.altura, tubo_receita,
            entrada.kit_produto_id,
        )
        if conjunto is not None:
            return conjunto
        pendencias.append(_diagnosticar_conjunto_dinamico(
            db, empresa_id, motor, entrada.largura, entrada.altura, tubo_receita,
            entrada.kit_produto_id,
        ))
    raise ValueError(
        f"Motor {entrada.motor_produto_id} sem composição dinâmica aprovada: "
        + " | ".join(pendencias)
        + f"; kit {entrada.kit_produto_id} ausente, inválido ou incompatível."
    )


def _controles_dinamicos(db, empresa_id, conjunto):
    perfil = conjunto["perfil"]
    tecnologia = conjunto["tecnologia"]
    resultado = []
    for equivalencia in _equivalencias_tecnicas(db, empresa_id, "ACESSORIO_MOTOR"):
        config = _configuracao_equivalencia(equivalencia)
        if _normalizar_cor(str(config.get("papel") or "")) != "CONTROLE":
            continue
        ids_compativeis = config.get("motores_compativeis", [])
        familias_compativeis = config.get("familias_instalacao_compativeis", [])
        tecnologias_compativeis = config.get("tecnologias_compativeis", [])
        ids_compativeis = ids_compativeis if isinstance(ids_compativeis, list) else []
        familias_compativeis = familias_compativeis if isinstance(familias_compativeis, list) else []
        tecnologias_compativeis = tecnologias_compativeis if isinstance(tecnologias_compativeis, list) else []
        vinculo_explicito = (
            conjunto["motor"].id in ids_compativeis
            or (
                perfil["familia"] in {
                    _normalizar_cor(str(item)) for item in familias_compativeis
                    if isinstance(item, str)
                }
                and tecnologia in _valores_textuais(config, "tecnologias_compativeis")
            )
        )
        try:
            canais = int(config.get("canais"))
        except (TypeError, ValueError):
            continue
        if not vinculo_explicito or canais not in {1, 6, 16}:
            continue
        cadastro_custo = _produto_equivalencia(db, empresa_id, equivalencia, "UN")
        if cadastro_custo is None:
            continue
        cadastro, _ = cadastro_custo
        tipo = str(config.get("tipo") or "").strip().upper()
        if tipo not in {"CONTROLE_RF", "BOTAO", "INTERRUPTOR"}:
            continue
        if (tecnologia == "CONTATO_SECO") == (tipo == "CONTROLE_RF"):
            continue
        resultado.append({
            "produto_id": cadastro.id, "nome": cadastro.nome,
            "codigo": cadastro.codigo_interno, "tipo": tipo, "canais": canais,
        })
    return resultado


def _selecionar_tubo_receita(receita, entrada, tubo_manual_identidade=None):
    if entrada.acionamento == "manual":
        # Mantém os limites e resultados já aprovados das receitas antigas.
        legado = selecionar_tubo_rolo(entrada.largura, "manual")
        if not receita.faixas_tubo:
            return legado
    elif not receita.faixas_tubo:
        raise ValueError("Motorizada sem faixas técnicas aprovadas para tubos 38/41/56/70 mm e altura. Configure a receita do fornecedor.")
    permitidos = {32, 38, 43} if entrada.acionamento == "manual" else {32, 38, 41, 43, 53, 56, 70}
    if any(f.diametro_mm not in permitidos for f in receita.faixas_tubo):
        raise ValueError("Faixa de tubo incompatível com o acionamento da receita.")
    faixas = [f for f in receita.faixas_tubo
              if f.largura_min_m < entrada.largura <= f.largura_max_m
              and entrada.altura <= f.altura_max_m]
    if len(faixas) > 1 and entrada.acionamento == "motorizado" and tubo_manual_identidade is not None:
        faixa_38 = [f for f in faixas if f.diametro_mm == 38]
        tubo_38 = receita.tubos.get("38mm")
        motor_38 = receita.motores.get("38mm")
        kit_38 = receita.kits_motor.get("38mm")
        if (len(faixa_38) == 1 and tubo_38 and (tubo_38.produto_id, tubo_38.codigo_interno) == tubo_manual_identidade
                and motor_38 and motor_38.diametro_mm == 38
                and kit_38 and kit_38.diametro_mm == 38):
            faixas = faixa_38
    if len(faixas) != 1:
        raise ValueError("Receita sem faixa técnica única aprovada para estas medidas e acionamento.")
    return TuboRoloSelecao(TuboRoloDiametro(f"{faixas[0].diametro_mm}mm"),
                          AcionamentoPermitido(entrada.acionamento))


def _tecido_screen_importado(db, empresa_id, cor, largura_corte):
    cor = _normalizar_cor(cor)
    if cor not in CORES_SCREEN_IMPORTADO:
        raise ValueError(
            "Selecione BRANCO, BEGE, CINZA ou PRETO para a Rolô Screen 3% Importado."
        )

    candidatos = db.query(ProdutoDB).filter(
        ProdutoDB.empresa_id == empresa_id,
        ProdutoDB.tipo_produto.in_(("Componente", "Insumo")),
        func.upper(ProdutoDB.situacao) == "ATIVO",
        func.upper(ProdutoDB.unidade_venda).in_(("M²", "M2")),
        func.upper(ProdutoDB.material_tecido) == "SCREEN 3% JP IMPORTADA",
        func.upper(ProdutoDB.cor) == cor,
        ProdutoDB.codigo_interno.like("JPTEC-%"),
        ProdutoDB.largura >= largura_corte,
    ).all()
    candidatos_validos = []
    for produto in candidatos:
        codigo = str(produto.codigo_interno or "").strip().upper()
        observacoes = str(produto.observacoes or "")
        regra_custo = _normalizar_cor(observacoes.replace("²", "2"))
        largura = Decimal(str(produto.largura or 0))
        custo = next(
            (
                Decimal(str(valor))
                for valor in (produto.custo_final, produto.valor_custo)
                if valor is not None and Decimal(str(valor)).is_finite()
                and Decimal(str(valor)) > 0
            ),
            None,
        )
        if (
            re.fullmatch(r"JPTEC-\d{4}", codigo)
            and _normalizar_cor(produto.material_tecido) == "SCREEN 3% JP IMPORTADA"
            and _normalizar_cor(produto.cor) == cor
            and largura.is_finite()
            and largura >= Decimal(str(largura_corte))
            and custo is not None
            and "CUSTO POR M2; NAO RECONVERTER POR LARGURA" in regra_custo
        ):
            candidatos_validos.append((largura, codigo, produto, custo, observacoes))

    if not candidatos_validos:
        raise ValueError(
            f"Tecido Screen 3% Importado {cor} ativo, com custo M² comprovado e "
            f"bobina suficiente para o corte ({largura_corte:.2f} m), não encontrado."
        )

    largura, _, produto, custo, observacoes = min(
        candidatos_validos, key=lambda candidato: (candidato[0], candidato[1])
    )
    return {
        "produto_id": produto.id,
        "codigo_interno": produto.codigo_interno,
        "unidade_tecnica": "M2",
        "preco_compra": float(custo),
        "ipi_percentual": None,
        "unidades_por_compra": float(largura),
        "origem": observacoes,
        "base_preco": "CUSTO_CADASTRADO",
        "diametro_mm": None,
    }, float(largura)



def _tecido_colecao_vinculado(
    db, empresa_id, cor, largura_corte, vinculos
):
    cor = _normalizar_cor(cor)
    corte = Decimal(str(largura_corte))
    candidatos = []

    for vinculo in vinculos:
        if _normalizar_cor(vinculo["cor"]) != cor:
            continue

        produto = db.query(ProdutoDB).filter(
            ProdutoDB.id == int(vinculo["produto_id"]),
            ProdutoDB.empresa_id == empresa_id,
            func.upper(ProdutoDB.situacao) == "ATIVO",
        ).one_or_none()

        if produto is None:
            continue

        if str(produto.tipo_produto or "").strip().casefold() not in {
            "componente", "insumo"
        }:
            continue

        if _normalizar_cor(produto.codigo_interno) != (
            _normalizar_cor(vinculo["codigo_interno"])
        ):
            continue

        largura = Decimal(str(vinculo["largura_bobina_m"]))
        custo = Decimal(str(vinculo["custo_m2"]))

        if not largura.is_finite() or not custo.is_finite():
            continue

        if largura <= 0 or largura < corte or custo <= 0:
            continue

        if not str(vinculo.get("origem") or "").strip():
            continue

        candidatos.append((largura, custo, produto.id, produto, vinculo))

    if not candidatos:
        raise ValueError(
            "Nenhum tecido homologado para a cor e largura solicitadas."
        )

    largura, custo, _, produto, vinculo = min(
        candidatos, key=lambda item: item[:3]
    )

    return {
        "produto_id": produto.id,
        "codigo_interno": produto.codigo_interno,
        "unidade_tecnica": "M2",
        "preco_compra": float(custo),
        "ipi_percentual": None,
        "unidades_por_compra": float(largura),
        "origem": vinculo["origem"],
        "base_preco": "CUSTO_CADASTRADO",
        "diametro_mm": None,
    }, float(largura)


def _obter_receita(db, produto, entrada, empresa_id):
    if produto.empresa_id != empresa_id or produto.id != entrada.produto_id:
        raise ValueError("Produto RolÃ´ incompatÃ­vel com a empresa e item selecionados.")
    empresa = db.query(EmpresaDB).filter_by(id=empresa_id, status="ATIVA").one_or_none()
    if empresa is None:
        raise ValueError("Empresa ativa nÃ£o encontrada.")
    if not isinstance(empresa.configuracoes, dict):
        raise ValueError("ConfiguraÃ§Ã£o da empresa invÃ¡lida.")
    receitas = empresa.configuracoes.get("receitas_rolo_v1", {})
    if not isinstance(receitas, dict):
        raise ValueError("ConfiguraÃ§Ã£o de receitas RolÃ´ invÃ¡lida.")
    # Receitas por acionamento, sem reutilizar comando manual na motorizada.
    # Compatibilidade: receitas antigas continuam usando a chave simples do ID.
    cor_chave = _normalizar_cor(entrada.cor)
    chave = f"{produto.id}:{entrada.acionamento}"
    screen_importado = (
        produto.id in {7, 84}
        and _tipo_rolo(produto) == "MANUAL"
        and re.search(r"\bSCREEN\s*3\s*%", produto.nome or "", re.I)
        and re.search(r"IMPORTAD", produto.nome or "", re.I)
    )
    if screen_importado and cor_chave not in CORES_SCREEN_IMPORTADO:
        raise ValueError(
            "Selecione BRANCO, BEGE, CINZA ou PRETO para a Rolô Screen 3% Importado."
        )
    chaves_receita = [f"{chave}:{cor_chave}", chave]
    if entrada.acionamento == "motorizado":
        chaves_receita.extend((
            f"{produto.id}:manual:{cor_chave}",
            f"{produto.id}:manual",
            str(produto.id),
        ))
    else:
        chaves_receita.extend((f"{produto.id}:manual:{cor_chave}", f"{produto.id}:manual", str(produto.id)))
    if screen_importado:
        chaves_receita.append(f"{produto.id}:manual:BRANCO")
    receita_bruta = next((receitas[k] for k in chaves_receita if k in receitas), None)

    tecidos_colecoes = empresa.configuracoes.get("tecidos_rolo_v1", {})

    if not isinstance(tecidos_colecoes, dict):
        raise ValueError("Configuracao de tecidos Rolo invalida.")

    vinculos_colecao = tecidos_colecoes.get(str(produto.id))

    if vinculos_colecao is not None and receita_bruta is None:
        if not isinstance(vinculos_colecao, list) or not vinculos_colecao:
            raise ValueError("Colecao sem tecidos tecnicos vinculados.")

        modelo = receitas.get("84:manual:BRANCO")

        if not isinstance(modelo, dict):
            raise ValueError("Receita mecanica de referencia indisponivel.")

        tecido, largura_bobina = _tecido_colecao_vinculado(
            db,
            empresa_id,
            cor_chave,
            entrada.largura - 0.03,
            vinculos_colecao,
        )

        dados_receita = {
            **modelo,
            "tecido": tecido,
            "cor_tecido": cor_chave,
            "largura_bobina_m": largura_bobina,
        }

        return ReceitaRolo.model_validate(dados_receita)

    # Apenas o acabado 7, manual, pode reutilizar a mecânica da referência 84.
    # Receita própria sempre tem prioridade; não transfere tecido nem preço.
    if receita_bruta is None and produto.id == 7 and screen_importado and entrada.acionamento == "manual":
        referencia = db.query(ProdutoDB).filter(
            ProdutoDB.id == 84, ProdutoDB.empresa_id == empresa_id,
        ).one_or_none()
        if (referencia is not None
                and str(referencia.situacao or "").casefold() == "ativo"
                and str(produto.situacao or "").casefold() == "ativo"
                and _tipo_rolo(referencia) == "MANUAL"
                and re.search(r"\bSCREEN\s*3\s*%", referencia.nome or "", re.I)
                and re.search(r"IMPORTAD", referencia.nome or "", re.I)):
            receita_bruta = receitas.get("84:manual:BRANCO")
    if receita_bruta is None:
        # Standard consolidada: preço comercial do próprio acabado, sem criar
        # receita nem aproveitar custos de tecidos/coleções diferentes.
        if (produto.id == 503 and entrada.acionamento == "manual"
                and _tipo_rolo(produto) == "MANUAL"
                and str(produto.situacao or "").casefold() == "ativo"
                and re.search(r"\bSCREEN\s*3\s*%\s+STAND(?:ARD|ART)\b", produto.nome or "", re.I)
                and not re.search(r"IMPORTAD", produto.nome or "", re.I)):
            if (entrada.cor or "").strip().upper() not in {"BRANCO", "CINZA"}:
                raise ValueError("Selecione BRANCO ou CINZA para a Rolô Screen 3% Standard.")
            return None
        if produto.id == 84 and entrada.acionamento == "motorizado":
            raise ValueError(
                "Receita técnica motorizado não configurada para este produto. "
                "Pendentes: vínculos aprovados de motor 6 Nm, tubo 41/56/70 mm, "
                "kit de adaptação, suportes, controle compatível e limites de medidas/carga. "
                "A receita manual não substitui a motorizada. Orçamento bloqueado."
            )
        raise ValueError(
            f"Receita técnica {entrada.acionamento} não configurada para este produto. "
            + ("Vincule tecido, tubo 38/41/56/70 mm, motor, kit compatível e faixas aprovadas. A receita manual não substitui a motorizada."
               if entrada.acionamento == "motorizado"
               else "Vincule tecido, tubo, comando e componentes reais antes de orçar.")
        )
    try:
        receita = ReceitaRolo.model_validate(receita_bruta)
    except ValidationError as exc:
        raise ValueError("Receita RolÃ´ invÃ¡lida. Revise os vÃ­nculos e custos cadastrados.") from exc
    if screen_importado:
        largura_corte = entrada.largura - 0.03
        tecido, largura_bobina = _tecido_screen_importado(
            db, empresa_id, cor_chave, largura_corte
        )
        receita = receita.model_copy(update={
            "cor_tecido": cor_chave,
            "largura_bobina_m": largura_bobina,
            "tecido": receita.tecido.model_copy(update=tecido),
        })
    return receita


def _bitolas_motor_compativeis(conjunto, entrada):
    torque = Decimal(str(conjunto.torque_nm))
    if torque < 6 and torque != Decimal("0.5"):
        return []
    if (
        conjunto.capacidade_kg is None
        or conjunto.peso_barra_kg is None
        or conjunto.peso_estimado_kg_m2 is None
        or not (conjunto.origem_carga or "").strip()
    ):
        return []
    carga = (
        Decimal(str(entrada.largura)) * Decimal(str(entrada.altura))
        * Decimal(str(conjunto.peso_estimado_kg_m2))
        + Decimal(str(conjunto.peso_barra_kg))
    )
    if carga > Decimal(str(conjunto.capacidade_kg)):
        return []
    candidatos = []
    for bitola, tubo in conjunto.tubos.items():
        if not re.fullmatch(r"(32|38|41|43|53|56|70)mm", bitola):
            continue
        diametro = int(bitola.removesuffix("mm"))
        if not _torque_compativel_rolo(torque, diametro):
            continue
        kit = conjunto.kits_motor.get(bitola)
        if kit is None or tubo.unidade_tecnica != "ML" or kit.unidade_tecnica != "KIT":
            continue
        if tubo.diametro_mm not in (None, diametro):
            continue
        if (kit.diametro_mm not in (None, diametro)
                and not conjunto.compatibilidades.get(bitola, "").strip()):
            continue
        faixas = [
            faixa for faixa in conjunto.faixas_tubo
            if faixa.diametro_mm == diametro
            and faixa.largura_min_m < entrada.largura <= faixa.largura_max_m
            and entrada.altura <= faixa.altura_max_m
        ]
        if len(faixas) == 1:
            candidatos.append((bitola, tubo, kit, faixas[0]))
    return candidatos



def _tubo_motorizado_empresa(db, empresa_id, entrada, motor_equivalencia):
    config = _configuracao_equivalencia(motor_equivalencia)
    perfis = config.get("perfis_rolo")

    if not isinstance(perfis, list):
        return None

    candidatos = []

    for dados in perfis:
        if not isinstance(dados, dict):
            continue

        diametro = dados.get("diametro_mm")
        perfil = _perfil_motor_rolo(
            config, entrada.largura, entrada.altura, diametro
        )

        if perfil is None:
            continue

        try:
            largura_min = Decimal(str(dados["largura_min_m"]))
            largura = Decimal(str(entrada.largura))
        except (KeyError, InvalidOperation, TypeError, ValueError):
            continue

        if (
            not largura_min.is_finite()
            or largura_min < 0
            or largura <= largura_min
        ):
            continue

        for vinculo in _equivalencias_tecnicas(
            db, empresa_id, f"TUBO_ROLO_{diametro}MM"
        ):
            cfg = _configuracao_equivalencia(vinculo)

            if (
                cfg.get("diametro_mm") != diametro
                or not _motor_vinculado(
                    cfg, motor_equivalencia.produto_id
                )
                or _normalizar_cor(str(cfg.get("perfil_tubo") or ""))
                != perfil["perfil"]
                or _normalizar_cor(str(cfg.get("familia_instalacao") or ""))
                != perfil["familia"]
            ):
                continue

            cadastro = _produto_equivalencia(
                db, empresa_id, vinculo, "ML"
            )

            if cadastro is not None:
                candidatos.append(
                    _insumo_dinamico(cadastro[0], "ML", diametro)
                )

    if len(candidatos) != 1:
        raise ValueError(
            "Motor sem tubo tecnico unico aprovado "
            "para estas medidas e carga."
        )

    return candidatos[0]



def _tubo_dinamico_por_motor(db, empresa_id, receita, entrada, motor_equivalencia=None):
    if motor_equivalencia is not None:
        motores = [motor_equivalencia]
    else:
        motores = [
            item for item in _equivalencias_tecnicas(
                db, empresa_id, "MOTOR_PERSIANA"
            )
            if item.produto_id == entrada.motor_produto_id
        ]

    configurados = [
        item for item in motores
        if "perfis_rolo" in _configuracao_equivalencia(item)
    ]

    if configurados:
        if len(configurados) != 1:
            raise ValueError(
                "Motor com configuracao tecnica duplicada."
            )

        tubo = _tubo_motorizado_empresa(
            db, empresa_id, entrada, configurados[0]
        )

        if tubo is None:
            raise ValueError(
                "Motor sem perfil de tubo aprovado."
            )

        return tubo

    return _tubo_receita_dinamico(receita, entrada)


def _tubo_receita_dinamico(receita, entrada):
    if receita.faixas_tubo:
        selecao = _selecionar_tubo_receita(receita, entrada)
    else:
        manual = entrada.model_copy(update={"acionamento": "manual", "motor_produto_id": None})
        try:
            selecao = _selecionar_tubo_receita(receita, manual)
        except MotorObrigatorioErro as exc:
            raise ValueError(str(exc)) from exc
    bitola = selecao.diametro.value
    tubo = receita.tubos.get(bitola)
    diametro = int(bitola.removesuffix("mm"))
    if tubo is None or tubo.diametro_mm not in (None, diametro):
        raise ValueError(f"Receita sem tubo {bitola} validado para estas medidas.")
    return tubo.model_copy(update={"diametro_mm": diametro})


def _filtrar_tubo_receita(receita, entrada, candidatos):
    if not candidatos:
        return []
    tubo = _tubo_receita_dinamico(receita, entrada)
    return [
        candidato for candidato in candidatos
        if candidato[0] == f"{tubo.diametro_mm}mm"
        and (candidato[1].produto_id, candidato[1].codigo_interno)
        == (tubo.produto_id, tubo.codigo_interno)
    ]


def _dados_kit(produto, diametro, conteudo=None):
    return {
        "produto_id": produto.id,
        "nome": produto.nome,
        "codigo": produto.codigo_fornecedor or produto.codigo_interno,
        "fornecedor": produto.nome_fornecedor,
        "diametro_tubo_mm": diametro,
        "conteudo": conteudo,
        "custo": float(produto.custo_final or produto.valor_custo or 0),
    }


def listar_motores_rolo(db, produto, entrada, empresa_id):
    if entrada.acionamento != "motorizado":
        raise ValueError("A seleção de motor exige acionamento motorizado.")
    receita = _obter_receita(db, produto, entrada, empresa_id)
    if receita is None:
        return []
    if _tipo_rolo(produto) not in {"MANUAL", "MOTORIZADA"}:
        raise ValueError("A receita exige produto final Rolô válido.")
    if entrada.cor and _normalizar_cor(entrada.cor) != _normalizar_cor(receita.cor_tecido):
        raise ValueError("Cor selecionada diferente da variação vinculada ao tecido.")
    resultado = []
    pendencias = []
    for conjunto in receita.conjuntos_motor:
        candidatos = _filtrar_tubo_receita(
            receita, entrada,
            _bitolas_motor_compativeis(conjunto, entrada),
        )
        if len(candidatos) != 1:
            pendencias.append(
                f"motor {conjunto.motor.produto_id}: tubo, kit, faixa ou carga "
                "sem compatibilidade comprovada para estas medidas"
            )
            continue
        cadastro = db.query(ProdutoDB).filter_by(
            id=conjunto.motor.produto_id, empresa_id=empresa_id,
            codigo_interno=conjunto.motor.codigo_interno,
        ).one_or_none()
        if (
            cadastro is None
            or str(cadastro.situacao or "").casefold() != "ativo"
            or conjunto.motor.unidade_tecnica != "UN"
        ):
            pendencias.append(f"motor {conjunto.motor.produto_id}: cadastro ou unidade inválidos")
            continue
        try:
            kit_id = candidatos[0][2].produto_id
            simulacao = simular_rolo_catalogo(
                db, produto, entrada.model_copy(update={
                    "motor_produto_id": cadastro.id, "kit_produto_id": kit_id,
                }), empresa_id,
            )
        except ValueError as exc:
            pendencias.append(f"motor {cadastro.id}: {exc}")
            continue
        kit_db = db.query(ProdutoDB).filter_by(id=kit_id, empresa_id=empresa_id).one_or_none()
        if kit_db is None:
            pendencias.append(f"kit {kit_id}: cadastro ausente")
            continue
        dados_kit = _dados_kit(kit_db, candidatos[0][3].diametro_mm)
        dados_kit["custo"] = next(
            item["custo_unitario_tecnico"] for item in simulacao["receita"]["custos"]
            if item["produto_id"] == kit_id
        )
        resultado.append({"produto_id": cadastro.id, "nome": cadastro.nome,
                          "torque_nm": conjunto.torque_nm, "tecnologia": conjunto.tecnologia,
                          "diametro_tubo_mm": candidatos[0][3].diametro_mm,
                          "kits": [dados_kit]})
    vinculos_dinamicos = _equivalencias_tecnicas(db, empresa_id, "MOTOR_PERSIANA")
    for equivalencia in vinculos_dinamicos:
        config = _configuracao_equivalencia(equivalencia)
        if (
            equivalencia.produto_id in {item.motor.produto_id for item in receita.conjuntos_motor}
            or equivalencia.produto_id in {item["produto_id"] for item in resultado}
            or _normalizar_cor(str(config.get("familia") or "")) != "ROLO"
        ):
            continue
        try:
            tubo_receita = _tubo_dinamico_por_motor(db, empresa_id, receita, entrada, equivalencia)
        except ValueError as exc:
            pendencias.append(str(exc))
            continue
        conjuntos = []
        for kit_vinculo in _equivalencias_tecnicas(
            db, empresa_id, ("KIT_INSTALACAO_MOTOR_ROLO", "ACESSORIO_MOTOR"),
        ):
            conjunto = _resolver_conjunto_dinamico(
                db, empresa_id, equivalencia, entrada.largura, entrada.altura,
                tubo_receita, kit_vinculo.produto_id,
            )
            if conjunto is not None and conjunto["kit"].id not in {c["kit"].id for c in conjuntos}:
                conjuntos.append(conjunto)
        if not conjuntos:
            pendencias.append(_diagnosticar_conjunto_dinamico(
                db, empresa_id, equivalencia, entrada.largura, entrada.altura, tubo_receita,
            ))
            continue
        conjunto = conjuntos[0]
        motor = conjunto["motor"]
        perfil = conjunto["perfil"]
        carga_estimada = (
            Decimal(str(entrada.largura)) * Decimal(str(entrada.altura))
            * Decimal(str(perfil["peso_estimado_kg_m2"]))
            + Decimal(str(perfil["peso_barra"]))
            if perfil["peso_estimado_kg_m2"] is not None
            and perfil["peso_barra"] is not None
            else None
        )
        resultado.append({
            "produto_id": motor.id,
            "nome": motor.nome,
            "torque_nm": float(config["torque_nm"]),
            "tecnologia": conjunto["tecnologia"],
            "diametro_tubo_mm": perfil["diametro"],
            "perfil_tubo": perfil["perfil"],
            "limite_largura_m": perfil["largura"],
            "limite_altura_m": min(perfil["altura"], perfil["altura_operacao"]),
             "carga_estimada_kg": (
                float(carga_estimada)
                if carga_estimada is not None else None
            ),
            "carga_pendente": perfil.get("carga_pendente", False),
            "capacidade_kg": perfil["peso"],
            "kits": [
                _dados_kit(c["kit"], c["perfil"]["diametro"],
                           _configuracao_equivalencia(c["kit_equivalencia"]).get("componentes_incluidos"))
                for c in conjuntos
            ],
        })
    if not resultado:
        if pendencias:
            raise ValueError("Nenhum conjunto dinâmico compatível: " + " | ".join(pendencias))
        if not vinculos_dinamicos:
            raise ValueError(
                "A empresa não possui vínculos ativos MOTOR_PERSIANA para selecionar motores individuais."
            )
    return resultado


def listar_acessorios_comando_rolo(db, entradas, empresa_id):
    if not entradas:
        raise ValueError("O ambiente precisa conter ao menos uma persiana motorizada.")
    comuns = None
    for entrada in entradas:
        if entrada.acionamento != "motorizado" or entrada.motor_produto_id is None:
            raise ValueError("Selecione um motor para cada persiana motorizada do ambiente.")
        produto = db.query(ProdutoDB).filter_by(id=entrada.produto_id, empresa_id=empresa_id).one_or_none()
        if produto is None:
            raise ValueError("Persiana não encontrada para a empresa ativa.")
        simular_rolo_catalogo(db, produto, entrada, empresa_id)
        receita = _obter_receita(db, produto, entrada, empresa_id)
        conjunto = next((c for c in receita.conjuntos_motor if c.motor.produto_id == entrada.motor_produto_id), None)
        if conjunto is None:
            tubo_receita = _tubo_dinamico_por_motor(db, empresa_id, receita, entrada)
            dinamico = _conjunto_dinamico_selecionado(db, empresa_id, entrada, tubo_receita)
            disponiveis = {
                item["produto_id"]: item
                for item in _controles_dinamicos(db, empresa_id, dinamico)
            }
        else:
            disponiveis = {}
            for acessorio in conjunto.acessorios_comando:
                insumo = acessorio.insumo
                cadastro = db.query(ProdutoDB).filter_by(
                    id=insumo.produto_id, empresa_id=empresa_id, codigo_interno=insumo.codigo_interno,
                ).one_or_none()
                if (cadastro is None or str(cadastro.situacao or "").casefold() != "ativo"
                        or str(cadastro.unidade_venda or "").strip().upper() != "UN"
                        or str(cadastro.tipo_produto or "").casefold() not in {"componente", "insumo"}
                        or _tipo_rolo(cadastro) is not None):
                    raise ValueError("Acessório de comando ausente, inativo ou sem unidade comercial UN.")
                if not any(v is not None and v > 0 for v in (cadastro.custo_final, cadastro.valor_custo, cadastro.valor_venda)):
                    raise ValueError("Acessório de comando sem preço ou custo cadastrado válido.")
                disponiveis[insumo.produto_id] = {
                    "produto_id": insumo.produto_id, "nome": cadastro.nome,
                    "codigo": cadastro.codigo_interno, "tipo": acessorio.tipo, "canais": acessorio.canais,
                }
        if comuns is None:
            comuns = disponiveis
        else:
            comuns = {chave: valor for chave, valor in comuns.items()
                      if chave in disponiveis and valor == disponiveis[chave]}
    return list(comuns.values()) if comuns is not None else []


def _pendencias_selecao_catalogo(db, empresa_id, entrada):
    pendencias = [
        "faltam dados técnicos cadastrados para validar torque, capacidade e carga do motor",
        "falta comprovação de compatibilidade do kit com o motor e o tubo da receita",
    ]
    for nome, produto_id, unidade in (
        ("motor", entrada.motor_produto_id, "UN"),
        ("kit", entrada.kit_produto_id, "KIT"),
    ):
        cadastro = db.query(ProdutoDB).filter_by(id=produto_id, empresa_id=empresa_id).one_or_none()
        if cadastro is None:
            pendencias.append(f"{nome} não encontrado na empresa")
            continue
        if str(cadastro.situacao or "").strip().casefold() != "ativo":
            pendencias.append(f"{nome} inativo")
        if str(cadastro.tipo_produto or "").strip().casefold() not in {"componente", "insumo"}:
            pendencias.append(f"{nome} não é componente ou insumo")
        if _unidade_tecnica_produto(cadastro) != unidade:
            pendencias.append(f"{nome} precisa de unidade {unidade}")
        if not _custos_positivos_produto(cadastro):
            pendencias.append(f"{nome} sem custo positivo cadastrado")
    return "; ".join(pendencias) + "."


def simular_rolo_catalogo(db: Session, produto: ProdutoDB, entrada: RoloSimulacaoInput, empresa_id: int):
    if entrada.acionamento == "manual" and (entrada.motor_produto_id is not None or entrada.kit_produto_id is not None):
        raise ValueError("Remova o motor e o kit antes de calcular o acionamento manual.")
    if entrada.acionamento == "motorizado" and entrada.motor_produto_id is None:
        raise ValueError("Selecione um motor com torque e composição técnica comprovados para a Rolô motorizada.")
    receita = _obter_receita(db, produto, entrada, empresa_id)
    if receita is None:
        if entrada.acionamento == "motorizado":
            raise ValueError("Receita motorizada ausente: não é possível validar motor, tubo e kit.")
        return simular_rolo(produto, entrada)
    conjunto = None
    conjunto_dinamico = None
    if entrada.acionamento == "motorizado" and receita.conjuntos_motor:
        conjunto = next(
            (c for c in receita.conjuntos_motor if c.motor.produto_id == entrada.motor_produto_id),
            None,
        )
    motor_dinamico_vinculado = bool(
        entrada.motor_produto_id is not None
        and any(
            item.produto_id == entrada.motor_produto_id
            for item in _equivalencias_tecnicas(db, empresa_id, "MOTOR_PERSIANA")
        )
    )
    if (
        entrada.acionamento == "motorizado"
        and receita.conjuntos_motor
        and conjunto is None
        and not motor_dinamico_vinculado
    ):
        raise ValueError(_pendencias_selecao_catalogo(db, empresa_id, entrada))
    if entrada.acionamento == "motorizado" and conjunto is not None:
        bitolas_compativeis = _filtrar_tubo_receita(
            receita, entrada,
            _bitolas_motor_compativeis(conjunto, entrada),
        )
        if not bitolas_compativeis:
            raise ValueError("Motor sem tubo, kit, faixa técnica e carga comprovados para estas medidas.")
        if len(bitolas_compativeis) != 1:
            raise ValueError("Mais de uma bitola compatível para este motor e medida; ajuste as faixas técnicas.")
        bitola, tubo, kit, faixa = bitolas_compativeis[0]
        if entrada.kit_produto_id is not None and kit.produto_id != entrada.kit_produto_id:
            raise ValueError("Kit selecionado incompatível com o motor e o tubo da receita.")
        receita = receita.model_copy(update={
            "tubos": {bitola: tubo},
            "faixas_tubo": [faixa],
            "motores": {bitola: conjunto.motor},
            "kits_motor": {bitola: kit},
        })
    elif entrada.acionamento == "motorizado" and entrada.motor_produto_id is not None:
        if not motor_dinamico_vinculado:
            raise ValueError(_pendencias_selecao_catalogo(db, empresa_id, entrada))
        tubo_receita = _tubo_dinamico_por_motor(db, empresa_id, receita, entrada)
        conjunto_dinamico = _conjunto_dinamico_selecionado(db, empresa_id, entrada, tubo_receita)
        perfil = conjunto_dinamico["perfil"]
        bitola = f"{perfil['diametro']}mm"
        tubo = _insumo_dinamico(conjunto_dinamico["tubo"], "ML", perfil["diametro"])
        motor = _insumo_dinamico(conjunto_dinamico["motor"], "UN")
        kit = _insumo_dinamico(conjunto_dinamico["kit"], "KIT", perfil["diametro"])
        faixa = FaixaTuboRolo.model_validate({
            "diametro_mm": perfil["diametro"],
            "largura_min_m": 0,
            "largura_max_m": perfil["largura"],
            "altura_max_m": min(perfil["altura"], perfil["altura_operacao"]),
            "origem": perfil["origem"],
        })
        receita = receita.model_copy(update={
            "tubos": {bitola: tubo},
            "faixas_tubo": [faixa],
            "motores": {bitola: motor},
            "kits_motor": {bitola: kit},
        })
    elif (
        entrada.acionamento == "motorizado"
        and entrada.motor_produto_id is None
    ):
        raise ValueError(
            "Receita manual ou legada: selecione um motor individual com torque e composição técnica comprovados "
            "antes de simular a persiana motorizada."
        )
    if _tipo_rolo(produto) not in {"MANUAL", "MOTORIZADA"}:
        raise ValueError("A receita exige produto final Rolô válido.")
    if entrada.cor and _normalizar_cor(entrada.cor) != _normalizar_cor(receita.cor_tecido):
        raise ValueError("Cor selecionada diferente da variaÃ§Ã£o vinculada ao tecido.")
    manual = entrada.acionamento == "manual"
    if not manual:
        receita = receita.model_copy(update={
            "componentes": {
                nome: insumo for nome, insumo in receita.componentes.items()
                if nome not in {"corrente", "emenda_corrente"}
            }
        })
    componentes_exigidos = COMPONENTES if manual else {
        k: v for k, v in COMPONENTES.items() if k not in {"corrente", "emenda_corrente"}
    }
    if set(receita.componentes) != set(componentes_exigidos):
        raise ValueError(f"Receita Rolô {entrada.acionamento} sem os acessórios obrigatórios compatíveis.")
    try:
        if not manual:
            faixas = [f for f in receita.faixas_tubo
                      if f.largura_min_m < entrada.largura <= f.largura_max_m
                      and entrada.altura <= f.altura_max_m]
            tubo_38 = receita.tubos.get("38mm")
            if len(faixas) > 1 and tubo_38 and sum(f.diametro_mm == 38 for f in faixas) == 1:
                entrada_manual = entrada.model_copy(update={"acionamento": "manual", "motor_produto_id": None})
                receita_manual = _obter_receita(db, produto, entrada_manual, empresa_id)
                if receita_manual is None:
                    raise ValueError("Não há receita manual vinculada para confirmar a manutenção do tubo 38 mm.")
                if entrada.cor and _normalizar_cor(entrada.cor) != _normalizar_cor(receita_manual.cor_tecido):
                    raise ValueError("A cor da receita manual não corresponde ao tecido selecionado.")
                selecao_manual = _selecionar_tubo_receita(receita_manual, entrada_manual)
                tubo_manual = receita_manual.tubos.get(selecao_manual.diametro.value)
                identidade = (tubo_manual.produto_id, tubo_manual.codigo_interno) if selecao_manual.diametro.value == "38mm" and tubo_manual else None
                selecao = _selecionar_tubo_receita(receita, entrada, identidade)
            else:
                selecao = _selecionar_tubo_receita(receita, entrada)
        else:
            selecao = _selecionar_tubo_receita(receita, entrada)
    except MotorObrigatorioErro as exc:
        raise ValueError(str(exc)) from exc
    bitola = selecao.diametro.value
    if bitola not in receita.tubos:
        raise ValueError(f"Receita sem tubo {bitola} validado para {entrada.acionamento}.")
    if manual and bitola not in receita.comandos:
        raise ValueError(f"Receita sem conjunto tubo/comando {bitola} validado. Orçamento bloqueado.")
    if not manual and (bitola not in receita.motores or bitola not in receita.kits_motor):
        raise ValueError(f"Receita motorizada sem motor ou kit de montagem compatível com tubo {bitola}.")
    componentes_bitola = [receita.tubos[bitola]]
    if manual:
        componentes_bitola.append(receita.comandos[bitola])
    else:
        componentes_bitola.append(receita.kits_motor[bitola])
    diametro = int(bitola.replace("mm", ""))
    if any(i.diametro_mm not in (None, diametro) for i in componentes_bitola):
        if not (conjunto and conjunto.compatibilidades.get(bitola, "").strip()):
            raise ValueError("Diâmetro do tubo/kit incompatível sem vínculo técnico explícito.")
    largura_corte = entrada.largura - 0.03
    if largura_corte <= 0 or entrada.altura <= 0.025:
        raise ValueError("Medidas produzem cortes nÃ£o positivos.")
    if largura_corte > receita.largura_bobina_m:
        raise ValueError("Largura de corte excede a bobina. Giro/emenda de tecido nÃ£o autorizado.")
    custos = []

    def insumo(especificacao, unidade):
        if especificacao.unidade_tecnica != unidade:
            raise ValueError("Unidade tÃ©cnica incompatÃ­vel na receita RolÃ´.")
        cadastro = db.query(ProdutoDB).filter(
            ProdutoDB.id == especificacao.produto_id, ProdutoDB.empresa_id == empresa_id,
        ).one_or_none()
        if cadastro is None or cadastro.codigo_interno != especificacao.codigo_interno:
            raise ValueError("Componente da receita ausente ou com identidade alterada.")
        if str(cadastro.situacao or "").casefold() != "ativo":
            raise ValueError("Componente da receita estÃ¡ inativo.")
        if str(cadastro.tipo_produto or "").casefold() not in {"componente", "insumo"}:
            raise ValueError("Receita exige insumo/componente, nÃ£o produto acabado.")
        if especificacao.base_preco == "CUSTO_CADASTRADO":
            custo = next((Decimal(str(v)) for v in (cadastro.custo_final, cadastro.valor_custo) if v and v > 0), None)
            if custo is None or not custo.is_finite():
                raise ValueError("Insumo sem custo cadastrado vÃ¡lido.")
            preco = custo
        else:
            preco = Decimal(str(especificacao.preco_compra))
            ipi = especificacao.ipi_percentual
            acrescimo = Decimal(1) if ipi is None else 1 + Decimal(str(ipi)) / 100
            custo = preco * acrescimo / Decimal(str(especificacao.unidades_por_compra))
        custos.append({
            "produto_id": cadastro.id, "codigo": cadastro.codigo_interno, "nome": cadastro.nome,
            "unidade_tecnica": unidade, "preco_compra": float(preco),
            "ipi_percentual": especificacao.ipi_percentual if especificacao.base_preco == "TABELA_2" else None,
            "base_preco": especificacao.base_preco, "unidades_por_compra": especificacao.unidades_por_compra,
            "custo_unitario_tecnico": float(custo), "origem": especificacao.origem,
        })
        return {"codigo": cadastro.codigo_interno, "nome": cadastro.nome,
                "unidade": unidade, "valor_custo": float(custo)}

    if receita.tecido.unidades_por_compra != receita.largura_bobina_m:
        raise ValueError("ConversÃ£o de tecido ML/MÂ² incompatÃ­vel com a largura da bobina.")
    catalogo = {"tecido": insumo(receita.tecido, "M2"), "tubo": insumo(receita.tubos[bitola], "ML")}
    if manual:
        catalogo["comando"] = insumo(receita.comandos[bitola], "KIT")
    else:
        catalogo["motor_rolo"] = insumo(receita.motores[bitola], "UN")
        catalogo["kit_motor_rolo"] = insumo(receita.kits_motor[bitola], "KIT")
    catalogo.update({nome: insumo(receita.componentes[nome], unidade) for nome, unidade in componentes_exigidos.items()})
    # O motor V2 exige a chave especÃ­fica da bitola jÃ¡ validada pela receita.
    # Preserva as chaves genÃ©ricas usadas no relatÃ³rio e todas as fitas originais.
    diametro_chave = bitola.replace("mm", "")
    catalogo[f"tubo_{diametro_chave}"] = catalogo["tubo"]
    if manual:
        catalogo[f"comando_{diametro_chave}"] = catalogo["comando"]
    opcoes = {"acionamento": entrada.acionamento, "perda_tecido_percentual": 5.0,
              "desconto_largura_tubo_base": 0.025, "desconto_largura_tecido": 0.03,
              "sobra_altura_tecido": 0.15}
    if receita.faixas_tubo:
        opcoes["selecao_tubo"] = selecao
    calculo = calcular_produto_sob_medida(
        "RolÃ´", entrada.largura, entrada.altura, entrada.quantidade, catalogo=catalogo,
        opcoes=opcoes,
    )
    quantidade_componentes = 10 if manual else 9
    if calculo.alertas or len(calculo.componentes) != quantidade_componentes or calculo.custo_total <= 0:
        raise ValueError("Receita RolÃ´ incompleta ou sem custo vÃ¡lido.")
    compra_tecido = None
    if receita.custeio_tecido == "FAIXA_INTEGRAL_ML":
        tecido = next(c for c in calculo.componentes if c.categoria == "Tecido")
        quantidade_ml = (Decimal(str(entrada.altura)) + Decimal("0.15")) * entrada.quantidade * Decimal("1.05")
        preco_ml = Decimal(str(custos[0]["custo_unitario_tecnico"])) * Decimal(str(receita.largura_bobina_m))
        custo_compra = quantidade_ml * preco_ml
        # O corte continua em M2; alocar o custo da faixa inteira sem creditar a sobra lateral.
        tecido.custo_total = round(float(custo_compra), 4)
        tecido.custo_unitario = round(float(preco_ml / Decimal(str(largura_corte))), 4)
        tecido.regra += "; custo de faixa integral ML, sem reaproveitamento de sobras"
        calculo.custo_total = round(sum(c.custo_total for c in calculo.componentes), 4)
        compra_tecido = {"quantidade_compra_ml": float(quantidade_ml), "preco_compra_ml_com_ipi": float(preco_ml),
                         "custo_compra": tecido.custo_total, "custeio": receita.custeio_tecido}
        custos[0].update(compra_tecido)
    area = calcular_area_faturavel(largura=entrada.largura, altura=entrada.altura,
                                  quantidade=entrada.quantidade, unidade_venda=produto.unidade_venda)
    if area.area_faturavel_m2 <= 0:
        raise ValueError("Ãrea comercial invÃ¡lida.")
    custo = Decimal(str(calculo.custo_total))
    custo_comercial = custo
    incluir_kit = not manual and entrada.incluir_kit_instalacao is not False

    if not manual and not incluir_kit:
        custo_kit = (
            Decimal(str(catalogo["kit_motor_rolo"]["valor_custo"]))
            * Decimal(str(entrada.quantidade))
        )
        custo_comercial = max(Decimal("0"), custo - custo_kit)

    preco_tecnico = _dinheiro(
        custo_comercial * MULTIPLICADORES[entrada.perfil_comercial]
        / area.area_faturavel_m2
    )

    preco = preco_tecnico
    custo_referencia = None
    origem_preco = "RECEITA_TECNICA_EMPRESA"

    # Protecao comercial de produtos fabricados por m2.
    # O custo industrial nao substitui a referencia comercial.
    if (
        produto.empresa_id == empresa_id
        and manual
        and str(produto.tipo_produto or "").strip().casefold() == "produto fabricado"
        and str(produto.modelo_tecnico or "").strip().upper() == "ROLO"
        and str(produto.unidade_venda or "").strip().upper() in {"M2", "M\u00b2"}
    ):
        custo_referencia = _custo_referencia_comercial(produto)

        if custo_referencia.is_finite() and custo_referencia > 0:
            preco_referencia = _preco_produto(
                produto, entrada.perfil_comercial
            )

            if preco_referencia > preco_tecnico:
                preco = preco_referencia
                origem_preco = "TABELA_COMERCIAL_PROTEGIDA"
        else:
            custo_referencia = None

    subtotal = _dinheiro(max(Decimal(0), preco * area.area_faturavel_m2 - Decimal(str(entrada.desconto))))
    componentes = _extrair_componentes_rolo(calculo, selecao.diametro, entrada.acionamento)
    if manual:
        componentes["comando"]["observacao"] = catalogo["comando"]["nome"]
    else:
        for chave_manual in ("comando", "corrente", "emenda_corrente"):
            componentes.pop(chave_manual, None)
        componentes["motor"] = {"produto_id": receita.motores[bitola].produto_id,
                                 "codigo": catalogo["motor_rolo"]["codigo"],
                                 "nome": catalogo["motor_rolo"]["nome"], "quantidade_un": entrada.quantidade}
        if conjunto:
            componentes["motor"].update(torque_nm=conjunto.torque_nm, tecnologia=conjunto.tecnologia)
        componentes["acessorios"] = [{
            "produto_id": receita.kits_motor[bitola].produto_id,
            "codigo": catalogo["kit_motor_rolo"]["codigo"],
            "nome": catalogo["kit_motor_rolo"]["nome"], "quantidade": entrada.quantidade,
            "unidade": "KIT",
            "inclusao_comercial": incluir_kit,
        }]
        if conjunto_dinamico:
            perfil = conjunto_dinamico["perfil"]
            config_motor = _configuracao_equivalencia(conjunto_dinamico["motor_equivalencia"])
            componentes["motor"].update(
                torque_nm=float(config_motor["torque_nm"]),
                tecnologia=conjunto_dinamico["tecnologia"],
                perfil_tubo=perfil["perfil"],
                tubo_mm=perfil["diametro"],
                carga_estimada_kg=(
                    round(
                        entrada.largura * entrada.altura
                        * perfil["peso_estimado_kg_m2"]
                        + perfil["peso_barra"], 3
                    )
                    if perfil["peso_estimado_kg_m2"] is not None
                    and perfil["peso_barra"] is not None
                    else None
                ),
                carga_pendente=perfil.get("carga_pendente", False),
                status_validacao_carga=(
                    "PENDENTE"
                    if perfil.get("carga_pendente", False)
                    else "COMPATIVEL_COM_ESTIMATIVA"
                ),
                capacidade_kg=perfil["peso"],
            )
    componentes["tubo"]["produto_codigo"] = catalogo["tubo"]["codigo"]
    componentes["tecido"].update(produto_id=receita.tecido.produto_id, cor=receita.cor_tecido,
                                  largura_bobina_m=receita.largura_bobina_m)
    if compra_tecido is not None:
        componentes["tecido"].update(compra_tecido)
    return {
        "modelo": "ROLÔ", "tipo_acionamento": entrada.acionamento.upper(), "quantidade_pecas": entrada.quantidade,
        "area_real_m2": area.area_real_m2, "area_faturavel_m2": area.area_faturavel_m2,
        "minimo_faturavel_aplicado": area.minimo_faturavel_aplicado, "bitola_tecnica": bitola,
        "acionamento_permitido": entrada.acionamento, "requer_confirmacao_vendedor": selecao.requer_confirmacao_vendedor,
        "observacao_tecnica": selecao.observacao, "fabricacao_por_peca": asdict(calculo),
        "componentes_tecnicos": componentes, "custo_tecnico": float(custo), "custo_cadastrado": float(custo_referencia) if custo_referencia is not None else None,
        "custo_base_comercial": float(custo_comercial),
        "incluir_kit_instalacao": incluir_kit,
        "preco_unitario": preco, "subtotal": subtotal, "preco_disponivel": True, "alertas": [],
        "origem_preco": origem_preco,
        "receita": {"versao": receita.versao, "acabamento": receita.acabamento, "custos": custos,
                   "fontes_motorizacao": list(EMTECO_ROLO_REFERENCES) if conjunto_dinamico else [],
                   "custeio_tecido": receita.custeio_tecido,
                   "consumo_tecido": "Corte com altura +15cm e perda de 5%; faixa integral ML por peÃ§a, sem crÃ©dito de sobras."
                   if compra_tecido is not None else "Ãrea de corte com perda de 5%; custo ML dividido pela bobina."},
        "aviso": "Preço pela receita vinculada: consumo do motor existente, custos documentados e multiplicador comercial. Não inclui serviços livres, frete ou montagem não cadastrados.",
    }
