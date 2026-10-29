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
 for(const file of ['src/utils/adminFinance.ts','src/components/AdminPaymentCard.tsx']){
  const filename=path.join(__dirname,'..',file)
  compiled.set(pathToFileURL(filename).href,(await transformWithOxc(fs.readFileSync(filename,'utf8'),filename,{jsx:{runtime:'automatic'}})).code)
 }
 const React=require('react'),{renderToStaticMarkup}=require('react-dom/server')
 const {financePresentation}=await import(pathToFileURL(path.join(__dirname,'../src/utils/adminFinance.ts')))
 const {AdminPaymentCard}=await import(pathToFileURL(path.join(__dirname,'../src/components/AdminPaymentCard.tsx')))
 const statuses=['PENDENTE','PROCESSANDO','PAGO','ATRASADO','CANCELADO','ESTORNADO'],html=[]
 const buttons=node=>{if(!node||typeof node!=='object')return [];return [...(node.type==='button'?[node]:[]),...React.Children.toArray(node.props?.children).flatMap(buttons)]}
 for(const tipo of ['MODULO_AVULSO','ASSINATURA'])for(const status of statuses){
  const payment={id:1,tipo,status,valor:40,pedido_modulo_id:tipo==='MODULO_AVULSO'?2:null,assinatura_id:tipo==='ASSINATURA'?3:null,ciclo_inicio:'2026-10-07',ciclo_fim:'2026-11-07',vencimento:'2026-10-10',pago_em:status==='PAGO'?'2026-10-09':null,forma_pagamento:'Banco Inter'}
  const company={empresa:{id:2,nome:'Empresa cliente de teste com nome longo'},pedidos_modulos:[{id:2,status:'AGUARDANDO_PAGAMENTO',modulo_nome:'Clientes'}],pagamentos:[payment],assinatura:{id:3,plano_nome:'Plano de teste',periodicidade:'MENSAL'}}
  const expected=['PENDENTE','PROCESSANDO','ATRASADO'].includes(status)
  assert.equal(financePresentation(payment,company.pedidos_modulos,company.pagamentos,true).confirm,expected)
  assert.equal(financePresentation(payment,company.pedidos_modulos,company.pagamentos,false).confirm,false)
  let called
  const props={payment,company,canEdit:true,busy:false,onConfirm:p=>{called=p}}
  const tree=AdminPaymentCard(props),markup=renderToStaticMarkup(tree)
  assert.match(markup,/Empresa cliente de teste/);assert.match(markup,/Banco Inter/);assert.match(markup,/10\/10\/2026/)
  const action=buttons(tree);assert.equal(action.length,expected?1:0)
  if(expected){action[0].props.onClick();assert.equal(called,payment);assert.equal(buttons(AdminPaymentCard({...props,busy:true}))[0].props.disabled,true)}
  if(tipo==='ASSINATURA'){assert.match(markup,/Assinatura #3 · Plano de teste/);assert.match(markup,/07\/10\/2026 → 07\/11\/2026/)}else assert.match(markup,/Pedido #2 · Clientes/)
  assert.equal(markup.includes('Pago em'),status==='PAGO')
  if(status==='ATRASADO')assert.match(markup,/admin-payment-overdue/)
  if(tipo==='MODULO_AVULSO'){
   assert.equal(financePresentation(payment,[{id:2,status:'PAGO'}],[payment],true).confirm,false)
   assert.equal(financePresentation(payment,company.pedidos_modulos,[payment,{...payment,id:9}],true).confirm,false)
  }
  html.push(markup)
 }
 assert.equal(financePresentation({id:1,tipo:'AJUSTE',status:'PENDENTE'},[],[],true).confirm,false)
 const css=fs.readFileSync(path.join(__dirname,'../src/components/adminFinance.css'),'utf8')
 assert.match(css,/@media\(max-width:600px\)/)
 if(process.env.ADMIN_FINANCE_PREVIEW)fs.writeFileSync(process.env.ADMIN_FINANCE_PREVIEW,`<!doctype html><html lang="pt-BR"><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Financeiro Admin · fixtures</title><style>body{margin:0;background:#f5f6f8;font-family:Arial,sans-serif}main{max-width:1000px;box-sizing:border-box;padding:20px;margin:auto}section{display:grid;gap:12px}${css}</style><main class="admin-finance"><h2>Financeiro · validação em memória</h2><p>Duas origens e seis status. Sem dados reais.</p><section>${html.join('')}</section></main></html>`)
 console.log('Financeiro Admin: 12 combinações, referências, ciclos, datas, permissões, ações, terminais e proteção de pagamento antigo aprovados.')
})().catch(error=>{console.error(error);process.exitCode=1})
