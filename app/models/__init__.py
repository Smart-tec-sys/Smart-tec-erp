from .fornecedor import FornecedorDB
from .empresa import EmpresaDB
from .empresa_portfolio import EmpresaPortfolioDB
from .usuario import UsuarioDB
from .empresa_usuario import EmpresaUsuarioDB
from .produto import ProdutoDB
from .classificacao_tecnica_produto import ClassificacaoTecnicaProdutoDB
from .equivalencia_tecnica import EmpresaEquivalenciaTecnicaDB
from .funcao_tecnica_referencia import FuncaoTecnicaReferenciaDB
from .fornecedor_alias import FornecedorAliasDB
from .produto_historico import ProdutoHistoricoAlteracaoDB

__all__ = [
    "EmpresaDB",
    "EmpresaPortfolioDB",
    "FornecedorDB",
    "UsuarioDB",
    "EmpresaUsuarioDB",
    "ProdutoDB",
    "ClassificacaoTecnicaProdutoDB",
    "EmpresaEquivalenciaTecnicaDB",
    "FuncaoTecnicaReferenciaDB",
    "FornecedorAliasDB",
    "ProdutoHistoricoAlteracaoDB",
]
