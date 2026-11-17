/* Regressões isoladas do catálogo de coleções; dados fictícios, sem acesso a APIs ou bancos. */
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const ts = require('/tmp/smarttec-test-ts/node_modules/typescript')

function loadTS(relativePath, dependencies = {}) {
  const original = fs.readFileSync(path.join(__dirname, '..', relativePath), 'utf8')
  const transpiled = ts.transpileModule(original, {
    compilerOptions: { module: 1, target: 9 }
  }).outputText
  const mod = { exports: {} }
  const requireLocal = (id) => {
    if (Object.prototype.hasOwnProperty.call(dependencies, id)) return dependencies[id]
    throw Error('Dependência não declarada: ' + id + ' em ' + relativePath)
  }
  new Function('require', 'module', 'exports', transpiled)(requireLocal, mod, mod.exports)
  return mod.exports
}

const budget = loadTS('src/types/budget.ts', {
  './romana': { romanaKey: () => '' },
  './romana_teto': { romanaTetoKey: () => '' },
  './rolo': { roloKey: () => '' },
  './double_vision': { doubleVisionKey: () => '' }
})
const fabric = loadTS('src/utils/fabricDisplay.ts', { '../types/budget': budget })
const rolo = loadTS('src/types/rolo.ts')
const rank = loadTS('src/utils/productSuggestionRank.ts', {
  '../types/budget': budget,
  './fabricDisplay': fabric
})

let checks = 0
function check(name, fn) {
  try { fn(); checks++; console.log('PASS', name) }
  catch (error) { console.error('FAIL', name); throw error }
}
function cloth(id, color, overrides = {}) {
  return {
    id, nome: 'TECIDO BK NÁPOLES - ' + color,
    grupo_tecnico: 'TECIDOS_ROLO_ROMANA_PAINEL',
    produto_base: 'BK NÁPOLES',
    familia_tecnica: 'ROLO_BK_NAPOLES',
    modelo_tecnico: 'BLACKOUT',
    cor: color, unidade_venda: 'ML', largura: 2.8,
    nome_fornecedor: 'FORNECEDOR A', valor_venda: id * 10,
    ...overrides
  }
}
const white = cloth(101, 'BRANCO')
const grey = cloth(102, 'CINZA')
const beige = cloth(103, 'BEGE')
check('classifica tecido pelo grupo técnico composto', () =>
  assert.equal(fabric.isFabricProduct(white), true))
check('nome visível remove somente a cor', () =>
  assert.equal(fabric.fabricDisplay(white).name, 'TECIDO BK NÁPOLES'))
check('duas cores de Nápoles são uma coleção', () => {
  const groups = fabric.groupFabricCollections([white, grey])
  assert.equal(groups.length, 1)
  assert.equal(groups[0].variants.length, 2)
  assert.equal(groups[0].colors.length, 2)
})
check('preserva SKU distinto na mesma cor', () => {
  const groups = fabric.groupFabricCollections([white, grey, cloth(104, 'BRANCO')])
  assert.equal(groups.length, 1)
  assert.equal(groups[0].variants.length, 3)
  assert.equal(groups[0].colors.find(c => c.color === 'BRANCO').variants.length, 2)
})
check('BK Nápoles real: cor e largura após hífens', () => {
  const items = ['BEGE','BRANCO','CINZA','CREME','MARROM'].map((cor, index) =>
    cloth(1000 + index, cor, { nome: 'BK NAPOLES - ' + cor + ' - 2,60M', largura: 2.6, unidade_venda: 'M²', produto_base: null, familia_tecnica: null }))
  const groups = fabric.groupFabricCollections(items)
  assert.equal(groups.length, 1)
  assert.equal(groups[0].colors.length, 5)
})
check('BK Brisk real: cor entre parênteses e largura dentro do nome', () => {
  const colors = ['WHITE', 'BEGE', 'CINZA']
  const items = colors.map((cor, index) => cloth(1100 + index, cor, {
    nome: 'TECIDO BK BRISK 1,80M (' + cor + ')',
    largura: index === 0 ? 1.8 : 0,
    produto_base: null, familia_tecnica: null, unidade_venda: 'METRO',
  }))
  const groups = fabric.groupFabricCollections(items)
  assert.equal(groups.length, 1)
  assert.equal(groups[0].colors.length, 3)
})
check('Romana BK Brisk real: cor entre parênteses e classificação técnica', () => {
  const items = ['AMENDOA','BLACK','BRANCO'].map((cor, index) => cloth(1200 + index, cor, {
    nome: 'ROMANA BK BRISK (' + cor + ')',
    familia_tecnica: 'ROMANA_BK_BRISK',
    modelo_tecnico: 'ROMANA',
    produto_base: null, largura: 0, unidade_venda: 'M²',
  }))
  const groups = fabric.groupFabricCollections(items)
  assert.equal(groups.length, 1)
  assert.equal(groups[0].variants.length, 3)
})
check('Romana Teto mantém estrutura e não confunde cores inativas com catálogo ativo', () => {
  const records = [{ id: 1500, nome: 'ROMANA TETO BLACKOUT NAPOLES',
    familia_tecnica: 'ROMANA_TETO_BLACKOUT_NAPOLES', grupo_tecnico: 'PERSIANA_ROMANA_TETO',
    modelo_tecnico: 'ROMANA_TETO', unidade_venda: 'M²', status_comercial: 'ATIVO', cor: null },
  ...['110','BEGE','CINZA'].map((cor,index)=>({
    id: 1501+index,nome: 'ROMANA TETO BLACKOUT NAPOLES ('+cor+')',
    familia_tecnica: 'ROMANA_TETO_BLACKOUT_NAPOLES',grupo_tecnico:'PERSIANA_ROMANA_TETO',
    modelo_tecnico:'ROMANA_TETO',unidade_venda:'M²',status_comercial:'INATIVO',cor
  }))]
  const ativos = records.filter(p=>!['INATIVO','INATIVA'].includes(budget.normalizeSearch(p.status_comercial||p.situacao||'ATIVO')))
  assert.equal(ativos.length,1)
  assert.equal(ativos[0].cor,null)
})
check('Picasso BK: cores no nome sem campo cor agrupam sem perda de SKU', () => {
  const items = ['AMENDOA','BEGE','CINZA','FENDI','GELO'].map((cor, i) => cloth(1600+i, '', {
    nome: 'TEC PICASSO BK - '+cor+' - 2,50M', cor: null, familia_tecnica: null,
    grupo_tecnico: 'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL',
    produto_base: null, largura: 2.5, unidade_venda: 'M²'
  }))
  const groups = fabric.groupFabricCollections(items)
  assert.equal(groups.length,1)
  assert.equal(groups[0].colors.length,5)
  assert.equal(fabric.fabricColor(items[0]), 'AMENDOA')
})
check('Picasso Trans não se mistura com Picasso BK', () => {
  const base={grupo_tecnico:'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL',cor:null,
    familia_tecnica:null,produto_base:null,largura:2.5,unidade_venda:'M²'}
  const groups=fabric.groupFabricCollections([
    {id:1901,nome:'TEC PICASSO BK - BEGE - 2,50M',...base},
    {id:1902,nome:'TEC PICASSO TRANS - BEGE - 2,50M',...base}
  ])
  assert.equal(groups.length,2)
})
check('sem campo cor: código numérico de Double Vision não é inventado', () => {
  const item=cloth(1800,'',{nome:'DOUBLE VISION W00D (3)',cor:null,
    grupo_tecnico:'TECIDOS_PERSIANAS_DOUBLE_VISION',modelo_tecnico:'DOUBLE_VISION',
    familia_tecnica:null,produto_base:null,largura:0})
  assert.equal(fabric.fabricColor(item),'')
})
check('Romana acabada cadastrada como TECIDOS é produto fabricado, não tecido', () => {
  const p={id:2100,nome:'ROMANA BK NÁPOLES (BRANCO)',cor:'BRANCO',
    tipo_produto:'Produto fabricado',grupo_tecnico:'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL',
    grupo_produto:'ROMANA',modelo_tecnico:'ROMANA',familia_tecnica:'ROMANA_BK_NAPOLES',unidade_venda:'M²'}
  assert.equal(fabric.isFabricProduct(p), false)
  assert.equal(fabric.fabricDisplay(p).name,'ROMANA BK NÁPOLES')
  assert.ok(fabric.commercialVariantKey(p))
})
check('Cores de Romana fabricada compartilham coleção, mas não se misturam aos tecidos', () => {
  const rows=['BRANCO','BEGE','CINZA'].map((cor,i)=>({
    id:2200+i,nome:'ROMANA BK NÁPOLES ('+cor+')',cor,
    tipo_produto:'Produto fabricado',grupo_tecnico:'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL',
    grupo_produto:'ROMANA',modelo_tecnico:'ROMANA',familia_tecnica:'ROMANA_BK_NAPOLES',unidade_venda:'M²',
  }))
  const fabricRow=cloth(2300,'BRANCO',{nome:'TECIDO BK NÁPOLES - BRANCO - 2,60M'})
  const groups=fabric.groupFabricCollections([...rows,fabricRow])
  assert.equal(groups.length,2)
  assert.equal(groups.find(g=>g.representative.id===2200).variants.length,3)
})
check('Eixo de Romana permanece componente, não produto acabado', () => {
  const p={id:2400,nome:'EIXO P/ ROMANA - 7,2MM',tipo_produto:'Produto fabricado',
    grupo_tecnico:'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL',modelo_tecnico:'ROMANA'}
  assert.equal(fabric.isClearlyFinishedProduct(p),false)
  assert.equal(fabric.commercialVariantKey(p),null)
})
check('Pinpoint: a coleção mantém cores e larguras distintas', () => {
  const items=['BEGE','CINZA'].map((cor,i)=>cloth(4000+i,'',{
    nome:'TECIDO BK - PINPOINT '+cor+' - 2,50M',cor:null,produto_base:null,
    familia_tecnica:null,largura:2.5,grupo_tecnico:'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'
  }))
  assert.equal(fabric.fabricColor(items[0]),'BEGE')
  assert.equal(fabric.fabricDisplay(items[0]).name,'TECIDO BK - PINPOINT')
  const grouped=fabric.groupFabricCollections(items)
  assert.equal(grouped.length,1)
  assert.equal(grouped[0].colors.length,2)
})
check('Venice: cores explícitas sem cor cadastral', () => {
  const items=['BEGE','FENDI'].map((cor,i)=>cloth(4100+i,'',{
    nome:'TECIDO BK - VENICE '+cor+' - 2,00M',cor:null,produto_base:null,
    familia_tecnica:null,grupo_tecnico:'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'
  }))
  assert.equal(fabric.groupFabricCollections(items).length,1)
})
check('Screen: cor entre coleção e qualificador STANDARD', () => {
  const items=['GREY','WHITE'].map((cor,i)=>cloth(4200+i,'',{
    nome:'TECIDO SC - SCREEN 3% '+cor+' STANDARD - 2,00M',cor:null,
    produto_base:null,familia_tecnica:null,largura:2,
    grupo_tecnico:'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'
  }))
  assert.equal(fabric.fabricDisplay(items[0]).name,'TECIDO SC - SCREEN 3% STANDARD')
  assert.equal(fabric.groupFabricCollections(items).length,1)
})
check('Aquarela: cor e largura compostas nos parênteses', () => {
  const items=['GREY','BEGE','CINZA'].map((cor,i)=>cloth(4300+i,'',{
    nome:'AQUARELA ('+cor+' / 2,50)',cor:null,produto_base:null,
    familia_tecnica:null,largura:0,
    grupo_tecnico:'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'
  }))
  assert.equal(fabric.fabricColor(items[0]),'GREY')
  assert.equal(fabric.fabricDisplay(items[0]).name,'AQUARELA')
  assert.equal(fabric.groupFabricCollections(items).length,1)
})
check('Double Vision: referências numéricas permanecem códigos, não cores', () => {
  const items=['3','4','06'].map((ref,i)=>cloth(4400+i,'',{
    nome:'DOUBLE VISION W00D ('+ref+')',cor:null,produto_base:null,
    familia_tecnica:null,largura:0,modelo_tecnico:'DOUBLE_VISION',
    grupo_tecnico:'TECIDOS_PERSIANAS_DOUBLE_VISION'
  }))
  assert.equal(fabric.fabricColor(items[0]),'')
  assert.equal(fabric.fabricReference(items[0]),'3')
  const groups=fabric.groupFabricCollections(items)
  assert.equal(groups.length,1)
  assert.equal(groups[0].variants.length,3)
  assert.deepEqual(groups[0].colors.map(c=>c.color),['Ref. 3','Ref. 4','Ref. 06'])
})
check('Códigos e medidas ambíguos continuam isolados', () => {
  const items=['TECIDO TR - AMAZONAS (44 / 2,50)','TUBO 32MM','TECIDO INDEFINIDO'].map((nome,i)=>cloth(4500+i,'',{
    nome,cor:null,produto_base:null,familia_tecnica:null
  }))
  for(const item of items) assert.equal(fabric.fabricColor(item),'')
  assert.equal(fabric.groupFabricCollections(items).length,3)
})
check('Pinpoint sem segundo hífen: cor e largura preservadas', () => {
  const p=cloth(5701,'',{nome:'TECIDO BK - PINPOINT CINZA 3,00M',cor:null,produto_base:null,familia_tecnica:null})
  assert.equal(fabric.fabricColor(p),'CINZA')
  assert.equal(fabric.fabricDisplay(p).name,'TECIDO BK - PINPOINT')
  assert.equal(fabric.fabricDisplay(p).width,'3,00 M')
})
check('Jade Double Vision com cor antes da largura é tecido, não produto acabado', () => {
  const p=cloth(5702,'',{nome:'JADE/DOUBLE VISION BRANCO 2,5M',cor:null,produto_base:null,familia_tecnica:null,
    modelo_tecnico:'DOUBLE_VISION',grupo_tecnico:'TECIDOS_PERSIANAS_DOUBLE_VISION'})
  assert.equal(fabric.fabricColor(p),'BRANCO')
  assert.equal(fabric.fabricDisplay(p).name,'JADE/DOUBLE VISION')
})
check('Amazonas: referência e largura juntas são reconhecidas sem criar cor', () => {
  const a=cloth(5703,'',{nome:'TECIDO TR - AMAZONAS (44 / 2,50)',cor:null,produto_base:null,familia_tecnica:null})
  const b={...a,id:5704}
  assert.equal(fabric.fabricColor(a),'')
  assert.equal(fabric.fabricReference(a),'44')
  assert.equal(fabric.fabricDisplay(a).name,'TECIDO TR - AMAZONAS')
  assert.equal(fabric.fabricDisplay(a).width,'2,50 M')
  const groups=fabric.groupFabricCollections([a,b])
  assert.equal(groups.length,1)
  assert.equal(groups[0].variants.length,2)
  assert.equal(groups[0].colors[0].color,'Ref. 44')
})
check('Houston BK: cor e referência numerada preservadas com coleção única', () => {
  const a=cloth(5705,'',{nome:'TEC HOUSTON BK - BEGE 812 - 2,50M',cor:null,produto_base:null,familia_tecnica:null})
  const b=cloth(5706,'',{nome:'TEC HOUSTON BK - BRANCO 802 - 2,50M',cor:null,produto_base:null,familia_tecnica:null})
  assert.equal(fabric.fabricColor(a),'BEGE')
  assert.equal(fabric.fabricReference(a),'812')
  assert.equal(fabric.fabricDisplay(a).name,'TEC HOUSTON BK')
  assert.equal(fabric.fabricDisplay(b).name,'TEC HOUSTON BK')
  const group=fabric.groupFabricCollections([a,b])
  assert.equal(group.length,1)
  assert.deepEqual(group[0].colors.map(c=>c.color),['BEGE','BRANCO'])
})
check('Nome genérico TECIDO BK - NATURAL 4303 não é agrupado por adivinhação', () => {
  const a=cloth(5707,'',{nome:'TECIDO BK - NATURAL 4303 - 2,50M',cor:null,produto_base:null,familia_tecnica:null})
  assert.equal(fabric.fabricColor(a),'')
  assert.equal(fabric.fabricReference(a),'')
})
check('Eixo, fita e bandô dentro de grupos TECIDOS não viram tecidos nem persianas', () => {
  for (const nome of ['EIXO P/ ROMANA - 7,2MM','FITA DECORATIVA ROMANA - COR 01','BANDÔ PARA ROMANA']) {
    const p=cloth(5708,'',{nome,cor:null,produto_base:null,familia_tecnica:null,modelo_tecnico:'ROMANA'})
    assert.equal(fabric.isClearlyAccessory(p),true,nome)
    assert.equal(fabric.isFabricProduct(p),false,nome)
    assert.equal(fabric.commercialVariantKey(p),null,nome)
  }
})
check('não mistura fornecedor diferente', () =>
  assert.equal(fabric.groupFabricCollections([white, cloth(105, 'CINZA', { nome_fornecedor: 'FORNECEDOR B' })]).length, 2))
check('não mistura BK Brisk com Nápoles', () =>
  assert.equal(fabric.groupFabricCollections([white, cloth(106, 'BRANCO', { nome: 'TECIDO BK BRISK - BRANCO', produto_base: 'BK BRISK', familia_tecnica: 'ROLO_BK_BRISK' })]).length, 2))
check('não mistura larguras de fornecimento', () =>
  assert.equal(fabric.groupFabricCollections([white, cloth(107, 'CINZA', { largura: 3 })]).length, 2))
check('não mistura tecido de empresa diferente', () =>
  assert.equal(fabric.groupFabricCollections([white, cloth(108, 'CINZA', { empresa_id: 2 })]).length, 2))
check('registro sem cor e sem coleção fica individual', () => {
  const first = cloth(200, '', { nome: 'TECIDO INDEFINIDO', cor: '', produto_base: '' })
  const second = cloth(201, '', { nome: 'TECIDO INDEFINIDO', cor: '', produto_base: '' })
  assert.equal(fabric.groupFabricCollections([first, second]).length, 2)
})
check('tecido não vira persiana rolô acabada', () =>
  assert.equal(rolo.roloKind(cloth(202, 'BRANCO', { nome: 'TECIDO BLACKOUT ROLÔ - BRANCO' })), null))
check('produto rolô acabado permanece produto acabado', () => {
  const p = { id: 300, nome: 'PERSIANA ROLO BLACKOUT MOTORIZADA', grupo_tecnico: 'PERSIANA_ROLO', modelo_tecnico: 'ROLO_MOTORIZADA' }
  assert.equal(fabric.isFabricProduct(p), false)
  assert.equal(rolo.roloKind(p), 'MOTORIZADA')
})
check('MOTOR é motorizado', () =>
  assert.equal(rolo.normalizeRoloDrive('MOTOR'), 'motorizado'))
check('manual segue manual', () =>
  assert.equal(rolo.normalizeRoloDrive('manual'), 'manual'))
check('chave de simulação distingue cor de tecido', () => {
  const a = { width: '2.8', height: '2.5', quantity: 1, discount: 0,
    color: 'BRANCO', curtain: { tecido: 'VOIL', cor: 'BRANCO', tecidoProdutoId: 101 } }
  const b = { ...a, color: 'CINZA', curtain: { ...a.curtain, cor: 'CINZA' } }
  assert.notEqual(budget.curtainKey(a, 'Varejo'), budget.curtainKey(b, 'Varejo'))
})
check('ordenação não esconde produto acabado', () => {
  const finished = { id: 450, nome: 'PERSIANA ROLO BK NÁPOLES',
    grupo_tecnico: 'PERSIANA_ROLO', modelo_tecnico: 'ROLO_MANUAL' }
  const order = rank.rankProductSuggestions([white, finished], 'ROLO BK NÁPOLES', p => Boolean(rolo.roloKind(p)))
  assert.equal(order[0].id, 450)
})
console.log('RESULTADO:', checks, 'testes aprovados.')
