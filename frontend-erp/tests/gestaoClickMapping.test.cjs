const assert = require('node:assert/strict')
const path = require('node:path')
const { pathToFileURL } = require('node:url')
const { test } = require('node:test')

test('mapeamento do backup validado relaciona as três fontes pelo código sem usar IDs ERP', async () => {
  const { gestaoClickMapping } = await import(pathToFileURL(path.join(__dirname, '../src/utils/gestaoClickMapping.ts')))
  const table = colunas => ({ colunas, total: 0, abas: ['Worksheet'], aba: 'Worksheet', separador: null, amostra: [] })
  const clients = table(['Codigo', 'Tipo de pessoa', 'Nome', 'CPF', 'RG', 'Data de nascimento',
    'Razão social', 'Nome social', 'CNPJ', 'Inscrição estadual', 'Inscrição municipal',
    'Ativo', 'Telefone', 'Celular', 'E-mail', 'Cadastrado em'])
  const addresses = table(['C\uFFFDdigo', 'Tipo', 'CEP', 'Logradouro', 'N\uFFFDmero', 'Complemento', 'Bairro', 'Cidade', 'UF'])
  const contacts = table(['C\uFFFDdigo', 'Tipo de contato', 'Nome', 'Contato', 'Cargo', 'Observa\uFFFD\uFFFDo'])
  const original = { mapeamento: {}, linha_cabecalho: 1, aba: null, separador: 'auto', encoding: 'auto',
    tipo_padrao: 'Física', complementar_vazios: false, ignorar_inconsistencias: false }
  const result = gestaoClickMapping(original, clients, addresses, contacts)
  assert.equal(result.codigo_cliente, 0)
  assert.equal(result.enderecos.codigo_cliente, 0)
  assert.equal(result.contatos.codigo_cliente, 0)
  assert.equal(result.mapeamento.nome, 2)
  assert.equal(result.mapeamento.cpf, 3)
  assert.equal(result.mapeamento.cnpj, 8)
  assert.equal(result.enderecos.mapeamento.logradouro, 3)
  assert.equal(result.contatos.mapeamento.contato, 3)
  assert.equal(result.complementar_vazios, false)
  assert.equal(result.ignorar_inconsistencias, false)
  assert.ok(!('id' in result.mapeamento))
  assert.ok(!('parceiro_id' in result.mapeamento))
  assert.deepEqual(original.mapeamento, {})
  assert.throws(() => gestaoClickMapping(original, { ...clients, colunas: [...clients.colunas].reverse() }, addresses, contacts), /mapeamento manual/)
  assert.throws(() => gestaoClickMapping(original, clients, { ...addresses, colunas: ['ID ERP', ...addresses.colunas.slice(1)] }, contacts), /código do cliente/)
})
