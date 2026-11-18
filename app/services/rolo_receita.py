"""Receitas configuráveis por empresa; catálogo/fornecedor não vivem no motor."""
from dataclasses import asdict
from decimal import Decimal

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.empresa import EmpresaDB
from app.models.produto import ProdutoDB
from app.schemas.rolo_receita import ReceitaRolo
from app.services.area_faturavel import calcular_area_faturavel
from app.services.composicao_comercial import MULTIPLICADORES, _dinheiro
from app.services.motor_calculo_produtos import calcular_produto_sob_medida
from app.services.rolo_simulacao import (
    RoloSimulacaoInput, _extrair_componentes_rolo, _tipo_rolo, simular_rolo,
)
from app.technical.rules.rolo import MotorObrigatorioErro, selecionar_tubo_rolo


COMPONENTES = {
    "fita_tubo": "ML", "base": "ML", "fita_base": "ML", "espaguete_base": "ML",
    "corrente": "ML", "emenda_corrente": "UN", "tampa_base": "UN",
}


def simular_rolo_catalogo(db: Session, produto: ProdutoDB, entrada: RoloSimulacaoInput, empresa_id: int):
    if produto.empresa_id != empresa_id or produto.id != entrada.produto_id:
        raise ValueError("Produto Rolô incompatível com a empresa e item selecionados.")
    empresa = db.query(EmpresaDB).filter_by(id=empresa_id, status="ATIVA").one_or_none()
    if empresa is None:
        raise ValueError("Empresa ativa não encontrada.")
    if not isinstance(empresa.configuracoes, dict):
        raise ValueError("Configuração da empresa inválida.")
    receitas = empresa.configuracoes.get("receitas_rolo_v1", {})
    if not isinstance(receitas, dict):
        raise ValueError("Configuração de receitas Rolô inválida.")
    if str(produto.id) not in receitas:
        return simular_rolo(produto, entrada)
    try:
        receita = ReceitaRolo.model_validate(receitas[str(produto.id)])
    except ValidationError as exc:
        raise ValueError("Receita Rolô inválida. Revise os vínculos e custos cadastrados.") from exc
    if _tipo_rolo(produto) != "MANUAL" or entrada.acionamento != "manual":
        raise ValueError("Receita liberada somente para produto Rolô manual.")
    if entrada.cor and entrada.cor.strip().casefold() != receita.cor_tecido.casefold():
        raise ValueError("Cor selecionada diferente da variação vinculada ao tecido.")
    if set(receita.componentes) != set(COMPONENTES):
        raise ValueError("Receita Rolô sem todos os componentes obrigatórios.")
    try:
        selecao = selecionar_tubo_rolo(entrada.largura, entrada.acionamento)
    except MotorObrigatorioErro as exc:
        raise ValueError(str(exc)) from exc
    bitola = selecao.diametro.value
    if bitola not in receita.tubos or bitola not in receita.comandos:
        raise ValueError(f"Receita sem conjunto tubo/comando {bitola} validado. Orçamento bloqueado.")
    if any(i.diametro_mm != int(bitola.replace("mm", "")) for i in
           (receita.tubos[bitola], receita.comandos[bitola])):
        raise ValueError("Diâmetro do tubo/comando incompatível com a regra técnica.")
    largura_corte = entrada.largura - 0.03
    if largura_corte <= 0 or entrada.altura <= 0.025:
        raise ValueError("Medidas produzem cortes não positivos.")
    if largura_corte > receita.largura_bobina_m:
        raise ValueError("Largura de corte excede a bobina. Giro/emenda de tecido não autorizado.")
    custos = []

    def insumo(especificacao, unidade):
        if especificacao.unidade_tecnica != unidade:
            raise ValueError("Unidade técnica incompatível na receita Rolô.")
        cadastro = db.query(ProdutoDB).filter(
            ProdutoDB.id == especificacao.produto_id, ProdutoDB.empresa_id == empresa_id,
        ).one_or_none()
        if cadastro is None or cadastro.codigo_interno != especificacao.codigo_interno:
            raise ValueError("Componente da receita ausente ou com identidade alterada.")
        if str(cadastro.situacao or "").casefold() != "ativo":
            raise ValueError("Componente da receita está inativo.")
        if str(cadastro.tipo_produto or "").casefold() not in {"componente", "insumo"}:
            raise ValueError("Receita exige insumo/componente, não produto acabado.")
        if especificacao.base_preco == "CUSTO_CADASTRADO":
            custo = next((Decimal(str(v)) for v in (cadastro.custo_final, cadastro.valor_custo) if v and v > 0), None)
            if custo is None or not custo.is_finite():
                raise ValueError("Insumo sem custo cadastrado válido.")
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
        raise ValueError("Conversão de tecido ML/M² incompatível com a largura da bobina.")
    catalogo = {"tecido": insumo(receita.tecido, "M2"), "tubo": insumo(receita.tubos[bitola], "ML"),
                "comando": insumo(receita.comandos[bitola], "KIT")}
    catalogo.update({nome: insumo(receita.componentes[nome], unidade) for nome, unidade in COMPONENTES.items()})
    # O motor V2 exige a chave específica da bitola já validada pela receita.
    # Preserva as chaves genéricas usadas no relatório e todas as fitas originais.
    diametro_chave = bitola.replace("mm", "")
    catalogo[f"tubo_{diametro_chave}"] = catalogo["tubo"]
    catalogo[f"comando_{diametro_chave}"] = catalogo["comando"]
    calculo = calcular_produto_sob_medida(
        "Rolô", entrada.largura, entrada.altura, entrada.quantidade, catalogo=catalogo,
        opcoes={"acionamento": entrada.acionamento, "perda_tecido_percentual": 5.0,
                "desconto_largura_tubo_base": 0.025, "desconto_largura_tecido": 0.03,
                "sobra_altura_tecido": 0.15},
    )
    if calculo.alertas or len(calculo.componentes) != 10 or calculo.custo_total <= 0:
        raise ValueError("Receita Rolô incompleta ou sem custo válido.")
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
        raise ValueError("Área comercial inválida.")
    custo = Decimal(str(calculo.custo_total))
    preco = _dinheiro(custo * MULTIPLICADORES[entrada.perfil_comercial] / area.area_faturavel_m2)
    subtotal = _dinheiro(max(Decimal(0), preco * area.area_faturavel_m2 - Decimal(str(entrada.desconto))))
    componentes = _extrair_componentes_rolo(calculo, selecao.diametro, entrada.acionamento)
    componentes["comando"]["observacao"] = catalogo["comando"]["nome"]
    componentes["tubo"]["produto_codigo"] = catalogo["tubo"]["codigo"]
    componentes["tecido"].update(produto_id=receita.tecido.produto_id, cor=receita.cor_tecido,
                                  largura_bobina_m=receita.largura_bobina_m)
    if compra_tecido is not None:
        componentes["tecido"].update(compra_tecido)
    return {
        "modelo": "ROLÔ", "tipo_acionamento": "MANUAL", "quantidade_pecas": entrada.quantidade,
        "area_real_m2": area.area_real_m2, "area_faturavel_m2": area.area_faturavel_m2,
        "minimo_faturavel_aplicado": area.minimo_faturavel_aplicado, "bitola_tecnica": bitola,
        "acionamento_permitido": "manual", "requer_confirmacao_vendedor": selecao.requer_confirmacao_vendedor,
        "observacao_tecnica": selecao.observacao, "fabricacao_por_peca": asdict(calculo),
        "componentes_tecnicos": componentes, "custo_tecnico": float(custo), "custo_cadastrado": None,
        "preco_unitario": preco, "subtotal": subtotal, "preco_disponivel": True, "alertas": [],
        "origem_preco": "RECEITA_TECNICA_EMPRESA",
        "receita": {"versao": receita.versao, "acabamento": receita.acabamento, "custos": custos,
                   "custeio_tecido": receita.custeio_tecido,
                   "consumo_tecido": "Corte com altura +15cm e perda de 5%; faixa integral ML por peça, sem crédito de sobras."
                   if compra_tecido is not None else "Área de corte com perda de 5%; custo ML dividido pela bobina."},
        "aviso": "Preço pela receita vinculada: consumo do motor existente, custos documentados e multiplicador comercial. Não inclui serviços livres, frete ou montagem não cadastrados.",
    }
