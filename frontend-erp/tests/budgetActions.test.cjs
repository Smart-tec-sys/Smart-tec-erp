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
        for (const ext of ['.ts', '.tsx']) { try { return next(spec + ext, context) } catch {} }
      }
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
  const { transformWithOxc } = await import('vite')
  const root = path.join(__dirname, '..')
  const url = file => pathToFileURL(path.join(root, 'src', file)).href
  let cells = [], index = 0, effects = []
  global.__actionsHooks = {
    useState(value) { const n = index++; if (!(n in cells)) cells[n] = typeof value === 'function' ? value() : value; return [cells[n], value => { cells[n] = typeof value === 'function' ? value(cells[n]) : value }] },
    useRef(value) { const n = index++; return cells[n] ?? (cells[n] = { current: value }) },
    useMemo: fn => fn(), useCallback: fn => fn,
    useEffect(fn, deps) { const n = index++; if (!cells[n] || deps.some((v, i) => v !== cells[n][i])) { cells[n] = deps; effects.push(fn) } },
  }
  const nodes = tree => tree == null || typeof tree !== 'object' ? [] : Array.isArray(tree) ? tree.flatMap(nodes) : [tree, ...nodes(tree.props?.children)]
  const text = tree => tree == null ? '' : typeof tree === 'string' || typeof tree === 'number' ? String(tree) : Array.isArray(tree) ? tree.map(text).join('') : text(tree.props?.children)
  async function compile(file, rewrite = s => s) {
    const filename = path.join(root, 'src', file)
    compiled.set(url(file), (await transformWithOxc(rewrite(fs.readFileSync(filename, 'utf8')), filename, { jsx: { runtime: 'automatic' } })).code)
    return import(url(file))
  }
  const approved = { id: 1, numero: '1', status: 'APROVADO', total_final: 100, itens: [] }
  const copy = { ...approved, id: 2, numero: '2', status: 'EM_ABERTO' }
  let calls = [], confirm = false, finishSale, failCopy = false
  const alerts = [], opened = []
  global.window = { innerWidth: 1200, innerHeight: 900, confirm: () => confirm, alert: message => alerts.push(message) }
  global.__actionsApi = {
    getBudgets: async () => [approved],
    deleteBudget: async id => calls.push(['delete', id]),
    duplicateBudget: async id => { calls.push(['copy', id]); if (failCopy) throw new Error('Falha cópia'); return copy },
    convertBudgetToOrder: id => { calls.push(['convert', id]); return new Promise(resolve => { finishSale = resolve }) },
  }
  const { BudgetsPage } = await compile('pages/BudgetsPage.tsx', source => source
    .replace(/import \{ useCallback, useEffect, useRef, useState \} from 'react'/, 'const {useCallback,useEffect,useRef,useState}=globalThis.__actionsHooks')
    .replace(/^import \{ (\w+) \} from '..\/components\/[^']+'$/gm, 'function $1(){return null}')
    .replace(/^import \{.*\} from '..\/services\/api'$/m, 'const {convertBudgetToOrder,deleteBudget,duplicateBudget,getBudgets}=globalThis.__actionsApi')
    .replace(/^import \{ budgetProductionDisabledReason, budgetProductionEnabled \}.*$/m, 'const budgetProductionEnabled=false,budgetProductionDisabledReason="Flag desligada"'))
  let page
  function render() { index = 0; page = BudgetsPage({ onNew() {}, onOpen: id => opened.push(id), refreshKey: 0 }); return page }
  async function settle() { render(); effects.splice(0).forEach(fn => fn()); await new Promise(setImmediate); return render() }
  const table = () => nodes(page).find(n => n.type?.name === 'BudgetTable').props
  await settle()
  await table().onGenerateSale(approved)
  await table().onDuplicate(approved)
  assert.deepEqual(calls, [], 'cancelamento não cria nada')
  confirm = true
  await table().onGenerateSale({ ...approved, status: 'EM_ABERTO' })
  assert.deepEqual(calls, [], 'aprovação obrigatória também no handler')
  render(); assert.match(text(page), /Apenas orçamentos aprovados/)
  const first = table().onGenerateSale(approved)
  await table().onGenerateSale(approved)
  await table().onDuplicate(approved)
  assert.deepEqual(calls, [['convert', 1]], 'lock impede ações concorrentes antes do rerender')
  finishSale({ id: 9, numero: '9' }); await first; render()
  assert.equal(alerts.length, 1)
  assert.ok(table().generatedSaleBudgetIds.has(1))
  await table().onGenerateSale(approved)
  assert.equal(calls.length, 1, 'orçamento já convertido fica bloqueado')
  await table().onDuplicate(approved); render()
  assert.deepEqual(opened, [2]); assert.deepEqual(table().budgets.map(b => b.id), [2, 1])
  assert.equal(approved.status, 'APROVADO', 'original preservado')
  failCopy = true
  await table().onDuplicate(approved); render()
  assert.match(text(page), /Falha cópia/)
  assert.equal(table().deletingId, null, 'falha libera ações')
  assert.deepEqual(table().budgets.map(b => b.id), [2, 1], 'falha não cria cópia fantasma')
  calls = []
  table().onShare(approved, 'email'); render()
  assert.ok(nodes(page).some(n => n.type?.name === 'BudgetShareDialog' && n.props.channel === 'email'))
  table().onPrepareServiceOrder(approved); render()
  assert.ok(nodes(page).some(n => n.type?.name === 'BudgetServiceOrderDialog' && n.props.budgetId === 1))
  assert.equal(table().onGenerateProduction, undefined, 'produção bloqueada com flag desabilitada')

  const apiSource = fs.readFileSync(path.join(root, 'src/services/api.ts'), 'utf8')
  compiled.set(url('services/auth.ts'), "export const getApiAuthHeaders=async()=>({Authorization:'Bearer synthetic','X-Empresa-ID':'7'})")
  compiled.set(url('services/api.ts'), (await transformWithOxc(apiSource.replaceAll('import.meta.env', JSON.stringify({ VITE_API_URL: 'http://127.0.0.1:8000' })), 'api.ts')).code)
  const api = await import(url('services/api.ts'))
  let responseStatus = 200
  global.fetch = async (url, init) => { calls.push([String(url), init]); return { ok: responseStatus === 200, status: responseStatus, json: async () => copy, text: async () => 'Já convertido' } }
  await api.duplicateBudget(1); await api.convertBudgetToOrder(1)
  assert.match(calls[0][0], /\/orcamentos\/1\/duplicar$/)
  assert.match(calls[1][0], /\/pedidos\/converter-orcamento\/1$/)
  for (const [, init] of calls) { assert.equal(init.method, 'POST'); assert.equal(init.headers.Authorization, 'Bearer synthetic'); assert.equal(init.headers['X-Empresa-ID'], '7') }
  assert.ok(!calls.some(([url]) => url.endsWith('/pedidos/')), 'venda manual nunca utilizada')
  responseStatus = 409
  await assert.rejects(api.convertBudgetToOrder(1), /409.*Já convertido/)

  // Exercise the actual portal menu and callbacks with controlled hooks.
  const { RowActionsMenu } = await compile('components/RowActionsMenu.tsx', source => source
    .replace("import { useEffect, useRef, useState } from 'react'", 'const {useRef,useState}=globalThis.__actionsHooks;const useEffect=()=>{}')
    .replace("import { createPortal } from 'react-dom'", 'const createPortal=element=>element'))
  cells = []; effects = []
  const activated = []
  global.document = { body: {} }
  const props = { module: 'budget', label: 'teste', onView() {}, onEdit() {}, onChangeStatus() {}, onDelete() {}, onPrintBudget() {}, onShareBudget: channel => activated.push(channel), onGenerateSale: () => activated.push('sale'), onDuplicateBudget: () => activated.push('copy'), onPrepareServiceOrder: () => activated.push('os'), onGenerateProduction: () => activated.push('production') }
  function menu() { index = 0; return RowActionsMenu(props) }
  let tree = menu()
  nodes(tree).find(n => n.type === 'button').props.onClick({ stopPropagation() {}, currentTarget: { getBoundingClientRect: () => ({ right: 400, bottom: 100, top: 90 }) } })
  tree = menu()
  for (const label of ['Visualizar proposta', 'Editar', 'Alterar situação', 'Imprimir', 'Compartilhar', 'Gerar', 'Excluir']) assert.equal(nodes(tree).filter(n => n.type === 'button' && text(n).trim() === label).length, 1, label)
  nodes(tree).find(n => n.type === 'button' && text(n) === 'Gerar').props.onClick(); tree = menu()
  for (const label of ['Cópia', 'Venda', 'Ordem de serviço']) assert.equal(nodes(tree).filter(n => n.type === 'button' && text(n) === label).length, 1)
  nodes(tree).find(n => n.type === 'button' && text(n) === 'Venda').props.onClick()
  assert.deepEqual(activated, ['sale'])
  assert.ok(!nodes(tree).some(n =>
    n.type === 'button' && text(n) === 'Produ\u00e7\u00e3o'))

  delete global.__actionsHooks; delete global.__actionsApi
  console.log('Menu de orçamentos: confirmação, aprovação, lock, cópia, venda única, OS/compartilhar, flag, API autenticada e opções preservadas aprovados.')
})().catch(error => { console.error(error); process.exitCode = 1 })
