const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { pathToFileURL } = require('node:url')
const { registerHooks } = require('node:module')
const compiled = new Map()
registerHooks({
  resolve(spec, context, next) {
    if (compiled.has(spec)) return { url: spec, shortCircuit: true }
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
  const root = path.resolve(__dirname, '..')
  const viteRoot = process.env.SMARTTEC_TEST_VITE_ROOT || root
  const { transformWithOxc } = await import(pathToFileURL(path.join(viteRoot, 'node_modules/vite/dist/node/index.js')))
  const filename = path.join(root, 'src/services/budgetProduction.ts')
  const source = fs.readFileSync(filename, 'utf8')
  const calls = []
  let company = '7', budget = { id: 2, status: 'APROVADO' }, orders = [{ id: 4, orcamento_id: 2 }]
  let order = { id: 4, orcamento_id: 2, empresa_id: 7, status: 'ABERTO' }, changeCompany = false
  global.__budgetProductionMock = {
    getApiAuthHeaders: async () => ({ 'X-Empresa-ID': company }),
    getBudget: async id => { calls.push(['budget', id]); return budget },
    getOrders: async () => { calls.push(['orders']); if (changeCompany) company = '8'; return orders },
    getOrder: async id => { calls.push(['order', id]); return order },
  }
  for (const [name, env, baseUrl, flag, expected] of [
    ['flag-off', { DEV: true }, 'http://127.0.0.1:8000', false, /desabilitada/],
    ['production-build', { DEV: false }, 'http://127.0.0.1:8000', true, /ambiente oficial/],
    ['remote-api', { DEV: true }, 'https://erp.example.invalid', true, /ambiente oficial/],
    ['local', { DEV: true }, 'http://127.0.0.1:8000', true, null],
  ]) {
    const suffix = `?case=${name}`
    // Unique URLs keep each environment evaluation isolated in the same process.
    const apiUrl = pathToFileURL(path.join(root, `src/services/api-${name}.ts`)).href
    const authUrl = pathToFileURL(path.join(root, `src/services/auth-${name}.ts`)).href
    const flagUrl = pathToFileURL(path.join(root, `src/services/flag-${name}.ts`)).href
    compiled.set(apiUrl, `export const apiConfig={baseUrl:${JSON.stringify(baseUrl)}}; export const {getBudget,getOrders,getOrder}=globalThis.__budgetProductionMock`)
    compiled.set(authUrl, 'export const {getApiAuthHeaders}=globalThis.__budgetProductionMock')
    compiled.set(flagUrl, `export const producaoV1Enabled=${flag}; export function exigirProducaoHabilitada(){if(!producaoV1Enabled)throw new Error('Produção V1 desabilitada.')}`)
    const adjusted = source.replace("'./api'", JSON.stringify(apiUrl)).replace("'./auth'", JSON.stringify(authUrl)).replace("'./producaoFlag'", JSON.stringify(flagUrl)).replaceAll('import.meta.env', JSON.stringify(env))
    const moduleUrl = pathToFileURL(filename).href + suffix
    compiled.set(moduleUrl, (await transformWithOxc(adjusted, filename)).code)
    const service = await import(moduleUrl)
    if (expected) {
      calls.length = 0
      assert.equal(service.budgetProductionEnabled, false)
      await assert.rejects(service.prepareBudgetProduction(2), expected)
      assert.deepEqual(calls, [])
      continue
    }
    assert.equal(service.budgetProductionEnabled, true)
    calls.length = 0
    assert.deepEqual((await service.prepareBudgetProduction(2)).order, order)
    assert.deepEqual(calls, [['budget', 2], ['orders'], ['order', 4]])
    budget = { ...budget, status: 'EM_ABERTO' }
    calls.length = 0
    await assert.rejects(service.prepareBudgetProduction(2), /aprovados/)
    assert.deepEqual(calls, [['budget', 2]])
    budget.status = 'APROVADO'; orders = []
    await assert.rejects(service.prepareBudgetProduction(2), /Nenhuma venda foi criada/)
    orders = [{ id: 4, orcamento_id: 2 }, { id: 5, orcamento_id: 2 }]
    await assert.rejects(service.prepareBudgetProduction(2), /mais de uma venda/)
    orders = [{ id: 4, orcamento_id: 2 }]; order.status = 'CANCELADO'
    await assert.rejects(service.prepareBudgetProduction(2), /cancelada/)
    order.status = 'ABERTO'; order.orcamento_id = 9
    await assert.rejects(service.prepareBudgetProduction(2), /incompatível/)
    order.orcamento_id = 2; order.empresa_id = 8
    await assert.rejects(service.prepareBudgetProduction(2), /empresa ativa/)
    order.empresa_id = 7; changeCompany = true
    await assert.rejects(service.prepareBudgetProduction(2), /empresa ativa mudou/)
  }
  delete global.__budgetProductionMock
  console.log('Produção orçamento: flag off, ambiente oficial e API remota bloqueados sem HTTP; vínculo único, aprovação e empresa validados; zero criação automática.')
})().catch(error => { console.error(error); process.exitCode = 1 })
