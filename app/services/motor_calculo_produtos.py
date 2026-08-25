from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import math


@dataclass
class ComponenteCalculado:
    codigo: str = ""
    nome: str = ""
    categoria: str = ""
    regra: str = ""
    quantidade: float = 0.0
    unidade: str = "UN"
    custo_unitario: float = 0.0
    custo_total: float = 0.0
    perda_percentual: float = 0.0


@dataclass
class ResultadoCalculoProduto:
    modelo: str
    largura: float
    altura: float
    quantidade_produto: float
    custo_total: float = 0.0
    componentes: List[ComponenteCalculado] = field(default_factory=list)
    alertas: List[str] = field(default_factory=list)


def _float(valor: Any, padrao: float=0.0) -> float:
    try:
        if valor is None:
            return padrao
        if isinstance(valor, str):
            valor = valor.replace("R$", "").replace("%", "").replace(".", "").replace(",", ".").strip()
            if not valor:
                return padrao
        return float(valor)
    except Exception:
        return padrao


def _norm(txt: Any) -> str:
    return str(txt or "").strip().lower()


def _pegar(catalogo: Dict[str, Dict[str, Any]], *chaves: str) -> Optional[Dict[str, Any]]:
    for chave in chaves:
        if chave in catalogo and catalogo.get(chave):
            item = dict(catalogo[chave])
            item["_chave_motor"] = chave
            return item
    return None


def _add(resultado: ResultadoCalculoProduto, item: Optional[Dict[str, Any]], categoria: str, regra: str, quantidade: float, unidade_padrao: str="UN", perda_percentual: float=0.0):
    if not item:
        resultado.alertas.append(f"Componente obrigatório não informado no carrinho: {categoria}.")
        return

    qtd = max(_float(quantidade), 0.0)
    custo_unit = _float(item.get("custo_unitario") or item.get("custo") or item.get("valor_custo"))
    unidade = str(item.get("unidade") or unidade_padrao or "UN").strip()
    custo_total = qtd * custo_unit

    resultado.componentes.append(
        ComponenteCalculado(
            codigo=str(item.get("codigo") or ""),
            nome=str(item.get("nome") or categoria),
            categoria=categoria,
            regra=regra,
            quantidade=round(qtd, 4),
            unidade=unidade,
            custo_unitario=round(custo_unit, 4),
            custo_total=round(custo_total, 4),
            perda_percentual=round(_float(perda_percentual), 4),
        )
    )
    resultado.custo_total += custo_total


def _calcular_rolo(modelo: str, largura: float, altura: float, quantidade_produto: float, catalogo: Dict[str, Dict[str, Any]], opcoes: Dict[str, Any]) -> ResultadoCalculoProduto:
    resultado = ResultadoCalculoProduto(modelo=modelo, largura=largura, altura=altura, quantidade_produto=quantidade_produto)

    perda_tecido = _float(opcoes.get("perda_tecido_percentual"), 5.0)
    desconto_tubo_base = _float(opcoes.get("desconto_largura_tubo_base"), 0.025)
    desconto_tecido = _float(opcoes.get("desconto_largura_tecido"), 0.03)
    sobra_tecido = _float(opcoes.get("sobra_altura_tecido"), 0.15)

    largura_tecido = max(largura - desconto_tecido, 0.0)
    altura_tecido = max(altura + sobra_tecido, 0.0)
    qtd_tecido_m2 = largura_tecido * altura_tecido * (1 + perda_tecido / 100.0) * quantidade_produto

    qtd_linear_tubo_base = max(largura - desconto_tubo_base, 0.0) * quantidade_produto
    qtd_linear_fita_base = max(largura - desconto_tecido, 0.0) * quantidade_produto
    qtd_corrente = min(max(altura * 2, 0.0), 3.0) * quantidade_produto

    tubo = _pegar(catalogo, "tubo_32", "tubo_38", "tubo")
    comando = _pegar(catalogo, "comando_32", "comando_38", "comando")

    _add(resultado, _pegar(catalogo, "tecido"), "Tecido", "Largura -3cm x altura +15cm", qtd_tecido_m2, "M²", perda_tecido)
    _add(resultado, tubo, "Tubo", "Largura -2,5cm", qtd_linear_tubo_base, "ML")
    _add(resultado, _pegar(catalogo, "fita_tubo"), "Fita tubo", "Fita dupla face 2,5 • largura -2,5cm", qtd_linear_tubo_base, "ML")
    _add(resultado, _pegar(catalogo, "base", "perfil"), "Perfil/Base", "Base chata/cônica • largura -2,5cm", qtd_linear_tubo_base, "ML")
    _add(resultado, _pegar(catalogo, "fita_base"), "Fita base", "Fita plástica 1,5 • largura -3cm", qtd_linear_fita_base, "ML")
    _add(resultado, _pegar(catalogo, "espaguete_base"), "Espaguete base", "Espaguete 3mm • largura -3cm", qtd_linear_fita_base, "ML")
    _add(resultado, _pegar(catalogo, "corrente"), "Corrente", "Altura dupla, máx. 3m", qtd_corrente, "ML")
    _add(resultado, _pegar(catalogo, "emenda_corrente"), "Emenda corrente", "Fixo", 3 * quantidade_produto, "UN")
    _add(resultado, _pegar(catalogo, "tampa_base"), "Tampa da base", "Fixo", 2 * quantidade_produto, "UN")
    _add(resultado, comando, "Comando", "Fixo • kit compatível com tubo", 1 * quantidade_produto, "KIT")

    resultado.custo_total = round(resultado.custo_total, 4)
    return resultado


def _calcular_generico(modelo: str, largura: float, altura: float, quantidade_produto: float, catalogo: Dict[str, Dict[str, Any]], opcoes: Dict[str, Any]) -> ResultadoCalculoProduto:
    resultado = ResultadoCalculoProduto(modelo=modelo, largura=largura, altura=altura, quantidade_produto=quantidade_produto)
    perda = _float(opcoes.get("perda_tecido_percentual") or opcoes.get("perda_percentual") or opcoes.get("perda_lona_percentual"), 5.0)

    for chave, item in (catalogo or {}).items():
        unidade = str(item.get("unidade") or "UN").upper()
        if unidade in ["M²", "M2", "MT²"]:
            qtd = max(largura * altura, 0.0) * (1 + perda / 100.0) * quantidade_produto
            regra = "Área largura x altura"
        elif unidade in ["ML", "M", "MT", "METRO", "METRO LINEAR"]:
            qtd = max(largura, altura, 0.0) * quantidade_produto
            regra = "Metro linear conforme maior medida"
        else:
            qtd = 1 * quantidade_produto
            regra = "Fixo"
        _add(resultado, item, str(chave).replace("_", " ").title(), regra, qtd, unidade, perda if unidade in ["M²", "M2", "MT²"] else 0)

    if not catalogo:
        resultado.alertas.append("Nenhum item recebido no catálogo do carrinho. Monte o carrinho antes de calcular.")

    resultado.custo_total = round(resultado.custo_total, 4)
    return resultado


def calcular_produto_sob_medida(modelo: str, largura: float, altura: float, quantidade: float=1, catalogo: Optional[Dict[str, Dict[str, Any]]]=None, opcoes: Optional[Dict[str, Any]]=None) -> ResultadoCalculoProduto:
    """
    Motor SmartTec ajustado para NÃO buscar componentes por nome.

    Ele calcula somente com os itens enviados no parâmetro `catalogo`, que vêm do carrinho/receita técnica.
    Assim não mistura Rolô, Romana, Horizontal, Double Vision, Painel etc.
    """
    catalogo = catalogo or {}
    opcoes = opcoes or {}

    largura = _float(largura)
    altura = _float(altura)
    quantidade_produto = max(_float(quantidade, 1.0), 1.0)
    modelo_norm = _norm(modelo)

    if largura <= 0 or altura <= 0:
        r = ResultadoCalculoProduto(modelo=modelo or "", largura=largura, altura=altura, quantidade_produto=quantidade_produto)
        r.alertas.append("Informe largura e altura maiores que zero para calcular.")
        return r

    if modelo_norm.startswith("rol") or "rolo" in modelo_norm or "rolô" in modelo_norm:
        return _calcular_rolo(modelo or "Rolô", largura, altura, quantidade_produto, catalogo, opcoes)

    return _calcular_generico(modelo or "Sob medida", largura, altura, quantidade_produto, catalogo, opcoes)
