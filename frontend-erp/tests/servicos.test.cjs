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
    if (compiled.has(url)) return { format: 'module', source: compiled.get(url), shortCircuit: true }
    return next(url, context)
  },
})

;(async () => {
  const { transformWithOxc } = await import('vite')
  const root = path.join(__dirname, '..')
  const url = file => pathToFileURL(path.join(root, file)).href
  const authFile = 'src/services/auth.ts'
  compiled.set(url(authFile), `export const getApiAuthHeaders=async()=>({'X-Empresa-ID':'7'});`)
  for (const file of ['src/services/api.ts', 'src/services/servicos.ts']) {
    const filename = path.join(root, file)
    const source = fs.readFileSync(filename, 'utf8').replaceAll('import.meta.env', JSON.stringify({ VITE_API_URL: 'https://backend.test.invalid' }))
    compiled.set(url(file), (await transformWithOxc(source, filename)).code)
  }
  const servicos = await import(url('src/services/servicos.ts'))
  assert.equal(servicos.precoServicoParaAltura({
    tipo_calculo: 'FAIXA_ALTURA', preco_venda: 0,
    faixas_altura: [{ altura_max_cm: 100, preco_unitario: 12 }, { altura_max_cm: 200, preco_unitario: 19 }],
  }, 100), 12)
  assert.equal(servicos.precoServicoParaAltura({
    tipo_calculo: 'FAIXA_ALTURA', preco_venda: 0,
    faixas_altura: [{ altura_max_cm: 100, preco_unitario: 12 }, { altura_max_cm: 200, preco_unitario: 19 }],
  }, 150), 19)
  assert.throws(() => servicos.precoServicoParaAltura({
    tipo_calculo: 'FAIXA_ALTURA', preco_venda: 0, faixas_altura: [{ altura_max_cm: 100, preco_unitario: 12 }],
  }, 101), /não possui faixa/)
  assert.equal(servicos.subtotalServico(2, 30, 5), 55)
  assert.equal(servicos.subtotalServico(1, 10, 15), 0)

  const originalFetch = global.fetch
  const calls = []
  global.fetch = async (url, init) => {
    calls.push({ url: String(url), init })
    return { ok: true, status: 200, json: async () => [], text: async () => '' }
  }
  try {
    await servicos.listarServicos('lavagem', false)
    assert.match(calls[0].url, /\/servicos\/\?incluir_inativos=false&busca=lavagem$/)
    assert.equal(calls[0].init.headers['X-Empresa-ID'], '7')
  } finally { global.fetch = originalFetch }

  const budgetSource = fs.readFileSync(path.join(root, 'src/pages/NewBudgetPage.tsx'), 'utf8')
  const saleSource = fs.readFileSync(path.join(root, 'src/pages/NewSalePage.tsx'), 'utf8')
  assert.match(budgetSource, /servico_id:s\.serviceId/)
  assert.match(saleSource, /servico_id: s\.serviceId/)
  assert.match(budgetSource, /tipo_item:'SERVICO'/)
  assert.match(saleSource, /tipo_item: 'SERVICO'/)
  console.log('Serviços frontend: cálculos, tenant, orçamento e pedido aprovados.')
})().catch(error => {
  console.error(error)
  process.exitCode = 1
})
