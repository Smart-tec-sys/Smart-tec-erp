from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from app.services.cortina_simulacao import CortinaSimulacaoInput, simular_cortina, simular_cortina_catalogo, componente_cortina_elegivel, entrada_cortina_item


def product(id, nome='Trilho cortina', cost=10, **extra):
    return SimpleNamespace(**dict(dict(id=id,nome=nome,grupo_tecnico='COMPONENTES_CORTINAS',situacao='Ativo',modelo_tecnico=None,grupo_produto='Componentes cortina',familia_tecnica=None,tipo_cortina_persiana=None,custo_final=cost,valor_custo=0,valor_venda=0,largura=3),**extra))


def input(**extra):
    return CortinaSimulacaoInput(**dict(dict(tecido_produto_id=1,largura=2,altura=2,fator=2.5,largura_tecido=3,modelo_prega='PREGA',componentes=[]),**extra))


@pytest.mark.parametrize('nome',['Trilho simples','Trilho duplo','Trilho Master','Varão','Rodízios','Carrinhos','Suportes cortina','Ponteiras','Tampas','Entretela','Acessório cortina'])
def test_allowed_curtain_components(nome):
    assert componente_cortina_elegivel(product(2,nome))


@pytest.mark.parametrize('extra',[
    dict(nome='Comando 32 Rolô'),dict(nome='Corrente de persiana'),dict(nome='Tubo cortina'),dict(nome='Base cortina'),
    dict(nome='Suporte Double Vision'),dict(modelo_tecnico='ROMANA'),dict(grupo_produto='Persianas'),
    dict(grupo_tecnico='COMPONENTES_PERSIANAS'),dict(situacao='Inativo'),
])
def test_persiana_and_inactive_never_enter(extra):
    assert not componente_cortina_elegivel(product(2,**extra))


@pytest.mark.parametrize('model',['PREGA','WAVE'])
def test_explicit_components_quantity_remove_no_automatic_links(model):
    fabric=product(1,'Tecido',grupo_tecnico='TECIDOS_CORTINA')
    rail=product(2,cost=20);accessory=product(3,'Ponteira',cost=3)
    empty=simular_cortina(fabric,input(modelo_prega=model))
    assert empty['custo_total']==118 and empty['custo_completo']
    data=input(modelo_prega=model,componentes=[dict(produto_id=2,quantidade=2.5),dict(produto_id=3,quantidade=4)])
    selected=simular_cortina(fabric,data,{'livres':[rail,accessory]})
    assert selected['custo_total']==180
    assert [r['produto_id'] for r in selected['composicao']]==[1,2,3,None]
    data.componentes[0].quantidade=3
    assert simular_cortina(fabric,data,{'livres':[rail,accessory]})['custo_total']==190
    data.componentes.pop(0)
    assert simular_cortina(fabric,data,{'livres':[accessory]})['custo_total']==130
    assert data.modelo_prega==model


def test_real_cost_precedence_not_frontend_value():
    fabric=product(1,'Tecido',grupo_tecnico='TECIDOS_CORTINA');p=product(2,cost=12,valor_custo=99)
    out=simular_cortina(fabric,input(componentes=[dict(produto_id=2,quantidade=2)]),{'livres':[p]})
    assert out['custo_total']==142
    assert out['composicao'][1]['custo_unitario']==12


@pytest.mark.parametrize('quantity',[-1,float('nan'),float('inf')])
def test_invalid_quantity(quantity):
    with pytest.raises(ValueError):input(componentes=[dict(produto_id=2,quantidade=quantity)])


def test_tenant_lookup_and_classification():
    db=MagicMock();fabric=product(1,'Tecido',grupo_tecnico='TECIDOS_CORTINA')
    data=input(componentes=[dict(produto_id=2,quantidade=2)])
    db.query.return_value.filter.return_value.first.side_effect=[fabric,None]
    with pytest.raises(ValueError,match='empresa ativa'):simular_cortina_catalogo(db,data,1)
    db.query.return_value.filter.return_value.first.side_effect=[fabric,product(2,'Comando 32 Rolô')]
    with pytest.raises(ValueError,match='ativos de cortina'):simular_cortina_catalogo(db,data,1)
    db.commit.assert_not_called()


def test_saved_technical_json_preserves_free_lines():
    item=SimpleNamespace(dados_tecnicos={'cortina':dict(fator=2.5,larguraTecido=3,modeloPrega='WAVE',tecidoProdutoId=1,componentes=[dict(produto_id=2,quantidade=3),dict(quantidade=1)])},quantidade=1,largura=2,altura=2,desconto=0)
    data=entrada_cortina_item(item,'VAREJO')
    assert len(data.componentes)==1 and data.componentes[0].produto_id==2 and data.componentes[0].quantidade==3
