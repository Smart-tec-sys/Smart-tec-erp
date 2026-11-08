from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy.orm import selectinload

from app.models.empresa import EmpresaDB
from app.models.cliente import ClienteDB
from app.models.pedido import PedidoDB
from app.models.produto import ProdutoDB
from app.models.producao import (
    ComponenteProducaoDB,
    OrdemProducaoDB,
    PecaProducaoDB,
    RevisaoFichaProducaoDB,
)
from app.tenant.isolation import require_tenant

STATUS = ("AGUARDANDO", "CORTE", "MONTAGEM", "CONFERENCIA", "CONCLUIDA")
VENDAS_PERMITIDAS = {"ABERTO", "FATURADO", "CONCLUIDO"}
BLOQUEIOS_MODELOS = {
    "ROLO": "Rolô manual: falta BOM industrial validada com vínculos/equivalências reais para tecido, tubo 32/38, fita do tubo, base, fita/espaguete da base, corrente, emenda, tampas e comando; consumo e cortes precisam de validação industrial.",
    "DOUBLE VISION": "Double Vision manual: falta BOM industrial validada com vínculos/equivalências reais para tecidos, tubo selecionado, comando, eixo/base, tampas, grapas, barra estabilizadora ou bandô, espaguete, fita, corrente, emenda e pêndulo.",
    "ROMANA": "Romana manual: falta BOM/equivalências validadas para tecido, varetas e tampas, guias/passadores, corda 1 mm, espaguetes, corrente e comando; o próprio motor mantém regras produtivas pendentes.",
}


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


def _exigir_pedido_autorizado(pedido):
    if pedido.producao_aprovado_em is None:
        raise ValueError("Aprovação explícita do pedido é necessária para fabricação.")
    if pedido.producao_liberado_em is None:
        raise ValueError("Liberação explícita para fabricação é necessária.")


def exigir_autorizacao_fabricacao(db, pedido_id, tenant):
    pedido = _venda(db, pedido_id, require_tenant(tenant))
    _exigir_pedido_autorizado(pedido)
    return pedido


def obter(db, ordem_id, tenant, bloquear=False):
    query = db.query(OrdemProducaoDB).options(
        selectinload(OrdemProducaoDB.pecas).selectinload(PecaProducaoDB.componentes),
        selectinload(OrdemProducaoDB.pecas).selectinload(PecaProducaoDB.revisoes),
    ).filter(
        OrdemProducaoDB.id == ordem_id, OrdemProducaoDB.empresa_id == require_tenant(tenant),
    )
    ordem = (query.with_for_update() if bloquear else query).first()
    if ordem is None:
        raise LookupError("Ordem de produção não encontrada para a empresa ativa.")
    return ordem


def listar(db, pedido_id, tenant):
    return db.query(OrdemProducaoDB).options(
        selectinload(OrdemProducaoDB.pecas).selectinload(PecaProducaoDB.componentes),
        selectinload(OrdemProducaoDB.pecas).selectinload(PecaProducaoDB.revisoes),
    ).filter(
        OrdemProducaoDB.empresa_id == require_tenant(tenant),
        OrdemProducaoDB.pedido_id == pedido_id,
    ).order_by(OrdemProducaoDB.id.desc()).all()


def obter_autorizacao(db, pedido_id, tenant):
    pedido = db.query(PedidoDB).filter(
        PedidoDB.id == pedido_id,
        PedidoDB.empresa_id == require_tenant(tenant),
    ).first()
    if pedido is None:
        raise LookupError("Venda não encontrada para a empresa ativa.")
    return {
        "pedido_id": pedido.id,
        "aprovado_por": pedido.producao_aprovado_por,
        "aprovado_em": pedido.producao_aprovado_em,
        "liberado_por": pedido.producao_liberado_por,
        "liberado_em": pedido.producao_liberado_em,
        "historico": pedido.producao_historico or [],
    }


def _nome_cliente(db, pedido, empresa_id):
    if pedido.parceiro_id is not None:
        nome = pedido.cliente_final_nome
    elif pedido.cliente_id is not None:
        cliente = db.query(ClienteDB).filter(
            ClienteDB.id == pedido.cliente_id,
            ClienteDB.empresa_id == empresa_id,
        ).first()
        if cliente is None:
            raise ValueError("Cliente da venda não encontrado para a empresa ativa.")
        nome = cliente.nome
    else:
        nome = pedido.cliente_final_nome
    if not (nome or "").strip():
        raise ValueError("Informe o cliente da venda antes de aprovar a fabricação.")
    return nome.strip()


def _registrar_autorizacao(pedido, acao, usuario, momento):
    pedido.producao_historico = [
        *(pedido.producao_historico or []),
        {"acao": acao, "usuario": usuario, "em": momento.isoformat()},
    ]


def aprovar_fabricacao(db, pedido_id, tenant):
    empresa_id = require_tenant(tenant)
    usuario = _usuario(tenant)
    pedido = _venda(db, pedido_id, empresa_id)
    _nome_cliente(db, pedido, empresa_id)
    if pedido.producao_aprovado_em is not None:
        raise ValueError("Venda já aprovada para fabricação.")
    agora = _agora()
    pedido.producao_aprovado_por = usuario
    pedido.producao_aprovado_em = agora
    pedido.producao_liberado_por = None
    pedido.producao_liberado_em = None
    _registrar_autorizacao(pedido, "APROVADO", usuario, agora)
    db.flush()
    return obter_autorizacao(db, pedido.id, tenant)


def liberar_pedido_fabricacao(db, pedido_id, tenant):
    empresa_id = require_tenant(tenant)
    usuario = _usuario(tenant)
    pedido = _venda(db, pedido_id, empresa_id)
    _nome_cliente(db, pedido, empresa_id)
    if pedido.producao_aprovado_em is None:
        raise ValueError("Aprovação explícita do pedido é necessária antes da liberação.")
    if pedido.producao_liberado_em is not None:
        raise ValueError("Venda já liberada para fabricação.")
    agora = _agora()
    pedido.producao_liberado_por = usuario
    pedido.producao_liberado_em = agora
    _registrar_autorizacao(pedido, "LIBERADO", usuario, agora)
    db.flush()
    return obter_autorizacao(db, pedido.id, tenant)


def criar(db, pedido_id, tenant, confirmar):
    empresa_id = require_tenant(tenant)
    usuario = _usuario(tenant)
    if confirmar is not True:
        raise ValueError("Confirme explicitamente a fabricação da venda.")
    pedido = _venda(db, pedido_id, empresa_id)
    _exigir_pedido_autorizado(pedido)
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
                          "descricao", "codigo_interno", "observacao_item", "ambiente")
        }
        itens.append(jsonable_encoder(dados))
        for sequencia in range(1, int(quantidade) + 1):
            pecas.append(PecaProducaoDB(
                pedido_item_id=item.id, sequencia=sequencia, modelo=item.modelo_tecnico,
                tecido=item.material, cor=item.cor, largura=item.largura, altura=item.altura,
                acionamento=item.acionamento, ambiente=item.ambiente or "",
                quantidade=1, modo_fabricacao="AUTOMATICA", especificacoes_fabricacao={},
                versao_ficha=1, observacoes=item.observacao_item or "",
                status="AGUARDANDO", historico=[],
            ))
    if not pecas:
        raise ValueError("Venda sem produtos para fabricar; serviços não geram peças.")
    ordem = OrdemProducaoDB(
        empresa_id=empresa_id, pedido_id=pedido.id, confirmado_por=usuario, confirmado_em=_agora(),
        snapshot=jsonable_encoder({
            "versao": 1, "empresa": empresa.nome, "pedido": pedido.numero,
            "cliente": _nome_cliente(db, pedido, empresa_id),
            "prazo_entrega": pedido.prazo_entrega, "perfil_comercial": pedido.perfil_comercial,
            "itens": itens,
        }), pecas=pecas,
    )
    db.add(ordem)
    db.flush()
    return ordem


def _calcular(db, dados, perfil, empresa_id):
    item = SimpleNamespace(**dados)
    modelo_original = " ".join((item.modelo_tecnico or "").strip().upper().replace("_", " ").split())
    modelo = next((base for base in ("DOUBLE VISION", "ROMANA", "ROLO")
                   if modelo_original.startswith(base)), modelo_original)
    acionamento = " ".join((item.acionamento or "").strip().upper().replace("_", " ").split())
    if modelo.startswith("CORTINA"):
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
        entrada = entrada_cortina_item(item, perfil).copy(update={"quantidade": 1, "desconto": 0})
        if entrada.modelo_prega.strip().upper() != "WAVE":
            return {}, ["Cortina: somente Wave possui regra de fabricação V1 validada; modelos de prega diferentes de Wave permanecem bloqueados."]
        resultado = simular_cortina_catalogo(db, entrada, empresa_id)
        pendencias = list(resultado["pendencias_custo"])
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
        from app.services.rolo_simulacao import simular_rolo, RoloSimulacaoInput, _tipo_rolo
        tipo = _tipo_rolo(produto)
        motorizado = "MOTORIZ" in acionamento or "MOTORIZ" in modelo_original or tipo == "MOTORIZADA"
        if motorizado:
            return {}, ["Rolô motorizado: faltam BOM industrial validada para motor, suporte/adaptador, controle, eixo/tubo compatível e equivalências de corte; a simulação atual não confirma esses componentes."]
        if tipo != "MANUAL":
            return {}, [BLOQUEIOS_MODELOS["ROLO"],
                        "Produto final Rolô manual não foi identificado com segurança no cadastro técnico."]
        parametros["acionamento"] = "manual"
        resultado = simular_rolo(produto, RoloSimulacaoInput(**parametros))
    elif modelo == "DOUBLE VISION":
        from app.services.double_vision_simulacao import simular_double_vision, DoubleVisionSimulacaoInput
        nome_modelo = " ".join(str(getattr(produto, campo, "") or "") for campo in
                               ("modelo_tecnico", "modelo", "nome")).upper()
        if "MOTORIZ" in acionamento or "MOTORIZ" in modelo_original or "MOTORIZ" in nome_modelo:
            return {}, ["Double Vision motorizado: não há regra/BOM industrial validada para motor, suporte, controle, tubo e componentes compatíveis."]
        resultado = simular_double_vision(produto, DoubleVisionSimulacaoInput(**parametros))
    elif modelo == "ROMANA":
        from app.services.romana_simulacao import simular_romana, RomanaSimulacaoInput
        nome_modelo = " ".join(str(getattr(produto, campo, "") or "") for campo in
                               ("modelo_tecnico", "modelo", "nome")).upper()
        if "MOTORIZ" in acionamento or "MOTORIZ" in modelo_original or "MOTORIZ" in nome_modelo:
            return {}, ["Romana motorizada: não há cálculo de produção nem BOM validada para motor e componentes compatíveis."]
        resultado = simular_romana(produto, RomanaSimulacaoInput(**parametros))
    else:
        return {}, ["Modelo ainda sem contrato completo de fabricação na Produção V1."]
    return resultado, [BLOQUEIOS_MODELOS[modelo]]


def listar_catalogo_componentes(db, tenant, busca=""):
    empresa_id = require_tenant(tenant)
    query = db.query(ProdutoDB).filter(
        ProdutoDB.empresa_id == empresa_id,
        ProdutoDB.situacao.ilike("ativo"),
    )
    termo = (busca or "").strip()
    if termo:
        padrao = f"%{termo}%"
        query = query.filter(
            (ProdutoDB.nome.ilike(padrao))
            | (ProdutoDB.descricao.ilike(padrao))
            | (ProdutoDB.codigo_interno.ilike(padrao))
            | (ProdutoDB.codigo_barras.ilike(padrao))
        )
    return [{
        "id": produto.id,
        "codigo_interno": produto.codigo_interno,
        "descricao": produto.descricao or produto.nome,
        "unidade": produto.unidade,
        "custo_unitario": (
            produto.custo_final if (produto.custo_final or 0) > 0
            else produto.valor_custo if (produto.valor_custo or 0) > 0
            else None
        ),
    } for produto in query.order_by(ProdutoDB.nome, ProdutoDB.id).limit(100).all()]


def _snapshot_ficha(peca):
    return {
        "modelo": peca.modelo,
        "tecido": peca.tecido,
        "cor": peca.cor,
        "largura": peca.largura,
        "altura": peca.altura,
        "quantidade": peca.quantidade,
        "acionamento": peca.acionamento,
        "ambiente": peca.ambiente,
        "observacoes": peca.observacoes,
        "modo_fabricacao": peca.modo_fabricacao,
        "especificacoes_fabricacao": peca.especificacoes_fabricacao or {},
        "conferido_por": peca.conferido_por,
        "conferido_em": peca.conferido_em,
        "componentes": [{
            "id": componente.id,
            "produto_id": componente.produto_id,
            "descricao": componente.descricao,
            "codigo_interno": componente.codigo_interno,
            "quantidade": componente.quantidade,
            "unidade": componente.unidade,
            "comprimento_corte": componente.comprimento_corte,
            "custo_unitario": componente.custo_unitario,
            "origem_custo": componente.origem_custo,
            "observacoes": componente.observacoes,
        } for componente in peca.componentes],
    }


def _registrar_revisao(db, ordem, peca, usuario, justificativa, antes):
    versao = int(peca.versao_ficha or 1) + 1
    peca.versao_ficha = versao
    peca.revisoes.append(RevisaoFichaProducaoDB(
        empresa_id=ordem.empresa_id,
        ordem_id=ordem.id,
        peca_id=peca.id,
        versao=versao,
        usuario=usuario,
        justificativa=justificativa.strip(),
        antes=jsonable_encoder(antes),
        depois=jsonable_encoder(_snapshot_ficha(peca)),
        criado_em=_agora(),
    ))


def _produto_componente(db, empresa_id, produto_id):
    produto = db.query(ProdutoDB).filter(
        ProdutoDB.id == produto_id,
        ProdutoDB.empresa_id == empresa_id,
    ).first()
    if produto is None:
        raise ValueError("Componente não pertence ao catálogo da empresa ativa.")
    if (produto.situacao or "").strip().upper() != "ATIVO":
        raise ValueError("Componente inativo não pode ser usado na ficha.")
    return produto


def _montar_componente(db, empresa_id, dados):
    produto = _produto_componente(db, empresa_id, dados["produto_id"])
    unidade = (dados.get("unidade") or "").strip()
    if not unidade:
        raise ValueError("Unidade do componente é obrigatória.")
    unidade_catalogo = (produto.unidade or "").strip()
    if unidade_catalogo and unidade.casefold() != unidade_catalogo.casefold():
        raise ValueError("Unidade informada difere da unidade cadastrada no produto.")
    quantidade = Decimal(str(dados["quantidade"]))
    if not quantidade.is_finite() or quantidade <= 0:
        raise ValueError("Quantidade do componente deve ser finita e positiva.")
    corte = dados.get("comprimento_corte")
    if corte is not None:
        corte = Decimal(str(corte))
        if not corte.is_finite() or corte <= 0:
            raise ValueError("Comprimento de corte deve ser finito e positivo.")
    custo_informado = dados.get("custo_unitario")
    if custo_informado is None:
        custo = next((
            Decimal(str(getattr(produto, campo) or 0))
            for campo in ("custo_final", "valor_custo")
            if Decimal(str(getattr(produto, campo) or 0)) > 0
        ), None)
        origem_custo = "CADASTRO"
    else:
        custo = Decimal(str(custo_informado))
        origem_custo = "INFORMADO"
    if custo is None or not custo.is_finite() or custo < 0:
        raise ValueError("Informe um custo unitário ou use um custo válido do cadastro.")
    return {
        "produto": produto,
        "quantidade": quantidade,
        "unidade": unidade,
        "comprimento_corte": corte,
        "custo_unitario": custo,
        "origem_custo": origem_custo,
        "observacoes": (dados.get("observacoes") or "").strip(),
    }


def _validar_composicao_manual(db, ordem, peca, exigir_conferencia=True):
    pendencias = []
    if peca.modo_fabricacao != "MANUAL_SUPERVISIONADA":
        pendencias.append("Modo manual supervisionado não selecionado.")
    if not (peca.modelo or "").strip():
        pendencias.append("Modelo técnico ausente.")
    if not (peca.ambiente or "").strip():
        pendencias.append("Ambiente da peça ausente.")
    if Decimal(str(peca.largura or 0)) <= 0 or Decimal(str(peca.altura or 0)) <= 0:
        pendencias.append("Medidas da peça devem ser positivas.")
    if Decimal(str(peca.quantidade or 0)) <= 0:
        pendencias.append("Quantidade da peça deve ser positiva.")
    especificacoes = peca.especificacoes_fabricacao or {}
    if not isinstance(especificacoes, dict) or not any(
        str(chave).strip() and str(valor).strip()
        for chave, valor in especificacoes.items()
    ):
        pendencias.append("Informe especificações de fabricação.")
    componentes = list(peca.componentes)
    if not componentes:
        pendencias.append("Inclua ao menos um componente do catálogo da empresa.")
    saida_componentes = []
    for componente in componentes:
        produto = db.query(ProdutoDB).filter(
            ProdutoDB.id == componente.produto_id,
            ProdutoDB.empresa_id == ordem.empresa_id,
        ).first()
        if produto is None:
            pendencias.append(f"Componente {componente.id}: produto não pertence à empresa.")
        elif (produto.situacao or "").strip().upper() != "ATIVO":
            pendencias.append(f"Componente {componente.id}: produto inativo.")
        if Decimal(str(componente.quantidade or 0)) <= 0:
            pendencias.append(f"Componente {componente.id}: quantidade inválida.")
        if not (componente.unidade or "").strip():
            pendencias.append(f"Componente {componente.id}: unidade ausente.")
        if componente.custo_unitario is None or Decimal(str(componente.custo_unitario)) < 0:
            pendencias.append(f"Componente {componente.id}: custo unitário ausente ou inválido.")
        saida_componentes.append({
            "componente_id": componente.id,
            "produto_id": componente.produto_id,
            "descricao": componente.descricao,
            "codigo_interno": componente.codigo_interno,
            "quantidade": componente.quantidade,
            "unidade": componente.unidade,
            "comprimento_corte": componente.comprimento_corte,
            "custo_unitario": componente.custo_unitario,
            "custo_total_informativo": (
                Decimal(str(componente.quantidade)) * Decimal(str(componente.custo_unitario))
                if componente.custo_unitario is not None else None
            ),
            "origem_custo": componente.origem_custo,
            "observacoes": componente.observacoes,
        })
    if exigir_conferencia and (not peca.conferido_por or not peca.conferido_em):
        pendencias.append("Conferência técnica obrigatória antes da liberação.")
    return {
        "modo_fabricacao": "MANUAL_SUPERVISIONADA",
        "status_composicao": "MANUAL_NAO_HOMOLOGADA",
        "versao_ficha": peca.versao_ficha,
        "especificacoes_fabricacao": especificacoes,
        "componentes": saida_componentes,
    }, pendencias


def avaliar(db, ordem):
    pendencias = []
    resultados = {}
    pecas_por_item = {}
    for peca in ordem.pecas:
        pecas_por_item.setdefault(peca.pedido_item_id, []).append(peca)
    for dados in ordem.snapshot["itens"]:
        pecas_item = pecas_por_item.get(dados["id"], [])
        if pecas_item and any(
            peca.modo_fabricacao == "MANUAL_SUPERVISIONADA" for peca in pecas_item
        ):
            for peca in pecas_item:
                if peca.modo_fabricacao != "MANUAL_SUPERVISIONADA":
                    continue
                resultado, faltas = _validar_composicao_manual(db, ordem, peca)
                resultados[f"peca:{peca.id}"] = jsonable_encoder(resultado)
                pendencias.extend(
                    f"Peça {peca.id}: {falta}" for falta in faltas
                )
            if all(peca.modo_fabricacao == "MANUAL_SUPERVISIONADA" for peca in pecas_item):
                continue
        try:
            resultado, faltas = _calcular(db, dados, ordem.snapshot["perfil_comercial"], ordem.empresa_id)
        except (ValueError, ValidationError) as exc:
            modelo = " ".join(str(dados.get("modelo_tecnico") or "").upper().replace("_", " ").split())
            base = next((nome for nome in BLOQUEIOS_MODELOS if modelo.startswith(nome)), None)
            resultado = {}
            faltas = [BLOQUEIOS_MODELOS[base], f"Cálculo técnico indisponível: {exc}"] if base else [str(exc)]
        resultados[str(dados["id"])] = jsonable_encoder(resultado)
        pendencias.extend(f"Item {dados['id']}: {falta}" for falta in faltas)
    for peca in ordem.pecas:
        if peca.modo_fabricacao == "MANUAL_SUPERVISIONADA":
            continue
        for campo in ("modelo", "tecido", "cor", "acionamento", "ambiente"):
            if not (getattr(peca, campo) or "").strip():
                pendencias.append(f"Peça {peca.id}: informe {campo} na origem ou na ficha.")
        if peca.largura <= 0 or peca.altura <= 0:
            pendencias.append(f"Peça {peca.id}: medidas devem ser positivas.")
    return resultados, pendencias


def liberar(db, ordem_id, tenant, confirmar):
    usuario = _usuario(tenant)
    ordem = obter(db, ordem_id, tenant, bloquear=True)
    pedido = _venda(db, ordem.pedido_id, ordem.empresa_id)
    if confirmar is not True:
        raise ValueError("Confirme explicitamente a liberação para fabricação.")
    _exigir_pedido_autorizado(pedido)
    if ordem.liberado_em:
        raise ValueError("Ordem já liberada.")
    resultados, pendencias = avaliar(db, ordem)
    if pendencias:
        raise ValueError("Liberação bloqueada: " + " | ".join(pendencias))
    ordem.snapshot = {**ordem.snapshot, "calculos_por_peca": resultados}
    ordem.liberado_em, ordem.liberado_por = _agora(), usuario
    db.flush()
    return ordem


def _justificativa(data):
    justificativa = str(data.get("justificativa") or "").strip()
    if len(justificativa) < 5:
        raise ValueError("Justificativa obrigatória: informe ao menos 5 caracteres.")
    return justificativa


def alterar_peca(db, ordem_id, peca_id, tenant, data):
    usuario = _usuario(tenant)
    ordem = obter(db, ordem_id, tenant, bloquear=True)
    pedido = _venda(db, ordem.pedido_id, ordem.empresa_id)
    _exigir_pedido_autorizado(pedido)
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
            raise ValueError("Ficha liberada é imutável; edições devem ocorrer antes da fabricação.")
        justificativa = _justificativa(data)
        antes = _snapshot_ficha(peca)
        modo_final = data.get("modo_fabricacao", peca.modo_fabricacao)
        if peca.modo_fabricacao == "MANUAL_SUPERVISIONADA" and modo_final != "MANUAL_SUPERVISIONADA":
            raise ValueError("Uma ficha manual supervisionada não pode voltar ao cálculo automático.")
        if modo_final != "MANUAL_SUPERVISIONADA":
            campos_tecnicos = ("largura", "altura", "quantidade")
            if any(
                campo in data and Decimal(str(data[campo])) != Decimal(str(getattr(peca, campo)))
                for campo in campos_tecnicos
            ) or (
                "especificacoes_fabricacao" in data
                and data["especificacoes_fabricacao"] not in (None, {})
            ):
                raise ValueError(
                    "Medidas, quantidade e especificações editáveis exigem modo manual supervisionado."
                )
        alterou = False
        campos = ("ambiente", "largura", "altura", "quantidade", "observacoes",
                  "especificacoes_fabricacao", "modo_fabricacao")
        for campo in campos:
            if campo not in data:
                continue
            valor = data[campo]
            if campo in ("ambiente", "observacoes"):
                valor = (valor or "").strip()
            elif campo == "especificacoes_fabricacao":
                if valor is None:
                    valor = {}
                if not isinstance(valor, dict) or any(
                    not isinstance(chave, str) or not isinstance(texto, str)
                    for chave, texto in valor.items()
                ):
                    raise ValueError("Especificações devem ser um objeto de textos.")
                valor = {chave.strip(): texto.strip() for chave, texto in valor.items()}
            elif campo in ("largura", "altura", "quantidade") and valor is not None:
                valor = Decimal(str(valor))
                if not valor.is_finite() or valor <= 0:
                    raise ValueError(f"{campo.capitalize()} deve ser finita e positiva.")
            if getattr(peca, campo) != valor:
                setattr(peca, campo, valor)
                alterou = True
        if alterou:
            peca.conferido_por = None
            peca.conferido_em = None
            _registrar_revisao(db, ordem, peca, usuario, justificativa, antes)
    db.flush()
    return ordem


def adicionar_componente(db, ordem_id, peca_id, tenant, data):
    usuario = _usuario(tenant)
    ordem = obter(db, ordem_id, tenant, bloquear=True)
    _exigir_pedido_autorizado(_venda(db, ordem.pedido_id, ordem.empresa_id))
    if ordem.liberado_em:
        raise ValueError("A composição da ficha liberada é imutável.")
    peca = next((p for p in ordem.pecas if p.id == peca_id), None)
    if peca is None:
        raise LookupError("Peça não encontrada nesta ordem.")
    if peca.modo_fabricacao != "MANUAL_SUPERVISIONADA":
        raise ValueError("Selecione o modo manual supervisionado antes de editar componentes.")
    justificativa = _justificativa(data)
    dados = _montar_componente(db, ordem.empresa_id, data)
    antes = _snapshot_ficha(peca)
    produto = dados.pop("produto")
    componente = ComponenteProducaoDB(
        empresa_id=ordem.empresa_id,
        ordem_id=ordem.id,
        peca_id=peca.id,
        produto_id=produto.id,
        descricao=produto.descricao or produto.nome,
        codigo_interno=produto.codigo_interno,
        **dados,
    )
    peca.componentes.append(componente)
    peca.conferido_por = None
    peca.conferido_em = None
    db.flush()
    _registrar_revisao(db, ordem, peca, usuario, justificativa, antes)
    db.flush()
    return ordem


def atualizar_componente(db, ordem_id, peca_id, componente_id, tenant, data):
    usuario = _usuario(tenant)
    ordem = obter(db, ordem_id, tenant, bloquear=True)
    _exigir_pedido_autorizado(_venda(db, ordem.pedido_id, ordem.empresa_id))
    if ordem.liberado_em:
        raise ValueError("A composição da ficha liberada é imutável.")
    peca = next((p for p in ordem.pecas if p.id == peca_id), None)
    if peca is None:
        raise LookupError("Peça não encontrada nesta ordem.")
    if peca.modo_fabricacao != "MANUAL_SUPERVISIONADA":
        raise ValueError("Selecione o modo manual supervisionado antes de editar componentes.")
    componente = next((c for c in peca.componentes if c.id == componente_id), None)
    if componente is None or componente.empresa_id != ordem.empresa_id:
        raise LookupError("Componente não encontrado nesta ficha.")
    justificativa = _justificativa(data)
    dados = _montar_componente(db, ordem.empresa_id, data)
    antes = _snapshot_ficha(peca)
    produto = dados.pop("produto")
    componente.produto_id = produto.id
    componente.descricao = produto.descricao or produto.nome
    componente.codigo_interno = produto.codigo_interno
    for campo, valor in dados.items():
        setattr(componente, campo, valor)
    peca.conferido_por = None
    peca.conferido_em = None
    db.flush()
    _registrar_revisao(db, ordem, peca, usuario, justificativa, antes)
    db.flush()
    return ordem


def remover_componente(db, ordem_id, peca_id, componente_id, tenant, justificativa):
    usuario = _usuario(tenant)
    ordem = obter(db, ordem_id, tenant, bloquear=True)
    _exigir_pedido_autorizado(_venda(db, ordem.pedido_id, ordem.empresa_id))
    if ordem.liberado_em:
        raise ValueError("A composição da ficha liberada é imutável.")
    peca = next((p for p in ordem.pecas if p.id == peca_id), None)
    if peca is None:
        raise LookupError("Peça não encontrada nesta ordem.")
    if peca.modo_fabricacao != "MANUAL_SUPERVISIONADA":
        raise ValueError("Selecione o modo manual supervisionado antes de editar componentes.")
    componente = next((c for c in peca.componentes if c.id == componente_id), None)
    if componente is None or componente.empresa_id != ordem.empresa_id:
        raise LookupError("Componente não encontrado nesta ficha.")
    justificativa_validada = _justificativa({"justificativa": justificativa})
    antes = _snapshot_ficha(peca)
    peca.componentes.remove(componente)
    peca.conferido_por = None
    peca.conferido_em = None
    db.flush()
    _registrar_revisao(db, ordem, peca, usuario, justificativa_validada, antes)
    db.flush()
    return ordem


def conferir_peca(db, ordem_id, peca_id, tenant, confirmar, justificativa):
    usuario = _usuario(tenant)
    ordem = obter(db, ordem_id, tenant, bloquear=True)
    _exigir_pedido_autorizado(_venda(db, ordem.pedido_id, ordem.empresa_id))
    if ordem.liberado_em:
        raise ValueError("A conferência não pode ser alterada após liberar a OP.")
    if confirmar is not True:
        raise ValueError("Confirme explicitamente a conferência técnica.")
    peca = next((p for p in ordem.pecas if p.id == peca_id), None)
    if peca is None:
        raise LookupError("Peça não encontrada nesta ordem.")
    justificativa_validada = _justificativa({"justificativa": justificativa})
    _, pendencias = _validar_composicao_manual(
        db, ordem, peca, exigir_conferencia=False,
    )
    if pendencias:
        raise ValueError("Conferência técnica bloqueada: " + " | ".join(pendencias))
    antes = _snapshot_ficha(peca)
    peca.conferido_por = usuario
    peca.conferido_em = _agora()
    _registrar_revisao(db, ordem, peca, usuario, justificativa_validada, antes)
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
                "quantidade", "acionamento", "ambiente", "observacoes", "status", "historico",
                "modo_fabricacao", "especificacoes_fabricacao", "versao_ficha",
                "conferido_por", "conferido_em",
            )},
            "componentes": [{
                "id": c.id, "produto_id": c.produto_id, "descricao": c.descricao,
                "codigo_interno": c.codigo_interno, "quantidade": c.quantidade,
                "unidade": c.unidade, "comprimento_corte": c.comprimento_corte,
                "custo_unitario": c.custo_unitario, "origem_custo": c.origem_custo,
                "observacoes": c.observacoes,
            } for c in p.componentes],
            "revisoes": [{
                "versao": r.versao, "usuario": r.usuario,
                "justificativa": r.justificativa, "antes": r.antes,
                "depois": r.depois, "criado_em": r.criado_em,
            } for r in p.revisoes],
        } for p in ordem.pecas],
    }
