const assert=require('node:assert/strict')
const {pathToFileURL}=require('node:url')
const path=require('node:path')
;(async()=>{
 const {moduleAction,requestModuleOrder,grantCourtesy}=await import(pathToFileURL(path.join(__dirname,'../src/utils/adminModules.ts')))
 for(const origin of ['PLANO','TRIAL']) for(const status of ['ATIVO','PENDENTE','SUSPENSO']) assert.equal(moduleAction(origin,status).cancel,false)
 for(const origin of ['AVULSO','CORTESIA']) {
  assert.equal(moduleAction(origin,'ATIVO').cancel,true)
  assert.equal(moduleAction(origin,'PENDENTE').cancel,true)
  for(const status of ['SUSPENSO','CANCELADO','EXPIRADO']) assert.equal(moduleAction(origin,status).cancel,false)
 }
 assert.match(moduleAction('PLANO','ATIVO').message,/assinatura/)
 assert.match(moduleAction('TRIAL','ATIVO').message,/trial/)
 const navigation=[]
 requestModuleOrder('12',id=>navigation.push(['select',id]),()=>navigation.push(['tab','pedidos']))
 assert.deepEqual(navigation,[['select','12'],['tab','pedidos']])
 let call
 await grantCourtesy(async(...args)=>{call=args},4,12,'2026-12-31',' Observação ')
 assert.deepEqual(call,[4,12,{origem:'CORTESIA',periodicidade:'CORTESIA',valor:null,data_fim:'2026-12-31',observacoes:'Observação'}])
 await grantCourtesy(async(...args)=>{call=args},4,12,'','')
 assert.equal(call[2].data_fim,null);assert.equal(call[2].observacoes,null)
 console.log('Módulos: AVULSO encaminha ao pedido; cortesia usa payload explícito sem preço; PLANO/TRIAL sem cancelamento isolado; estados históricos preservados.')
})().catch(error=>{console.error(error);process.exitCode=1})
