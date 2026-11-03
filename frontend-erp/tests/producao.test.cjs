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
  const url = file => pathToFileURL(path.join(root, file)).href
  compiled.set(url('src/services/auth.ts'), `export const getApiAuthHeaders=async()=>({'X-Empresa-ID':'7',Authorization:'Bearer TEST_ONLY'});`)
  for (const file of ['src/services/api.ts', 'src/services/producao.ts', 'src/components/ProducaoPanel.tsx']) {
    const filename = path.join(root, file)
    const source = fs.readFileSync(filename, 'utf8').replaceAll('import.meta.env',
      JSON.stringify({ VITE_API_URL: 'https://backend.test.invalid' }))
    compiled.set(url(file), (await transformWithOxc(source, filename, { jsx: { runtime: 'automatic' } })).code)
  }
  const service = await import(url('src/services/producao.ts'))
  const calls = []
  global.fetch = async (target, options) => {
    calls.push({ target, options })
    return Response.json({ id: 1 })
  }
  await service.listarProducao(12)
  assert.equal(calls.at(-1).target, 'https://backend.test.invalid/producao/?pedido_id=12')
  await service.criarProducao(12)
  assert.equal(calls.at(-1).target, 'https://backend.test.invalid/producao/vendas/12')
  assert.equal(calls.at(-1).options.method, 'POST')
  assert.deepEqual(JSON.parse(calls.at(-1).options.body), { confirmar_fabricacao: true })
  assert.equal(calls.at(-1).options.headers['X-Empresa-ID'], '7')
  await service.liberarProducao(1)
  assert.equal(calls.at(-1).target, 'https://backend.test.invalid/producao/1/liberar')
  await service.salvarPeca(1, 4, 'Ambiente manual', 'Observação manual')
  assert.deepEqual(JSON.parse(calls.at(-1).options.body),
    { ambiente: 'Ambiente manual', observacoes: 'Observação manual' })
  assert.equal(calls.at(-1).options.method, 'PATCH')
  for (const [index, status] of service.statusProducao.slice(0, -1).entries()) {
    await service.avancarPeca(1, { id: 4, status })
    assert.deepEqual(JSON.parse(calls.at(-1).options.body),
      { status_atual: status, status: service.statusProducao[index + 1] })
  }
  assert.throws(() => service.avancarPeca(1, { id: 4, status: 'CONCLUIDA' }), /próxima etapa/)
  global.fetch = async (target, options) => {
    calls.push({ target, options })
    return new Response('<html>Ficha autenticada</html>', { headers: { 'Content-Type': 'text/html' } })
  }
  assert.match(await service.carregarDocumentoProducao(1), /Ficha autenticada/)
  assert.equal(calls.at(-1).target, 'https://backend.test.invalid/producao/1/ficha')
  assert.equal(calls.at(-1).options.headers.Authorization, 'Bearer TEST_ONLY')
  await service.carregarDocumentoProducao(1, 4)
  assert.equal(calls.at(-1).target, 'https://backend.test.invalid/producao/1/pecas/4/etiqueta')
  global.fetch = async () => Response.json({ detail: 'Migration pendente' }, { status: 503 })
  await assert.rejects(() => service.listarProducao(1), /503.*Migration pendente/)
  await assert.rejects(() => service.carregarDocumentoProducao(1), /503.*Migration pendente/)
  global.fetch = async () => { throw new Error('Rede indisponível') }
  await assert.rejects(() => service.criarProducao(1), /Rede indisponível/)
  const React = require('react')
  const { renderToStaticMarkup } = require('react-dom/server')
  const { ProducaoPanel } = await import(url('src/components/ProducaoPanel.tsx'))
  const html = renderToStaticMarkup(React.createElement(ProducaoPanel, { pedidoId: 1, statusVenda: 'CANCELADO' }))
  assert.match(html, /Venda cancelada/)
  assert.match(html, /Não reserva nem baixa estoque/)
  assert.match(html, /Carregando produção/)
  console.log('Produção V1: contratos, 4 transições, documentos autenticados, falhas e renderização aprovados.')
})().catch(error => { console.error(error); process.exitCode = 1 })
