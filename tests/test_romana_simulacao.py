"""Integração sem conexão real: fabricação, precificação e revalidação."""
import unittest
from dataclasses import asdict
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from pydantic import ValidationError

from app.services.romana_simulacao import RomanaSimulacaoInput, simular_romana, tipo_romana
from app.services.romana_calculo_producao import RomanaCalculoEntrada, calcular_distribuicao_fabricacao_romana
from app.services.orcamento_service import _fill
from app.schemas.orcamento import OrcamentoInput


def produto(**kw):
    data = dict(id=10, nome='Romana manual', modelo_tecnico='ROMANA', modelo='MANUAL', custo_final=27.95, valor_custo=10, valor_venda=99)
    return SimpleNamespace(**(data | kw))


def entrada(**kw):
    return RomanaSimulacaoInput(**(dict(produto_id=10, largura=1.2, altura=2, quantidade=1) | kw))


class RomanaSimulacaoTest(unittest.TestCase):
    def test_padrao_reutiliza_motor_e_retorna_fabricacao_integral(self):
        r = simular_romana(produto(), entrada())
        esperado = calcular_distribuicao_fabricacao_romana(RomanaCalculoEntrada(120, 200, 1))
        self.assertEqual(r['fabricacao_por_peca'], asdict(esperado))
        self.assertIsNone(r['custo_tecnico'])
        self.assertEqual(r['defaults_utilizados'], dict(tipo_corrente='SEM_FIM_PRONTA', tipo_comando='NORMAL'))
        self.assertEqual(r['area_total'], Decimal('2.4'))

    def test_multiplas_pecas_sem_inventar_bom_total(self):
        a, b = (simular_romana(produto(), entrada(quantidade=n)) for n in (1, 3))
        self.assertEqual(a['fabricacao_por_peca'], b['fabricacao_por_peca'])
        self.assertEqual(b['quantidade_pecas'], 3)
        self.assertEqual(b['area_total'], Decimal('7.2'))
        self.assertEqual(b['subtotal'], Decimal('402.48'))

    def test_invalidos(self):
        for kw in [dict(largura=0), dict(altura=-1), dict(altura=float('inf')), dict(quantidade=1.5), dict(quantidade=0), dict(quantidade=True)]:
            with self.subTest(kw=kw), self.assertRaises(ValidationError):
                entrada(**kw)
        with self.assertRaises(ValueError):
            simular_romana(produto(), entrada(largura=.001))

    def test_perfis_e_fallback_oficial(self):
        for perfil, esperado in [('DECORADOR', '41.93'), ('VAREJO', '55.90'), ('CONSUMIDOR_FINAL', '69.88')]:
            self.assertEqual(simular_romana(produto(), entrada(perfil_comercial=perfil))['preco_unitario'], Decimal(esperado))
        r = simular_romana(produto(custo_final=0, valor_custo=0, valor_venda=90), entrada())
        self.assertEqual(r['preco_unitario'], Decimal('90.00'))
        self.assertIsNone(r['custo_cadastrado'])
        self.assertTrue(r['alertas'])
        self.assertFalse(simular_romana(produto(custo_final=0, valor_custo=0, valor_venda=0), entrada())['preco_disponivel'])

    def test_modelos_fora_escopo_e_motor_bloqueado(self):
        for model in ['ROMANA MOTORIZADA', 'ROMANA_TETO', 'ROLO', 'DOUBLE_VISION', 'PAINEL']:
            p = produto(modelo_tecnico=model, nome=model, modelo='')
            with self.subTest(model=model), self.assertRaises(ValueError):
                simular_romana(p, entrada())
        self.assertIsNone(tipo_romana(produto(modelo_tecnico='ROMANA_TETO', nome='Romana de teto')))

    def test_sem_fallback_quando_motor_falha(self):
        with patch('app.services.romana_simulacao.calcular_distribuicao_fabricacao_romana', side_effect=ValueError('erro técnico')):
            with self.assertRaisesRegex(ValueError, 'erro técnico'):
                simular_romana(produto(), entrada())

    def preencher(self, p, **kw):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = p
        o = SimpleNamespace(itens=[])
        data = OrcamentoInput(cliente_id=1, perfil_comercial='VAREJO', itens=[dict(
            tipo_item='PRODUTO', produto_id=10, descricao='Romana', largura=1.2, altura=2,
            quantidade=2, area=999, preco_unitario=999, subtotal=999, modelo_tecnico='ROLO',
            observacao_item='Sala - comando à direita', cor='Branco') | kw])
        with patch('app.services.orcamento_service.OrcamentoItemDB', side_effect=lambda **v: SimpleNamespace(**v)):
            _fill(db, o, data, 1)
        db.commit.assert_not_called()
        return o

    def test_salvamento_recalcula_sem_area_ou_preco_do_cliente(self):
        o = self.preencher(produto())
        item = o.itens[0]
        self.assertEqual(item.area, Decimal('4.8'))
        self.assertEqual(item.subtotal, Decimal('268.32'))
        self.assertEqual(item.modelo_tecnico, 'ROMANA')
        self.assertEqual(item.observacao_item, 'Sala - comando à direita')
        self.assertEqual(item.cor, 'Branco')
        self.assertFalse(hasattr(item, 'fabricacao_por_peca'))

    def test_salvamento_nao_usa_generico_em_erro_ou_motorizacao(self):
        for p, kw in [(produto(), dict(largura=0)), (produto(nome='Romana motorizada'), {}), (produto(), dict(quantidade=1.5))]:
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                self.preencher(p, **kw)

    def test_endpoint_contrato_sem_escrita_e_isolamento(self):
        from fastapi import FastAPI
        # ASGI em memória, sem httpx nem socket/banco reais.
        import asyncio
        import json as jsonlib
        class TestClient:
            def __init__(self, app):
                self.app = app
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def post(self, path, json):
                async def request():
                    messages = []
                    async def receive():
                        return {'type': 'http.request', 'body': jsonlib.dumps(json).encode(), 'more_body': False}
                    async def send(message):
                        messages.append(message)
                    await self.app(dict(type='http', asgi={'version': '3.0'}, http_version='1.1', method='POST',
                        scheme='http', path=path, raw_path=path.encode(), query_string=b'', root_path='',
                        headers=[(b'content-type', b'application/json')], server=('test', 80), client=('test', 1)), receive, send)
                    status = next(m['status'] for m in messages if m['type'] == 'http.response.start')
                    body = b''.join(m.get('body', b'') for m in messages).decode()
                    return SimpleNamespace(status_code=status, text=body, json=lambda: jsonlib.loads(body))
                return asyncio.run(request())
        from app.routes.orcamento import router, get_db, get_current_tenant
        from app.tenant.context import TenantContext
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = produto()
        app = FastAPI()
        app.include_router(router, prefix='/orcamentos')
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_tenant] = lambda: TenantContext(empresa_id=1)
        with TestClient(app) as client:
            payload = entrada().dict()
            r = client.post('/orcamentos/simulacao-romana', json=payload)
            self.assertEqual(r.status_code, 200, r.text)
            self.assertIsNone(r.json()['custo_tecnico'])
            self.assertEqual(float(r.json()['preco_unitario']), 55.9)
            filtros = db.query.return_value.filter.call_args.args
            self.assertIn('empresa_id', str(filtros[1]))
            self.assertEqual(filtros[1].right.value, 1)
            self.assertEqual(client.post('/orcamentos/simulacao-romana', json=payload | {'quantidade': 1.5}).status_code, 422)
            db.query.return_value.filter.return_value.first.return_value = produto(nome='Romana motorizada')
            self.assertEqual(client.post('/orcamentos/simulacao-romana', json=payload).status_code, 422)
            db.query.return_value.filter.return_value.first.return_value = None
            self.assertEqual(client.post('/orcamentos/simulacao-romana', json=payload).status_code, 404)
        db.commit.assert_not_called()
        db.add.assert_not_called()
        db.execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
