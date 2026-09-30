from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from app.database import engine

from app.routes.cliente import router as router_cliente
from app.routes.fornecedor import router as router_fornecedor
from app.routes.funcionario import router as router_funcionario
from app.routes.transportadora import router as router_transportadora
from app.routes.opcao_auxiliar import router as router_opcao_auxiliar
from app.routes.produto import router as router_produto
from app.routes.orcamento import router as router_orcamento
from app.routes.auth import router as router_auth
from app.routes.admin import router as router_admin
from app.routes.equivalencia_tecnica import router as router_equivalencia_tecnica
from app.routes.empresa import router as router_empresa
from app.routes.agenda_evento import router as router_agenda_evento

# =========================================================
# INSTANCIAR O FASTAPI
# =========================================================
app = FastAPI(title="Smart-tec ERP API")
from pathlib import Path

MEDIA_DIR = Path("media")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

app.mount(
    "/media",
    StaticFiles(directory=str(MEDIA_DIR)),
    name="media",
)


# =========================================================
# CONFIGURAR CORS
# =========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "service": "smart-tec-erp-api",
    }


@app.get("/health/db", tags=["Health"])
def health_db():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "ok",
            "database": "connected",
        }
    except Exception:
        import logging

        logging.exception("Falha no health check do banco de dados")

        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "database": "unavailable",
            },
        )

# =========================================================
# INCLUIR ROTAS
# =========================================================
app.include_router(router_cliente, prefix="/clientes", tags=["Clientes"])
app.include_router(router_fornecedor, prefix="/fornecedores", tags=["Fornecedores"])
app.include_router(router_funcionario, prefix="/funcionarios", tags=["Funcionários"])
app.include_router(router_transportadora, prefix="/transportadoras", tags=["Transportadoras"])
app.include_router(router_opcao_auxiliar, prefix="/opcoes-auxiliares", tags=["Opções Auxiliares"])
app.include_router(router_produto, prefix="/produtos", tags=["Produtos"])
app.include_router(router_orcamento, prefix="/orcamentos", tags=["Orçamentos"])
app.include_router(router_auth, prefix="/auth", tags=["Autenticação"])
app.include_router(router_admin, prefix="/admin", tags=["Administração Smart-tec"])
app.include_router(router_empresa, prefix="/empresa", tags=["Empresa"])
app.include_router(router_agenda_evento, prefix="/agenda", tags=["Agenda"])
app.include_router(
    router_equivalencia_tecnica,
    prefix="/equivalencias-tecnicas",
    tags=["Equivalências Técnicas"],
)




# =========================================================
# ROTA RAIZ
# =========================================================
@app.get("/")
def raiz():
    return {"mensagem": "API do Smart-tec ERP rodando perfeitamente!"}
