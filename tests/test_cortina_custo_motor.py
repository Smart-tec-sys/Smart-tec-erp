from types import SimpleNamespace
from decimal import Decimal
from unittest.mock import MagicMock
import pytest
from app.services.cortina_simulacao import CortinaSimulacaoInput, simular_cortina, simular_cortina_catalogo
from app.services.composicao_comercial import calcular_itens
from app.schemas.orcamento import OrcamentoInput
from app.schemas.pedido import PedidoCreate

def produto(id, custo=10, **kw):
    return SimpleNamespace(id=id, custo_final=custo, valor_custo=0, valor_venda=0,
                           modelo_tecnico=None, grupo_tecnico='TECIDOS_CORTINA', largura=3, **kw)

def entrada(**kw):
    return CortinaSimulacaoInput(**dict(dict(tecido_produto_id=1,largura=2,altura=2,quantidade=1,
                                            fator=2.5,largura_tecido=3,modelo_prega='PREGA'),**kw))

@pytest.mark.parametrize('altura,alturas,custo',[(1.5,1,35),(2,2,70),(3,2,70),(3.1,3,105)])
def test_mao_de_obra_confirmada(altura,alturas,custo):
    out=simular_cortina(produto(1),entrada(altura=altura))
    assert out['mao_de_obra']==dict(quantidade_alturas=alturas,valor_por_altura=35,total=custo)

def componentes():
    return dict(forro=produto(2,5),trilho=produto(3,20),rodizio=produto(4,.5),entretela=produto(5,1))

def test_cenario_completo_sem_duplicidade_e_quantidade():
    out=simular_cortina(produto(1),entrada(possui_forro=True,forro_produto_id=2,quantidade=2,desconto=10),componentes())
    assert out['tecido']['consumo_total_ml']==9.6
    assert out['forro']['consumo_unitario_ml']==4.8
    assert out['forro']['custo_total']==24
    costs={c['componente']:c['custo_total'] for c in out['composicao']}
    assert costs==dict(tecido=48,forro=24,trilho=40,rodizios=10,entretela=5,mao_de_obra=70)
    assert out['custo_total']==197 and out['custo_completo']
    assert out['preco_unitario']==394 and out['subtotal']==778
    print('Cenario: 2m x 2m; 2 alturas costureira=70; tecido 4.8ml=48; forro 4.8ml=24; trilho=40; acessorios=10; entretela=5; custo=197; VAREJO=394; 2 pecas -10=778')

def test_tecido_diferente_altera_preco():
    a=simular_cortina(produto(1,10),entrada(),componentes())
    b=simular_cortina(produto(6,20),entrada(tecido_produto_id=6),componentes())
    assert b['preco_unitario']-a['preco_unitario']==96

def test_componentes_sem_vinculo_nao_sao_inventados():
    out=simular_cortina(produto(1),entrada())
    assert set(out['pendencias_custo'])=={'trilho','rodizios','entretela'}
    assert not out['custo_completo'] and out['origem_preco'].endswith('PARCIAL')
    assert all(c['produto_id'] in (1,None) for c in out['composicao'])

@pytest.mark.parametrize('perfil,preco',[('DECORADOR',259.5),('VAREJO',346),('CONSUMIDOR_FINAL',432.5)])
def test_helper_comercial_canonico(perfil,preco):
    assert simular_cortina(produto(1),entrada(perfil_comercial=perfil),componentes())['preco_unitario']==preco

def test_fallback_custo_final_valor_custo_valor_venda():
    p=produto(1,0);p.valor_custo=12
    assert simular_cortina(p,entrada())['composicao'][0]['custo_unitario']==12
    p.valor_custo=0;p.valor_venda=13
    out=simular_cortina(p,entrada())
    assert out['composicao'][0]['custo_unitario']==13
    assert out['composicao'][0]['origem_custo']=='VALOR_VENDA_CADASTRADO'

def test_historico_nao_e_base():
    p=produto(1);p.modelo_tecnico='CORTINA'
    with pytest.raises(ValueError,match='histórico'):simular_cortina(p,entrada())

@pytest.mark.parametrize('forro,largura',[(None,3),(produto(2,5),None)])
def test_forro_incompleto_nao_libera_preco(forro,largura):
    if forro:forro.largura=0
    out=simular_cortina(produto(1),entrada(possui_forro=True,largura_forro=largura),dict(forro=forro))
    assert not out['preco_disponivel']

def test_id_fora_tenant_recusado():
    db=MagicMock();db.query.return_value.filter.return_value.first.return_value=None
    with pytest.raises(ValueError,match='empresa ativa'):simular_cortina_catalogo(db,entrada(),1)
    db.commit.assert_not_called()

@pytest.mark.parametrize('schema',[OrcamentoInput,PedidoCreate])
def test_documento_virtual_recalcula_nao_confia_no_preco_frontend(schema):
    p=produto(1);db=MagicMock();db.query.return_value.filter.return_value.first.return_value=p
    item=dict(tipo_item='PRODUTO',produto_id=None,descricao='Cortina de tecido',modelo_tecnico='CORTINA',
              grupo_tecnico='TECIDOS_CORTINA',largura=2,altura=2,quantidade=2,preco_unitario=999,subtotal=999,
              dados_tecnicos={'cortina':dict(tecidoProdutoId=1,fator=2.5,larguraTecido=3,modeloPrega='PREGA')})
    doc=SimpleNamespace(itens=[])
    calcular_itens(db,doc,schema(cliente_id=1,itens=[item]),1,SimpleNamespace)
    assert doc.itens[0].preco_unitario==236 and doc.total==Decimal('472')
    assert doc.itens[0].produto_id is None
    assert doc.itens[0].dados_tecnicos['cortina']['result']['custo_total']==118
    db.commit.assert_not_called()


def test_produto_generico_sem_id_continua_bloqueado():
    with pytest.raises(ValueError, match='Selecione o produto'):
        PedidoCreate(cliente_id=1,itens=[dict(descricao='Produto',modelo_tecnico='ROLO',produto_id=None)])

def test_forro_final_historico_recusado():
    tecido=produto(1);forro=produto(2);forro.modelo_tecnico='CORTINA'
    db=MagicMock();db.query.return_value.filter.return_value.first.side_effect=[tecido,forro]
    with pytest.raises(ValueError,match='Forro: selecione o tecido real'):
        simular_cortina_catalogo(db,entrada(possui_forro=True,forro_produto_id=2),1)
