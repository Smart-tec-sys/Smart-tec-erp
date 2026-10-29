const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { pathToFileURL } = require('node:url')
const { registerHooks } = require('node:module')
const compiled = new Map()
registerHooks({
 resolve(spec, ctx, next) { try { return next(spec,ctx) } catch(e) { if(spec.startsWith('.')&&!path.extname(spec)) return next(spec+(spec.endsWith('/ColumnManager')?'.tsx':'.ts'),ctx); throw e } },
 load(url,ctx,next) { if(compiled.has(url)) return {format:'module',source:compiled.get(url),shortCircuit:true}; if(url.endsWith('.css')) return {format:'module',source:'',shortCircuit:true}; return next(url,ctx) }
})
;(async()=>{
 const {transformWithOxc}=await import('vite')
 const root=path.join(__dirname,'..')
 let state=[],cursor=0,effects=[],mounted=false
 globalThis.gradeHooks={
  useState(initial){const i=cursor++;if(!(i in state)) state[i]=typeof initial==='function'?initial():initial;return [state[i],v=>{state[i]=typeof v==='function'?v(state[i]):v}]},
  useEffect(fn){if(!mounted)effects.push(fn)}
 }
 const page=path.join(root,'src/pages/GradesVariacoesPage.tsx')
 let src=fs.readFileSync(page,'utf8').replace("import { useEffect, useState, type FormEvent } from 'react'","const {useEffect,useState}=globalThis.gradeHooks; type FormEvent = any")
 compiled.set(pathToFileURL(page).href,(await transformWithOxc(src,page,{jsx:{runtime:'automatic'}})).code)
 const column=path.join(root,'src/components/ColumnManager.tsx')
 compiled.set(pathToFileURL(column).href,'export function ColumnManager(props){ return props.children }')
 const apiFile=path.join(root,'src/services/gradesVariacoes.ts')
 src=fs.readFileSync(apiFile,'utf8').replace("import { apiConfig } from './api'","const apiConfig={baseUrl:'http://test'}").replace("import { getApiAuthHeaders } from './auth'","const getApiAuthHeaders=async()=>({Authorization:'Bearer test'})")
 compiled.set(pathToFileURL(apiFile).href,(await transformWithOxc(src,apiFile)).code)
 const api=await import(pathToFileURL(apiFile))
 const calls=[]
 const seed=fs.readFileSync(path.join(root,'../migrations/20261009_grades_variacoes_up.sql'),'utf8')
 const colors=[...seed.matchAll(/ [(]'([^']+)',([0-9]+)[)]/g)].map((m,i)=>({id:i+1,grade_id:1,valor:m[1],ativo:true,ordem:Number(m[2])}))
 let grades=[{id:1,empresa_id:1,nome:'CORES',descricao:null,ativo:true,ordem:0,quantidade_valores:43}]
 let vals=colors
 let failure=null
 globalThis.fetch=async(url,init)=>{
  calls.push({url,...init}); assert.equal(init.headers.Authorization,'Bearer test')
  if(failure){const msg=failure;failure=null;return {ok:false,status:503,json:async()=>({detail:msg})}}
  const p=url.replace('http://test/grades-variacoes',''),method=init.method
  const data=init.body?JSON.parse(init.body):null
  let result
  if(method==='GET')result=p==='/'?grades:vals
  else if(method==='POST'&&p==='/'){result={id:2,empresa_id:1,quantidade_valores:0,...data};grades=[...grades,result]}
  else if(method==='POST'){result={id:44,grade_id:1,...data};vals=[...vals,result]}
  else if(method==='PATCH'&&p.includes('/valores/')){const id=Number(p.split('/').at(-1));result={...vals.find(v=>v.id===id),...data};vals=vals.map(v=>v.id===id?result:v)}
  else if(method==='PATCH'){const id=Number(p.slice(1));result={...grades.find(g=>g.id===id),...data};grades=grades.map(g=>g.id===id?result:g)}
  else if(method==='DELETE'){if(p.includes('/valores/'))vals=vals.filter(v=>v.id!==Number(p.split('/').at(-1)));else grades=grades.filter(g=>g.id!==Number(p.slice(1)))}
  return {ok:true,status:method==='DELETE'?204:200,json:async()=>result}
 }
 const {GradesVariacoesPage}=await import(pathToFileURL(page))
 const nodes=t=>!t||typeof t!=='object'?[]:Array.isArray(t)?t.flatMap(nodes):[t,...nodes(t.props?.children)]
 const text=t=>t==null?'':Array.isArray(t)?t.map(text).join(''):typeof t==='object'?text(t.props?.children):String(t)
 let tree,back=false
 function render(){cursor=0;tree=GradesVariacoesPage({onBack(){back=true}});if(!mounted){mounted=true;effects.splice(0).forEach(f=>f())}return tree}
 async function flush(){await new Promise(setImmediate);render()}
 function button(name,scope=tree){const b=nodes(scope).find(n=>n.type==='button'&&text(n)===name);assert.ok(b,name);return b}
 function input(label){const node=nodes(tree).find(n=>n.type==='label'&&text(n).startsWith(label));assert.ok(node,label);return nodes(node).find(n=>n.type==='input')}
 async function click(name,scope){button(name,scope).props.onClick();await flush()}
 function row(name){return nodes(tree).find(n=>n.type==='tr'&&text(n).includes(name))}
 render();await flush()
 assert.ok(text(tree).includes('43 valores'));console.log('OK listagem inicial e 43 valores')
 await click('+ Nova grade');input('Nome').props.onChange({target:{value:'TAMANHOS'}});render();nodes(tree).find(n=>n.type==='form').props.onSubmit({preventDefault(){}});await flush()
 assert.ok(text(tree).includes('TAMANHOS'));console.log('OK criar grade')
 await click('Editar',row('TAMANHOS'));input('Ordem').props.onChange({target:{value:'4'}});render();nodes(tree).find(n=>n.type==='form').props.onSubmit({preventDefault(){}});await flush()
 assert.equal(grades.find(g=>g.id===2).ordem,4);console.log('OK editar e ordenar grade')
 await click('Inativar',row('TAMANHOS'));assert.equal(grades.find(g=>g.id===2).ativo,false);await click('Ativar',row('TAMANHOS'));assert.equal(grades.find(g=>g.id===2).ativo,true);console.log('OK ativar/inativar')
 globalThis.window={confirm:()=>false};let before=calls.length;await click('Excluir',row('TAMANHOS'));assert.equal(calls.length,before)
 window.confirm=()=>true;await click('Excluir',row('TAMANHOS'));assert.equal(grades.length,1);console.log('OK confirmação e exclusão')
 await click('CORES');assert.ok(text(tree).includes('MIDNIGHT BLUE'));assert.equal(nodes(tree).filter(n=>n.type==='tr').length,44);console.log('OK abrir valores da grade')
 await click('+ Novo valor');input('Valor').props.onChange({target:{value:'TESTE'}});render();failure='Nome/valor duplicado';nodes(tree).find(n=>n.type==='form').props.onSubmit({preventDefault(){}});await flush()
 assert.equal(input('Valor').props.value,'TESTE');assert.ok(text(tree).includes('Nome/valor duplicado'));console.log('OK falha preserva formulário')
 nodes(tree).find(n=>n.type==='form').props.onSubmit({preventDefault(){}});await flush();assert.ok(vals.some(v=>v.valor==='TESTE'))
 await click('Editar',row('TESTE'));input('Valor').props.onChange({target:{value:'NOVO'}});render();input('Ordem').props.onChange({target:{value:'1'}});render();nodes(tree).find(n=>n.type==='form').props.onSubmit({preventDefault(){}});await flush()
 assert.equal(vals.find(v=>v.id===44).valor,'NOVO');assert.equal(vals.find(v=>v.id===44).ordem,1)
 await click('Inativar',row('NOVO'));assert.equal(vals.find(v=>v.id===44).ativo,false);await click('Ativar',row('NOVO'));await click('Excluir',row('NOVO'));assert.equal(vals.length,43);console.log('OK CRUD e ordem dos valores')
 failure='Grades/Variações aguarda aplicação da migration aprovada.'
 await assert.rejects(api.listGrades(),/aguarda aplicação/);console.log('OK erro migration pendente')
 await click('Voltar para grades'.replace('Voltar','← Voltar'));await click('← Voltar para Configurações');assert.ok(back);console.log('OK retorno Configurações')
 console.log('10 cenários frontend aprovados')
})().catch(e=>{console.error(e);process.exitCode=1})
