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
  const file = path.join(__dirname, '../src/components/BudgetProductRow.tsx')
  let source = fs.readFileSync(file, 'utf8')
    .replace("import { useEffect, useMemo, useState } from 'react'", `const useMemo = f => f(); const useEffect = f => { globalThis.__effects.push(f) }; const useState = initial => [globalThis.__query ?? initial, value => { globalThis.__query = value }]`)
    .replace(/import \{ ZeroNumberInput, zeroInputValue \} from '[^']+'/g, 'const ZeroNumberInput = () => null; const zeroInputValue = v => v')
    .replace(/import \{ (\w+Simulation) \} from '[^']+'/g, 'const $1 = () => null')
  compiled.set(pathToFileURL(file).href, (await transformWithOxc(source, file, { jsx: { runtime: 'automatic' } })).code)
  const { BudgetProductRow } = await import(pathToFileURL(file))
  const { emptyProduct } = await import(pathToFileURL(path.join(__dirname, '../src/types/budget.ts')))

  const base={id:99,nome:'Cortina de tecido',grupo_produto:'CORTINAS',grupo_tecnico:null,modelo_tecnico:null,tipo_produto:'Produto fabricado'}
  const bahamas={id:3671,nome:'WILER - BAHAMAS - BAHAMAS-75 (POLIESTER)',grupo_produto:'TECIDOS_CORTINA',nome_fornecedor:'Wiler'}
  const veludo={id:3024,nome:'TECIDO VELUDO - ALUMINIO - 3,00M',grupo_produto:'Tecidos',grupo_tecnico:'TECIDOS_CORTINA',tipo_cortina_persiana:'TECIDO PARA CORTINA',nome_fornecedor:'AÇÃO DISTRIBUIDORA'}
  const rawGase={id:1282,nome:'GASE BORA BORA',grupo_produto:'Tecidos',grupo_tecnico:'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL',tipo_cortina_persiana:null,nome_fornecedor:null}
  const eligibleGase={...rawGase,id:1283,grupo_tecnico:'TECIDOS_CORTINA',tipo_cortina_persiana:'TECIDO PARA CORTINA',nome_fornecedor:'AÇÃO DISTRIBUIDORA'} // Explicitly synthetic eligible fixture, not a production record.
  const nodes=tree=>!tree||typeof tree!=='object'?[]:Array.isArray(tree)?tree.flatMap(nodes):[tree,...nodes(tree.props?.children)]
  let changed
  const render=(query,catalog)=>{
    globalThis.__query=query;globalThis.__effects=[]
    return BudgetProductRow({product:emptyProduct(1),catalog,commercialType:'Varejo',onChange:p=>changed=p,onRemove(){},onCurtain(){},onRomana(){},onRomanaTeto(){},onRolo(){},onDoubleVision(){}})
  }
  const options=tree=>nodes(tree).filter(n=>n.type==='div'&&n.props.className==='product-suggestions').flatMap(n=>nodes(n).filter(c=>c.type==='button'))
  const text=tree=>nodes(tree).filter(n=>n.type==='strong').map(n=>n.props.children).join(' ')
  const catalog=[bahamas,veludo,rawGase,eligibleGase]
  for(const [query,key] of [['cortina','curtain-base'],['cortina de tecido','curtain-base'],['bahamas','curtain-3671'],['veludo','curtain-3024'],['gase','curtain-1283']]) {
    const result=options(render(query,catalog))
    const virtual=result.find(n=>n.key===key)
    assert.ok(virtual,query);assert.ok(!virtual.props.disabled)
    virtual.props.onClick();assert.equal(changed.productId,null); assert.equal(changed.modelTechnical,'CORTINA'); assert.equal(changed.product,'Cortina de tecido')
    if(query==='gase') assert.ok(result.some(n=>n.key==='1282'),'raw and virtual coexist')
    console.log('OK dropdown: '+query)
  }

  // Real technical component render: classification activates the motor without a base ID.
  const sectionFile=path.join(__dirname,'../src/components/CurtainSimulation.tsx')
  const sectionSource=fs.readFileSync(sectionFile,'utf8').replace("import { useEffect } from 'react'",'const useEffect=()=>{}').replace("import { simulateCurtain } from '../services/api'",'const simulateCurtain=()=>{throw Error("unexpected network")}')
  compiled.set(pathToFileURL(sectionFile).href,(await transformWithOxc(sectionSource,sectionFile,{jsx:{runtime:'automatic'}})).code)
  const { CurtainSimulation }=await import(pathToFileURL(sectionFile))
  options(render('bahamas',catalog)).find(n=>n.key==='curtain-3671').props.onClick()
  assert.equal(changed.curtain.tecidoProdutoId,3671)
  assert.equal(changed.curtain.fornecedorTecido,'Wiler');assert.equal(changed.curtain.colecaoTecido,'BAHAMAS')
  const section=CurtainSimulation({product:changed,catalog,profile:'Varejo',onResult(){}})
  assert.ok(section);assert.equal(section.props.className,'curtain-simulation')
  const selects=nodes(section).filter(n=>n.type==='select')
  assert.equal(selects[0].props.value,'Wiler');assert.equal(selects[1].props.value,'BAHAMAS')
  const finalSource=fs.readFileSync(file,'utf8')
  assert.ok(!finalSource.includes('resolveCurtainBase'));assert.ok(!finalSource.includes('curtainBase'))
  assert.ok(!finalSource.includes('Produto-base não cadastrado'));assert.ok(!finalSource.includes('seleção indisponível'))
  console.log('OK: Cortina e Bahamas selecionáveis sem base; motor abre configurado; nenhuma resolução de base.')

})().catch(e=>{console.error(e);process.exitCode=1})
