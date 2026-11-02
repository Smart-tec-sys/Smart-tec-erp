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
  for (const file of ['src/services/api.ts', 'src/services/cadastroConsultas.ts', 'src/services/preenchimentoAssistido.ts',
    'src/services/revendas.ts', 'src/components/RevendaForm.tsx', 'src/components/EnderecoPrincipalFields.tsx']) {
    const filename = path.join(root, file)
    const source = fs.readFileSync(filename, 'utf8').replaceAll('import.meta.env', JSON.stringify({ VITE_API_URL: 'https://backend.test.invalid' }))
    compiled.set(url(file), (await transformWithOxc(source, filename, { jsx: { runtime: 'automatic' } })).code)
  }
  const consultas = await import(url('src/services/cadastroConsultas.ts'))
  const assisted = await import(url('src/services/preenchimentoAssistido.ts'))
  const revendas = await import(url('src/services/revendas.ts'))
  const api = await import(url('src/services/api.ts'))
  const { RevendaForm } = await import(url('src/components/RevendaForm.tsx'))
  const React = require('react')
  const { renderToStaticMarkup } = require('react-dom/server')
  const cnpj = '11222333000181'
  assert.equal(consultas.cnpjValido(cnpj), true)
  assert.equal(consultas.cnpjValido('11.222.333/0001-81'), true)
  assert.equal(consultas.cnpjValido('12.ABC.345/01DE-35'), true)
  for (const value of ['', '00000000000000', '11111111111111', '11222333000180', 'https://provider.invalid', '11!222333000181']) assert.equal(consultas.cnpjValido(value), false)
  assert.equal(consultas.cepValido('01001-000'), true)
  assert.equal(consultas.cepValido('abcdefgh'), false)
  assert.equal(consultas.cepValido('1234567'), false)

  const initial = revendas.formularioDaRevenda()
  initial.nome = 'Cadastro manual'
  assert.equal(revendas.validarFormularioRevenda(initial), null)
  assert.equal(revendas.payloadDaRevenda(initial).limite_credito, null)
  initial.limite_credito = '0'
  assert.equal(revendas.payloadDaRevenda(initial).limite_credito, '0')
  initial.limite_credito = '1234.56'
  assert.equal(revendas.payloadDaRevenda(initial).limite_credito, '1234.56')
  initial.limite_credito = '-1'
  assert.match(revendas.validarFormularioRevenda(initial), /crédito/)
  initial.limite_credito = '-0.001'
  assert.match(revendas.validarFormularioRevenda(initial), /crédito/)
  initial.limite_credito = ''
  initial.estado = 'sp'
  assert.equal(revendas.payloadDaRevenda(initial).estado, 'SP')
  initial.estado = 'ZZ'
  assert.match(revendas.validarFormularioRevenda(initial), /UF/)
  initial.estado = ''
  initial.vendedor_responsavel_id = '-1'
  assert.match(revendas.validarFormularioRevenda(initial), /vendedor/)
  initial.vendedor_responsavel_id = ''
  initial.percentual_padrao = '101'
  assert.match(revendas.validarFormularioRevenda(initial), /percentual/)
  initial.percentual_padrao = '100.00001'
  assert.match(revendas.validarFormularioRevenda(initial), /percentual/)
  initial.percentual_padrao = '10.1234'
  initial.isento_ie = 'true'; initial.inscricao_estadual = '123'
  assert.match(revendas.validarFormularioRevenda(initial), /inscrição/)
  initial.inscricao_estadual = ''; initial.tipo_contribuinte = 'CONTRIBUINTE'
  assert.match(revendas.validarFormularioRevenda(initial), /contribuinte/)
  initial.tipo_contribuinte = 'ISENTO'
  assert.equal(revendas.validarFormularioRevenda(initial), null)

  const remote = {
    razao_social: 'Empresa consultada', nome_fantasia: 'Fantasia', telefone_comercial: '11999999999',
    cep: '01001000', numero: '10', complemento: 'Sala', estado: 'SP',
    ativo: false, percentual_padrao: '99', vendedor_responsavel_id: 2, observacao: 'EXTERNAL',
    limite_credito: 100, responsavel: 'EXTERNAL', isento_ie: true,
  }
  const mapped = revendas.camposConsultaCnpj(remote)
  for (const key of ['ativo', 'percentual_padrao', 'vendedor_responsavel_id', 'observacao', 'limite_credito', 'responsavel', 'isento_ie']) assert.ok(!(key in mapped))
  assert.equal(mapped.telefone, '11999999999')
  assert.equal(mapped.numero, '10')
  assert.equal(revendas.camposConsultaCnpj({}).numero, undefined)
  assert.equal(revendas.camposConsultaCnpj({}).inscricao_estadual, undefined)
  assert.deepEqual(revendas.camposConsultaCep({ cep: '01001000', logradouro: 'Praça', numero: '999', complemento: 'Não usar' }), { cep: '01001000', logradouro: 'Praça' })

  let state = assisted.iniciarPreenchimento(revendas.formularioDaRevenda())
  const first = assisted.aplicarConsulta(state, mapped, 'cnpj', state.versao)
  state = first.estado
  assert.equal(state.valores.razao_social, 'Empresa consultada')
  assert.equal(state.valores.percentual_padrao, '0')
  assert.equal(state.valores.limite_credito, '')
  state = assisted.editarCampo(state, 'razao_social', 'Minha edição')
  state = assisted.editarCampo(state, 'telefone', '')
  const next = assisted.aplicarConsulta(state, { razao_social: 'Outra razão', telefone: '123', cidade: 'São Paulo' }, 'cnpj', state.versao)
  assert.equal(next.estado.valores.razao_social, 'Minha edição')
  assert.equal(next.estado.valores.telefone, '')
  assert.deepEqual(next.sugestoes, { razao_social: 'Outra razão', telefone: '123' })
  assert.equal(next.estado.valores.cidade, 'São Paulo')
  const manuallyAccepted = assisted.editarCampo(next.estado, 'razao_social', next.sugestoes.razao_social)
  assert.equal(manuallyAccepted.valores.razao_social, 'Outra razão')
  assert.equal(manuallyAccepted.origens.razao_social, 'manual')
  const saved = assisted.iniciarPreenchimento(revendas.formularioDaRevenda({ id: 1, nome: 'Existente', ativo: true, percentual_padrao: '12', razao_social: 'Salva', limite_credito: null }), true)
  assert.equal(assisted.aplicarConsulta(saved, { razao_social: 'Externa' }, 'cnpj', 0).estado.valores.razao_social, 'Salva')
  const startedAt = state.versao
  state = assisted.editarCampo(state, 'logradouro', 'Digitado durante consulta')
  assert.equal(assisted.aplicarConsulta(state, { logradouro: 'Resposta atrasada' }, 'cep', startedAt).estado.valores.logradouro, 'Digitado durante consulta')
  let race = assisted.iniciarPreenchimento(revendas.formularioDaRevenda())
  race = assisted.aplicarConsulta(race, { cidade: 'Resposta mais nova' }, 'cep', 0).estado
  assert.equal(assisted.aplicarConsulta(race, { cidade: 'CNPJ antigo' }, 'cnpj', 0).estado.valores.cidade, 'Resposta mais nova')
  let autoName = assisted.iniciarPreenchimento(revendas.formularioDaRevenda())
  autoName = assisted.aplicarConsulta(autoName, { nome: 'Primeira empresa' }, 'cnpj', autoName.versao).estado
  autoName = assisted.aplicarConsulta(autoName, { nome: 'Outra empresa' }, 'cnpj', autoName.versao).estado
  assert.equal(autoName.valores.nome, 'Outra empresa')
  autoName = assisted.editarCampo(autoName, 'nome', 'Nome escolhido manualmente')
  assert.equal(assisted.aplicarConsulta(autoName, { nome: 'Outra fonte' }, 'cnpj', autoName.versao).estado.valores.nome, 'Nome escolhido manualmente')
  assert.equal(consultas.consultaAindaAtual('cnpj', cnpj, 1, { requestId: 1, documento: cnpj, tipo_pessoa: 'JURIDICA', cep: '' }), true)
  assert.equal(consultas.consultaAindaAtual('cnpj', cnpj, 1, { requestId: 2, documento: cnpj, tipo_pessoa: 'JURIDICA', cep: '' }), false)
  assert.equal(consultas.consultaAindaAtual('cnpj', cnpj, 1, { requestId: 1, documento: cnpj, tipo_pessoa: 'FISICA', cep: '' }), false)
  assert.equal(consultas.consultaAindaAtual('cep', '01001000', 1, { requestId: 1, documento: '', tipo_pessoa: '', cep: '20000000' }), false)

  const html = renderToStaticMarkup(React.createElement(RevendaForm, { onClose() {}, onSaved() {} }))
  for (const title of ['1. Dados gerais', '2. Contato', '3. Endereço principal', '4. Fiscal', '5. Comercial Smart-tec', '6. Financeiro / Crédito', '7. Observações']) assert.ok(html.includes(title))
  assert.equal((html.match(/ required=""/g) || []).length, 1)
  assert.match(html, /name="limite_credito"[^>]*value=""/)
  assert.ok(html.includes('limite não definido'))
  assert.ok(!html.includes('Adicionar endereço'))
  const view = renderToStaticMarkup(React.createElement(RevendaForm, { revenda: { id: 1, nome: 'Teste', ativo: true, percentual_padrao: '0' }, somenteLeitura: true, onClose() {}, onSaved() {} }))
  assert.ok(!view.includes('Salvar revenda'))
  assert.ok(!view.includes('Consultar CEP'))

  const calls = []
  global.fetch = async (target, options) => {
    const pathname = new URL(target).pathname
    assert.equal(new URL(target).hostname, 'backend.test.invalid')
    assert.equal(options.headers['X-Empresa-ID'], '7')
    calls.push({ pathname, method: options.method || 'GET', body: options.body ? JSON.parse(options.body) : null })
    if (pathname === '/consultas/cnpj') return Response.json({ dados: mapped, fonte: 'Mock CNPJ', consultado_em: '2026-11-02T12:00:00Z' })
    if (pathname === '/consultas/cep') return Response.json({ dados: { cep: '01001000', cidade: 'São Paulo' }, fonte: 'Mock CEP', consultado_em: '2026-11-02T12:00:00Z' })
    return Response.json({ id: 1, nome: 'Teste', ativo: true, percentual_padrao: '0', ...JSON.parse(options.body || '{}') })
  }
  assert.equal((await consultas.consultarCnpj(cnpj)).fonte, 'Mock CNPJ')
  await consultas.consultarCep('01001000')
  await api.createCommercialPartner({ nome: 'Cadastro rápido' })
  assert.deepEqual(calls[2].body, { nome: 'Cadastro rápido' })
  await revendas.obterRevenda(1)
  const result = await revendas.atualizarRevenda(1, { limite_credito: null, observacao: 'Manual' })
  assert.equal(result.limite_credito, null)
  assert.deepEqual(calls.at(-1), { pathname: '/representantes/parceiros/1', method: 'PATCH', body: { limite_credito: null, observacao: 'Manual' } })
  global.fetch = async () => Response.json({ detail: 'Consulta indisponível' }, { status: 503 })
  await assert.rejects(consultas.consultarCnpj(cnpj), /503/)
  assert.equal(revendas.validarFormularioRevenda({ ...revendas.formularioDaRevenda(), nome: 'Manual após falha' }), null)
  console.log('Revendas V1: contratos, crédito NULL/zero, CNPJ/CEP, allowlist, proteção manual, corridas, formulário, cadastro rápido e API simulada aprovados.')
})().catch(error => { console.error(error); process.exitCode = 1 })
