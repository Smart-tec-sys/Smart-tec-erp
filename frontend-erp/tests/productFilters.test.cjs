const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { pathToFileURL } = require('node:url')
const { registerHooks } = require('node:module')
const compiled = new Map()

registerHooks({
  resolve(spec, context, next) {
    try { return next(spec) } catch (error) {
      if (spec.startsWith('.') && !path.extname(spec)) return next(`${spec}.ts`)
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
  const filename = path.join(__dirname, '../src/pages/productFilters.ts')
  const url = pathToFileURL(filename).href
  const source = fs.readFileSync(filename, 'utf8')
  compiled.set(url, (await transformWithOxc(source, filename)).code)
  const filters = await import(url)
  const product = {
    id: 8,
    nome: 'Tubo de acionamento',
    descricao: 'Tubo galvanizado para persiana',
    codigo_interno: 'TB-32',
    codigo_fornecedor: 'FORN-900',
    nome_fornecedor: 'Fornecedor Norte',
    fornecedores: 'Fornecedor Norte; Fornecedor Sul',
    grupo_produto: 'Acessórios',
    grupo_tecnico: 'TUBO',
    familia_tecnica: 'ROLÔ',
    modelo_tecnico: 'ROLÔ 32 mm',
    unidade_venda: 'UN',
  }
  const indexed = filters.indexProduct(product)
  for (const termo of [
    'galvanizado', 'FORN-900', 'fornecedor sul',
    'tubo rolô', 'tubo',
  ]) {
    assert.ok(indexed.text.includes(filters.normalizeProductSearch(termo)), termo)
  }
  const values = filters.productFilterValues(product)
  assert.equal(values.technicalGroup[0], 'TUBO')
  assert.equal(values.family[0], 'ROLÔ')
  assert.equal(values.model[0], 'ROLÔ 32 mm')
  assert.deepEqual(filters.emptyProductFilters.technicalGroup, '')
  assert.deepEqual(filters.emptyProductFilters.model, '')
  assert.equal(filters.productFilterLabels.technicalGroup, 'Grupo técnico')
  assert.equal(filters.productFilterLabels.model, 'Modelo técnico')
  const options = filters.productFilterOptions([product])
  assert.deepEqual(options.technicalGroup.map(option => option.value), ['tubo'])
  assert.deepEqual(options.family.map(option => option.value), ['rolo'])
  assert.deepEqual(options.model.map(option => option.value), ['rolo 32 mm'])
  console.log('Filtro do catálogo: grupo/família/modelo, descrição, código e fornecedor aprovados.')
})().catch(error => { console.error(error); process.exitCode = 1 })
