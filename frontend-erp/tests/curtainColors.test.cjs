const assert=require('node:assert/strict')
const fs=require('node:fs'),path=require('node:path')
const {pathToFileURL}=require('node:url')
const {registerHooks}=require('node:module')
const compiled=new Map()
registerHooks({
 resolve(spec,ctx,next){try{return next(spec,ctx)}catch(e){if(spec.startsWith('.')&&!path.extname(spec)){for(const ext of ['.ts','.tsx']){try{return next(spec+ext,ctx)}catch{}}}throw e}},
 load(url,ctx,next){if(compiled.has(url))return{format:'module',source:compiled.get(url),shortCircuit:true};return next(url,ctx)}
})
;(async()=>{
 const {transformWithOxc}=await import('vite')
 const root=path.join(__dirname,'..')
 async function compile(file,change){const p=path.join(root,file);compiled.set(pathToFileURL(p).href,(await transformWithOxc(change(fs.readFileSync(p,'utf8')),p,{jsx:{runtime:'automatic'}})).code);return p}
 let states=[],cursor=0,effects=[],mounted=false,mode='ok',calls=[]
 globalThis.colorHooks={useId:()=> 'test-colors',useState:v=>{const i=cursor++;if(!(i in states))states[i]=v;return[states[i],n=>states[i]=n]},useEffect:f=>{if(!mounted)effects.push(f)}}
 globalThis.colorsApi={
  listGrades:async()=>{calls.push('grades');if(mode==='fail')throw Error('offline');return mode==='missing'?[]:[{id:9,nome:'CORES',ativo:true}]},
  listGradeValues:async id=>{assert.equal(id,9);calls.push('values');return[{valor:'CAFÉ',ativo:true},{valor:'BRANCO',ativo:true},{valor:'01',ativo:true},{valor:'INATIVA',ativo:false}]}
 }
 const fieldFile=await compile('src/components/CurtainColorField.tsx',s=>s.replace("import { useEffect, useId, useState } from 'react'","const {useEffect,useId,useState}=globalThis.colorHooks").replace("import { listGrades, listGradeValues } from '../services/gradesVariacoes'","const {listGrades,listGradeValues}=globalThis.colorsApi"))
 const {CurtainColorField}=await import(pathToFileURL(fieldFile))
 const h=await import(pathToFileURL(path.join(root,'src/utils/curtainColors.ts')))
 const cat=await import(pathToFileURL(path.join(root,'src/utils/curtainFabricCatalog.ts')))
 const {emptyProduct}=await import(pathToFileURL(path.join(root,'src/types/budget.ts')))
 const fabrics=[
  {id:500,nome:'WILER - FILIPINAS - 50.073-01',nome_fornecedor:'Wiler',grupo_tecnico:'TECIDOS_CORTINA'},
  {id:501,nome:'WILER - FILIPINAS - 50.073-02',nome_fornecedor:'Wiler',grupo_tecnico:'TECIDOS_CORTINA'},
  {id:502,nome:'WILER - FILIPINAS - 50.072-04',nome_fornecedor:'Wiler',grupo_tecnico:'TECIDOS_CORTINA'},
 ]
 let product={...emptyProduct(1),product:'Cortina de tecido',productId:null,modelTechnical:'CORTINA',groupTechnical:'TECIDOS_CORTINA',curtain:cat.fabricState(cat.DEFAULT_CURTAIN,fabrics[1]),color:'02'}
 const nodes=t=>!t||typeof t!=='object'?[]:Array.isArray(t)?t.flatMap(nodes):[t,...nodes(t.props?.children)]
 let tree
 function render(){cursor=0;tree=CurtainColorField({product,catalog:fabrics,onChange:p=>product=p});if(!mounted){mounted=true;effects.splice(0).forEach(f=>f())}return tree}
 async function flush(){await new Promise(setImmediate);render()}
 const options=()=>nodes(tree).filter(n=>n.type==='option').map(n=>n.props.value)
 function enter(value){nodes(tree).find(n=>n.type==='input').props.onChange({target:{value}});render()}
 render();await flush();assert.equal(tree.props.style.position,'relative');const clearButton=nodes(tree).find(n=>n.type==='button');assert.equal(clearButton.props['aria-label'],'Limpar cor');assert.equal(clearButton.props.children,'×');assert.equal(clearButton.props.style.position,'absolute');assert.deepEqual(calls,['grades','values']);assert.ok(options().includes('BRANCO'));assert.ok(!options().includes('INATIVA'));assert.equal(options().filter(v=>v==='01').length,1);console.log('OK 1 grade ativa e deduplicação')
 assert.ok(options().includes('CAFÉ'));console.log('OK 2 CAFÉ')
 enter('COR ESPECIAL CLIENTE');assert.equal(product.color,'COR ESPECIAL CLIENTE');assert.equal(product.curtain.cor,product.color);console.log('OK 3 texto livre')
 nodes(tree).find(n=>n.type==='button').props.onClick();render();assert.equal(product.color,'');assert.equal(product.curtain.cor,'');assert.equal(product.curtain.tecidoProdutoId,501);assert.ok(!nodes(tree).some(n=>n.type==='button'));console.log('OK 4 limpar sem remover tecido; botão oculto quando vazio')
 enter('01');assert.equal(product.curtain.tecidoProdutoId,500);assert.equal(product.curtain.colecaoTecido,'FILIPINAS');assert.equal(product.curtain.tecidoNome,'50.073');assert.equal(product.productId,null);console.log('OK 5 variante real preservada')
 const before=product.curtain;enter('VERDE ESPECIAL');assert.equal(product.curtain.tecidoProdutoId,500);assert.equal(product.curtain.tecido,before.tecido);assert.equal(product.productId,null);console.log('OK 6 nenhum ID falso')
 const simulationFile=await compile('src/components/CurtainSimulation.tsx',s=>s.replace("import { CurtainComponents } from './CurtainComponents'","const CurtainComponents=()=>null").replace("import { useEffect, useRef } from 'react'","const useEffect=()=>{};const useRef=v=>({current:v})").replace("import { simulateCurtain } from '../services/api'","const simulateCurtain=()=>{throw Error('unexpected calculation')}"))
 const {CurtainSimulation}=await import(pathToFileURL(simulationFile))
 let changed
 let section=CurtainSimulation({product,catalog:fabrics,profile:'Varejo',onResult:(id,state)=>changed=state})
 const selects=nodes(section).filter(n=>n.type==='select')
 selects[2].props.onChange({target:{value:'50.072'}})
 assert.equal(changed.cor,'');assert.equal(changed.tecidoProdutoId,502);assert.equal(changed.tecidoNome,'50.072');console.log('OK 7 troca de tecido limpa cor incompatível e preserva o novo ID real')
 product.curtain={...product.curtain,result:{saved:true},simulationKey:'saved'}
 const preserved=product.curtain
 enter('COR LIVRE')
 assert.equal(product.curtain.result,preserved.result);assert.equal(product.curtain.simulationKey,preserved.simulationKey)
 section=CurtainSimulation({product,catalog:fabrics,profile:'Varejo',onResult(){}})
 assert.ok(section);assert.ok(!nodes(section).some(n=>n.type==='input'&&n.props['aria-label']==='Cor do tecido'));console.log('OK 8 valor livre preserva configuração e resumo técnico')
 const rowFile=await compile('src/components/BudgetProductRow.tsx',s=>s.replace("import { useEffect, useMemo, useState } from 'react'","const useEffect=()=>{};const useRef=v=>({current:v});const useMemo=f=>f();const useState=v=>[v,()=>{}]")
 .replace(/import [{] ZeroNumberInput, zeroInputValue [}] from '[^']+'/g,'const ZeroNumberInput=()=>null;const zeroInputValue=v=>v')
 .replace(/import [{] ([A-Za-z]+Simulation) [}] from '[^']+'/g,'const $1=()=>null'))
 const {BudgetProductRow}=await import(pathToFileURL(rowFile))
 for(const page of ['NewBudgetPage','NewSalePage']){
  const source=fs.readFileSync(path.join(root,'src/pages/'+page+'.tsx'),'utf8');assert.ok(source.includes('<BudgetProductRow'))
  const row=BudgetProductRow({product,catalog:fabrics,commercialType:'Varejo',onChange(){},onRemove(){},onCurtain(){},onRomana(){},onRomanaTeto(){},onRolo(){},onDoubleVision(){}})
  assert.equal(nodes(row).filter(n=>n.type===CurtainColorField).length,1);assert.ok(!nodes(row).some(n=>n.type==='span'&&n.props.children==='Desconto'))
 }
 console.log('OK 9 componente único compartilhado entre Orçamento/Venda')
 for(const fallback of ['missing','fail']){
  mode=fallback;states=[];cursor=0;effects=[];mounted=false;render();await flush()
  assert.ok(options().includes('01'));assert.ok(!options().includes('CAFÉ'))
  enter('17');assert.equal(product.color,'17')
 }
 assert.equal(h.curtainColorSuggestions(fabrics,product,[' café ','CAFÉ']).filter(s=>s.value.toUpperCase().trim()==='CAFÉ').length,1)
 console.log('OK 10 ausência/falha da grade mantém variantes e texto livre')
 const summaryFile=await compile('src/components/BudgetSummary.tsx',s=>s.replace("import { ZeroNumberInput } from './ZeroNumberInput'",'const ZeroNumberInput=()=>null'))
 const {BudgetSummary}=await import(pathToFileURL(summaryFile))
 let discountChanged
 const summary=BudgetSummary({products:100,services:0,freight:0,discount:10,onDiscount:value=>discountChanged=value,includeBankFee:false,onIncludeBankFee(){},bankFeePercent:0,onBankFeePercent(){},internalValue:90,partnerValue:0,rtValue:0,bankFeeValue:0,clientTotal:90,onCancel(){},onSave(){}})
 const discountInput=nodes(summary).find(n=>n.props?.onValueChange&&n.props.value===10)
 assert.ok(discountInput);discountInput.props.onValueChange(20);assert.equal(discountChanged,20)
 console.log('OK: Desconto ausente na linha; Desconto R$ do Resumo continua funcional')
 console.log('10 testes focados aprovados')
})().catch(e=>{console.error(e);process.exitCode=1})
