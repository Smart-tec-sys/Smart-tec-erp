from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy.orm import selectinload

from app.models.empresa import EmpresaDB
from app.models.pedido import PedidoDB
from app.models.produto import ProdutoDB
from app.models.producao import OrdemProducaoDB, PecaProducaoDB
from app.tenant.isolation import require_tenant

STATUS = ("AGUARDANDO", "CORTE", "MONTAGEM", "CONFERENCIA", "CONCLUIDA")
VENDAS_PERMITIDAS = {"ABERTO", "FATURADO", "CONCLUIDO"}


def _agora():
    return datetime.now(timezone.utc)


def _usuario(tenant):
    if tenant.user_id is None or not str(tenant.user_id).strip():
        raise PermissionError("Confirmação de fabricação exige usuário identificado. Entre com acesso autenticado.")
    return str(tenant.user_id)


def _venda(db, pedido_id, empresa_id):
    pedido = db.query(PedidoDB).options(selectinload(PedidoDB.itens)).filter(
        PedidoDB.id == pedido_id, PedidoDB.empresa_id == empresa_id,
    ).with_for_update().first()
    if pedido is None:
        raise LookupError("Venda não encontrada para a empresa ativa.")
    if pedido.status not in VENDAS_PERMITIDAS:
        raise ValueError("Venda cancelada ou com situação não suportada para fabricação.")
    return pedido


def obter(db, ordem_id, tenant, bloquear=False):
    query = db.query(OrdemProducaoDB).options(selectinload(OrdemProducaoDB.pecas)).filter(
        OrdemProducaoDB.id == ordem_id, OrdemProducaoDB.empresa_id == require_tenant(tenant),
    )
    ordem = (query.with_for_update() if bloquear else query).first()
    if ordem is None:
        raise LookupError("Ordem de produção não encontrada para a empresa ativa.")
    return ordem


def listar(db, pedido_id, tenant):
    return db.query(OrdemProducaoDB).options(selectinload(OrdemProducaoDB.pecas)).filter(
        OrdemProducaoDB.empresa_id == require_tenant(tenant),
        OrdemProducaoDB.pedido_id == pedido_id,
    ).order_by(OrdemProducaoDB.id.desc()).all()


def criar(db, pedido_id, tenant, confirmar):
    empresa_id = require_tenant(tenant)
    usuario = _usuario(tenant)
    if confirmar is not True:
        raise ValueError("Confirme explicitamente a fabricação da venda.")
    pedido = _venda(db, pedido_id, empresa_id)
    if listar(db, pedido_id, tenant):
        raise ValueError("Esta venda já possui ordem de produção; não é permitido duplicar peças.")
    empresa = db.query(EmpresaDB).filter(EmpresaDB.id == empresa_id, EmpresaDB.status == "ATIVA").first()
    if empresa is None:
        raise ValueError("Empresa ativa não encontrada.")
    itens = []
    pecas = []
    for item in pedido.itens:
        if item.tipo_item == "SERVICO":
            continue
        if item.tipo_item != "PRODUTO":
            raise ValueError("Tipo de item não suportado para fabricação.")
        quantidade = Decimal(str(item.quantidade))
        if not quantidade.is_finite() or quantidade <= 0 or quantidade != quantidade.to_integral_value():
            raise ValueError("Produção exige quantidade inteira positiva por item.")
        dados = {
            campo: deepcopy(getattr(item, campo))
            for campo in ("id", "produto_id", "modelo_tecnico", "material", "cor", "largura", "altura",
                          "acionamento", "lado_comando", "quantidade", "desconto", "dados_tecnicos",
                          "descricao", "codigo_interno", "observacao_item")
        }
        itens.append(jsonable_encoder(dados))
        for sequencia in range(1, int(quantidade) + 1):
            pecas.append(PecaProducaoDB(
                pedido_item_id=item.id, sequencia=sequencia, modelo=item.modelo_tecnico,
                tecido=item.material, cor=item.cor, largura=item.largura, altura=item.altura,
                acionamento=item.acionamento, ambiente="",
                observacoes=item.observacao_item or "", status="AGUARDANDO", historico=[],
            ))
    if not pecas:
        raise ValueError("Venda sem produtos para fabricar; serviços não geram peças.")
    ordem = OrdemProducaoDB(
        empresa_id=empresa_id, pedido_id=pedido.id, confirmado_por=usuario, confirmado_em=_agora(),
        snapshot=jsonable_encoder({
            "versao": 1, "empresa": empresa.nome, "pedido": pedido.numero,
            "prazo_entrega": pedido.prazo_entrega, "perfil_comercial": pedido.perfil_comercial,
            "itens": itens,
        }), pecas=pecas,
    )
    db.add(ordem)
    db.flush()
    return ordem


def _calcular(db, dados, perfil, empresa_id):
    item = SimpleNamespace(**dados)
    modelo = (item.modelo_tecnico or "").strip().upper().replace("_", " ")
    if modelo == "CORTINA":
        from app.services.cortina_simulacao import (
            componente_cortina_elegivel, entrada_cortina_item, simular_cortina_catalogo,
        )
        tecnicos = item.dados_tecnicos
        if not isinstance(tecnicos, dict) or not isinstance(tecnicos.get("cortina"), dict):
            return {}, ["Parâmetros de cortina ausentes ou inválidos; revise os dados técnicos da origem."]
        config = tecnicos["cortina"]
        if "componentes" in config and (
            not isinstance(config["componentes"], list) or
            any(not isinstance(linha, dict) for linha in config["componentes"])
        ):
            return {}, ["Lista de componentes inválida; revise os vínculos de fabricação."]
        entrada = entrada_cortina_item(item, perfil).model_copy(update={"quantidade": 1, "desconto": 0})
        resultado = simular_cortina_catalogo(db, entrada, empresa_id)
        pendencias = list(resultado["pendencias_custo"])
        if entrada.modelo_prega.strip().upper() not in {"WAVE", "FRANZIDO", "PREGA_MACHO", "PREGA_FEMEA", "PREGA"}:
            pendencias.append("Modelo de prega sem regra de fabricação reconhecida.")
        if entrada.fator < 1:
            pendencias.append("Fator do tecido deve ser pelo menos 1 para cobrir a largura da peça.")
        if "componentes" in config:
            pendencias.append("Lista livre de componentes ainda sem validação de funções obrigatórias de fabricação.")
        for linha in resultado["composicao"]:
            quantidade = Decimal(str(linha["quantidade"]))
            if not quantidade.is_finite() or quantidade <= 0:
                pendencias.append(f"Consumo inválido: {linha['componente']}.")
            if linha.get("origem_custo") == "VALOR_VENDA_CADASTRADO":
                pendencias.append(f"Insumo sem custo industrial cadastrado: {linha['componente']}.")
            produto_id = linha.get("produto_id")
            if produto_id is None and linha["componente"] != "mao_de_obra":
                pendencias.append(f"Insumo sem vínculo: {linha['componente']}.")
            if produto_id is not None:
                produto = db.query(ProdutoDB).filter(
                    ProdutoDB.id == produto_id, ProdutoDB.empresa_id == empresa_id,
                ).first()
                if produto is None or (produto.situacao or "").strip().upper() != "ATIVO":
                    pendencias.append(f"Insumo indisponível: {linha['componente']}.")
                elif linha["componente"] not in {"tecido", "forro"} and not componente_cortina_elegivel(produto):
                    pendencias.append(f"Insumo não elegível para cortina: {linha['componente']}.")
        return resultado, pendencias
    produto = db.query(ProdutoDB).filter(
        ProdutoDB.id == item.produto_id, ProdutoDB.empresa_id == empresa_id,
    ).first()
    if produto is None:
        return {}, ["Produto não encontrado para a empresa ativa."]
    parametros = dict(produto_id=produto.id, largura=item.largura, altura=item.altura, quantidade=1,
                      perfil_comercial=perfil, desconto=0)
    if modelo == "ROLO":
        from app.services.rolo_simulacao import simular_rolo, RoloSimulacaoInput
        resultado = simular_rolo(produto, RoloSimulacaoInput(**parametros))
    elif modelo == "DOUBLE VISION":
        from app.services.double_vision_simulacao import simular_double_vision, DoubleVisionSimulacaoInput
        resultado = simular_double_vision(produto, DoubleVisionSimulacaoInput(**parametros))
    elif modelo == "ROMANA":
        from app.services.romana_simulacao import simular_romana, RomanaSimulacaoInput
        resultado = simular_romana(produto, RomanaSimulacaoInput(**parametros))
    else:
        return {}, ["Modelo ainda sem contrato completo de fabricação na Produção V1."]
    return resultado, ["Cálculo disponível para consulta, mas composição/cortes e equivalências ainda incompletos para liberação."]


def avaliar(db, ordem):
    pendencias = []
    resultados = {}
    for dados in ordem.snapshot["itens"]:
        try:
            resultado, faltas = _calcular(db, dados, ordem.snapshot["perfil_comercial"], ordem.empresa_id)
        except (ValueError, ValidationError) as exc:
            resultado, faltas = {}, [str(exc)]
        resultados[str(dados["id"])] = jsonable_encoder(resultado)
        pendencias.extend(f"Item {dados['id']}: {falta}" for falta in faltas)
    for peca in ordem.pecas:
        for campo in ("modelo", "tecido", "cor", "acionamento", "ambiente"):
            if not (getattr(peca, campo) or "").strip():
                pendencias.append(f"Peça {peca.id}: informe {campo} na origem ou na ficha.")
        if peca.largura <= 0 or peca.altura <= 0:
            pendencias.append(f"Peça {peca.id}: medidas devem ser positivas.")
    return resultados, pendencias


def liberar(db, ordem_id, tenant, confirmar):
    usuario = _usuario(tenant)
    ordem = obter(db, ordem_id, tenant, bloquear=True)
    _venda(db, ordem.pedido_id, ordem.empresa_id)
    if confirmar is not True:
        raise ValueError("Confirme explicitamente a liberação para fabricação.")
    if ordem.liberado_em:
        raise ValueError("Ordem já liberada.")
    resultados, pendencias = avaliar(db, ordem)
    if pendencias:
        raise ValueError("Liberação bloqueada: " + " | ".join(pendencias))
    ordem.snapshot = {**ordem.snapshot, "calculos_por_peca": resultados}
    ordem.liberado_em, ordem.liberado_por = _agora(), usuario
    db.flush()
    return ordem


def alterar_peca(db, ordem_id, peca_id, tenant, data):
    usuario = _usuario(tenant)
    ordem = obter(db, ordem_id, tenant, bloquear=True)
    _venda(db, ordem.pedido_id, ordem.empresa_id)
    peca = next((p for p in ordem.pecas if p.id == peca_id), None)
    if peca is None:
        raise LookupError("Peça não encontrada nesta ordem.")
    if "status" in data:
        if not ordem.liberado_em:
            raise ValueError("Libere a ordem antes de iniciar fabricação.")
        atual = peca.status
        if data["status_atual"] != atual or atual == STATUS[-1] or data["status"] != STATUS[STATUS.index(atual) + 1]:
            raise ValueError("Transição inválida ou ficha desatualizada; recarregue a ordem.")
        peca.status = data["status"]
        peca.historico = [*peca.historico, {
            "de": atual, "para": peca.status, "usuario": usuario, "em": _agora().isoformat(),
        }]
    else:
        if ordem.liberado_em:
            raise ValueError("Ficha liberada é imutável; ambiente e observações devem ser conferidos antes.")
        peca.ambiente, peca.observacoes = data["ambiente"].strip(), data["observacoes"].strip()
    db.flush()
    return ordem


def serializar(db, ordem):
    resultados, pendencias = ({}, []) if ordem.liberado_em else avaliar(db, ordem)
    return {
        "id": ordem.id, "pedido_id": ordem.pedido_id, "empresa_id": ordem.empresa_id,
        "confirmado_por": ordem.confirmado_por, "confirmado_em": ordem.confirmado_em,
        "liberado_por": ordem.liberado_por, "liberado_em": ordem.liberado_em,
        "snapshot": ordem.snapshot,
        "status": min((p.status for p in ordem.pecas), key=STATUS.index),
        "pendencias": pendencias, "calculos_por_peca": ordem.snapshot.get("calculos_por_peca", resultados),
        "pecas": [{
            "id": p.id, "codigo": f"OP-{ordem.id:06d}-I{p.pedido_item_id}-P{p.sequencia:04d}",
            **{campo: getattr(p, campo) for campo in (
                "pedido_item_id", "sequencia", "modelo", "tecido", "cor", "largura", "altura",
                "acionamento", "ambiente", "observacoes", "status", "historico",
            )},
        } for p in ordem.pecas],
    }
