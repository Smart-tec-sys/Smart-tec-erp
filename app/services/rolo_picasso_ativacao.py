"""Ativação comercial explícita. Dados específicos ficam no manifesto revisado."""
import copy
from decimal import Decimal

from app.models.empresa import EmpresaDB
from app.models.produto import ProdutoDB
from app.schemas.rolo_receita import ReceitaRolo


def _nome(texto):
    import unicodedata
    return " ".join(unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().upper().split())


def ativar_picasso(db, empresa_id, manifesto):
    """Chamador controla a transação. Sem commit, auto-DDL ou edição de documentos."""
    empresa = db.query(EmpresaDB).filter_by(id=empresa_id, status="ATIVA").with_for_update().one_or_none()
    if (empresa is None or empresa.documento != manifesto["empresa_documento"] or
            empresa.nome != manifesto["empresa_nome"]):
        raise ValueError("Empresa não corresponde ao destino comercial aprovado.")
    if not isinstance(empresa.configuracoes, dict):
        raise ValueError("Configuração existente da empresa inválida.")
    todos = db.query(ProdutoDB).filter_by(empresa_id=empresa_id).all()
    vinculados = {}
    criados, alterados = [], []
    for chave, especificacao in manifesto["insumos"].items():
        codigo = especificacao["codigo_interno"]
        nomes = {_nome(especificacao["nome"]), _nome(especificacao.get("nome_legado", especificacao["nome"]))}
        encontrados = [p for p in todos if p.codigo_interno == codigo and _nome(p.nome) in nomes]
        if "unidades_venda_validas" in especificacao:
            unidades = {_nome(u) for u in especificacao["unidades_venda_validas"]}
            encontrados = [p for p in encontrados if _nome(p.unidade_venda) in unidades]
        if len(encontrados) > 1:
            raise ValueError(f"Insumo ambíguo: {chave}. Não deduplicar automaticamente.")
        if not encontrados:
            if not especificacao.get("criar_se_ausente"):
                raise ValueError(f"Insumo não encontrado pela identidade validada: {chave}.")
            row = ProdutoDB(
                empresa_id=empresa_id, nome=especificacao["nome"], codigo_interno=codigo,
                codigo_fornecedor=codigo, fornecedores=especificacao["fornecedor"],
                tipo_produto="Componente", grupo_produto="Componentes", grupo_tecnico="TUBO",
                familia_tecnica="ROLO", unidade="ML", unidade_venda="ML", unidade_controle="ML",
                unidade_compra="BR", comprimento_compra=6, valor_custo=0, custo_final=0,
                situacao="Ativo", observacoes=especificacao["origem"],
            )
            # Custo ML documentado, sem contaminar preço de acabados existentes.
            ipi = especificacao["ipi_percentual"]
            acrescimo = Decimal(1) if ipi is None else 1 + Decimal(str(ipi)) / 100
            custo = Decimal(str(especificacao["preco_compra"])) * acrescimo / Decimal(str(especificacao["unidades_por_compra"]))
            row.valor_custo = row.custo_final = float(custo)
            db.add(row)
            db.flush()
            todos.append(row)
            criados.append(row.id)
        else:
            row = encontrados[0]
        if especificacao.get("corrigir_nome") and row.nome != especificacao["nome"]:
            row.nome = especificacao["nome"]
            row.cor = manifesto["acabamento"]
            row.observacoes = (row.observacoes or "") + " | Identidade corrigida pela fonte: " + especificacao["origem"]
            alterados.append(row.id)
        if str(row.situacao or "").casefold() != "ativo":
            raise ValueError(f"Insumo inativo: {chave}.")
        vinculados[chave] = row

    config = copy.deepcopy(empresa.configuracoes)
    receitas = config.setdefault("receitas_rolo_v1", {})
    if not isinstance(receitas, dict):
        raise ValueError("Configuração anterior de receitas Rolô inválida.")
    acabados = []
    for modelo in manifesto["modelos"]:
        base = modelo["nome"]
        for variacao in modelo["variacoes"]:
            codigo, nome = variacao["codigo_comercial"], base + " - " + variacao["cor"]
            encontrados = [p for p in todos if p.codigo_interno == codigo or _nome(p.nome) == _nome(nome)]
            if len(encontrados) > 1:
                raise ValueError("Variação comercial duplicada/ambígua.")
            if encontrados:
                row = encontrados[0]
                if row.codigo_interno != codigo or row.tipo_produto != "Produto Fabricado" or row.modelo_tecnico != "ROLO":
                    raise ValueError("Produto existente com identidade/classificação incompatível. Revisão necessária.")
            else:
                row = ProdutoDB(
                    empresa_id=empresa_id, nome=nome, codigo_interno=codigo, tipo_produto="Produto Fabricado",
                    grupo_produto="Persianas", grupo_tecnico="PERSIANA ROLO", familia_tecnica="ROLO",
                    modelo_tecnico="ROLO", modelo="MANUAL", produto_base=base,
                    cor=variacao["cor"], variacao_cor=variacao["cor"], varia_cor=False,
                    unidade="M2", unidade_venda="M2", fornecedores=manifesto["fornecedor"],
                    situacao="Ativo", possui_composicao="Sim", largura=manifesto["largura_bobina_m"],
                    valor_custo=0, custo_final=0, valor_venda=0,
                    observacoes="Preço calculado por receita da empresa; acabamento " + manifesto["acabamento"],
                )
                db.add(row)
                db.flush()
                todos.append(row)
                criados.append(row.id)
            tecidos = [p for p in todos if p.codigo_interno == variacao["codigo_tecido"] and
                       _nome(p.nome) == _nome(variacao["nome_tecido"])]
            if len(tecidos) != 1:
                raise ValueError("Tecido sem correspondência única por código e descrição.")
            tecido = tecidos[0]

            def especificacao(chave):
                dados = manifesto["insumos"][chave]
                return {k: dados[k] for k in (
                    "unidade_tecnica", "preco_compra", "ipi_percentual", "unidades_por_compra", "origem",
                )} | {"produto_id": vinculados[chave].id, "codigo_interno": vinculados[chave].codigo_interno,
                       "base_preco": dados.get("base_preco", "TABELA_2"), "diametro_mm": dados.get("diametro_mm")}

            receita = {
                "versao": 1, "acabamento": manifesto["acabamento"], "cor_tecido": variacao["cor"],
                "custeio_tecido": manifesto["custeio_tecido"],
                "largura_bobina_m": manifesto["largura_bobina_m"],
                "tecido": {"produto_id": tecido.id, "codigo_interno": tecido.codigo_interno, "unidade_tecnica": "M2",
                           "preco_compra": modelo["preco_tecido_ml"], "ipi_percentual": modelo["ipi_percentual"],
                           "unidades_por_compra": manifesto["largura_bobina_m"], "origem": modelo["origem"]},
                "componentes": {k: especificacao(v) for k, v in manifesto["componentes"].items()},
                "tubos": {k: especificacao(v) for k, v in manifesto["tubos"].items()},
                "comandos": {k: especificacao(v) for k, v in manifesto["comandos"].items()},
            }
            receitas[str(row.id)] = ReceitaRolo.model_validate(receita).model_dump(mode="json")
            acabados.append({"produto_id": row.id, "nome": row.nome, "tecido_id": tecido.id})
    empresa.configuracoes = config
    db.flush()
    return {"empresa_id": empresa_id, "produtos_criados": criados, "produtos_corrigidos": alterados,
            "acabados": acabados}
