const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path')
const {pathToFileURL}=require('node:url'),{registerHooks}=require('node:module'),compiled=new Map()
registerHooks({resolve(s,c,n){try{return n(s,c)}catch(e){if(s.startsWith('.')&&!path.extname(s))return n(s+'.ts',c);throw e}},load(u,c,n){if(compiled.has(u))return{format:'module',source:compiled.get(u),shortCircuit:true};return n(u,c)}})
;(async()=>{
 const {transformWithOxc}=await import('vite'),root=path.join(__dirname,'../src'),file=path.join(root,'components/CurtainSimulation.tsx')
 let effects=[],timers=[],request,state
 globalThis.mooreaHooks={useEffect:f=>effects.push(f),useRef:v=>({current:v})}
 globalThis.window={setTimeout:f=>{timers.push(f);return timers.length},clearTimeout:()=>{}}
 const result={preco_disponivel:true,custo_total:337.53,preco_unitario:675.06,subtotal:675.06,desenvolvimento_m:7,quantidade_alturas:3,quantidade_pecas:1,tecido:{consumo_total_ml:8.55,cabeca_cm:10,barra_cm:15,barra_dupla:true,consumo_barra_m:.3,consumo_por_altura_m:2.85},mao_de_obra:{quantidade_alturas:2,valor_por_altura:35,total:70},forro:{possui:false},entretela:{usa:false,quantidade_ml:0},trilho:{quantidade_ml:2.8},rodizios:{quantidade_cortina_un:0,quantidade_trilho_un:0},ganchos:{quantidade_cortina_un:0},wave:{aplicavel:false},avisos:[]}
 globalThis.mooreaSimulate=async p=>{request=p;return result}
 const src=fs.readFileSync(file,'utf8').replace("import { useEffect, useRef } from 'react'","const {useEffect,useRef}=globalThis.mooreaHooks").replace("import { simulateCurtain } from '../services/api'","const simulateCurtain=globalThis.mooreaSimulate").replace("import { CurtainComponents } from './CurtainComponents'","const CurtainComponents=()=>null")
 compiled.set(pathToFileURL(file).href,(await transformWithOxc(src,file,{jsx:{runtime:'automatic'}})).code)
 const {CurtainSimulation}=await import(pathToFileURL(file)),{DEFAULT_CURTAIN}=await import(pathToFileURL(path.join(root,'utils/curtainFabricCatalog.ts'))),{emptyProduct}=await import(pathToFileURL(path.join(root,'types/budget.ts')))
 const names=['13158-12768 - LINHO MOOREA - (60)LINHO - 3,00M','13992-14423 - LINHO MOOREA - (01)BRANCO - 3,00M']
 const catalog=names.map((nome,i)=>({id:3985+i,nome,nome_fornecedor:'AÇÃO DISTRIBUIDORA',grupo_tecnico:'TECIDOS_CORTINA',situacao:'Ativo',cor:i?'Branco':'Linho',largura:3,custo_final:i?30.11:31.29}))
 state={...DEFAULT_CURTAIN,fornecedorTecido:'AÇÃO DISTRIBUIDORA',colecaoTecido:'LINHO',componentes:[]}
 const nodes=t=>!t||typeof t!=='object'?[]:Array.isArray(t)?t.flatMap(nodes):[t,...nodes(t.props?.children)]
 const render=()=>{effects=[];return CurtainSimulation({product:{...emptyProduct(1),modelTechnical:'CORTINA',groupTechnical:'TECIDOS_CORTINA',width:'2,80',height:'2,45',curtain:state},catalog,profile:'Varejo',onResult:(_,v)=>state=v})}
 let tree=render();nodes(tree).filter(n=>n.type==='select')[2].props.onChange({target:{value:'LINHO MOOREA'}})
 assert.equal(state.tecidoProdutoId,3985);assert.equal(state.tecidoNome,'LINHO MOOREA');assert.equal(state.cor,'');assert.deepEqual(state.componentes,[])
 tree=render();assert.ok(!JSON.stringify(tree).includes('Selecione o tecido real e informe largura'))
 effects.forEach(f=>f());timers.splice(0).forEach(f=>f());await new Promise(setImmediate)
 assert.equal(request.tecido_produto_id,3985);assert.equal(request.largura,2.8);assert.equal(request.altura,2.45);assert.deepEqual(request.componentes,[])
 tree=render();assert.equal(state.result.tecido.consumo_total_ml,8.55);assert.equal(state.result.mao_de_obra.total,70);assert.ok(JSON.stringify(tree).includes('Cortina — simulação técnica'))
 state={...state,cor:'BRANCO',componentes:[{produto_id:700,quantidade:3}]};tree=render();nodes(tree).filter(n=>n.type==='select')[2].props.onChange({target:{value:'LINHO MOOREA'}})
 assert.equal(state.tecidoProdutoId,3986);assert.deepEqual(state.componentes,[{produto_id:700,quantidade:3}])
 tree=render();effects.forEach(f=>f());timers.splice(0).forEach(f=>f());await new Promise(setImmediate)
 assert.deepEqual(request.componentes,[{produto_id:700,quantidade:3}]);assert.equal(request.tecido_produto_id,3986)
 console.log('MOOREA aprovado: seleção sem cor preserva ID real; 2,80 × 2,45 chegam ao motor; resultado renderiza consumo/mão de obra; variante BRANCO atualiza ID; componentes livres preservados no payload.')
})().catch(e=>{console.error(e);process.exitCode=1})
