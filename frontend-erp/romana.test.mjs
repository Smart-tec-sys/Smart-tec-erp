import test from 'node:test'
import assert from 'node:assert/strict'

import { romanaKind, romanaKey } from './src/types/romana.ts'
import { productLineSubtotal, emptyProduct } from './src/types/budget.ts'

test('Somente Romana manual; motorizada bloqueável; demais modelos intactos', () => {
  assert.equal(romanaKind({ modelo_tecnico: 'ROMANA', nome: 'Romana branca' }), 'MANUAL')
  assert.equal(romanaKind({ modelo_tecnico: 'ROMANA', nome: 'Romana motorizada' }), 'MOTORIZADA')

  for (const m of ['ROMANA_TETO', 'ROLO', 'DOUBLE_VISION', 'PAINEL']) {
    assert.equal(romanaKind({ modelo_tecnico: m, nome: m }), null)
  }
})

test('Subtotal de Romana vem da resposta; nunca do cálculo genérico', () => {
  const item = {
    ...emptyProduct(1),
    romanaKind: 'MANUAL',
    modelTechnical: 'ROMANA',
    width: '9',
    height: '9',
    quantity: 9,
    price: 999,
  }

  assert.equal(productLineSubtotal(item), 0)

  assert.equal(
    productLineSubtotal({
      ...item,
      romana: {
        key: 'simulação',
        result: { subtotal: 134.16 },
      },
    }),
    134.16,
  )
})

test('Medidas, SKU, quantidade, desconto e perfil invalidam a chave; detalhes não', () => {
  const item = {
    ...emptyProduct(1),
    productId: 10,
  }

  const key = romanaKey(item, 'Varejo')

  for (const change of [
    { width: '1' },
    { height: '2' },
    { quantity: 2 },
    { discount: 1 },
    { productId: 11 },
  ]) {
    assert.notEqual(
      romanaKey({ ...item, ...change }, 'Varejo'),
      key,
    )
  }

  assert.notEqual(
    romanaKey(item, 'Decorador'),
    key,
  )

  assert.equal(
    romanaKey({ ...item, details: 'Sala' }, 'Varejo'),
    key,
  )
})
