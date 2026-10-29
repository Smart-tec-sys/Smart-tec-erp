const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path')
const {pathToFileURL}=require('node:url'),{registerHooks}=require('node:module'),compiled=new Map()
registerHooks({resolve(s,c,n){try{return n(s,c)}catch(e){if(s.startsWith('.')&&!path.extname(s))for(const ext of ['.ts','.tsx'])try{return n(s+ext,c)}catch{}throw e}},load(u,c,n){if(u.endsWith('.css'))return{format:'module',source:'',shortCircuit:true};if(compiled.has(u))return{format:'module',source:compiled.get(u),shortCircuit:true};return n(u,c)}})
;(async()=>{
 const {transformWithOxc}=await import('vite'),root=path.join(__dirname,'../src'),file=path.join(root,'components/CurtainComponents.tsx')
 let states=[],cursor=0
 globalThis.quantityHooks={useState:v=>{let i=cursor++;if(!(i in states))states[i]=v;return[states[i],n=>states[i]=n]}}
 compiled.set(pathToFileURL(file).href,(await transformWithOxc(fs.readFileSync(file,'utf8').replace("import { useState } from 'react'","const {useState}=globalThis.quantityHooks"),file,{jsx:{runtime:'automatic'}})).code)
 const {CurtainComponents}=await import(pathToFileURL(file))
 globalThis.QuantityComponents=CurtainComponents
 const motorFile=path.join(root,'components/CurtainSimulation.tsx')
 const source=fs.readFileSync(motorFile,'utf8').replace("import { useEffect, useRef } from 'react'","const useEffect=()=>{};const useRef=v=>({current:v})").replace("import { simulateCurtain } from '../services/api'","const simulateCurtain=async()=>{throw Error('unexpected request')}").replace("import { CurtainComponents } from './CurtainComponents'","const CurtainComponents=globalThis.QuantityComponents")
 compiled.set(pathToFileURL(motorFile).href,(await transformWithOxc(source,motorFile,{jsx:{runtime:'automatic'}})).code)
 const {CurtainSimulation}=await import(pathToFileURL(motorFile)),b=await import(pathToFileURL(path.join(root,'types/budget.ts'))),{DEFAULT_CURTAIN}=await import(pathToFileURL(path.join(root,'utils/curtainFabricCatalog.ts')))
 const nodes=t=>!t||typeof t!=='object'?[]:Array.isArray(t)?t.flatMap(nodes):[t,...nodes(t.props?.children)]
 const catalog=[{id:50,nome:'TRILHO AL DESL SIMPLES MAX (BRANCO)',grupo_tecnico:'COMPONENTES_CORTINAS',situacao:'Ativo',unidade_venda:'ML',custo_final:5.7583}]
 let product={...b.emptyProduct(1),modelTechnical:'CORTINA',groupTechnical:'TECIDOS_CORTINA',width:'2,8',height:'2,45',curtain:{...DEFAULT_CURTAIN,tecidoProdutoId:3985,componentes:[{produto_id:50,quantidade:3}]}},changes=0,tree
 const result={preco_disponivel:true,custo_total:337.53,preco_unitario:675.06,subtotal:675.06,desenvolvimento_m:7,quantidade_alturas:3,quantidade_pecas:1,tecido:{consumo_total_ml:8.55,cabeca_cm:10,barra_cm:15,barra_dupla:true,consumo_barra_m:.3,consumo_por_altura_m:2.85},mao_de_obra:{quantidade_alturas:2,valor_por_altura:35,total:70},forro:{possui:false},entretela:{usa:false,quantidade_ml:0},trilho:{quantidade_ml:2.8},rodizios:{quantidade_cortina_un:0,quantidade_trilho_un:0},ganchos:{quantidade_cortina_un:0},wave:{aplicavel:false},avisos:[]}
 function calculated(){product.curtain={...product.curtain,result,simulationKey:b.curtainKey(product,'Varejo')}}
 function render(){cursor=0;tree=CurtainSimulation({product,catalog,profile:'Varejo',onResult:(_,s)=>{changes++;product={...product,curtain:s}}});const area=nodes(tree).find(n=>n.type===CurtainComponents);const line=nodes(area.type(area.props)).find(n=>typeof n.type==='function');return nodes(line.type(line.props)).find(n=>n.props?.['aria-label']==='Quantidade do componente')}
 calculated();let input=render()
 for(const text of ['3','3,0','3,00','3.0','3.00']){
  const previousResult=product.curtain.result,previousKey=product.curtain.simulationKey
  input.props.onChange({target:{value:text}});input=render();assert.equal(input.props.value,text)
  assert.equal(product.curtain.componentes[0].quantidade,3);assert.equal(changes,0);assert.equal(product.curtain.result,previousResult);assert.equal(product.curtain.simulationKey,previousKey)
  assert.ok(!JSON.stringify(tree).includes('Calculando a simulação técnica'))
  input.props.onBlur();input=render();assert.equal(input.props.value,'3,00');assert.equal(changes,0)
  assert.equal(b.formatCurrency(3*5.7583),'R$ 17,27')
 }
 input.props.onChange({target:{value:'2,80'}});input=render();assert.equal(changes,1);assert.equal(typeof product.curtain.componentes[0].quantidade,'number');assert.equal(product.curtain.componentes[0].quantidade,2.8);assert.equal(b.formatCurrency(2.8*5.7583),'R$ 16,12')
 calculated();input=render();input.props.onChange({target:{value:'2.8'}});assert.equal(changes,1);input=render();input.props.onBlur();input=render();assert.equal(input.props.value,'2,80');assert.ok(!JSON.stringify(tree).includes('Calculando a simulação técnica'))
 for(const text of ['-','NaN','Infinity']){input.props.onChange({target:{value:text}});input=render();assert.equal(product.curtain.componentes[0].quantidade,2.8);assert.equal(changes,1)}
 console.log('PASS: 3 / 3,0 / 3,00 / 3.0 / 3.00 preservam número 3, resultado e chave, sem loading/recálculo; 2,80 / 2.8 geram número 2.8; subtotais 17,27 e 16,12; blur só formata; entradas inválidas não chegam ao motor.')
})().catch(e=>{console.error(e);process.exitCode=1})
