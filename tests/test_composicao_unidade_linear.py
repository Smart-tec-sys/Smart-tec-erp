from decimal import Decimal
from types import SimpleNamespace

from app.services.area_faturavel import AreaFaturavelResultado
from app.services.composicao_comercial import _preco_produto, calcular_base_comercial
from app.schemas.produto import ProdutoCreate
from app.services.produto_service import update
from app.tenant.context import TenantContext


def area(real, faturavel):
    return AreaFaturavelResultado(
        area_real_m2=Decimal(str(real)),
        area_faturavel_m2=Decimal(str(faturavel)),
        minimo_faturavel_aplicado=Decimal(str(real)) != Decimal(str(faturavel)),
    )


def test_bando_ml_usa_comprimento_sem_exigir_altura():
    base = calcular_base_comercial('ML', 'ROLO', 1.65, area(0, 0), 1)
    assert base == Decimal('1.65')
    assert base * Decimal('87.50') == Decimal('144.3750')


def test_ml_multiplica_comprimento_por_quantidade():
    base = calcular_base_comercial('METRO LINEAR', '', 1.65, area(0, 0), 3)
    assert base == Decimal('4.95')


def test_m2_preserva_area_faturavel_minima():
    assert calcular_base_comercial('M2', '', 0.70, area(0.49, 1.50), 1) == Decimal('1.50')


def test_un_e_demais_unidades_usam_quantidade():
    assert calcular_base_comercial('UN', '', 1.65, area(0, 0), 3) == Decimal('3')


def test_perfil_comercial_150_porcento_nao_divide_preco_por_barra():
    produto = SimpleNamespace(custo_final=35, valor_custo=35, valor_venda=524.92)
    preco_ml = _preco_produto(produto, 'CONSUMIDOR_FINAL')
    subtotal = calcular_base_comercial('ML', '', 1.65, area(0, 0), 1) * preco_ml
    assert preco_ml == Decimal('87.50')
    assert subtotal.quantize(Decimal('0.01')) == Decimal('144.38')


class Query:
    def __init__(self, produto):
        self.produto = produto

    def filter(self, *_args):
        return self

    def first(self):
        return self.produto


class Database:
    def __init__(self, produto):
        self.produto = produto

    def query(self, *_args):
        return Query(self.produto)

    def commit(self):
        pass

    def refresh(self, _produto):
        pass

    def rollback(self):
        pass


def test_editar_margem_preserva_preco_manual_sem_recalculo_explicito():
    produto = SimpleNamespace(
        id=7, empresa_id=1, nome='Bandô', valor_custo=35,
        despesas_acessorias=0, outras_despesas=0, custo_final=35,
        margem_lucro=150, valor_venda=524.92,
    )
    atualizado = update(
        Database(produto),
        7,
        ProdutoCreate(nome='Bandô', margem_lucro=200),
        TenantContext(empresa_id=1),
    )
    assert atualizado.margem_lucro == 200
    assert atualizado.valor_venda == 524.92
