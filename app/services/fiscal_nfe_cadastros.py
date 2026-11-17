"""Conferência dos cadastros fiscais da empresa e dos SKUs da venda.

Apenas leitura. NÃO calcula impostos, gera NF-e ou autoriza emissão.
"""
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.models.fiscal_produto import FiscalProdutoDB
from app.models.produto import ProdutoDB
from app.schemas.fiscal_cadastros import FiscalEmpresaDados, FiscalProdutoDados


def conferir_cadastros_fiscais(db, pedido: dict, empresa, empresa_id: int):
    pendencias: list[dict] = []

    def registrar(codigo, campo, mensagem, nivel="bloqueante"):
        pendencias.append({
            "codigo": codigo, "campo": campo, "mensagem": mensagem, "nivel": nivel,
        })

    raw_config = empresa.configuracoes if isinstance(
        getattr(empresa, "configuracoes", None), dict
    ) else {}
    raw_fiscal = raw_config.get("fiscal_nfe")
    raw_fiscal = raw_fiscal if isinstance(raw_fiscal, dict) else {}
    try:
        permitidos = {campo: raw_fiscal[campo] for campo in FiscalEmpresaDados.model_fields
                      if campo in raw_fiscal}
        fiscal_empresa = FiscalEmpresaDados.model_validate(permitidos).model_dump()
    except ValidationError:
        fiscal_empresa = FiscalEmpresaDados().model_dump()
        registrar("EMITENTE_CONFIG_INVALIDA", "fiscal.empresa",
                  "Configuração fiscal armazenada inválida; revise o cadastro da empresa.")

    if not fiscal_empresa.get("inscricao_estadual"):
        registrar("EMITENTE_IE", "fiscal.empresa.inscricao_estadual",
                  "Informe ou confirme a situação da inscrição estadual.")
    if not fiscal_empresa.get("crt"):
        registrar("EMITENTE_CRT", "fiscal.empresa.crt", "Informe o CRT do emitente.")
    for campo, label in (
        ("uf", "UF"), ("municipio_codigo_ibge", "código IBGE do município"),
        ("cep", "CEP"), ("cidade", "cidade"), ("logradouro", "logradouro"),
        ("numero", "número"), ("bairro", "bairro"), ("serie_nfe", "série de homologação"),
    ):
        if fiscal_empresa.get(campo) in (None, ""):
            registrar("EMITENTE_" + campo.upper(), "fiscal.empresa." + campo,
                      f"Complete {label} no cadastro fiscal da empresa.")

    linhas_por_sku: dict[int, list[int]] = {}
    for numero, item in enumerate(pedido.get("itens") or [], start=1):
        if str(item.get("tipo_item") or "PRODUTO").upper() != "PRODUTO":
            continue
        sku = item.get("produto_id")
        if type(sku) is int and sku > 0:
            linhas_por_sku.setdefault(sku, []).append(numero)

    skus = sorted(linhas_por_sku)
    registros = {}
    produtos_existentes = set()
    if skus:
        # Consultas em lote, sempre vinculadas ao CNPJ/empresa do tenant.
        produtos = db.query(ProdutoDB).filter(
            ProdutoDB.empresa_id == empresa_id, ProdutoDB.id.in_(skus)
        ).all()
        produtos_existentes = {produto.id for produto in produtos}
        try:
            fiscais = db.query(FiscalProdutoDB).filter(
                FiscalProdutoDB.empresa_id == empresa_id,
                FiscalProdutoDB.produto_id.in_(skus),
            ).all()
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=503,
                detail="Cadastro fiscal indisponível; confirme a migração do ambiente de testes.",
            ) from exc
        registros = {
            fiscal.produto_id: fiscal for fiscal in fiscais
            if fiscal.empresa_id == empresa_id and fiscal.produto_id in produtos_existentes
        }

    for sku in skus:
        local = f"fiscal.produtos[{sku}]"
        linhas = ", ".join(str(i) for i in linhas_por_sku[sku])
        if sku not in produtos_existentes:
            registrar("ITEM_PRODUTO_INEXISTENTE", local,
                      f"Produto da linha {linhas} não encontrado na empresa ativa.")
            continue
        row = registros.get(sku)
        if row is None:
            dados = FiscalProdutoDados()
        else:
            try:
                dados = FiscalProdutoDados.model_validate({
                    campo: getattr(row, campo) for campo in FiscalProdutoDados.model_fields
                })
            except ValidationError:
                registrar("ITEM_CONFIG_INVALIDA", local,
                          f"SKU {sku}: classificação fiscal inválida; revise o cadastro.")
                dados = FiscalProdutoDados()

        for campo, rotulo in (
            ("ncm", "NCM"), ("cfop_padrao_saida", "CFOP sugerido de saída"),
            ("origem_mercadoria", "origem da mercadoria"),
        ):
            if not getattr(dados, campo):
                registrar("ITEM_" + campo.upper(), local + "." + campo,
                          f"SKU {sku}: informe {rotulo} no cadastro fiscal.")
        if not (dados.cst_icms or dados.csosn):
            registrar("ITEM_CLASSIFICACAO_ICMS", local + ".cst_icms",
                      f"SKU {sku}: informe CST ou CSOSN conforme enquadramento.")
        if not dados.cst_ibs_cbs or not dados.cclass_trib_ibs_cbs:
            registrar("ITEM_IBS_CBS_A_CONFERIR", local + ".cst_ibs_cbs",
                      f"SKU {sku}: revise a classificação IBS/CBS conforme tabelas vigentes.",
                      nivel="revisao")
        if not dados.cst_pis or not dados.cst_cofins:
            registrar("ITEM_PIS_COFINS_A_CONFERIR", local + ".cst_pis",
                      f"SKU {sku}: revise a classificação PIS/COFINS.",
                      nivel="revisao")

    # Nem mesmo todos os códigos preenchidos equivalem a uma operação fiscal válida.
    registrar("REGRAS_TRIBUTARIAS_NAO_VALIDADAS", "fiscal.operacao",
              "Conferir CFOP e tributação por operação, destinatário e UF com a contabilidade.")
    return pendencias, {
        "emitente_cadastrado": bool(raw_fiscal),
        "total_skus": len(skus),
        "skus_com_cadastro": sum(1 for sku in skus if sku in registros),
        "skus_sem_cadastro": [sku for sku in skus if sku not in registros],
        "tipo_validacao": "CADASTRAL_SEM_CALCULO_TRIBUTARIO",
    }
