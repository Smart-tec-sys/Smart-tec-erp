from app.settings import get_commercial_mode_setting, initialize_backend_configuration

initialize_backend_configuration()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from app.database import engine

from app.tenant.commercial_observer_integration import preparar_integracao_comercial
from app.routes.webhooks_wix import router as router_webhooks_wix
from app.routes.cliente import router as router_cliente
from app.routes.fornecedor import router as router_fornecedor
from app.routes.funcionario import router as router_funcionario
from app.routes.transportadora import router as router_transportadora
from app.routes.opcao_auxiliar import router as router_opcao_auxiliar
from app.routes.grades_variacoes import router as router_grades_variacoes
from app.routes.produto import router as router_produto
from app.routes.orcamento import router as router_orcamento
from app.routes.pedido import router as router_pedido
from app.routes.contabilidade import router as router_contabilidade
from app.routes.representante import router as router_representante
from app.routes.auth import router as router_auth
from app.routes.admin import router as router_admin
from app.routes.equivalencia_tecnica import router as router_equivalencia_tecnica
from app.routes.empresa import router as router_empresa
from app.routes.agenda_evento import router as router_agenda_evento
from app.routes.financeiro_cadastros import router as router_financeiro_cadastros
from app.routes.financeiro_titulos import router as router_financeiro_titulos
from app.routes.financeiro_fluxo_caixa import router as router_financeiro_fluxo_caixa

# =========================================================
# INSTANCIAR O FASTAPI
# =========================================================
app = FastAPI(title="Smart-tec ERP API")

# Integracao comercial: sempre OFF nesta fase; sem pool, thread, consulta ou dependencia em rotas.
app.state.integracao_comercial = preparar_integracao_comercial(get_commercial_mode_setting())
app.add_event_handler("shutdown", app.state.integracao_comercial.encerrar)
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
app.include_router(router_webhooks_wix)
app.include_router(router_cliente, prefix="/clientes", tags=["Clientes"])
app.include_router(router_fornecedor, prefix="/fornecedores", tags=["Fornecedores"])
app.include_router(router_funcionario, prefix="/funcionarios", tags=["Funcionários"])
app.include_router(router_transportadora, prefix="/transportadoras", tags=["Transportadoras"])
app.include_router(router_opcao_auxiliar, prefix="/opcoes-auxiliares", tags=["Opções Auxiliares"])
app.include_router(router_grades_variacoes, prefix="/grades-variacoes", tags=["Grades / Variações"])
app.include_router(router_produto, prefix="/produtos", tags=["Produtos"])
app.include_router(router_orcamento, prefix="/orcamentos", tags=["Orçamentos"])
app.include_router(router_pedido, prefix="/pedidos", tags=["Vendas / Pedidos"])
app.include_router(router_contabilidade, prefix="/contabilidade", tags=["Contabilidade"])
app.include_router(router_representante, prefix="/representantes", tags=["Representantes e RT"])
app.include_router(router_auth, prefix="/auth", tags=["Autenticação"])
app.include_router(router_admin, prefix="/admin", tags=["Administração Smart-tec"])
app.include_router(router_empresa, prefix="/empresa", tags=["Empresa"])
app.include_router(router_agenda_evento, prefix="/agenda", tags=["Agenda"])
app.include_router(router_financeiro_cadastros, prefix="/financeiro", tags=["Financeiro"])
app.include_router(router_financeiro_titulos, prefix="/financeiro", tags=["Financeiro"])
app.include_router(router_financeiro_fluxo_caixa, prefix="/financeiro", tags=["Financeiro"])
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
