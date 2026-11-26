from contextlib import asynccontextmanager
from app.settings import get_commercial_mode_setting, initialize_backend_configuration

initialize_backend_configuration()

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.database import engine
from app import media_storage
from app.media_storage import (
    MediaNaoEncontrada,
    MediaStorageError,
    chave_valida,
    tipo_da_chave,
)

from app.tenant.commercial_observer_integration import preparar_integracao_comercial
from app.routes.webhooks_wix import router as router_webhooks_wix
from app.routes.cliente import router as router_cliente
from app.routes.fornecedor import router as router_fornecedor
from app.routes.funcionario import router as router_funcionario
from app.routes.transportadora import router as router_transportadora
from app.routes.opcao_auxiliar import router as router_opcao_auxiliar
from app.routes.grades_variacoes import router as router_grades_variacoes
from app.routes.produto import router as router_produto
from app.routes.servico import router as router_servico
from app.routes.orcamento import router as router_orcamento
from app.routes.pedido import router as router_pedido
from app.routes.fiscal_cadastros import router as router_fiscal_cadastros
from app.routes.producao import router as router_producao
from app.routes.contabilidade import router as router_contabilidade
from app.routes.representante import router as router_representante
from app.routes.consultas_cadastro import router as router_consultas_cadastro
from app.routes.diagnostico import router as router_diagnostico
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
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.integracao_comercial = preparar_integracao_comercial(
        get_commercial_mode_setting()
    )
    try:
        yield
    finally:
        app.state.integracao_comercial.encerrar()


app = FastAPI(
    title="Smart-tec ERP API",
    lifespan=lifespan,
)

# Integracao comercial inicializada e encerrada pelo lifespan do FastAPI.
# Imagens servidas pela propria API para manter as URLs /media/... ja gravadas no banco.
@app.api_route("/media/{chave:path}", methods=["GET", "HEAD"], include_in_schema=False)
def servir_media(chave: str):
    if not chave_valida(chave):
        raise HTTPException(status_code=404, detail="Not Found")
    try:
        conteudo = media_storage.obter_media_storage().ler(chave)
    except MediaNaoEncontrada:
        raise HTTPException(status_code=404, detail="Not Found") from None
    except MediaStorageError:
        raise HTTPException(status_code=503, detail="armazenamento de imagens indisponível") from None
    return Response(
        content=conteudo,
        media_type=tipo_da_chave(chave),
        headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"},
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
app.include_router(router_servico, prefix="/servicos", tags=["Serviços"])
app.include_router(router_orcamento, prefix="/orcamentos", tags=["Orçamentos"])
app.include_router(router_pedido, prefix="/pedidos", tags=["Vendas / Pedidos"])
app.include_router(router_fiscal_cadastros, prefix="/fiscal/cadastros", tags=["Fiscal - Cadastros"])
app.include_router(router_producao, prefix="/producao", tags=["Produção"])
app.include_router(router_contabilidade, prefix="/contabilidade", tags=["Contabilidade"])
app.include_router(router_representante, prefix="/representantes", tags=["Representantes e RT"])
app.include_router(router_consultas_cadastro, prefix="/consultas", tags=["Consultas cadastrais"])
app.include_router(router_diagnostico)
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
