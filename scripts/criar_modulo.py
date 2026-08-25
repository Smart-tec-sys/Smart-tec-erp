    import sys
from pathlib import Path

# Usando .parent.parent para evitar o bug de formatação do chat
ROOT = Path(__file__).resolve().parent.parent


def nome_cap(nome):
    return "".join(p.capitalize() for p in nome.split("_"))


def ensure_init(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    init_file = path / "__init__.py"
    if not init_file.exists():
        init_file.write_text("", encoding="utf-8")


def criar_modulo(nome):
    nome = nome.lower()
    Nome = nome_cap(nome)

    # ───────── CAMINHOS ─────────
    plugin_dir = ROOT / "plugins" / nome
    modulos_dir = ROOT / "modulos"
    backend_dir = ROOT / "backend" / "app"

    models_dir = backend_dir / "models"
    schemas_dir = backend_dir / "schemas"
    crud_dir = backend_dir / "crud"
    routers_dir = backend_dir / "routers"

    # ───────── GARANTIR ESTRUTURA ─────────
    for p in [plugin_dir, modulos_dir, models_dir, schemas_dir, crud_dir, routers_dir]:
        ensure_init(p)

    ensure_init(backend_dir)

    # ───────── FRONT ─────────
    front = f"""from core.plugin_api import FrontPlugin
from modulos.{nome} import tela{Nome}

class Plugin(FrontPlugin):
    slug = "{nome}"
    label = "📦 {Nome}"
    group = "Cadastros"

    def render(self):
        tela{Nome}()

def get_plugin():
    return Plugin
"""

    # ───────── BACK (PLUGIN) ─────────
    back = f"""from core.plugin_api import BackPlugin
from backend.app.routers.{nome} import router

class Plugin(BackPlugin):
    def register(self, app):
        app.include_router(router)

def get_plugin():
    return Plugin
"""

    # ───────── MODULE UI ─────────
    modulo = f"""import streamlit as st
import pandas as pd
from utils.ui import toolbar

def tela{Nome}():

    if "tela_{nome}" not in st.session_state:
        st.session_state.tela_{nome} = "listar"

    def mudar_tela(tela):
        st.session_state.tela_{nome} = tela

    st.title("📦 {Nome}")

    if st.session_state.tela_{nome} == "listar":

        tb = toolbar(placeholder="Buscar {nome}...")

        if tb.get("add"):
            mudar_tela("adicionar")
            st.rerun()

        st.info("Nenhum {nome} cadastrado.")

    elif st.session_state.tela_{nome} == "adicionar":

        if st.button("⬅️ Voltar"):
            mudar_tela("listar")
            st.rerun()

        st.subheader("Adicionar {Nome}")

        with st.form("form_{nome}"):

            nome_campo = st.text_input("Nome")

            salvar = st.form_submit_button("Salvar", type="primary")

            if salvar:
                st.success("{Nome} salvo com sucesso!")
                mudar_tela("listar")
                st.rerun()
"""

    # ───────── MODEL ─────────
    model = f"""from sqlalchemy import Column, Integer, String
from backend.app.database import Base

class {Nome}(Base):
    __tablename__ = "{nome}"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
"""

    # ───────── SCHEMA ─────────
    schema = f"""from pydantic import BaseModel

class {Nome}Base(BaseModel):
    nome: str

class {Nome}Create({Nome}Base):
    pass

class {Nome}Out({Nome}Base):
    id: int

    model_config = {{"from_attributes": True}}
"""

    # ───────── CRUD ─────────
    crud = f"""from sqlalchemy.orm import Session
from backend.app.models.{nome} import {Nome}
from backend.app.schemas.{nome} import {Nome}Create

def get_all(db: Session):
    return db.query({Nome}).all()

def create(db: Session, obj_in: {Nome}Create):
    db_obj = {Nome}(**obj_in.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
"""

    # ───────── ROUTER ─────────
    router = f"""from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.crud import {nome} as crud_{nome}
from backend.app.schemas.{nome} import {Nome}Out, {Nome}Create

router = APIRouter(prefix="/{nome}", tags=["{Nome}"])

@router.get("/", response_model=list[{Nome}Out])
def listar(db: Session = Depends(get_db)):
    return crud_{nome}.get_all(db)

@router.post("/", response_model={Nome}Out)
def criar(item: {Nome}Create, db: Session = Depends(get_db)):
    return crud_{nome}.create(db=db, obj_in=item)
"""

    # ───────── SALVAR ─────────
    (plugin_dir / "front.py").write_text(front, encoding="utf-8")
    (plugin_dir / "back.py").write_text(back, encoding="utf-8")

    (modulos_dir / f"{nome}.py").write_text(modulo, encoding="utf-8")

    (models_dir / f"{nome}.py").write_text(model, encoding="utf-8")
    (schemas_dir / f"{nome}.py").write_text(schema, encoding="utf-8")
    (crud_dir / f"{nome}.py").write_text(crud, encoding="utf-8")
    (routers_dir / f"{nome}.py").write_text(router, encoding="utf-8")

    print(f"✅ Módulo '{nome}' criado COMPLETO!")


# ───────── EXECUÇÃO ─────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Uso: python scripts/criar_modulo.py nome_modulo")
    else:
        # Usando -1 para pegar o último argumento e evitar o bug do chat
        criar_modulo(sys.argv[-1])
