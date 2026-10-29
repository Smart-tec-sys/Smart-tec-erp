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
  const file = path.join(__dirname, '../src/components/CurtainSimulation.tsx')
  // Only effects/network are stubbed; render and actual catalog predicates run unchanged.
  const source = fs.readFileSync(file, 'utf8')
    .replace("import { CurtainComponents } from './CurtainComponents'", 'const CurtainComponents = () => null')
    .replace("import { useEffect, useRef } from 'react'", 'const useEffect = () => {};const useRef=v=>({current:v})')
    .replace("import { simulateCurtain } from '../services/api'", 'const simulateCurtain = async () => { throw new Error("unexpected request") }')
  compiled.set(pathToFileURL(file).href, (await transformWithOxc(source, file, { jsx: { runtime: 'automatic' } })).code)
  const { CurtainSimulation } = await import(pathToFileURL(file))
  const { emptyProduct, productCost, productLineSubtotal } = await import(pathToFileURL(path.join(__dirname, '../src/types/budget.ts')))
  const catalog = [
    { id: 1, nome: 'VOIL LISO - BRANCO', linha: 'CORTINA' },
    { id: 2, nome: 'RATTAN - BEGE', nome_fornecedor: 'JP Persianas', grupo_tecnico: 'TECIDOS_CORTINA' },
    { id: 3, nome: 'WILER - COZUMEL - ALGEDI (01)', nome_fornecedor: 'Wiler', grupo_produto: 'TECIDOS_CORTINA', situacao: 'Ativo' },
    { id: 4, nome: 'WILER - COZUMEL - ALGEDI (02)', fornecedores: 'Wiler', grupo_produto: 'TECIDOS_CORTINA' },
    { id: 5, nome: 'WILER - JACQUARD - LISO-COR 138', nome_fornecedor: 'Wiler', grupo_produto: 'TECIDOS_CORTINA' },
    { id: 6, nome: 'WILER - JACQUARD - LISO-COR 23', nome_fornecedor: 'Wiler', grupo_produto: 'TECIDOS_CORTINA', cor: 'Cinza cadastrado' },
    { id: 7, nome: 'WILER – COZUMEL – AQUILA 01 AO 04', nome_fornecedor: 'Wiler', grupo_produto: 'TECIDOS_CORTINA' },
    { id: 8, nome: 'WILER - COZUMEL - CASTOR (01 AO 03)', nome_fornecedor: 'Wiler', grupo_produto: 'TECIDOS_CORTINA' },
    { id: 9, nome: 'WILER - COZUMEL - ARCA (01)', nome_fornecedor: 'Wiler', grupo_produto: 'TECIDOS_CORTINA' },
    { id: 10, nome: 'WILER - COZUMEL - ARCA 02', nome_fornecedor: 'Wiler', grupo_produto: 'TECIDOS_CORTINA' },
    ...['TRILHO', 'MOTOR', 'SUPORTE', 'COMANDO', 'RODIZIO', 'HOSPITALAR', 'VERTICAL', 'VERTICAIS', 'FITA', 'VARAO', 'PONTEIRA', 'CURVA', 'CORREIA', 'PERFIL', 'TAMPA', 'CLIP', 'FIO CONTINUO', 'MANIVELA', 'CORTINA WAVE', 'CORTINA MOTORIZADA', 'APMOTV'].map((name, i) => ({ id: 100 + i, nome: 'WILER - ' + name, nome_fornecedor: 'Wiler', grupo_produto: 'TECIDOS_CORTINA' })),
    { id: 200, nome: 'WILER - OUTRO COMPONENTE', nome_fornecedor: 'Wiler', grupo_produto: 'COMPONENTES' },
    { id: 201, nome: 'WILER - INATIVA - COR 01', nome_fornecedor: 'Wiler', grupo_produto: 'TECIDOS_CORTINA', situacao: 'Inativo' },
    { id: 202, nome: 'WILER - INATIVA - COR 02', nome_fornecedor: 'Wiler', grupo_produto: 'TECIDOS_CORTINA', ativo: false },
  ]
  const { fabricVariants, fabricState, getFabricColorLabel } = await import(pathToFileURL(path.join(__dirname, '../src/utils/curtainFabricCatalog.ts')))
  const colorSelect = (state, products = catalog) => ({ props: { children: [ { type: 'option', props: { value: '', children: '' } }, ...fabricVariants(products, state).map(p => ({ type: 'option', props: { value: p.id, children: getFabricColorLabel(p) } })) ], onChange: event => { const fabric = products.find(p => p.id === Number(event.target.value)); changed = fabricState(state, fabric) } } })
  const base = { ...emptyProduct(10), productId: 300, modelTechnical: 'CORTINA', groupTechnical: 'TECIDOS_CORTINA', width: '2', height: '3', price: 244 }
  let changed
  const render = (curtain, products = catalog) => CurtainSimulation({ product: { ...base, curtain }, catalog: products, profile: 'Varejo', onResult: (_, value) => { changed = value } })
  const nodes = tree => !tree || typeof tree !== 'object' ? [] : Array.isArray(tree) ? tree.flatMap(nodes) : [tree, ...nodes(tree.props?.children)]
  const selects = tree => nodes(tree).filter(node => node.type === 'select')
  const options = select => nodes(select.props.children).filter(node => node.type === 'option').map(node => [node.props.value, node.props.children])
  const suppliers = options(selects(render())[0]).map(option => option[1])
  for (const name of ['AÇÃO DISTRIBUIDORA', 'Wiler']) assert.ok(suppliers.includes(name), name)
  assert.ok(!suppliers.includes('JP PERSIANAS'))
  const state = { fornecedorTecido: 'Wiler', tecido: '', larguraTecido: 1.5, fator: 2.5 }
  const collections = options(selects(render(state))[1]).map(option => option[1])
  assert.deepEqual(collections.slice(1), ['COZUMEL', 'JACQUARD'])
  const names = options(selects(render({ ...state, colecaoTecido: 'COZUMEL' }))[2]).slice(1).map(([, name]) => name)
  assert.deepEqual(names, ['ALGEDI', 'AQUILA', 'ARCA', 'CASTOR'])
  const colors = colorSelect({ ...state, colecaoTecido: 'COZUMEL', tecidoNome: 'ALGEDI' })
  assert.deepEqual(options(colors).slice(1), [[3, '01'], [4, '02']])
  colors.props.onChange({ target: { value: '4' } })
  assert.equal(changed.tecidoProdutoId, 4)
  assert.equal(changed.fornecedorTecido, 'Wiler')
  assert.equal(changed.colecaoTecido, 'COZUMEL')
  assert.equal(changed.cor, '02')
  assert.equal(changed.result, undefined)
  const jacquard = options(colorSelect({ ...state, colecaoTecido: 'JACQUARD', tecidoNome: 'LISO' })).slice(1)
  assert.ok(jacquard.some(([id, color]) => id === 5 && color === '138'))
  assert.ok(jacquard.some(([id, color]) => id === 6 && color === 'Cinza cadastrado'))
  const colorOptions = (name) => options(colorSelect({ ...state, colecaoTecido: 'COZUMEL', tecidoNome: name })).slice(1)
  assert.deepEqual(colorOptions('AQUILA'), [[7, '01 AO 04']])
  assert.deepEqual(colorOptions('ARCA'), [[9, '01'], [10, '02']])
  assert.deepEqual(colorOptions('CASTOR'), [[8, '01 AO 03']])
  const selected = { ...state, colecaoTecido: 'COZUMEL', tecidoProdutoId: 9, tecidoNome: catalog.find(p => p.id === 9).nome, cor: '01', result: { subtotal: 244 } }
  assert.equal(selects(render(selected))[2].props.value, 'ARCA')
  selects(render(selected))[2].props.onChange({ target: { value: 'AQUILA' } })
  assert.equal(changed.tecidoNome, 'AQUILA'); assert.equal(changed.cor, ''); assert.equal(changed.tecidoProdutoId, undefined); assert.equal(changed.result, undefined)
  assert.deepEqual(options(colorSelect(changed)).slice(1), [[7, '01 AO 04']])
  selects(render(selected))[1].props.onChange({ target: { value: 'JACQUARD' } })
  assert.equal(changed.colecaoTecido, 'JACQUARD'); assert.equal(changed.tecidoNome, ''); assert.equal(changed.tecido, ''); assert.equal(changed.cor, '')
  selects(render(selected))[0].props.onChange({ target: { value: 'AÇÃO DISTRIBUIDORA' } })
  assert.equal(changed.fornecedorTecido, 'AÇÃO DISTRIBUIDORA'); assert.equal(changed.colecaoTecido, ''); assert.equal(changed.tecidoNome, ''); assert.equal(changed.cor, ''); assert.equal(changed.tecidoProdutoId, undefined)
  for (const [supplier, collection, color, id] of [['AÇÃO DISTRIBUIDORA', 'VOIL', 'BRANCO', 1]]) {
    const tree = render({ ...state, fornecedorTecido: supplier, colecaoTecido: collection, tecidoNome: 'VOIL LISO' })
    assert.deepEqual(options(selects(tree)[2]).slice(1), [['VOIL LISO', 'LISO']])
    const select = colorSelect({ ...state, fornecedorTecido: supplier, colecaoTecido: collection, tecidoNome: 'VOIL LISO' })
    assert.deepEqual(options(select).slice(1), [[id, color]])
    select.props.onChange({ target: { value: String(id) } })
    assert.equal(changed.tecidoProdutoId, id); assert.equal(changed.cor, color)
  }
  const historical = { grupo_produto: ' Tecidos ', grupo_tecnico: 'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL', tipo_cortina_persiana: ' tecido para cortina ', nome_fornecedor: 'AÇÃO DISTRIBUIDORA', situacao: 'Ativo', custo_final: 17.2 }
  const eligibleHistorical = [
    { ...historical, id: 1282, nome: 'GASE BORA BORA' },
    ...['MERLOT', 'NUDE', 'PRETO', 'TERRACOTA', 'TITANIO', 'TOMATO', 'TUSCANY', 'VERDE MINERAL'].map((color, i) => ({ ...historical, id: 3000 + i, nome: 'TECIDO VELUDO - ' + color + ' - 3,00M' })),
  ]
  const blockedHistorical = [
    { ...historical, id: 4000, nome: 'Produto marcado incorretamente', grupo_produto: 'Motorização' },
    { ...historical, id: 4001, nome: 'MOTOR PARA CORTINA' },
    { ...historical, id: 4002, nome: 'CORRENTE PARA CORTINA' },
    { ...historical, id: 4003, nome: 'TECIDO INATIVO', situacao: 'Inativo' },
    { ...historical, id: 4004, nome: 'TECIDO SEM TIPO DE CORTINA', tipo_cortina_persiana: 'TECIDO PARA PERSIANA' },
  ]
  const historicalProducts = [...eligibleHistorical, ...blockedHistorical]
  for (const fabric of eligibleHistorical) {
    const collection = fabric.id === 1282 ? 'GASE' : 'VELUDO'
    const fabricName = fabric.id === 1282 ? 'GASE BORA BORA' : 'VELUDO'
    const tree = render({ tecido: '', fornecedorTecido: 'AÇÃO DISTRIBUIDORA', colecaoTecido: collection, tecidoNome: fabricName }, historicalProducts)
    assert.ok(options(colorSelect({ tecido: '', fornecedorTecido: 'AÇÃO DISTRIBUIDORA', colecaoTecido: collection, tecidoNome: fabricName }, historicalProducts)).some(([id]) => id === fabric.id), fabric.nome)
  }
  const historicalCollections = options(selects(render({ tecido: '', fornecedorTecido: 'AÇÃO DISTRIBUIDORA' }, historicalProducts))[1]).slice(1).map(([, name]) => name)
  assert.deepEqual(historicalCollections, ['GASE', 'VELUDO'])
  assert.deepEqual(options(selects(render(undefined, blockedHistorical))[0]).slice(1), [])
  assert.equal(productCost(eligibleHistorical[0]), 17.2)
  console.log('Compatibilidade histórica: 14 casos aprovados (GASE + 8 veludos aceitos; Motorização, motor, corrente, inativo e tipo divergente bloqueados).')
  assert.equal(productCost({ custo_final: 12, valor_custo: 9, valor_venda: 5 }), 12)
  assert.equal(productCost({ custo_final: 0, valor_custo: 9, valor_venda: 5 }), 9)
  assert.equal(productCost({ custo_final: 0, valor_custo: 0, valor_venda: 5 }), 5)
  assert.equal(productLineSubtotal({ ...base, curtain: { ...state, result: { preco_disponivel: true, subtotal: 488, preco_unitario: 244 } } }), 488)
  assert.equal(productLineSubtotal({ ...base, curtain: { ...state, result: { preco_disponivel: true, subtotal: 700, preco_unitario: 350 } } }), 700)
  console.log('Catálogo: Ação/Wiler; JP excluído, coleções, variações, IDs, inativos, 21 exclusões técnicas, custo e subtotal aprovados.')
})().catch(error => { console.error(error); process.exitCode = 1 })
