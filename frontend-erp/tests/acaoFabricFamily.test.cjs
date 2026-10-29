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
  const file = path.join(__dirname, '../src/components/CurtainSimulation.tsx')
  // Only effects/network are stubbed; render and actual catalog predicates run unchanged.
  const source = fs.readFileSync(file, 'utf8')
    .replace("import { useEffect } from 'react'", 'const useEffect = () => {}')
    .replace("import { simulateCurtain } from '../services/api'", 'const simulateCurtain = async () => { throw new Error("unexpected request") }')
  compiled.set(pathToFileURL(file).href, (await transformWithOxc(source, file, { jsx: { runtime: 'automatic' } })).code)
  const { CurtainSimulation } = await import(pathToFileURL(file))
  const { emptyProduct, productCost, productLineSubtotal } = await import(pathToFileURL(path.join(__dirname, '../src/types/budget.ts')))

  const h=await import(pathToFileURL(path.join(__dirname,'../src/utils/curtainFabricCatalog.ts')))
  // References transcribed from Tabela de cortinas 30-04-24.pdf; IDs below are test identities.
  const specs=[
    [1,'11317 - VOIL LISO - (01)BRANCO - 3,00M','VOIL','VOIL LISO','BRANCO'],
    [2,'12241 - VOIL BORDADO ARABESCO - (01)BRANCO - 2,80M','VOIL','VOIL BORDADO ARABESCO','BRANCO'],
    [3,'13264-14561 - VOIL GAZE - (01)BRANCO - 3,00M','VOIL','VOIL GAZE','BRANCO'],
    [4,'15632 - LINHO ABSOLUTO - (60)LINHO - 3,00M','LINHO','LINHO ABSOLUTO','LINHO'],
    [5,'15670 - LINHO CRONOS - (23)OFF WHITE - 3,00M','LINHO','LINHO CRONOS','OFF WHITE'],
    [6,'12285-12654-13851 - BLACKOUT FOSCO - (02)PRETO - 2,80M','BLACKOUT','BLACKOUT FOSCO','PRETO'],
    [7,'2849 - BLACKOUT LISO - (01)BRANCO - 2,80M (100% POLIESTER)','BLACKOUT','BLACKOUT LISO','BRANCO'],
    [8,'TECIDO TERGAL VERAO - 01 BRANCO - 2,95M','TERGAL','TECIDO TERGAL VERAO','BRANCO'],
  ]
  const catalog=specs.map(([id,nome,,,cor])=>({id,nome,cor,nome_fornecedor:'AÇÃO DISTRIBUIDORA',grupo_tecnico:'TECIDOS_CORTINA',material_tecido:nome}))
  const unchanged=JSON.stringify(catalog)
  const nodes=tree=>!tree||typeof tree!=='object'?[]:Array.isArray(tree)?tree.flatMap(nodes):[tree,...nodes(tree.props?.children)]
  const options=select=>nodes(select).filter(n=>n.type==='option').slice(1).map(n=>n.props.value)
  const render=collection=>CurtainSimulation({product:{...emptyProduct(1),modelTechnical:'CORTINA',groupTechnical:'TECIDOS_CORTINA',curtain:{...h.DEFAULT_CURTAIN,fornecedorTecido:'AÇÃO DISTRIBUIDORA',colecaoTecido:collection}},catalog,profile:'Varejo',onResult(){}})
  for(const [id,,family,name,color] of specs){
    const p=catalog.find(p=>p.id===id)
    assert.equal(h.getFabricCollection(p.nome,h.getFabricSupplier(p)),family)
    assert.deepEqual(h.getFabricVariant(p),{name,color})
    const state=h.fabricState(h.DEFAULT_CURTAIN,p)
    assert.equal(state.tecidoProdutoId,id)
    assert.equal(h.fabricVariants(catalog,state).find(p=>p.id===id).id,id)
    console.log('OK '+family+' / '+name+' / '+color)
  }
  assert.deepEqual(options(nodes(render('')).filter(n=>n.type==='select')[1]),['BLACKOUT','LINHO','TERGAL','VOIL'])
  for(const family of ['VOIL','LINHO','BLACKOUT','TERGAL']){
    const names=options(nodes(render(family)).filter(n=>n.type==='select')[2])
    const expected=[...new Set(specs.filter(s=>s[2]===family).map(s=>s[3]))].sort((a,b)=>a.localeCompare(b,'pt-BR'))
    assert.deepEqual(names,expected)
    console.log('OK dropdown Tecido: '+family+' → '+names.join(', '))
  }
  for (const [reference,family,display] of [
    ['BLACKOUT FOSCO','BLACKOUT','FOSCO'],['BLACKOUT 100%','BLACKOUT','100%'],
    ['BLACKOUT GIARDINO','BLACKOUT','GIARDINO'],['BLACKOUT TERRAZO','BLACKOUT','TERRAZO'],
    ['LINHO MOOREA','LINHO','MOOREA'],['LINHO CRONOS','LINHO','CRONOS'],
    ['LINHO ABSOLUTO','LINHO','ABSOLUTO'],['LINHO GAIA','LINHO','GAIA'],
    ['VOIL LISO','VOIL','LISO'],['VOIL XADREZ','VOIL','XADREZ'],
  ]) {
    const p={id:99,nome:reference+' - BRANCO - 3,00M',cor:'BRANCO',nome_fornecedor:'AÇÃO DISTRIBUIDORA'}
    assert.equal(h.getFabricCollection(p.nome,p.nome_fornecedor),family)
    assert.equal(h.getFabricDisplayName(p),display)
    assert.equal(h.getFabricVariant(p).name,reference)
    const state=h.fabricState(h.DEFAULT_CURTAIN,p)
    assert.equal(state.tecido,p.nome);assert.equal(state.tecidoNome,p.nome);assert.equal(state.tecidoProdutoId,99)
  }
  for(const family of ['VOIL','LINHO','BLACKOUT','TERGAL']) {
    const select=nodes(render(family)).filter(n=>n.type==='select')[2]
    const labels=nodes(select).filter(n=>n.type==='option').slice(1).map(n=>n.props.children)
    const expected=specs.filter(s=>s[2]===family).map(s=>s[3].replace(/^TECIDO /,'').slice(family.length).trim()).sort((a,b)=>a.localeCompare(b,'pt-BR'))
    assert.deepEqual(labels,expected)
    console.log('OK exibição '+family+': '+labels.join(', '))
  }
  assert.equal(h.getFabricDisplayName({id:1,nome:'TECIDO VELUDO - MERLOT - 3,00M',cor:'MERLOT',nome_fornecedor:'AÇÃO DISTRIBUIDORA'}),'—')
  assert.equal(JSON.stringify(catalog),unchanged)
  for (const category of ['CORTINA','TECIDOS PARA CORTINA']) assert.equal(h.getFabricCollection(category,'AÇÃO DISTRIBUIDORA'),'')
  for(const name of ['ALCOR','ALGEDI','ANITA','AQUILA','ARCA']){
    const p={id:20,nome:'WILER - COZUMEL - '+name+' (01 AO 04)',nome_fornecedor:'Wiler'}
    assert.equal(h.getFabricCollection(p.nome,'Wiler'),'COZUMEL')
    assert.deepEqual(h.getFabricVariant(p),{name,color:'01 AO 04'});assert.equal(h.getFabricDisplayName(p),name)
  }
  for(const [name,family] of [['LINHO CRONOS','LINHO'],['LINHO ABSOLUTO','LINHO'],['BLACKOUT BRANCO','BLACKOUT'],['TERGAL VERÃO','TERGAL']]) assert.equal(h.getFabricCollection(name,'AÇÃO DISTRIBUIDORA'),family)
  console.log('OK Wiler intacta; IDs/objetos preservados; BLACKOUT/TERGAL/LINHO reconhecidos.')
})().catch(e=>{console.error(e);process.exitCode=1})
