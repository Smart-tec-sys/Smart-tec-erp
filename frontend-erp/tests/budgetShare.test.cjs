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
  const root = path.join(__dirname, '..')
  const url = file => pathToFileURL(path.join(root, file)).href
  const source = fs.readFileSync(path.join(root, 'src/services/budgetShare.ts'), 'utf8')
  compiled.set(url('src/services/budgetShare.ts'), (await transformWithOxc(source, 'budgetShare.ts')).code)
  const calls = []
  let fail = false
  global.__sharePdfMock = {
    prepareSavedBudgetPdf: async (id, mode) => {
      calls.push(['prepare', id, mode])
      if (fail) throw new Error('Empresa ativa mudou')
      return { budget: { id, numero: '123' }, blob: new Blob(['PDF']), filename: 'test.pdf', warnings: ['Aviso da logo'] }
    },
    downloadBudgetPdf: (blob, filename) => calls.push(['download', blob.size, filename]),
  }
  compiled.set(url('src/services/budgetPdf.ts'), 'export const {prepareSavedBudgetPdf,downloadBudgetPdf}=globalThis.__sharePdfMock')
  const { budgetShareOptions, budgetShareUrl, downloadBudgetForShare } = await import(url('src/services/budgetShare.ts'))
  assert.deepEqual(budgetShareOptions(false).map(x => x.mode), ['direct'])
  assert.deepEqual(budgetShareOptions(true).map(x => x.mode), ['reseller_client', 'reseller_commercial', 'reseller_internal'])
  for (const mode of ['direct', 'reseller_client', 'reseller_commercial', 'reseller_internal']) {
    calls.length = 0
    const result = await downloadBudgetForShare(123, mode, true)
    assert.deepEqual(calls[0], ['prepare', 123, mode])
    assert.equal(calls[1][0], 'download')
    assert.deepEqual(result.warnings, ['Aviso da logo'])
  }
  calls.length = 0
  await assert.rejects(downloadBudgetForShare(123, 'reseller_internal', false), /equipe Smart-tec/)
  assert.deepEqual(calls, [])
  fail = true
  await assert.rejects(downloadBudgetForShare(123, 'reseller_client', false), /Empresa ativa mudou/)
  assert.equal(calls.length, 1) // failed PDFs must never be downloaded
  const whatsapp = new URL(budgetShareUrl('whatsapp', '+55 (11) 99999-8888', '123 & 4', false))
  assert.equal(whatsapp.origin, 'https://wa.me')
  assert.equal(whatsapp.pathname, '/5511999998888')
  assert.match(whatsapp.searchParams.get('text'), /123 & 4/)
  assert.match(whatsapp.searchParams.get('text'), /manualmente/)
  const email = new URL(budgetShareUrl('email', 'Pessoa+vendas@example.invalid', '123\r\nBcc:fake', true))
  assert.equal(decodeURIComponent(email.pathname), 'Pessoa+vendas@example.invalid')
  assert.doesNotMatch(email.searchParams.get('subject'), /[\r\n]/)
  assert.match(email.searchParams.get('body'), /Uso exclusivo da equipe interna/)
  assert.throws(() => budgetShareUrl('email', 'ok@example.invalid?bcc=other', '1', false), /válido/)
  assert.throws(() => budgetShareUrl('whatsapp', 'javascript:12345678', '1', false), /telefone/)
  assert.ok(budgetShareUrl('email', '', '1', false).startsWith('mailto:?'))
  assert.ok(budgetShareUrl('whatsapp', '', '1', false).startsWith('https://wa.me/?'))
  delete global.__sharePdfMock
  console.log('Compartilhar: perfis, confirmação interna, gerador único, download, falhas e URLs de composição aprovados.')
})().catch(error => { console.error(error); process.exitCode = 1 })
