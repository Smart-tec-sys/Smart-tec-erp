import pandas as pd
import streamlit as st

from app.technical.catalog import TECHNICAL_CATALOG
from utils.api_client import (
    atualizar_equivalencia_tecnica,
    criar_equivalencia_tecnica,
    get_equivalencias_tecnicas,
    get_fornecedores,
    get_produtos_todos,
)
from utils.ui import cabecalho


def _json(response, default):
    if response is None or response.status_code != 200:
        return default
    payload = response.json()
    return payload if isinstance(payload, list) else default


def telaEquivalenciasTecnicas():
    cabecalho(
        titulo="⚙️ Equivalências técnicas",
        modulo="Produtos",
        tela_atual="Catálogo comercial",
    )
    st.caption("Vincule funções técnicas globais a produtos comerciais desta empresa.")

    products = get_produtos_todos()
    suppliers = _json(get_fornecedores(), [])
    equivalences = _json(get_equivalencias_tecnicas(), [])

    if not products:
        st.info("Cadastre produtos comerciais antes de criar equivalências.")
        return

    product_labels = {
        int(item["id"]): f'{item.get("codigo_interno") or item["id"]} — {item.get("nome") or "Produto"}'
        for item in products
    }
    supplier_labels = {0: "Sem fornecedor específico"}
    supplier_labels.update({int(item["id"]): item.get("nome") or str(item["id"]) for item in suppliers})

    with st.form("form_equivalencia_tecnica"):
        technical_function = st.selectbox("Função técnica", sorted(TECHNICAL_CATALOG))
        product_id = st.selectbox("Produto comercial", list(product_labels), format_func=product_labels.get)
        supplier_id = st.selectbox("Fornecedor", list(supplier_labels), format_func=supplier_labels.get)
        col_priority, col_preferred, col_active = st.columns(3)
        with col_priority:
            priority = st.number_input("Prioridade", min_value=0, value=100, step=1)
        with col_preferred:
            preferred = st.checkbox("Preferencial")
        with col_active:
            active = st.checkbox("Ativo", value=True)
        submit = st.form_submit_button("Vincular", type="primary")
        if submit:
            response = criar_equivalencia_tecnica({
                "funcao_tecnica": technical_function,
                "produto_id": product_id,
                "fornecedor_id": supplier_id or None,
                "prioridade": int(priority),
                "preferencial": preferred,
                "ativo": active,
                "configuracoes_locais": {},
            })
            if response is not None and response.status_code in (200, 201):
                st.success("Equivalência criada.")
                st.rerun()
            else:
                st.error("Não foi possível criar a equivalência.")

    if not equivalences:
        st.info("Nenhuma equivalência cadastrada para esta empresa.")
        return

    display = []
    for item in equivalences:
        display.append({
            "ID": item.get("id"),
            "Função técnica": item.get("funcao_tecnica"),
            "Produto": product_labels.get(int(item.get("produto_id") or 0), item.get("produto_id")),
            "Fornecedor": supplier_labels.get(int(item.get("fornecedor_id") or 0), item.get("fornecedor_id")),
            "Prioridade": item.get("prioridade"),
            "Preferencial": item.get("preferencial"),
            "Ativo": item.get("ativo"),
        })
    st.dataframe(pd.DataFrame(display), use_container_width=True, hide_index=True)

    by_id = {int(item["id"]): item for item in equivalences}
    with st.form("form_atualizar_equivalencia"):
        selected_id = st.selectbox("Equivalência para atualizar", list(by_id))
        selected = by_id[selected_id]
        priority = st.number_input("Nova prioridade", min_value=0, value=int(selected.get("prioridade") or 0))
        preferred = st.checkbox("Preferencial", value=bool(selected.get("preferencial")))
        active = st.checkbox("Ativo", value=bool(selected.get("ativo")), key="equivalencia_ativa_update")
        if st.form_submit_button("Atualizar"):
            response = atualizar_equivalencia_tecnica(selected_id, {
                "prioridade": int(priority), "preferencial": preferred, "ativo": active
            })
            if response is not None and response.status_code == 200:
                st.success("Equivalência atualizada.")
                st.rerun()
            else:
                st.error("Não foi possível atualizar a equivalência.")
