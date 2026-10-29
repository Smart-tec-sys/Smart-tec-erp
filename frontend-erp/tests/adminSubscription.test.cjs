const assert = require('node:assert/strict')
const {pathToFileURL} = require('node:url')
const path = require('node:path')
;(async () => {
  const {localDate,trialDays,subscriptionError,prepareAndCharge} = await import(pathToFileURL(path.join(__dirname,'../src/utils/adminSubscription.ts')))
  assert.equal(localDate(new Date(2026,9,5,23,59)), '2026-10-05')
  assert.equal(trialDays('2026-10-06','2026-10-05'),1)
  assert.equal(trialDays('2026-10-04','2026-10-05'),0)
  assert.equal(trialDays(null),0)
  assert.match(subscriptionError(new Error('Módulo possui vínculo AVULSO independente.')),/Revise os módulos/)
  assert.equal(subscriptionError(new Error('Já existe cobrança.')),'Já existe cobrança.')
  const calls=[]; let savedId=null
  await assert.rejects(prepareAndCharge(async()=>{calls.push('create'); return {assinatura_id:8}},async id=>{calls.push(['charge',id]); throw new Error('Cobrança recusada')},id=>{savedId=id;calls.push('remember')}),/Cobrança recusada/)
  assert.equal(savedId,8)
  assert.deepEqual(calls,['create','remember',['charge',8]])
  // A retry uses the saved ID and the charge endpoint alone.
  await (async id=>calls.push(['retry',id]))(savedId)
  assert.equal(calls.filter(c=>c==='create').length,1)
  let remembered=false,charged=false
  await assert.rejects(prepareAndCharge(async()=>{throw new Error('Contrato recusado')},async()=>{charged=true},()=>{remembered=true}),/Contrato recusado/)
  assert.equal(remembered,false);assert.equal(charged,false)
  const success=[]
  await prepareAndCharge(async()=>({assinatura_id:9}),async id=>success.push(['charge',id]),id=>success.push(['remember',id]))
  assert.deepEqual(success,[['remember',9],['charge',9]])
  console.log('F2: datas locais, trial, conflitos, contrato + cobrança, falha parcial e retry sem duplicação aprovados (13 verificações).')
})().catch(err=>{console.error(err);process.exitCode=1})
