const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { pathToFileURL } = require('node:url')
const { registerHooks } = require('node:module')
const compiled = new Map()
registerHooks({
  resolve(spec, context, next) {
    try { return next(spec, context) } catch (error) {
      if (spec.startsWith('.') && !path.extname(spec)) {
        for (const extension of ['.ts', '.tsx']) {
          try { return next(spec + extension, context) } catch {}
        }
      }
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
  const source = fs.readFileSync(file, 'utf8')
    .replace("import { CurtainColorField } from './CurtainColorField'", 'const CurtainColorField = () => null')
    .replace("import { useEffect, useMemo, useState } from 'react'", `const useMemo = f => f(); const useEffect = () => {}; const useState = initial => [globalThis.__query ?? initial, value => { globalThis.__query = value }]`)
    .replace(/import \{ ZeroNumberInput, zeroInputValue \} from '[^']+'/g, 'const ZeroNumberInput = () => null; const zeroInputValue = v => v')
    .replace(/import \{ (\w+Simulation) \} from '[^']+'/g, 'const $1 = () => null')
  compiled.set(pathToFileURL(file).href, (await transformWithOxc(source, file, { jsx: { runtime: 'automatic' } })).code)
  const { BudgetProductRow } = await import(pathToFileURL(file))
  const { emptyProduct, commercialPrice } = await import(pathToFileURL(path.join(__dirname, '../src/types/budget.ts')))
  const { productSuggestionTier, rankProductSuggestions } = await import(pathToFileURL(path.join(__dirname, '../src/utils/productSuggestionRank.ts')))

  // Reproduz a forma do catálogo oficial: acabados Rolô com IDs baixos, tecidos/componentes com IDs altos.
  const rolo = (id, nome, extra = {}) => ({ id, nome, grupo_produto: 'ROLÔ', grupo_tecnico: 'PERSIANA_ROLO', modelo_tecnico: 'ROLO', tipo_produto: 'Produto fabricado', unidade_venda: 'M²', valor_custo: 100, situacao: 'Ativo', status_comercial: 'ATIVO', ...extra })
  const finished = [
    rolo(7, 'ROLO SCREEN 3% IMPORTADO', { grupo_produto: 'PERSIANAS' }),
    rolo(10, 'ROLO SCREEN 1%', { grupo_produto: 'PERSIANAS' }),
    rolo(81, 'ROLO SCREEN 1%', { grupo_produto: 'PERSIANAS' }),
    rolo(82, 'ROLO SCREEN 1% IMPORTADO - CÓPIA', { grupo_produto: 'PERSIANAS' }),
    rolo(84, 'ROLO SCREEN 3% IMPORTADO', { grupo_produto: 'PERSIANAS' }),
    rolo(85, 'ROLO SCREEN 1%', { grupo_produto: 'PERSIANAS' }),
    rolo(1267, 'ROLO TRANSLÚCIDA LUGANO (CREME)'),
    rolo(1290, 'ROLÔ BK.BRISK 32MM BEGE', { familia_tecnica: 'ROLO_BK_BRISK_32MM' }),
    rolo(3477, 'ROLÒ SCREEN 0,8%', { grupo_produto: 'PERSIANAS', grupo_tecnico: null, modelo_tecnico: null, tipo_produto: null, status_comercial: 'Ativo' }),
    rolo(3530, 'ROLÔ BK NAPOLES', { familia_tecnica: 'ROLO_BK_NAPOLES' }),
    rolo(3531, 'ROLÔ BK.DENVER', { familia_tecnica: 'ROLO_BK_DENVER' }),
  ]
  const fabrics = []
  for (let i = 0; i < 20; i += 1) {
    for (const [offset, cor] of [[0, 'CINZA'], [1, 'BEGE'], [2, 'BRANCO']]) {
      fabrics.push({ id: 2000 + i * 3 + offset, nome: `SCREEN 1% ECO IMPORTADA ${i} - ${cor} - 2,50M`, cor, grupo_produto: 'Tecidos', grupo_tecnico: 'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL', tipo_produto: 'Componente', unidade_venda: 'M²', valor_custo: 40 + i, situacao: 'Ativo', status_comercial: 'ATIVO' })
    }
  }
  const components = Array.from({ length: 20 }, (_, i) => ({ id: 2500 + i, nome: `TAMPA DO BANDÔ ${i}`, grupo_produto: 'Componentes', grupo_tecnico: 'COMPONENTES_PERSIANAS_ROLO', tipo_produto: 'Componente', unidade_venda: 'UN', valor_custo: 5, situacao: 'Ativo', status_comercial: 'ATIVO' }))
  const fabricsPersiana = Array.from({ length: 15 }, (_, i) => ({ id: 2800 + i, nome: `TECIDO PERSIANA ROLO PADRAO ${i}`, grupo_produto: 'Tecidos', grupo_tecnico: 'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL', tipo_produto: 'Componente', unidade_venda: 'M²', valor_custo: 30, situacao: 'Ativo', status_comercial: 'ATIVO' }))
  const inactive = rolo(8, 'ROLO SCREEN 5% IMPORTADO', { situacao: 'Inativo', status_comercial: 'INATIVO' })
  const catalog = [...finished, ...fabrics, ...components, ...fabricsPersiana, inactive].sort((a, b) => b.id - a.id)

  let changed
  const render = (query, product = emptyProduct(1)) => {
    globalThis.__query = query
    return BudgetProductRow({ product, catalog, commercialType: 'Varejo', onChange: value => { changed = value }, onRemove() {}, onCurtain() {}, onRomana() {}, onRomanaTeto() {}, onRolo() {}, onDoubleVision() {} })
  }
  const nodes = tree => !tree || typeof tree !== 'object' ? [] : Array.isArray(tree) ? tree.flatMap(nodes) : [tree, ...nodes(tree.props?.children)]
  const suggestions = query => nodes(render(query)).filter(n => n.type === 'div' && n.props.className === 'product-suggestions').flatMap(n => nodes(n).filter(c => c.type === 'button'))
  const ids = query => suggestions(query).map(n => Number(n.key))
  const finishedIds = finished.map(p => p.id)

  // "rolô screen": os 7 acabados Rolô Screen vêm antes dos tecidos screen.
  const screen = ids('rolô screen')
  assert.equal(screen.length, 12)
  assert.deepEqual(screen.slice(0, 7), [3477, 85, 84, 82, 81, 10, 7])
  assert.ok(screen.slice(7).every(id => id >= 2000), 'tecidos continuam disponíveis depois dos acabados')
  assert.ok(!screen.includes(8), 'inativo continua oculto')

  // "rolo" e "persiana rolô": todos os acabados aparecem primeiro, na ordem original do catálogo.
  for (const query of ['rolo', 'Rolô', 'persiana rolô', 'PERSIANA ROLO']) {
    const result = ids(query)
    assert.equal(result.length, 12, query)
    assert.deepEqual(result.slice(0, finished.length), [...finishedIds].sort((a, b) => b - a), query)
  }
  // "persiana rolô": nome casa com todos os termos vem antes de produto encontrado só por grupo.
  assert.ok(ids('persiana rolô').slice(finished.length).every(id => id >= 2800), 'tecido com o nome completo antes de componentes')

  // Busca específica de tecido mantém o tecido no topo e o agrupamento por cor.
  const eco = ids('screen eco importada 3')
  assert.ok(eco.includes(2011))
  assert.ok(!eco.includes(2009) && !eco.includes(2010), 'variações de cor continuam agrupadas em uma sugestão')
  assert.ok(eco.every(id => id >= 2000 && id < 2100), 'busca de tecido não traz acabados')
  assert.ok(ids('tampa bando').every(id => id >= 2500 && id < 2600))

  // Seleção preserva unidade, preço e cálculo técnico.
  suggestions('rolô screen')[0].props.onClick()
  assert.equal(changed.productId, 3477); assert.equal(changed.roloKind, 'MANUAL'); assert.equal(changed.price, 0); assert.equal(changed.unit, 'M²')
  suggestions('screen eco importada 3').find(n => Number(n.key) === 2011).props.onClick()
  const fabric = catalog.find(p => p.id === 2011)
  assert.equal(changed.productId, 2011); assert.equal(changed.roloKind, null); assert.equal(changed.color, 'BRANCO')
  assert.equal(changed.price, commercialPrice(fabric, 'Varejo')); assert.equal(changed.suggestedPrice, commercialPrice(fabric, 'Varejo'))

  // Função pura: faixas e estabilidade.
  const byId = Object.fromEntries(catalog.map(p => [p.id, p]))
  assert.equal(productSuggestionTier(byId[3477], 'rolô screen', true), 0)
  assert.equal(productSuggestionTier(byId[3531], 'persiana rolô', true), 1)
  assert.equal(productSuggestionTier(byId[2800], 'persiana rolô', false), 2)
  assert.equal(productSuggestionTier(byId[2500], 'rolo', false), 3)
  assert.equal(productSuggestionTier(byId[3531], 'denver cinza', true), 3, 'termo fora do nome e da classificação não promove')
  const sample = [byId[2500], byId[2000], byId[3531], byId[3530]]
  assert.deepEqual(rankProductSuggestions(sample, 'rolo', p => p.id > 3000).map(p => p.id), [3531, 3530, 2500, 2000])
  assert.equal(rankProductSuggestions(sample, '   ', () => true), sample)

  console.log('productSuggestionRank: ok')
})().catch(error => { console.error(error); process.exit(1) })
