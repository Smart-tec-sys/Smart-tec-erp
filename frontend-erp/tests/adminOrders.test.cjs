const assert=require('node:assert/strict')
const fs=require('node:fs')
const path=require('node:path')
const {pathToFileURL}=require('node:url')
const {registerHooks}=require('node:module')
const compiled=new Map()
registerHooks({
 resolve(spec,context,next){try{return next(spec,context)}catch(error){if(spec.startsWith('.')&&!path.extname(spec)){for(const extension of ['.ts','.tsx']){try{return next(spec+extension,context)}catch{}}}throw error}},
 load(url,context,next){if(url.endsWith('.css'))return {format:'module',source:'',shortCircuit:true};if(compiled.has(url))return {format:'module',source:compiled.get(url),shortCircuit:true};return next(url,context)}
})
;(async()=>{
 const {transformWithOxc}=await import('vite')
 for(const file of ['src/utils/adminOrders.ts','src/components/AdminModuleOrderCard.tsx']){
  const filename=path.join(__dirname,'..',file)
  const result=await transformWithOxc(fs.readFileSync(filename,'utf8'),filename,{jsx:{runtime:'automatic'}})
  compiled.set(pathToFileURL(filename).href,result.code)
 }
 const React=require('react')
 const {renderToStaticMarkup}=require('react-dom/server')
 const {orderPresentation}=await import(pathToFileURL(path.join(__dirname,'../src/utils/adminOrders.ts')))
 const {AdminModuleOrderCard}=await import(pathToFileURL(path.join(__dirname,'../src/components/AdminModuleOrderCard.tsx')))
 const statuses=['SOLICITADO','EM_ANALISE','AGUARDANDO_PAGAMENTO','PAGO','ATIVADO','CANCELADO']
 const targets=['EM_ANALISE','AGUARDANDO_PAGAMENTO','PAGO','ATIVADO']
 const labels=['Iniciar análise','Aprovar','Confirmar pagamento','Ativar módulo']
 const fixtures=[]
 const buttons=node=>{if(!node||typeof node!=='object')return [];return [...(node.type==='button'?[node]:[]),...React.Children.toArray(node.props?.children).flatMap(buttons)]}
 statuses.forEach((status,index)=>{
  const action=orderPresentation(status)
  assert.equal(action.primary?.destination,targets[index])
  assert.equal(action.cancel,index<3)
  const calls=[]
  const order={id:index+1,modulo_id:1,modulo_nome:'Clientes',status,periodicidade:'ANUAL',valor:40,data_pedido:'2026-09-29T10:00:00',forma_pagamento:'Banco Inter',responsavel_nome:'Responsável de teste'}
  const props={order,payments:[{id:12,pedido_modulo_id:index+1,status:'PENDENTE'}],busy:false,onChange:(...args)=>calls.push(args)}
  const tree=AdminModuleOrderCard(props)
  const html=renderToStaticMarkup(tree)
  assert.match(html,/Banco Inter/);assert.match(html,/29\/09\/2026/)
  const actions=buttons(tree)
  if(index<4){assert.ok(html.includes(labels[index]));actions[0].props.onClick();assert.deepEqual(calls[0],[index+1,targets[index]])}
  else assert.equal(actions.length,0)
  if(index<3){actions[1].props.onClick();assert.deepEqual(calls[1],[index+1,'CANCELADO'])}
  for(const button of buttons(AdminModuleOrderCard({...props,busy:true}))) assert.equal(button.props.disabled,true)
  if(status==='AGUARDANDO_PAGAMENTO'){
   assert.match(html,/Pagamento pendente vinculado: #12/)
   const without=renderToStaticMarkup(AdminModuleOrderCard({...props,payments:[]}))
   assert.match(without,/Nenhum pagamento pendente/)
   assert.ok(!without.includes('Pagamento pendente vinculado:'))
  }
  if(status==='PAGO')assert.match(html,/Pagamento confirmado/)
  fixtures.push(html)
 })
 assert.equal(orderPresentation('DESCONHECIDO').primary,undefined)
 assert.equal(orderPresentation('DESCONHECIDO').cancel,false)
 const css=fs.readFileSync(path.join(__dirname,'../src/components/adminOrders.css'),'utf8')
 assert.match(css,/@media\(max-width:600px\)/)
 assert.match(css,/flex-direction:column/)
 assert.match(css,/overflow-wrap:anywhere/)
 if(process.env.ADMIN_ORDERS_PREVIEW) fs.writeFileSync(process.env.ADMIN_ORDERS_PREVIEW,`<!doctype html><html lang="pt-BR"><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Validação de Pedidos — fixtures</title><style>body{margin:0;background:#f5f6f8;font-family:Arial,sans-serif;color:#202938}main{max-width:1000px;margin:auto;padding:20px;box-sizing:border-box}section{display:grid;gap:12px}${css}</style><main class="admin-orders"><h2>Pedidos · validação em memória</h2><p>Seis estados, sem conexão com dados reais.</p><div class="admin-order-form"><label>Módulo<select><option>Clientes</option></select></label><label>Periodicidade<select><option>ANUAL</option></select></label><label>Valor<input value="40,00"></label><label>Forma de pagamento<select><option>Banco Inter</option></select></label><label>Observações<textarea></textarea></label><button class="admin-order-primary">Registrar pedido</button></div><section>${fixtures.join('')}</section></main></html>`)
 console.log('Pedidos: seis estados, transições, terminais, cancelamento, busy, pagamento vinculado e regras mobile aprovados.')
})().catch(error=>{console.error(error);process.exitCode=1})
