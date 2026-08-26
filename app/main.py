from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.cliente import router as router_cliente
from app.routes.fornecedor import router as router_fornecedor
from app.routes.funcionario import router as router_funcionario
from app.routes.transportadora import router as router_transportadora
from app.routes.opcao_auxiliar import router as router_opcao_auxiliar
from app.routes.produto import router as router_produto
from app.routes.orcamento import router as router_orcamento

# =========================================================
# INSTANCIAR O FASTAPI
# =========================================================
app = FastAPI(title="Smart-tec ERP API")

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


# =========================================================
# ROTA RAIZ
# =========================================================
@app.get("/")
def raiz():
    return {"mensagem": "API do Smart-tec ERP rodando perfeitamente!"}
