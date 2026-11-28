const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { createRequire, registerHooks } = require('node:module')
const { pathToFileURL } = require('node:url')

const root = path.resolve(__dirname, '..')
const sourceRoot = process.env.SMARTTEC_TEST_SOURCE_ROOT || root
const libraryRoot = process.env.SMARTTEC_TEST_VITE_ROOT || sourceRoot
const dependencyRequire = createRequire(path.join(libraryRoot, 'package.json'))
const compiled = new Map()
registerHooks({
  resolve(spec, context, next) {
    if (compiled.has(spec)) return { url: spec, shortCircuit: true }
    if (spec.endsWith('.css') && context.parentURL) return { url: new URL(spec, context.parentURL).href, shortCircuit: true }
    try { return next(spec, context) } catch (error) {
      if (spec.startsWith('.') && !path.extname(spec)) {
        for (const ext of ['.ts', '.tsx']) { try { return next(spec + ext, context) } catch {} }
      }
      if (!spec.startsWith('.') && !spec.startsWith('file:') && !spec.startsWith('node:')) {
        return { url: pathToFileURL(dependencyRequire.resolve(spec)).href, shortCircuit: true }
      }
      throw error
    }
  },
  load(url, context, next) {
    if (url.endsWith('.css')) return { format: 'module', source: '', shortCircuit: true }
    if (compiled.has(url)) return { format: 'module', source: compiled.get(url), shortCircuit: true }
    if (url.startsWith('file:') && /\.tsx?$/.test(url)) {
      const result = next(url, context)
      const source = String(result.source)
      return {
        ...result,
        source: source.replaceAll(
          'import.meta.env',
          '({ VITE_AUTH_MODE: "dev", DEV: true, PROD: false, MODE: "test" })'
        )
      }
    }
    return next(url, context)
  },
})

;(async () => {
  const { transformWithOxc } = await import(pathToFileURL(path.join(libraryRoot, 'node_modules/vite/dist/node/index.js')))
  const pdfDocument = path.join(sourceRoot, 'src/components/budgetPdf/BudgetPdfDocument.tsx')
  compiled.set(
    pathToFileURL(pdfDocument).href,
    (await transformWithOxc(
      fs.readFileSync(pdfDocument, 'utf8'),
      pdfDocument,
      { jsx: { runtime: 'automatic' } }
    )).code
  )

  const authFile = path.join(sourceRoot, 'src/services/auth.ts')
  const authSource = fs.readFileSync(authFile, 'utf8')
    .replaceAll('import.meta.env',
      '({ VITE_AUTH_MODE: "dev", DEV: true, PROD: false, MODE: "test" })')

  compiled.set(
    pathToFileURL(authFile).href,
    (await transformWithOxc(authSource, authFile)).code
  )

  const testEnv = JSON.stringify({
    VITE_AUTH_MODE: 'dev',
    VITE_API_URL: 'http://127.0.0.1:1',
    DEV: true,
    PROD: false,
    MODE: 'test',
    BASE_URL: '/'
  })

  globalThis.fetch = async () => {
    throw new Error('HTTP externo bloqueado neste teste')
  }

  async function prepareModules(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const filename = path.join(directory, entry.name)

      if (entry.isDirectory()) {
        await prepareModules(filename)
        continue
      }

      if (!/\.tsx?$/.test(filename) || filename.endsWith('.d.ts')) continue

      const moduleUrl = pathToFileURL(filename).href

      if (compiled.has(moduleUrl)) continue

      const source = fs.readFileSync(filename, 'utf8')
        .replaceAll('import.meta.env', '(' + testEnv + ')')

      const result = await transformWithOxc(
        source,
        filename,
        { jsx: { runtime: 'automatic' } }
      )

      compiled.set(moduleUrl, result.code)
    }
  }

  await prepareModules(path.join(sourceRoot, 'src'))
  const apiModuleUrl = pathToFileURL(
    path.join(sourceRoot, 'src/services/api.ts')
  ).href

  assert.ok(compiled.has(apiModuleUrl), 'API nao compilada')
  assert.ok(
    !compiled.get(apiModuleUrl).includes('import.meta.env'),
    'Variaveis Vite nao substituidas'
  )

  console.log('MODULOS PREPARADOS:', compiled.size)
  console.log('API VALIDADA NO EXECUTOR')


  const { renderToStaticMarkup } = dependencyRequire('react-dom/server')
  let cells = [], index = 0, effects = [], cleanups = [], dirty = false
  const hooks = global.__salesRecoveryHooks = {
    useState(initial) { const n = index++; if (!(n in cells)) cells[n] = typeof initial === 'function' ? initial() : initial; return [cells[n], value => { cells[n] = typeof value === 'function' ? value(cells[n]) : value; dirty = true }] },
    useRef(initial) { const n = index++; return cells[n] ?? (cells[n] = { current: initial }) },
    useMemo: fn => fn(),
    useCallback: fn => fn,
    useEffect(fn, deps) { const n = index++; if (!cells[n] || deps.some((v, i) => v !== cells[n][i])) { cells[n] = deps; effects.push(fn) } },
  }
  const nodes = tree => tree == null || typeof tree !== 'object' ? [] : Array.isArray(tree) ? tree.flatMap(nodes) : [tree, ...nodes(tree.props?.children)]
  const text = tree => tree == null ? '' : typeof tree === 'string' || typeof tree === 'number' ? String(tree) : Array.isArray(tree) ? tree.map(text).join('') : text(tree.props?.children)
  let component, props, tree
  function render() { index = 0; dirty = false; tree = component(props); return tree }
  async function settle() {
    for (let round = 0; round < 8; round++) {
      render(); effects.splice(0).forEach(fn => { const cleanup = fn(); if (cleanup) cleanups.push(cleanup) })
      await new Promise(setImmediate)
      if (!dirty && !effects.length) break
    }
    return render()
  }
  async function mount(next, nextProps) {
    cleanups.splice(0).forEach(fn => fn()); cells = []; effects = []; component = next; props = nextProps
    return settle()
  }
  const originalConsoleWarn = console.warn
  const warnings = []
  console.warn = (...args) => warnings.push(args)
  global.document = { activeElement: { focus() {} }, body: {} }
  global.window = { confirm: () => true }

  const item = { id: 11, tipo_item: 'PRODUTO', produto_id: 10, descricao: 'Cortina Linho', codigo_interno: 'C-10', grupo_tecnico: 'CORTINAS', modelo_tecnico: 'CORTINA', unidade: 'UN', quantidade: 1, largura: 2.5, altura: 2.2, area: 5.5, preco_unitario: 100, desconto: 0, subtotal: 100, ambiente: 'Sala', material: 'Linho', cor: 'Areia', acionamento: 'Manual', lado_comando: 'DIREITA', observacao_item: 'Conferir barra', dados_tecnicos: { cortina: { tecido: 'Linho', modeloPrega: 'WAVE', fator: 2.5 } } }
  const orders = ['ABERTO', 'ABERTO', 'FATURADO', 'CONCLUIDO', 'CANCELADO', 'ABERTO'].map((status, n) => ({
    id: n + 1, numero: `VEN-${n + 1}`, cliente_id: 1, cliente_nome: 'Cliente Teste', orcamento_id: 100 + n, orcamento_numero: String(1000 + n), parceiro_id: null, representante_id: null, vendedor_id: null,
    status, perfil_comercial: 'VAREJO', data_venda: '2026-11-13', prazo_entrega: '2026-11-30', canal_venda: 'LOCAL', total: (n + 1) * 100, desconto: 0, total_final: (n + 1) * 100,
    observacao: 'Proposta salva', observacao_interna: 'Apenas equipe', itens: [{ ...item, id: 11 + n, preco_unitario: (n + 1) * 100, subtotal: (n + 1) * 100 }],
  }))
  const frozen = JSON.stringify(orders)
  let clientsFail = false, ordersFail = false, orderFail = '', patchFail = false
  const apiCalls = [], patches = [], opened = [], saved = []
  global.__salesRecoveryApi = {
    getOrders: async () => { apiCalls.push(['orders']); if (ordersFail) throw new Error('API 500: pedidos indisponíveis'); return structuredClone(orders) },
    getClients: async () => { apiCalls.push(['clients']); if (clientsFail) throw new TypeError('Failed to fetch'); return [{ id: 1, nome: 'Cliente Teste' }] },
    getFuncionariosCadastro: async () => [], getCommercialPartners: async () => [], getRepresentatives: async () => [],
    getOrder: async id => { apiCalls.push(['order', id]); if (orderFail) throw new Error(orderFail); return structuredClone(orders.find(order => order.id === id)) },
    updateOrder: async (id, payload) => { patches.push({ id, payload: structuredClone(payload) }); if (patchFail) throw new Error('API 422: alteração recusada'); return { ...structuredClone(orders.find(order => order.id === id)), ...payload } },
    deleteOrder: async () => { throw new Error('Exclusão não faz parte deste ensaio') },
    createOrderReceivable: async () => { throw new Error('Financeiro não faz parte deste ensaio') },
  }
  async function compile(relative, rewrite, candidate = false) {
    const filename = path.join(candidate ? root : sourceRoot, 'src', relative)
    const moduleUrl = pathToFileURL(filename).href
    let source = rewrite(fs.readFileSync(filename, 'utf8'))
    compiled.set(moduleUrl, (await transformWithOxc(source, filename, { jsx: { runtime: 'automatic' } })).code)
    return import(moduleUrl)
  }
  // These support modules contain presentation/helpers only; the three pages/dialog remain real.
  for (const relative of ['utils/commercialDisplay.ts', 'types/budget.ts', 'types/romana.ts', 'types/romana_teto.ts', 'types/rolo.ts', 'types/double_vision.ts']) {
    const filename = path.join(sourceRoot, 'src', relative)
    if (fs.existsSync(filename)) compiled.set(pathToFileURL(filename).href, (await transformWithOxc(fs.readFileSync(filename, 'utf8'), filename)).code)
  }
  const helperUrl = relative => JSON.stringify(pathToFileURL(path.join(sourceRoot, 'src', relative)).href)
  const supportImports = source => source
    .replace("'../utils/commercialDisplay'", helperUrl('utils/commercialDisplay.ts'))
    .replaceAll("'../types/budget'", helperUrl('types/budget.ts'))
  const { SalesPage } = await compile('pages/SalesPage.tsx', source => supportImports(source)
    .replace("import { useCallback, useEffect, useMemo, useState } from 'react'", 'const {useCallback,useEffect,useMemo,useState}=globalThis.__salesRecoveryHooks')
    .replace(/import \{\s*deleteOrder,[\s\S]*?\} from '..\/services\/api'/, 'const {deleteOrder,updateOrder,getClients,getOrders,getCommercialPartners,getRepresentatives,createOrderReceivable}=globalThis.__salesRecoveryApi')
    .replace("import { ColumnManager } from '../components/ColumnManager'", 'const ColumnManager=({children})=>children')
    .replace("import { SaleEditDialog } from '../components/SaleEditDialog'", 'function SaleEditDialog(){return null}')
    .replace("import { SaleProductionDialog } from '../components/SaleProductionDialog'", 'function SaleProductionDialog(){return null}')
    .replace(/import\s+\{\s*SaleShareDialog\s*\}\s+from\s+['"]\.\.\/components\/SaleShareDialog['"]/, 'function SaleShareDialog(){return null}')
    .replace("import { saleProductionReason } from '../services/saleProduction'", 'const saleProductionReason=()=>globalThis.__salesRecoveryProductionEnabled?undefined:"flag desligada"')
    .replace("import { RowActionsMenu } from '../components/RowActionsMenu'", 'function RowActionsMenu(){return null}'), true)
  await mount(SalesPage, { onOpenSale: id => opened.push(id), onNewSale() {} })
  let cards = nodes(tree).filter(n => n.props?.className === 'budget-kpi dark')
  assert.deepEqual(cards.map(card => text(nodes(card).find(n => n.type === 'strong'))), ['6', '3', 'R$\u00a0900,00', 'R$\u00a02.100,00'])
  assert.equal(nodes(tree).filter(n => n.type === 'tr').length, 7, 'seis pedidos e cabeçalho')
  assert.match(renderToStaticMarkup(tree), /CLIENTE TESTE/)
  nodes(tree).find(n => n.type === 'button' && n.props['aria-label'] === 'Abrir venda VEN-1').props.onClick()
  assert.deepEqual(opened, [1])
  let menu = nodes(tree).find(n => n.type?.name === 'RowActionsMenu')
  assert.equal(menu.props.onPrepareFiscal, undefined, 'Fiscal V1 fora da publicacao comercial')
  assert.equal(menu.props.onGenerateProduction, undefined, 'flag desabilitada bloqueia Produção')
  global.__salesRecoveryProductionEnabled = true; render()
  menu = nodes(tree).find(n => n.type?.name === 'RowActionsMenu')
  assert.equal(menu.props.onGenerateProduction, undefined)
  orders[0].status = 'APROVADO'
  await mount(SalesPage, { onOpenSale: id => opened.push(id), onNewSale() {} })
  menu = nodes(tree).find(n => n.type?.name === 'RowActionsMenu')
  menu.props.onGenerateProduction(); render()
  const productionDialog = nodes(tree).find(n => n.type?.name === 'SaleProductionDialog')
  assert.equal(productionDialog.props.saleId, 1, 'menu abre a produção da venda selecionada')
  productionDialog.props.onClose(); render()
  global.__salesRecoveryProductionEnabled = false
  orders[0].status = 'ABERTO'
  await mount(SalesPage, { onOpenSale: id => opened.push(id), onNewSale() {} })
  menu = nodes(tree).find(n => n.type?.name === 'RowActionsMenu')

  menu.props.onEdit(); render()
  assert.equal(nodes(tree).find(n => n.type?.name === 'SaleEditDialog').props.order.id, 1)
  nodes(tree).find(n => n.type?.name === 'SaleEditDialog').props.onSaved({ ...orders[0], status: 'CONCLUIDO' }); render()
  cards = nodes(tree).filter(n => n.props?.className === 'budget-kpi dark')
  assert.equal(text(nodes(cards[1]).find(n => n.type === 'strong')), '2', 'KPIs atualizam após edição')

  clientsFail = true
  await mount(SalesPage, { onOpenSale() {}, onNewSale() {} })
  assert.equal(nodes(tree).filter(n => n.type === 'tr').length, 7, 'falha de clientes não esconde pedidos')
  cards = nodes(tree).filter(n => n.props?.className === 'budget-kpi dark')
  assert.equal(text(nodes(cards[0]).find(n => n.type === 'strong')), '6')
  assert.match(renderToStaticMarkup(tree), /CLIENTE #1/)
  assert.ok(warnings.length, 'falha auxiliar fica registrada')
  ordersFail = true
  await mount(SalesPage, { onOpenSale() {}, onNewSale() {} })
  assert.match(text(tree), /API 500: pedidos indisponíveis/)
  ordersFail = false; clientsFail = false

  const { SaleDetailPage } = await compile('pages/SaleDetailPage.tsx', source => supportImports(source)
    .replace("import { useEffect, useState, type ReactNode } from 'react'", 'const {useEffect,useState}=globalThis.__salesRecoveryHooks;type ReactNode=any')
    .replace(/import \{\s*getOrder,[\s\S]*?\} from '..\/services\/api'/, 'const {getOrder,getClients,getFuncionariosCadastro,getCommercialPartners,getRepresentatives}=globalThis.__salesRecoveryApi')
    .replace("import { ProducaoPanel } from '../components/ProducaoPanel'", 'function ProducaoPanel(){return null}')
    .replace("import { saleProductionEnabled, saleProductionReason } from '../services/saleProduction'", 'const saleProductionEnabled=false;const saleProductionReason=()=>undefined')
    .replace("import { downloadDirectSalePdf } from '../services/salePdf'", 'const downloadDirectSalePdf=async()=>{}'))
  await mount(SaleDetailPage, { saleId: 1, onBack() {} })
  let markup = renderToStaticMarkup(tree)
  for (const expected of ['VEN-1', 'Cliente Teste', '#1000', 'Cortina Linho', '2,5', '2,2', '100,00', 'Em aberto', 'Sala', 'Linho', 'Areia', 'Manual', 'Conferir barra']) assert.ok(markup.includes(expected), expected)
  assert.ok(apiCalls.some(call => call[0] === 'order' && call[1] === 1))
  clientsFail = true
  await mount(SaleDetailPage, { saleId: 1, onBack() {} })
  assert.match(renderToStaticMarkup(tree), /Cliente #1/)
  orderFail = 'API 404: não encontrado'
  await mount(SaleDetailPage, { saleId: 999, onBack() {} })
  assert.match(text(tree), /Venda não encontrada/)
  orderFail = ''; clientsFail = false

  const { SaleEditDialog } = await compile('components/SaleEditDialog.tsx', source => supportImports(source)
    .replace("import { useEffect, useRef, useState } from 'react'", 'const {useEffect,useRef,useState}=globalThis.__salesRecoveryHooks')
    .replace("import { createPortal } from 'react-dom'", 'const createPortal=element=>element')
    .replace(/import \{ getOrder,.*\} from '..\/services\/api'/, 'const {getOrder,getClients,getFuncionariosCadastro,getCommercialPartners,getRepresentatives,updateOrder}=globalThis.__salesRecoveryApi'))
  await mount(SaleEditDialog, { order: orders[0], onClose() {}, onSaved: order => saved.push(order) })
  const field = label => nodes(tree).find(n => n.type === 'label' && text(n.props.children[0]) === label)
  const control = label => nodes(field(label)).find(n => ['select', 'input', 'textarea'].includes(n.type))
  control('Situação').props.onChange({ target: { value: 'CONCLUIDO' } }); render()
  control('Observações').props.onChange({ target: { value: 'Agendar instalação' } }); render()
  nodes(tree).find(n => n.type === 'form').props.onSubmit({ preventDefault() {} }); await settle()
  assert.deepEqual(patches, [{ id: 1, payload: { status: 'CONCLUIDO', observacao: 'Agendar instalação' } }])
  assert.equal(saved.length, 1)
  assert.equal(saved[0].orcamento_id, orders[0].orcamento_id)
  assert.deepEqual(saved[0].itens, orders[0].itens)
  assert.equal(saved[0].total_final, 100)
  clientsFail = true
  await mount(SaleEditDialog, { order: orders[0], onClose() {}, onSaved: order => saved.push(order) })
  assert.equal(control('Cliente').props.disabled, true)
  assert.equal(control('Cliente').props.value, 1, 'cadastro indisponível preserva vínculo')
  control('Observações').props.onChange({ target: { value: 'Nota de teste' } }); render()
  patchFail = true
  nodes(tree).find(n => n.type === 'form').props.onSubmit({ preventDefault() {} }); await settle()
  assert.match(text(tree), /API 422: alteração recusada/)
  assert.equal(saved.length, 1, 'falha não informa sucesso')
  assert.equal(JSON.stringify(orders), frozen, 'fixtures originais não foram alteradas')
  cleanups.splice(0).forEach(fn => fn())
  console.warn = originalConsoleWarn
  delete global.__salesRecoveryHooks; delete global.__salesRecoveryApi
  console.log('Vendas: seis pedidos/KPIs, cliente opcional, detalhe técnico, 404, edição por PATCH mínimo e falha sem sucesso simulado aprovados; sem rede/banco.')
})().catch(error => { console.error(error); process.exitCode = 1 })
