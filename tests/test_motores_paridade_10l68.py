"""Motores reais em memória: nenhuma escrita nem conexão com banco."""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from app.schemas.orcamento import OrcamentoInput
from app.schemas.pedido import PedidoCreate
from app.services.composicao_comercial import calcular_itens
from app.services.romana_simulacao import simular_romana, RomanaSimulacaoInput
from app.services.rolo_simulacao import simular_rolo, RoloSimulacaoInput
from app.services.double_vision_simulacao import simular_double_vision, DoubleVisionSimulacaoInput
from app.services.romana_teto_simulacao import simular_romana_teto, RomanaTetoSimulacaoInput
from app.services.cortina_simulacao import simular_cortina, CortinaSimulacaoInput

MODELS = ['ROLO', 'ROMANA', 'ROMANA_TETO', 'DOUBLE_VISION', 'CORTINA']
CURTAIN = dict(tecidoProdutoId=1, fator=2.5, larguraTecido=1.5, modeloPrega='WAVE', trilhoLinha='MINI', rodizioTipo='MINI', barraCm=15)

def setup(model, width=1.82, quantity=1):
    product = SimpleNamespace(id=1, nome=model.replace('_',' '), modelo_tecnico=None if model == 'CORTINA' else model,
        grupo_tecnico='TECIDOS_CORTINA' if model == 'CORTINA' else None,
        tipo_produto='Tecido' if model == 'CORTINA' else 'Produto fabricado', familia_tecnica='ROMANA_TETO_BLACKOUT_PIMPOINT' if model == 'ROMANA_TETO' else None,
        custo_final=100, valor_custo=100, valor_venda=250, unidade_venda='M2')
    config = {'romana_teto': dict(acionamento='MANUAL_CORRENTE',lado_comando='DIREITA',comprimento_corrente_sem_fim_m=1.75)} if model == 'ROMANA_TETO' else {'cortina': CURTAIN} if model == 'CORTINA' else None
    item = dict(produto_id=1, descricao=product.nome, quantidade=quantity, largura=width, altura=2.45,
                modelo_tecnico=model, cor='BEGE', dados_tecnicos=config, preco_unitario=99999, subtotal=99999)
    common = dict(produto_id=1, largura=width, altura=2.45, quantidade=quantity, perfil_comercial='VAREJO')
    if model == 'ROMANA': expected=simular_romana(product, RomanaSimulacaoInput(**common))
    elif model == 'ROLO': expected=simular_rolo(product, RoloSimulacaoInput(**common))
    elif model == 'DOUBLE_VISION': expected=simular_double_vision(product, DoubleVisionSimulacaoInput(**common))
    elif model == 'ROMANA_TETO': expected=simular_romana_teto(product, RomanaTetoSimulacaoInput(produto_id=1,
        largura_modulo_m=width, comprimento_avanco_m=2.45, quantidade_modulos=quantity, cor='BEGE', **config['romana_teto']))
    else: expected=simular_cortina(product, CortinaSimulacaoInput(**common, fator=2.5, largura_tecido=1.5,
        modelo_prega='WAVE', trilho_linha='MINI', rodizio_tipo='MINI', barra_cm=15))
    return product,item,expected

@pytest.mark.parametrize('model',MODELS)
@pytest.mark.parametrize('width,quantity',[(1.82,1),(2.00,1),(2.00,2)])
def test_documentos_reutilizam_resultado_exato_do_motor(model,width,quantity):
    product,item,expected=setup(model,width,quantity)
    results=[]
    for schema in [OrcamentoInput,PedidoCreate]:
        data=schema(cliente_id=1,itens=[item])
        db=MagicMock(); db.query.return_value.filter.return_value.first.return_value=product
        document=SimpleNamespace(itens=[])
        calcular_itens(db,document,data,1,SimpleNamespace)
        saved=document.itens[0]
        assert Decimal(str(saved.subtotal)) == Decimal(str(expected['subtotal']))
        assert Decimal(str(saved.preco_unitario)) == Decimal(str(expected['preco_unitario']))
        assert document.total == Decimal(str(expected['subtotal']))
        assert saved.calculo_producao_status == 'SIMULACAO_RECALCULADA'
        db.commit.assert_not_called()
        results.append((saved.preco_unitario,saved.subtotal,saved.area))
    assert results[0] == results[1]

@pytest.mark.parametrize('model',['ROLO','ROMANA_TETO','CORTINA'])
def test_quantidade_fracionada_nao_cai_em_calculo_generico(model):
    product,item,_=setup(model); item['quantidade']=1.5
    db=MagicMock(); db.query.return_value.filter.return_value.first.return_value=product
    with pytest.raises(ValueError,match='inteira'):
        calcular_itens(db,SimpleNamespace(itens=[]),PedidoCreate(cliente_id=1,itens=[item]),1,SimpleNamespace)

def test_pimpoint_sem_cor_nao_salva_preco_generico():
    product,item,_=setup('ROMANA_TETO'); item['cor']=None
    db=MagicMock(); db.query.return_value.filter.return_value.first.return_value=product
    with pytest.raises(ValueError,match='Preço técnico indisponível'):
        calcular_itens(db,SimpleNamespace(itens=[]),PedidoCreate(cliente_id=1,itens=[item]),1,SimpleNamespace)
