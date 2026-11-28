const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { pathToFileURL } = require('node:url')
const { registerHooks } = require('node:module')
const compiled = new Map()
registerHooks({
  resolve(spec, context, next) {
    if (spec.startsWith('.') && !path.extname(spec)) {
      const target = new URL(spec + '.ts', context.parentURL).href
      if (compiled.has(target)) return { url: target, shortCircuit: true }
    }
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
  const root = process.env.SMARTTEC_FRONTEND_ROOT || path.join(__dirname, '..')
  const { transformWithOxc } = await import(pathToFileURL(path.join(root, 'node_modules/vite/dist/node/index.js')).href)
  const url = file => pathToFileURL(path.join(__dirname, '..', file)).href
  const file = path.join(__dirname, '../src/services/budgetServiceOrder.ts')
  compiled.set(url('src/services/budgetServiceOrder.ts'), (await transformWithOxc(fs.readFileSync(file, 'utf8'), file)).code)
  const original = { id: 41, numero: 'ORC-41', empresa_id: 7, cliente_id: 9, cliente_nome: 'Cliente sintético', cliente_final_nome: 'Cliente final sintético', cliente_final_telefone: '5511999999999', cliente_final_email: 'cliente@example.invalid', cliente_final_documento: 'sintético', cliente_final_endereco: 'Rua sintética 1', observacao: 'Instalação agendada', observacao_interna: 'SEGREDO FINANCEIRO', itens: [{ id: 15, tipo_item: 'SERVICO', servico_id: 3, descricao: 'Instalação de persiana', quantidade: 2, largura: 1.2, altura: 2.1, area: 2.52, unidade: 'UN', cor: 'Branca', observacao_item: 'Sala', dados_tecnicos: { romana_teto: { acionamento: 'MANUAL_BASTAO' } }, preco_unitario: 100 }] }
  let empresa = 7, changed = false, fail = false
  const requests = []
  global.__osMocks = {
    getApiAuthHeaders: async () => ({ 'X-Empresa-ID': String(empresa) }),
    getBudget: async id => { requests.push(id); if (fail) throw new Error('Falha sintética'); if (changed) empresa = 8; return original },
  }
  compiled.set(url('src/services/api.ts'), 'export const {getBudget}=globalThis.__osMocks')
  compiled.set(url('src/services/auth.ts'), 'export const {getApiAuthHeaders}=globalThis.__osMocks')
  const { budgetToServiceOrderDraft, prepareBudgetServiceOrder, serviceOrderDraftText, downloadServiceOrderDraft } = await import(url('src/services/budgetServiceOrder.ts'))
  const draft = await prepareBudgetServiceOrder(41)
  assert.deepEqual(requests, [41])
  assert.equal(draft.tipo, 'RASCUNHO_OS')
  assert.equal(draft.orcamento_id, 41)
  assert.equal(draft.numero_orcamento, 'ORC-41')
  assert.equal(draft.cliente_id, 9)
  assert.equal(draft.cliente_nome, original.cliente_nome)
  assert.equal(draft.cliente_final.endereco, original.cliente_final_endereco)
  assert.equal(draft.itens[0].descricao, original.itens[0].descricao)
  assert.equal(draft.itens[0].servico_id, 3)
  assert.deepEqual(draft.itens[0].dados_tecnicos, original.itens[0].dados_tecnicos)
  draft.itens[0].dados_tecnicos.romana_teto.acionamento = 'ALTERADO'
  assert.equal(original.itens[0].dados_tecnicos.romana_teto.acionamento, 'MANUAL_BASTAO')
  assert.ok(!('numero' in draft))
  assert.ok(!('preco_unitario' in draft.itens[0]))
  assert.ok(!serviceOrderDraftText(draft).includes('SEGREDO FINANCEIRO'))
  assert.match(serviceOrderDraftText(draft), /OS NÃO CRIADA/)
  assert.throws(() => budgetToServiceOrderDraft(original, 8), /outra empresa/)
  assert.throws(() => budgetToServiceOrderDraft(original, 0), /Empresa ativa/)
  changed = true
  await assert.rejects(prepareBudgetServiceOrder(41), /empresa ativa mudou/)
  changed = false; empresa = 7; fail = true
  await assert.rejects(prepareBudgetServiceOrder(41), /Falha sintética/)
  fail = false
  await assert.rejects(prepareBudgetServiceOrder(42), /não corresponde/)
  let clicked = false, revoked = false, callback
  const link = { click() { clicked = true }, remove() {} }
  const originals = { document: global.document, create: URL.createObjectURL, revoke: URL.revokeObjectURL, timeout: global.setTimeout }
  try {
    global.document = { createElement: () => link, body: { appendChild() {} } }
    URL.createObjectURL = () => 'blob:os-draft-test'
    URL.revokeObjectURL = value => { assert.equal(value, 'blob:os-draft-test'); revoked = true }
    global.setTimeout = fn => { callback = fn }
    downloadServiceOrderDraft(draft)
    assert.equal(clicked, true)
    assert.equal(link.download, 'Rascunho-OS-Orcamento-ORC-41.txt')
    assert.equal(revoked, false); callback(); assert.equal(revoked, true)
  } finally { global.document = originals.document; URL.createObjectURL = originals.create; URL.revokeObjectURL = originals.revoke; global.setTimeout = originals.timeout }
  delete global.__osMocks
  console.log('OS: rascunho salvo, cliente, vínculo, descrições, especificações isoladas, empresa, erros e download aprovados; nenhuma criação simulada.')
})().catch(error => { console.error(error); process.exitCode = 1 })
