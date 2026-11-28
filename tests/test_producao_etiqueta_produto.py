"""Identificação do produto nas etiquetas; nenhum banco ou serviço externo."""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from app.services.producao_documentos import _dados_etiqueta, etiqueta_da_peca, etiquetas_lote_html


def fixture():
    piece = SimpleNamespace(id=31, pedido_item_id=12, sequencia=1, modelo='ROLO',
                            tecido='Screen', cor='Branco', acionamento='Manual', ambiente='Sala',
                            largura=Decimal('1.500'), altura=Decimal('2.250'), quantidade=1,
                            observacoes='Conferir acabamento', modo_fabricacao='AUTOMATICA',
                            especificacoes_fabricacao={})
    order = SimpleNamespace(id=9, snapshot={'empresa': 'Smart-tec Teste', 'pedido': 'VEN-TESTE',
                            'cliente': 'Cliente Teste', 'itens': [
                                {'id': 11, 'descricao': 'Produto de outro item', 'codigo_interno': 'OUTRO'},
                                {'id': 12, 'descricao': 'Persiana <Screen>', 'codigo_interno': 'RT-100&2'},
                            ]}, liberado_em=datetime(2026, 11, 13, tzinfo=timezone.utc), pecas=[piece])
    return order, piece


def test_label_identifies_product_from_matching_frozen_snapshot():
    order, piece = fixture()
    before = deepcopy(order.snapshot)
    data = _dados_etiqueta(order, piece)
    assert data['modelo'] == 'ROLO · Persiana &lt;Screen&gt; [RT-100&amp;2]'
    assert 'Produto de outro item' not in data['modelo']
    assert data['codigo'] == 'OP-000009-I12-P0001'
    assert data['cliente'] == 'Cliente Teste' and data['pedido'] == 'VEN-TESTE'
    assert data['ambiente'] == 'Sala' and data['largura'] == '1.500 m'
    assert data['altura'] == '2.250 m' and piece.modelo == 'ROLO'
    assert order.snapshot == before


def test_individual_and_batch_reuse_existing_renderer_with_product_identity():
    order, piece = fixture()
    from modulos.produtos_etiquetas import gerar_html_impressao, gerar_html_impressao_lote
    with patch('modulos.produtos_etiquetas.gerar_html_impressao', wraps=gerar_html_impressao) as single:
        html = etiqueta_da_peca(order, piece)
    with patch('modulos.produtos_etiquetas.gerar_html_impressao_lote', wraps=gerar_html_impressao_lote) as batch:
        batch_html = etiquetas_lote_html(order)
    single.assert_called_once()
    batch.assert_called_once()
    for result in (html, batch_html):
        assert 'Persiana &lt;Screen&gt;' in result and 'RT-100&amp;2' in result
        assert 'OP-000009-I12-P0001' in result and 'Cliente Teste' in result
        assert 'Sala' in result and '1.500 m' in result and '2.250 m' in result
        assert 'Produto de outro item' not in result and '<Screen>' not in result


def test_old_snapshot_without_product_identity_preserves_technical_model():
    order, piece = fixture()
    order.snapshot['itens'] = []
    assert _dados_etiqueta(order, piece)['modelo'] == 'ROLO'
