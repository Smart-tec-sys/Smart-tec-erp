from decimal import Decimal
from types import SimpleNamespace

from app.models.cliente import ClienteDB
from app.models.orcamento import OrcamentoItemDB
from app.schemas.orcamento import OrcamentoItemInput
from app.services.orcamento_service import ITEM_PERSISTED_FIELDS
from app.services.romana_teto_simulacao import (
    resolver_tecido_pimpoint,
    STATUS_RESOLVIDO,
)


def test_romana_teto_campos_transitorios_nao_vazam_para_orm():
    item = OrcamentoItemInput(
        tipo_item="PRODUTO",
        produto_id=3526,
        descricao="ROMANA TETO BLACKOUT PIMPOINT",
        quantidade=1,
        largura=2.20,
        altura=2.00,
        area=4.40,
        preco_unitario=59.96,
        desconto=0,
        subtotal=263.82,
        cor="BRANCO",
        largura_modulo_m=2.20,
        comprimento_avanco_m=2.00,
        quantidade_modulos=1,
        acionamento_romana_teto="MANUAL_BASTAO",
        comprimento_bastao_m=1.50,
        comprimento_corrente_sem_fim_m=None,
    )

    valores = item.dict(include=ITEM_PERSISTED_FIELDS)

    esperados = {
        "produto_id",
        "quantidade",
        "largura",
        "altura",
        "preco_unitario",
        "desconto",
        "cor",
    }

    transitorios = {
        "largura_modulo_m",
        "comprimento_avanco_m",
        "quantidade_modulos",
        "acionamento_romana_teto",
        "comprimento_bastao_m",
        "comprimento_corrente_sem_fim_m",
    }

    assert esperados.issubset(valores.keys())
    assert transitorios.isdisjoint(valores.keys())

    orm = OrcamentoItemDB(**valores)

    assert orm.produto_id == 3526
    assert orm.cor == "BRANCO"
    assert orm.quantidade == 1


def test_pimpoint_sem_payload_e_sem_produto_cor_usa_variacao_cor():
    produto = SimpleNamespace(
        familia_tecnica="ROMANA_TETO_BLACKOUT_PIMPOINT",
        modelo_tecnico="ROMANA_TETO",
        nome="ROMANA TETO BLACKOUT PIMPOINT",
        cor=None,
        variacao_cor="BRANCO",
    )

    resultado = resolver_tecido_pimpoint(
        produto,
        largura_modulo_m=2.20,
        entrada_cor=None,
    )

    assert resultado.status == STATUS_RESOLVIDO
    assert resultado.cor == "BRANCO"
    assert resultado.codigo_fonte == "JPTEC-0092"
    assert resultado.largura_tecido_selecionada_m == 2.50
    assert resultado.custo_tecido_m2 == Decimal("29.98")



