const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { pathToFileURL } = require('node:url')
const { registerHooks } = require('node:module')
const compiled = new Map()
registerHooks({
  resolve(spec, context, next) {
    try { return next(spec, context) } catch (error) {
      if (spec.startsWith('.') && !path.extname(spec)) return next(spec + '.ts', context)
      throw error
    }
  },
  load(url, context, next) {
    if (compiled.has(url)) return { format: 'module', source: compiled.get(url), shortCircuit: true }
    return next(url, context)
  },
})
;(async () => {
  const { transformWithOxc } = await import('vite')
  const file = path.join(__dirname, '../src/components/BudgetProductRow.tsx')
  let source = fs.readFileSync(file, 'utf8')
    .replace("import { useEffect, useMemo, useState } from 'react'", `const useMemo = f => f(); const useEffect = f => { globalThis.__effects.push(f) }; const useState = initial => [globalThis.__query ?? initial, value => { globalThis.__query = value }]`)
    .replace(/import \{ ZeroNumberInput, zeroInputValue \} from '[^']+'/g, 'const ZeroNumberInput = () => null; const zeroInputValue = v => v')
    .replace(/import \{ (\w+Simulation) \} from '[^']+'/g, 'const $1 = () => null')
  compiled.set(pathToFileURL(file).href, (await transformWithOxc(source, file, { jsx: { runtime: 'automatic' } })).code)
  const { BudgetProductRow } = await import(pathToFileURL(file))
  const { emptyProduct } = await import(pathToFileURL(path.join(__dirname, '../src/types/budget.ts')))
  const base = { id: 99, nome: 'CORTINA DE TECIDO', modelo_tecnico: 'CORTINA', grupo_tecnico: 'TECIDOS_CORTINA', tipo_produto: 'Produto fabricado', valor_custo: 100, situacao: 'Ativo' }
  const lining = { ...base, id: 10, nome_fornecedor: 'AÇÃO DISTRIBUIDORA', nome: 'CORTINA FORRO TERGAL VERÃO BRANCO' }
  const component = { ...base, id: 2, nome: 'VARÃO AL P/ CORTINA', tipo_produto: 'Componente' }
  const wrongClass = { ...base, id: 1, modelo_tecnico: 'ROLO' }
  const catalog = [lining, component, wrongClass, { ...base, id: 3, situacao: 'Inativo' }, base,
    { id: 101, nome: 'WILER - COZUMEL - ARCA (01)', nome_fornecedor: 'Wiler', grupo_produto: 'TECIDOS_CORTINA' },
    { id: 102, nome: 'ROLÔ TESTE', modelo_tecnico: 'ROLO', valor_custo: 10 },
    { id: 103, nome: 'ROMANA TESTE', modelo_tecnico: 'ROMANA', valor_custo: 10 },
    { id: 104, nome: 'DOUBLE VISION TESTE', modelo_tecnico: 'DOUBLE_VISION', valor_custo: 10 },
    { id: 105, nome: 'JP ROLÔ TESTE', nome_fornecedor: 'JP PERSIANAS', modelo_tecnico: 'ROLO', valor_custo: 25 },
  ]
  let changed
  const render = (query, products = catalog, product = emptyProduct(1)) => {
    globalThis.__query = query; globalThis.__effects = []
    return BudgetProductRow({ product, catalog: products, commercialType: 'Varejo', onChange: value => { changed = value }, onRemove() {}, onCurtain() {}, onRomana() {}, onRomanaTeto() {}, onRolo() {}, onDoubleVision() {} })
  }
  const nodes = tree => !tree || typeof tree !== 'object' ? [] : Array.isArray(tree) ? tree.flatMap(nodes) : [tree, ...nodes(tree.props?.children)]
  const suggestions = tree => nodes(tree).filter(n => n.type === 'div' && n.props.className === 'product-suggestions').flatMap(n => nodes(n).filter(c => c.type === 'button'))
  for (const query of ['Cortina', 'Cortina de tecido', 'Cortina forro tergal verão']) {
    const results = suggestions(render(query))
    const baseResult = results.find(n => n.key === 'curtain-base') || results[0]
    assert.ok(baseResult)
    assert.ok(nodes(baseResult).find(n => n.type === 'strong').props.children.startsWith('Cortina de tecido'))
    baseResult.props.onClick()
    assert.equal(changed.productId, null); assert.equal(changed.product, 'Cortina de tecido')
    assert.equal(changed.groupTechnical, 'TECIDOS_CORTINA'); assert.equal(changed.modelTechnical, 'CORTINA')
    const chosen = changed
    render(undefined, catalog, chosen)
    globalThis.__effects.forEach(f => f())
    assert.equal(globalThis.__query, 'Cortina de tecido') // catalog name cannot undo the canonical display
    assert.equal(suggestions(render('Cortina de tecido', catalog, chosen)).length, 0)
  }
  const independentBase = { id: 999, nome: '  Cortina  de tecido ', tipo_produto: 'Produto fabricado', grupo_produto: 'CORTINAS', grupo_tecnico: null, modelo_tecnico: null }
  for (const query of ['cortina','cortina de tecido']) {
    const suggestion = suggestions(render(query,[independentBase,...catalog.filter(p=>p.id!==99)])).find(n=>n.key==='curtain-base')
    assert.ok(suggestion); suggestion.props.onClick()
    assert.equal(changed.productId,null);assert.equal(changed.product,'Cortina de tecido')
    assert.equal(changed.modelTechnical,'CORTINA');assert.equal(changed.groupTechnical,'TECIDOS_CORTINA')
  }
  const missing = render('Cortina', [lining, component, wrongClass])
  assert.ok(suggestions(missing).some(n => n.key === 'curtain-base' && !n.props.disabled))
  assert.ok(!nodes(missing).some(n => n.type === 'small' && String(n.props.children).includes('Produto-base não cadastrado')))
  assert.equal(suggestions(render('Wiler')).length, 1)
  assert.ok(suggestions(render('tergal')).length > 0)
  for (const [query, id] of [['rolô', 102], ['romana', 103], ['double vision', 104], ['JP rolô', 105]]) {
    const results = suggestions(render(query))
    assert.ok(results.some(n => String(n.key) === String(id)), query)
    results.find(n => String(n.key) === String(id)).props.onClick()
    assert.equal(changed.productId, id)
  }
  delete globalThis.__query; delete globalThis.__effects
  console.log('Produto-base: buscas Cortina, ID/classificação, nome estável, forros/componentes bloqueados, ausência segura e Rolô/Romana/DV aprovados.')
})().catch(error => { console.error(error); process.exitCode = 1 })
