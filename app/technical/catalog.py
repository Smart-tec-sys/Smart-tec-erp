"""Catálogo técnico universal, versionado exclusivamente em código."""

from types import MappingProxyType

from .models import TechnicalFunction, TechnicalFunctionStatus
from .units import TechnicalUnit, VALID_TECHNICAL_UNITS


VALID_TECHNICAL_FAMILIES = frozenset({
    "ROMANA", "ROLO", "DOUBLE_VISION", "HORIZONTAL", "VERTICAL",
    "PAINEL", "CORTINAS", "SHANGRILA", "MOTORIZACAO",
})
GRUPO_COMANDO_ROMANA = "COMANDO_ROMANA"
GRUPO_ACIONAMENTO_CORRENTE_ROMANA = "ACIONAMENTO_CORRENTE_ROMANA"
GRUPO_TUBO_ROLO = "TUBO_ROLO"
GRUPO_COMANDO_ROLO = "COMANDO_ROLO"


def _f(codigo, nome, familia, unidade, descricao, *, requeridos=(),
       atributos=None, status=TechnicalFunctionStatus.ATIVA, grupo=None):
    return TechnicalFunction(
        codigo=codigo, nome=nome, familia=familia, unidade_tecnica=unidade,
        descricao=descricao, atributos_requeridos=frozenset(requeridos),
        atributos_tecnicos=atributos or {}, status=status,
        grupo_alternativa=grupo,
    )


_ROMANA = (
    _f("TECIDO_ROMANA", "Tecido da Romana", "ROMANA", TechnicalUnit.M2, "Corpo têxtil da peça.", status=TechnicalFunctionStatus.SEM_REGRA),
    _f("VARETA_ROMANA", "Vareta da Romana", "ROMANA", TechnicalUnit.M, "Vareta estrutural.", status=TechnicalFunctionStatus.SEM_REGRA),
    _f("TAMPA_VARETA_ROMANA", "Tampa de vareta da Romana", "ROMANA", TechnicalUnit.UN, "Fechamento das extremidades das varetas."),
    _f("CABECEIRA_ROMANA", "Cabeceira da Romana", "ROMANA", TechnicalUnit.M, "Perfil superior da peça.", status=TechnicalFunctionStatus.SEM_REGRA),
    _f("EIXO_ROMANA", "Eixo da Romana", "ROMANA", TechnicalUnit.M, "Eixo do conjunto de acionamento.", status=TechnicalFunctionStatus.SEM_REGRA),
    _f("BASE_ROMANA", "Base da Romana", "ROMANA", TechnicalUnit.M, "Perfil inferior da peça.", status=TechnicalFunctionStatus.SEM_REGRA),
    _f("TAMPA_BASE_ROMANA", "Tampa da base da Romana", "ROMANA", TechnicalUnit.UN, "Fechamento das extremidades da base.", status=TechnicalFunctionStatus.SEM_REGRA),
    _f("CAVALETE_CARRETEL_ROMANA", "Cavalete com carretel da Romana", "ROMANA", TechnicalUnit.UN, "Conjunto de condução conforme faixa de largura."),
    _f("GUIA_CORDA_ROMANA", "Guia de corda da Romana", "ROMANA", TechnicalUnit.UN, "Guia aplicada nas varetas pares."),
    _f("CORDA_ROMANA_1MM", "Corda da Romana 1 mm", "ROMANA", TechnicalUnit.M, "Linha de sustentação até após a última vareta.", atributos={"bitola_mm": 1.0}),
    _f("ESPAGUETE_ROMANA_2_5MM", "Espaguete da Romana 2,5 mm", "ROMANA", TechnicalUnit.M, "Reforço da cabeceira e das varetas.", atributos={"bitola_mm": 2.5}),
    _f("ESPAGUETE_BASE_ROMANA_3MM", "Espaguete da base da Romana 3 mm", "ROMANA", TechnicalUnit.M, "Reforço da base inferior.", atributos={"bitola_mm": 3.0}),
    _f("COMANDO_NORMAL_ROMANA", "Comando normal da Romana", "ROMANA", TechnicalUnit.UN, "Alternativa de comando manual.", grupo=GRUPO_COMANDO_ROMANA),
    _f("COMANDO_REDUCAO_ROMANA", "Comando com redução da Romana", "ROMANA", TechnicalUnit.UN, "Alternativa de comando manual recomendável conforme largura.", grupo=GRUPO_COMANDO_ROMANA),
    _f("CORRENTE_SEM_FIM_ROMANA_BOLA10", "Corrente sem fim Bola 10 da Romana", "ROMANA", TechnicalUnit.UN, "Alternativa pronta por medida de referência.", requeridos={"medida_m"}, grupo=GRUPO_ACIONAMENTO_CORRENTE_ROMANA),
    _f("CORRENTE_JUTA_BOLA10_PERSONALIZADA", "Corrente Bola 10 personalizada da Romana", "ROMANA", TechnicalUnit.M, "Alternativa com medida técnica informada.", requeridos={"medida_personalizada_m"}, grupo=GRUPO_ACIONAMENTO_CORRENTE_ROMANA),
    _f("PENDULO_CORRENTE_ROMANA", "Pêndulo da corrente da Romana", "ROMANA", TechnicalUnit.UN, "Acabamento do acionamento por corrente.", status=TechnicalFunctionStatus.SEM_REGRA),
)

_ROLO = (
    _f("TECIDO_ROLO", "Tecido da Rolô", "ROLO", TechnicalUnit.M2, "Corpo têxtil da peça."),
    _f("TUBO_ROLO_32MM", "Tubo Rolô 32 mm", "ROLO", TechnicalUnit.M, "Alternativa estrutural de tubo.", atributos={"diametro_mm": 32.0}, grupo=GRUPO_TUBO_ROLO),
    _f("TUBO_ROLO_38MM", "Tubo Rolô 38 mm", "ROLO", TechnicalUnit.M, "Alternativa estrutural de tubo.", atributos={"diametro_mm": 38.0}, grupo=GRUPO_TUBO_ROLO),
    _f("TUBO_ROLO_43MM", "Tubo Rolô 43 mm", "ROLO", TechnicalUnit.M, "Alternativa estrutural de tubo para larguras > 2,50m até 3,20m.", atributos={"diametro_mm": 43.0}, grupo=GRUPO_TUBO_ROLO, status=TechnicalFunctionStatus.PROVISORIA),
    _f("TUBO_ROLO_65MM", "Tubo Rolô 65 mm", "ROLO", TechnicalUnit.M, "Alternativa estrutural de tubo para motorização em larguras > 3,20m.", atributos={"diametro_mm": 65.0}, grupo=GRUPO_TUBO_ROLO, status=TechnicalFunctionStatus.PROVISORIA),
    _f("TUBO_ROLO_70MM", "Tubo Rolô 70 mm", "ROLO", TechnicalUnit.M, "Alternativa estrutural de tubo para casos especiais (ex.: pé-direito) em motorização > 3,20m.", atributos={"diametro_mm": 70.0}, grupo=GRUPO_TUBO_ROLO, status=TechnicalFunctionStatus.PENDENTE_VALIDACAO),
    _f("FITA_TUBO_ROLO", "Fita do tubo da Rolô", "ROLO", TechnicalUnit.M, "Fita aplicada ao tubo."),
    _f("BASE_ROLO", "Base da Rolô", "ROLO", TechnicalUnit.M, "Perfil inferior da peça."),
    _f("FITA_BASE_ROLO", "Fita da base da Rolô", "ROLO", TechnicalUnit.M, "Fita aplicada à base."),
    _f("ESPAGUETE_BASE_ROLO", "Espaguete da base da Rolô", "ROLO", TechnicalUnit.M, "Reforço aplicado à base."),
    _f("CORRENTE_ROLO", "Corrente da Rolô", "ROLO", TechnicalUnit.M, "Corrente de acionamento."),
    _f("EMENDA_CORRENTE_ROLO", "Emenda de corrente da Rolô", "ROLO", TechnicalUnit.UN, "Emenda do circuito de corrente."),
    _f("TAMPA_BASE_ROLO", "Tampa da base da Rolô", "ROLO", TechnicalUnit.UN, "Fechamento das extremidades da base."),
    _f("COMANDO_ROLO_32MM", "Comando Rolô para tubo 32 mm", "ROLO", TechnicalUnit.KIT, "Alternativa compatível com tubo 32 mm.", atributos={"diametro_tubo_mm": 32.0}, grupo=GRUPO_COMANDO_ROLO),
    _f("COMANDO_ROLO_38MM", "Comando Rolô para tubo 38 mm", "ROLO", TechnicalUnit.KIT, "Alternativa compatível com tubo 38 mm.", atributos={"diametro_tubo_mm": 38.0}, grupo=GRUPO_COMANDO_ROLO),
    _f("COMANDO_ROLO_43MM", "Comando Rolô para tubo 43 mm", "ROLO", TechnicalUnit.KIT, "Alternativa compatível com tubo 43 mm.", atributos={"diametro_tubo_mm": 43.0}, grupo=GRUPO_COMANDO_ROLO, status=TechnicalFunctionStatus.PROVISORIA),
)

_DOUBLE_VISION_DATA = (
    ("TECIDO_DOUBLE_VISION", "Tecido Double Vision", TechnicalUnit.M2),
    ("TUBO_DOUBLE_VISION_32MM", "Tubo Double Vision 32 mm", TechnicalUnit.M),
    ("TUBO_DOUBLE_VISION_38MM", "Tubo Double Vision 38 mm", TechnicalUnit.M),
    ("TUBO_DOUBLE_VISION_41MM", "Tubo Double Vision 41 mm", TechnicalUnit.M),
    ("COMANDO_DOUBLE_VISION", "Comando Double Vision", TechnicalUnit.KIT),
    ("CORRENTE_BOLA10_DOUBLE_VISION", "Corrente Bola 10 Double Vision", TechnicalUnit.M),
    ("EMENDA_CORRENTE_DOUBLE_VISION", "Emenda de corrente Double Vision", TechnicalUnit.UN),
    ("EIXO_BASE_DOUBLE_VISION", "Eixo da base Double Vision", TechnicalUnit.M),
    ("BASE_CUNHA_DOUBLE_VISION", "Base cunha Double Vision", TechnicalUnit.M),
    ("TAMPA_EIXO_DOUBLE_VISION", "Tampa de eixo Double Vision", TechnicalUnit.UN),
    ("TAMPA_BASE_DOUBLE_VISION", "Tampa da base Double Vision", TechnicalUnit.UN),
    ("GRAPA_DOUBLE_VISION_40MM", "Grapa Double Vision 40 mm", TechnicalUnit.UN),
    ("BARRA_ESTABILIZADORA_DOUBLE_VISION", "Barra estabilizadora Double Vision", TechnicalUnit.M),
    ("BANDO_DOUBLE_VISION", "Bandô Double Vision", TechnicalUnit.M),
    ("TAMPA_BANDO_DOUBLE_VISION", "Tampa de bandô Double Vision", TechnicalUnit.UN),
    ("ESPAGUETE_DOUBLE_VISION_2_5MM", "Espaguete Double Vision 2,5 mm", TechnicalUnit.M),
    ("FITA_PLASTICA_DOUBLE_VISION_1_5MM", "Fita plástica Double Vision 1,5 mm", TechnicalUnit.M),
    ("MOTOR_DOUBLE_VISION", "Motor Double Vision", TechnicalUnit.UN),
    ("SUPORTE_ADAPTADOR_MOTOR_DOUBLE_VISION", "Suporte de motor Double Vision", TechnicalUnit.KIT),
    ("CONTROLE_MOTOR", "Controle de motor", TechnicalUnit.UN),
)
_DOUBLE_VISION = tuple(
    _f(code, name, "DOUBLE_VISION", unit, "Conceito confirmado; contrato produtivo ainda provisório.", status=TechnicalFunctionStatus.PROVISORIA)
    for code, name, unit in _DOUBLE_VISION_DATA
)

_OTHER_DATA = (
    ("LAMINA_HORIZONTAL", "Lâmina horizontal", "HORIZONTAL", TechnicalUnit.M),
    ("COMPONENTE_HORIZONTAL", "Componente horizontal", "HORIZONTAL", TechnicalUnit.UN),
    ("LAMINA_VERTICAL", "Lâmina vertical", "VERTICAL", TechnicalUnit.M),
    ("COMPONENTE_VERTICAL", "Componente vertical", "VERTICAL", TechnicalUnit.UN),
    ("TECIDO_PAINEL", "Tecido de painel", "PAINEL", TechnicalUnit.M2),
    ("COMPONENTE_PAINEL", "Componente de painel", "PAINEL", TechnicalUnit.UN),
    ("TECIDO_CORTINAS", "Tecido de cortinas", "CORTINAS", TechnicalUnit.M),
    ("COMPONENTE_CORTINAS", "Componente de cortinas", "CORTINAS", TechnicalUnit.UN),
    ("TECIDO_SHANGRILA", "Tecido Shangrila", "SHANGRILA", TechnicalUnit.M2),
    ("MOTOR_PERSIANA", "Motor de persiana", "MOTORIZACAO", TechnicalUnit.UN),
    ("ACESSORIO_MOTOR", "Acessório de motor", "MOTORIZACAO", TechnicalUnit.UN),
)
_OTHER = tuple(
    _f(code, name, family, unit, "Conceito identificado; regra produtiva pendente.", status=TechnicalFunctionStatus.PENDENTE_VALIDACAO)
    for code, name, family, unit in _OTHER_DATA
)

_FUNCTIONS = _ROMANA + _ROLO + _DOUBLE_VISION + _OTHER
FORBIDDEN_COMMERCIAL_TERMS = frozenset({
    "produto_id", "fornecedor_id", "sku", "codigo_comercial", "nome_comercial",
    "custo", "preco", "preço", "estoque", "fornecedor", "tenant",
})


def validate_technical_catalog(functions=_FUNCTIONS):
    codes = [function.codigo for function in functions]
    if len(codes) != len(set(codes)):
        raise ValueError("código técnico duplicado")
    for function in functions:
        if function.familia not in VALID_TECHNICAL_FAMILIES:
            raise ValueError(f"família técnica inválida: {function.familia}")
        if function.unidade_tecnica not in VALID_TECHNICAL_UNITS:
            raise ValueError(f"unidade técnica inválida: {function.unidade_tecnica}")
        searchable = " ".join((function.codigo, function.nome, function.descricao,
                               *function.atributos_requeridos,
                               *function.atributos_tecnicos)).casefold()
        found = {term for term in FORBIDDEN_COMMERCIAL_TERMS if term in searchable}
        if found:
            raise ValueError(f"função {function.codigo} contém termos comerciais: {sorted(found)}")


validate_technical_catalog()
TECHNICAL_CATALOG = MappingProxyType({item.codigo: item for item in _FUNCTIONS})


def get_technical_function(code):
    return TECHNICAL_CATALOG[code.strip().upper()]
