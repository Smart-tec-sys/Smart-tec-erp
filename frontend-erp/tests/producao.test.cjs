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
  const flag = process.env.TEST_PRODUCAO_FLAG
  for (const file of ['src/services/producaoFlag.ts', 'src/services/api.ts', 'src/services/producao.ts', 'src/components/ProducaoPanel.tsx']) {
    const filename = path.join(root, file)
    const source = fs.readFileSync(filename, 'utf8').replaceAll('import.meta.env',
      JSON.stringify({ VITE_API_URL: 'https://backend.test.invalid', ...(flag == null ? {} : {VITE_PRODUCAO_V1_ENABLED:flag}) }))
    compiled.set(url(file), (await transformWithOxc(source, filename, { jsx: { runtime: 'automatic' } })).code)
  }
  const service = await import(url('src/services/producao.ts'))
  const calls = []
  global.fetch = async (target, options) => {
    calls.push({ target, options })
    return Response.json({ id: 1 })
  }
  if (flag?.trim().toLowerCase() !== 'true') {
    for (const action of [
      () => service.obterAutorizacaoProducao(1), () => service.aprovarProducao(1),
      () => service.liberarPedidoProducao(1),
      () => service.listarProducao(1), () => service.criarProducao(1),
      () => service.liberarProducao(1), () => service.listarCatalogoComponentes('tubo'),
      () => service.salvarPeca(1,1,{ justificativa: 'Teste' }),
      () => service.adicionarComponentePeca(1,1,{ produto_id: 1 }),
      () => service.atualizarComponentePeca(1,1,1,{ produto_id: 1 }),
      () => service.removerComponentePeca(1,1,1,'Teste'),
      () => service.conferirPeca(1,1,'Teste'),
      () => service.avancarPeca(1,{id:1,status:'AGUARDANDO'}),
      () => service.carregarDocumentoProducao(1), () => service.carregarDocumentoProducao(1,1),
      () => service.carregarEtiquetasLoteProducao(1),
    ]) await assert.rejects(async()=>action(), /desabilitada/)
    const React=require('react')
    const {renderToStaticMarkup}=require('react-dom/server')
    const {ProducaoPanel}=await import(url('src/components/ProducaoPanel.tsx'))
    assert.equal(renderToStaticMarkup(React.createElement(ProducaoPanel,{pedidoId:1,statusVenda:'ABERTO'})),'')
    assert.equal(calls.length,0)
    const sale=fs.readFileSync(path.join(root,'src/pages/SaleDetailPage.tsx'),'utf8')
    assert.match(sale,/producaoV1Enabled && <button/)
    assert.match(sale,/producaoV1Enabled && producaoAberta && <ProducaoPanel/)
    console.log('Produção desligada: painel vazio, controles ocultos, todos os serviços bloqueados e zero HTTP.')
    return
  }
  await service.obterAutorizacaoProducao(12)
  assert.equal(calls.at(-1).target, 'https://backend.test.invalid/producao/vendas/12/autorizacao')
  await service.aprovarProducao(12)
  assert.equal(calls.at(-1).target, 'https://backend.test.invalid/producao/vendas/12/aprovar')
  assert.equal(calls.at(-1).options.method, 'POST')
  await service.liberarPedidoProducao(12)
  assert.equal(calls.at(-1).target, 'https://backend.test.invalid/producao/vendas/12/liberar-fabricacao')
  await service.listarProducao(12)
  assert.equal(calls.at(-1).target, 'https://backend.test.invalid/producao/?pedido_id=12')
  await service.criarProducao(12)
  assert.equal(calls.at(-1).target, 'https://backend.test.invalid/producao/vendas/12')
  assert.equal(calls.at(-1).options.method, 'POST')
  assert.deepEqual(JSON.parse(calls.at(-1).options.body), { confirmar_fabricacao: true })
  assert.equal(calls.at(-1).options.headers['X-Empresa-ID'], '7')
  await service.liberarProducao(1)
  assert.equal(calls.at(-1).target, 'https://backend.test.invalid/producao/1/liberar')
  const ficha = {
    modo_fabricacao: 'MANUAL_SUPERVISIONADA',
    ambiente: 'Ambiente manual',
    largura: 2.2,
    altura: 2.4,
    quantidade: 1,
    observacoes: 'Observação manual',
    especificacoes_fabricacao: { acabamento: 'Conferir' },
    justificativa: 'Ajuste técnico aprovado',
  }
  await service.salvarPeca(1, 4, ficha)
  assert.deepEqual(JSON.parse(calls.at(-1).options.body), ficha)
  assert.equal(calls.at(-1).options.method, 'PATCH')
  await service.listarCatalogoComponentes('tubo 38')
  assert.equal(calls.at(-1).target, 'https://backend.test.invalid/producao/catalogo-componentes?q=tubo%2038')
  const component = {
    produto_id: 17, quantidade: 2, unidade: 'UN', comprimento_corte: 2.2,
    custo_unitario: 12, observacoes: 'Corte', justificativa: 'Componente revisado',
  }
  await service.adicionarComponentePeca(1, 4, component)
  assert.equal(calls.at(-1).options.method, 'POST')
  assert.deepEqual(JSON.parse(calls.at(-1).options.body), component)
  await service.atualizarComponentePeca(1, 4, 9, component)
  assert.equal(calls.at(-1).target, 'https://backend.test.invalid/producao/1/pecas/4/componentes/9')
  assert.equal(calls.at(-1).options.method, 'PATCH')
  await service.removerComponentePeca(1, 4, 9, 'Remoção autorizada')
  assert.equal(calls.at(-1).options.method, 'DELETE')
  assert.deepEqual(JSON.parse(calls.at(-1).options.body), { justificativa: 'Remoção autorizada' })
  await service.conferirPeca(1, 4, 'Conferência técnica')
  assert.equal(calls.at(-1).target, 'https://backend.test.invalid/producao/1/pecas/4/conferir')
  assert.deepEqual(JSON.parse(calls.at(-1).options.body), {
    confirmar_conferencia: true, justificativa: 'Conferência técnica',
  })
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
  await service.carregarEtiquetasLoteProducao(1)
  assert.equal(calls.at(-1).target, 'https://backend.test.invalid/producao/1/etiquetas')
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
