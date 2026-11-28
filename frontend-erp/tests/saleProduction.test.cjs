const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { createRequire, registerHooks } = require('node:module')
const { pathToFileURL } = require('node:url')
const root = path.resolve(__dirname, '..')
const libraryRoot = process.env.SMARTTEC_TEST_VITE_ROOT || root
const dependencyRequire = createRequire(path.join(libraryRoot, 'package.json'))
const compiled = new Map()
registerHooks({
  resolve(spec, context, next) {
    if (compiled.has(spec)) return { url: spec, shortCircuit: true }
    if (spec.startsWith('.') && context.parentURL) {
      for (const ext of ['', '.ts', '.tsx']) {
        const candidate = new URL(spec + ext, context.parentURL).href
        if (compiled.has(candidate)) return { url: candidate, shortCircuit: true }
      }
    }
    if (spec.endsWith('.css')) return { url: new URL(spec, context.parentURL).href, shortCircuit: true }
    try { return next(spec, context) } catch (error) {
      if (spec.startsWith('.') && !path.extname(spec)) {
        for (const ext of ['.ts', '.tsx']) { try { return next(spec + ext, context) } catch {} }
      }
      if (!spec.startsWith('.') && !spec.startsWith('file:') && !spec.startsWith('node:')) return { url: pathToFileURL(dependencyRequire.resolve(spec)).href, shortCircuit: true }
      throw error
    }
  },
  load(url, context, next) {
    if (url.endsWith('.css')) return { format: 'module', source: '', shortCircuit: true }
    if (compiled.has(url)) return { format: 'module', source: compiled.get(url), shortCircuit: true }
    return next(url, context)
  },
})
;(async () => {
  const { transformWithOxc } = await import(pathToFileURL(path.join(libraryRoot, 'node_modules/vite/dist/node/index.js')))
  const url = file => pathToFileURL(path.join(root, 'src', file)).href
  async function compile(file, rewrite = source => source, suffix = '') {
    const filename = path.join(root, 'src', file), moduleUrl = url(file) + suffix
    compiled.set(moduleUrl, (await transformWithOxc(rewrite(fs.readFileSync(filename, 'utf8')), filename, { jsx: { runtime: 'automatic' } })).code)
    return import(moduleUrl)
  }
  const calls = []
  let company = '7', switchCompany = false
  const original = { id: 4, empresa_id: 7, numero: 'VEN-4', orcamento_id: 8, orcamento_numero: '1008', status: 'APROVADO', cliente_id: 9,
    itens: [{ id: 11, tipo_item: 'PRODUTO', produto_id: 21, modelo_tecnico: 'CORTINA', descricao: 'Cortina Linho', ambiente: 'Sala', largura: 2.5, altura: 2.2, material: 'Linho', cor: 'Areia', acionamento: 'Manual', observacao_item: 'Conferir barra', dados_tecnicos: { cortina: { tecido: 'Linho', modeloPrega: 'WAVE' } } }, { id: 12, tipo_item: 'SERVICO', descricao: 'Instalação' }] }
  const frozen = JSON.stringify(original)
  let order = structuredClone(original)
  global.__saleProductionMock = {
    getOrder: async id => { calls.push(['order', id]); if (switchCompany) company = '8'; return order },
    getApiAuthHeaders: async () => { calls.push(['auth']); return { 'X-Empresa-ID': company } },
  }
  compiled.set(url('services/api.ts'), 'export const {getOrder}=globalThis.__saleProductionMock')
  compiled.set(url('services/auth.ts'), 'export const {getApiAuthHeaders}=globalThis.__saleProductionMock')
  const localGateUrl = url('services/sale-production-local-gate.ts')
  const blockedGateUrl = url('services/sale-production-blocked-gate.ts')
  compiled.set(localGateUrl, "export const budgetProductionEnabled=true,budgetProductionDisabledReason='Produção bloqueada no ambiente oficial.'")
  compiled.set(blockedGateUrl, "export const budgetProductionEnabled=false,budgetProductionDisabledReason='Produção bloqueada no ambiente oficial.'")
  const local = await compile('services/saleProduction.ts', source => source.replace("'./budgetProduction'", JSON.stringify(localGateUrl)), '?local')
  const blocked = await compile('services/saleProduction.ts', source => source.replace("'./budgetProduction'", JSON.stringify(blockedGateUrl)), '?blocked')
  await assert.rejects(blocked.prepareSaleProduction(4), /ambiente oficial/)
  assert.deepEqual(calls, [], 'gate bloqueado recusa antes de autenticação e HTTP')
  assert.equal(local.saleProductionReason(order), undefined)
  assert.deepEqual(await local.prepareSaleProduction(4), original)
  assert.deepEqual(calls, [['auth'], ['order', 4], ['auth']], 'abertura só recarrega venda salva')
  for (const status of ['APROVADO', 'FATURADO', 'CONCLUIDO']) assert.equal(local.saleProductionReason({ ...order, status }), undefined)
  order = { ...original, status: 'ABERTO' }
  await assert.rejects(local.prepareSaleProduction(4), /cancelada/)
  order = { ...original, status: 'CANCELADO' }
  await assert.rejects(local.prepareSaleProduction(4), /cancelada/)
  order = { ...original, itens: [original.itens[1]] }
  await assert.rejects(local.prepareSaleProduction(4), /somente serviços/)
  order = { ...original, empresa_id: 8 }
  await assert.rejects(local.prepareSaleProduction(4), /empresa ativa/)
  order = { ...original, id: 5 }
  await assert.rejects(local.prepareSaleProduction(4), /empresa ativa/)
  order = structuredClone(original); switchCompany = true
  await assert.rejects(local.prepareSaleProduction(4), /empresa ativa mudou/)
  company = '7'; switchCompany = false
  assert.equal(JSON.stringify(original), frozen, 'vínculos, itens e especificações preservados')

  let cells = [], index = 0, effects = [], dialogFailure = false, reads = 0
  const hooks = global.__saleProductionHooks = {
    useState(initial) { const n = index++; if (!(n in cells)) cells[n] = typeof initial === 'function' ? initial() : initial; return [cells[n], value => { cells[n] = typeof value === 'function' ? value(cells[n]) : value }] },
    useRef(initial) { const n = index++; return cells[n] ?? (cells[n] = { current: initial }) },
    useEffect(fn, deps) { const n = index++; if (!cells[n] || deps.some((v, i) => v !== cells[n][i])) { cells[n] = deps; effects.push(fn) } },
  }
  const nodes = tree => tree == null || typeof tree !== 'object' ? [] : Array.isArray(tree) ? tree.flatMap(nodes) : [tree, ...nodes(tree.props?.children)]
  const text = tree => tree == null ? '' : typeof tree === 'string' || typeof tree === 'number' ? String(tree) : Array.isArray(tree) ? tree.map(text).join('') : text(tree.props?.children)
  global.document = { body: {}, activeElement: { focus() {} }, addEventListener() {}, removeEventListener() {} }
  global.window = { innerWidth: 1200, innerHeight: 900 }
  global.__prepareSaleProduction = async id => { reads++; assert.equal(id, 4); if (dialogFailure) throw new Error('Venda de outra empresa'); return order }
  const { SaleProductionDialog } = await compile('components/SaleProductionDialog.tsx', source => source
    .replace("import { useEffect, useRef, useState } from 'react'", 'const {useEffect,useRef,useState}=globalThis.__saleProductionHooks')
    .replace("import { createPortal } from 'react-dom'", 'const createPortal=tree=>tree')
    .replace("import { prepareSaleProduction } from '../services/saleProduction'", 'const prepareSaleProduction=(...args)=>globalThis.__prepareSaleProduction(...args)')
    .replace("import { ProducaoPanel } from './ProducaoPanel'", 'function ProducaoPanel(){return null}'))
  let tree
  const props = { saleId: 4, onClose() {} }
  function renderDialog() { index = 0; tree = SaleProductionDialog(props); return tree }
  renderDialog(); effects.splice(0).forEach(fn => fn()); await new Promise(setImmediate); renderDialog()
  assert.equal(reads, 1)
  const panel = nodes(tree).find(node => node.type?.name === 'ProducaoPanel')
  assert.equal(panel.props.pedidoId, 4)
  assert.equal(panel.props.statusVenda, 'APROVADO')
  assert.match(text(tree), /aprovação|Aprovação/)
  assert.match(text(tree), /1008/)
  dialogFailure = true; cells = []; effects = []
  renderDialog(); effects.splice(0).forEach(fn => fn()); await new Promise(setImmediate); renderDialog()
  assert.match(text(tree), /Venda de outra empresa/)
  assert.ok(!nodes(tree).some(node => node.type?.name === 'ProducaoPanel'))

  const { RowActionsMenu } = await compile('components/RowActionsMenu.tsx', source => source
    .replace("import { useEffect, useRef, useState } from 'react'", 'const {useRef,useState}=globalThis.__saleProductionHooks;const useEffect=()=>{}')
    .replace("import { createPortal } from 'react-dom'", 'const createPortal=tree=>tree'))
  cells = []; effects = []; let productionClicks = 0
  const menuProps = { module: 'sale', label: 'VEN-4', onView() {}, onEdit() {}, onChangeStatus() {}, onDelete() {}, onGenerateProduction() { productionClicks++ } }
  function renderMenu() { index = 0; return RowActionsMenu(menuProps) }
  tree = renderMenu()
  nodes(tree).find(node => node.type === 'button').props.onClick({ stopPropagation() {}, currentTarget: { getBoundingClientRect: () => ({ right: 400, bottom: 100, top: 90 }) } })
  tree = renderMenu()
  nodes(tree).find(node => node.type === 'button' && text(node) === 'Gerar').props.onClick(); tree = renderMenu()
  let production = nodes(tree).filter(node => node.type === 'button' && text(node) === 'Produção')
  assert.equal(production.length, 1)
  assert.equal(production[0].props.disabled, false)
  production[0].props.onClick()
  assert.equal(productionClicks, 1)
  assert.equal(cells[0], null, 'ação fecha o menu antes de abrir produção')
  console.log('Venda → Produção: gate, empresa, status, serviços, dados preservados, abertura apenas consultiva e callback único do menu aprovados.')
  delete global.__saleProductionMock; delete global.__saleProductionHooks; delete global.__prepareSaleProduction
})().catch(error => { console.error(error); process.exitCode = 1 })
