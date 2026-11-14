/* Regressões isoladas do catálogo de coleções; dados fictícios, sem acesso a APIs ou bancos. */
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const ts = require('/tmp/smarttec-test-ts/node_modules/typescript')

function loadTS(relativePath, dependencies = {}) {
  const original = fs.readFileSync(path.join(__dirname, '..', relativePath), 'utf8')
  const transpiled = ts.transpileModule(original, {
    compilerOptions: { module: 1, target: 9 }
  }).outputText
  const mod = { exports: {} }
  const requireLocal = (id) => {
    if (Object.prototype.hasOwnProperty.call(dependencies, id)) return dependencies[id]
    throw Error('Dependência não declarada: ' + id + ' em ' + relativePath)
  }
  new Function('require', 'module', 'exports', transpiled)(requireLocal, mod, mod.exports)
  return mod.exports
}

const budget = loadTS('src/types/budget.ts', {
  './romana': { romanaKey: () => '' },
  './romana_teto': { romanaTetoKey: () => '' },
  './rolo': { roloKey: () => '' },
  './double_vision': { doubleVisionKey: () => '' }
})
const fabric = loadTS('src/utils/fabricDisplay.ts', { '../types/budget': budget })
const rolo = loadTS('src/types/rolo.ts')
const rank = loadTS('src/utils/productSuggestionRank.ts', {
  '../types/budget': budget,
  './fabricDisplay': fabric
})

let checks = 0
function check(name, fn) {
  try { fn(); checks++; console.log('PASS', name) }
  catch (error) { console.error('FAIL', name); throw error }
}
function cloth(id, color, overrides = {}) {
  return {
    id, nome: 'TECIDO BK NÁPOLES - ' + color,
    grupo_tecnico: 'TECIDOS_ROLO_ROMANA_PAINEL',
    produto_base: 'BK NÁPOLES',
    familia_tecnica: 'ROLO_BK_NAPOLES',
    modelo_tecnico: 'BLACKOUT',
    cor: color, unidade_venda: 'ML', largura: 2.8,
    nome_fornecedor: 'FORNECEDOR A', valor_venda: id * 10,
    ...overrides
  }
}
const white = cloth(101, 'BRANCO')
const grey = cloth(102, 'CINZA')
const beige = cloth(103, 'BEGE')
check('classifica tecido pelo grupo técnico composto', () =>
  assert.equal(fabric.isFabricProduct(white), true))
check('nome visível remove somente a cor', () =>
  assert.equal(fabric.fabricDisplay(white).name, 'TECIDO BK NÁPOLES'))
check('duas cores de Nápoles são uma coleção', () => {
  const groups = fabric.groupFabricCollections([white, grey])
  assert.equal(groups.length, 1)
  assert.equal(groups[0].variants.length, 2)
  assert.equal(groups[0].colors.length, 2)
})
check('preserva SKU distinto na mesma cor', () => {
  const groups = fabric.groupFabricCollections([white, grey, cloth(104, 'BRANCO')])
  assert.equal(groups.length, 1)
  assert.equal(groups[0].variants.length, 3)
  assert.equal(groups[0].colors.find(c => c.color === 'BRANCO').variants.length, 2)
})
check('não mistura fornecedor diferente', () =>
  assert.equal(fabric.groupFabricCollections([white, cloth(105, 'CINZA', { nome_fornecedor: 'FORNECEDOR B' })]).length, 2))
check('não mistura BK Brisk com Nápoles', () =>
  assert.equal(fabric.groupFabricCollections([white, cloth(106, 'BRANCO', { nome: 'TECIDO BK BRISK - BRANCO', produto_base: 'BK BRISK', familia_tecnica: 'ROLO_BK_BRISK' })]).length, 2))
check('não mistura larguras de fornecimento', () =>
  assert.equal(fabric.groupFabricCollections([white, cloth(107, 'CINZA', { largura: 3 })]).length, 2))
check('não mistura tecido de empresa diferente', () =>
  assert.equal(fabric.groupFabricCollections([white, cloth(108, 'CINZA', { empresa_id: 2 })]).length, 2))
check('registro sem cor e sem coleção fica individual', () => {
  const first = cloth(200, '', { nome: 'TECIDO INDEFINIDO', cor: '', produto_base: '' })
  const second = cloth(201, '', { nome: 'TECIDO INDEFINIDO', cor: '', produto_base: '' })
  assert.equal(fabric.groupFabricCollections([first, second]).length, 2)
})
check('tecido não vira persiana rolô acabada', () =>
  assert.equal(rolo.roloKind(cloth(202, 'BRANCO', { nome: 'TECIDO BLACKOUT ROLÔ - BRANCO' })), null))
check('produto rolô acabado permanece produto acabado', () => {
  const p = { id: 300, nome: 'PERSIANA ROLO BLACKOUT MOTORIZADA', grupo_tecnico: 'PERSIANA_ROLO', modelo_tecnico: 'ROLO_MOTORIZADA' }
  assert.equal(fabric.isFabricProduct(p), false)
  assert.equal(rolo.roloKind(p), 'MOTORIZADA')
})
check('MOTOR é motorizado', () =>
  assert.equal(rolo.normalizeRoloDrive('MOTOR'), 'motorizado'))
check('manual segue manual', () =>
  assert.equal(rolo.normalizeRoloDrive('manual'), 'manual'))
check('chave de simulação distingue cor de tecido', () => {
  const a = { width: '2.8', height: '2.5', quantity: 1, discount: 0,
    color: 'BRANCO', curtain: { tecido: 'VOIL', cor: 'BRANCO', tecidoProdutoId: 101 } }
  const b = { ...a, color: 'CINZA', curtain: { ...a.curtain, cor: 'CINZA' } }
  assert.notEqual(budget.curtainKey(a, 'Varejo'), budget.curtainKey(b, 'Varejo'))
})
check('ordenação não esconde produto acabado', () => {
  const finished = { id: 450, nome: 'PERSIANA ROLO BK NÁPOLES',
    grupo_tecnico: 'PERSIANA_ROLO', modelo_tecnico: 'ROLO_MANUAL' }
  const order = rank.rankProductSuggestions([white, finished], 'ROLO BK NÁPOLES', p => Boolean(rolo.roloKind(p)))
  assert.equal(order[0].id, 450)
})
console.log('RESULTADO:', checks, 'testes aprovados.')
