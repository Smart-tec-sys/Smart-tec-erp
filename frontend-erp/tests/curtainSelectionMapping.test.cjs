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
    .replace("import { CurtainComponents } from './CurtainComponents'", 'const CurtainComponents = () => null')
    .replace("import { useEffect, useRef } from 'react'", 'const useEffect = () => {};const useRef=v=>({current:v})')
    .replace("import { simulateCurtain } from '../services/api'", 'const simulateCurtain = async () => { throw new Error("unexpected request") }')
  compiled.set(pathToFileURL(file).href, (await transformWithOxc(source, file, { jsx: { runtime: 'automatic' } })).code)
  const { CurtainSimulation } = await import(pathToFileURL(file))
  const { emptyProduct, productCost, productLineSubtotal } = await import(pathToFileURL(path.join(__dirname, '../src/types/budget.ts')))

  const h=await import(pathToFileURL(path.join(__dirname,'../src/utils/curtainFabricCatalog.ts')))
  const cases=[
    [1,'WILER - FILIPINAS - 50.073-01','Wiler','FILIPINAS','50.073','01','50.073'],
    [2,'WILER - FILIPINAS - 50.072-04','Wiler','FILIPINAS','50.072','04','50.072'],
    [3,'TECIDO VELUDO - VERDE MINERAL - 3,00M','AÇÃO DISTRIBUIDORA','VELUDO','VELUDO','VERDE MINERAL','—'],
    [4,'VOIL LISO - BRANCO - 3,00M','AÇÃO DISTRIBUIDORA','VOIL','VOIL LISO','BRANCO','LISO'],
    [5,'LINHO CRONOS - CINZA - 2,80M','AÇÃO DISTRIBUIDORA','LINHO','LINHO CRONOS','CINZA','CRONOS'],
  ]

  const catalog=cases.map(([id,nome,supplier,,,cor])=>({id,nome,nome_fornecedor:supplier,cor,grupo_tecnico:'TECIDOS_CORTINA'}))
  const nodes=t=>!t||typeof t!=='object'?[]:Array.isArray(t)?t.flatMap(nodes):[t,...nodes(t.props?.children)]
  for(const [id,nome,,collection,fabricName,color,label] of cases){
    const p=catalog.find(p=>p.id===id)
    const suggestion=h.curtainSuggestions(catalog,color).find(s=>s.fabric?.id===id)
    assert.ok(suggestion)
    const state=h.applyCurtainSuggestion(h.DEFAULT_CURTAIN,suggestion)
    assert.equal(state.tecido,nome)
    assert.equal(state.tecidoProdutoId,id)
    assert.equal(state.colecaoTecido,collection)
    assert.equal(state.tecidoNome,fabricName)
    assert.equal(state.cor,color)
    assert.equal(suggestion.normalized.displayFabricName,label)
    const tree=CurtainSimulation({product:{...emptyProduct(1),modelTechnical:'CORTINA',groupTechnical:'TECIDOS_CORTINA',curtain:state},catalog,profile:'Varejo',onResult(){}})
    const selects=nodes(tree).filter(n=>n.type==='select')
    assert.equal(selects[1].props.value,collection)
    assert.equal(selects[2].props.value,fabricName)
    assert.ok(nodes(selects[2]).some(n=>n.type==='option'&&n.props.value===fabricName&&n.props.children===label))
    assert.deepEqual(h.fabricVariants(catalog,state).map(p=>p.id),[id])
    console.log('OK '+id+' '+collection+' / '+label+' / '+color)
  }
  assert.deepEqual(h.getFabricVariant({id:99,nome:'WILER - FILIPINAS - 50.073-01 AO 50.073-17 (ALGODÃO)',nome_fornecedor:'Wiler'}),{name:'50.073',color:'01 AO 17'})
  console.log('5 casos aprovados; faixa preservada sem variantes inventadas')
})().catch(error=>{console.error(error);process.exitCode=1})
