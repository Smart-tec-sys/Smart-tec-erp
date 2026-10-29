// 4D.11: executa o componente real e seus eventos com hooks simulados em memoria.
// JSX/React reais; sem DOM/navegador, API, autenticacao, rede ou arquivos compilados.
const assert = require('node:assert/strict')
const {test} = require('node:test')
const fs = require('node:fs')
const path = require('node:path')
const {pathToFileURL} = require('node:url')
const {registerHooks} = require('node:module')
const React = require('react')
const {renderToStaticMarkup} = require('react-dom/server')

const networkAttempts = []
function forbidNetwork() { networkAttempts.push(true); throw new Error('Rede proibida no teste 4D.11') }
globalThis.fetch = forbidNetwork
require('node:net').Socket.prototype.connect = forbidNetwork
for (const name of ['node:http','node:https']) {
  const api = require(name); api.request = forbidNetwork; api.get = forbidNetwork
}

const root = path.join(__dirname, '..')
const componentFile = path.join(root, 'src/components/AdminSubscriptionPanel.tsx')
const componentUrl = pathToFileURL(componentFile).href
const serviceUrl = pathToFileURL(path.join(root, 'src/services/admin.ts')).href
const compiled = new Map()
registerHooks({
  resolve(spec, context, next) {
    try { return next(spec, context) }
    catch (error) {
      if (spec.startsWith('.') && !path.extname(spec)) {
        for (const extension of ['.ts','.tsx']) {
          try { return next(spec + extension, context) } catch {}
        }
      }
      throw error
    }
  },
  load(url, context, next) {
    if (url === serviceUrl) return {format:'module',shortCircuit:true,source:
      'export const createAdminSubscription=(...a)=>globalThis.subscriptionApi.create(...a);' +
      'export const createAdminSubscriptionCharge=(...a)=>globalThis.subscriptionApi.charge(...a);' +
      'export const confirmAdminSubscriptionPayment=(...a)=>globalThis.subscriptionApi.confirm(...a);' +
      'export const startAdminTrial=(...a)=>globalThis.subscriptionApi.trial(...a);'}
    if (url.endsWith('.css')) return {format:'module',source:'',shortCircuit:true}
    if (compiled.has(url)) return {format:'module',source:compiled.get(url),shortCircuit:true}
    return next(url, context)
  }
})

let current
globalThis.subscriptionHooks = {
  useState(initial) {
    const host = current, index = host.cursor++
    if (!(index in host.slots)) host.slots[index] = typeof initial === 'function' ? initial() : initial
    return [host.slots[index], value => {
      host.slots[index] = typeof value === 'function' ? value(host.slots[index]) : value
    }]
  },
  useRef(initial) {
    const host = current, index = host.cursor++
    if (!(index in host.slots)) host.slots[index] = {current:initial}
    return host.slots[index]
  },
  useEffect(effect, dependencies) {
    const host = current, index = host.cursor++, previous = host.slots[index]
    if (!previous || dependencies.some((value,i) => !Object.is(value,previous[i]))) {
      host.slots[index] = dependencies
      host.effects.push(effect)
    }
  }
}
const ready = (async () => {
  const {transformWithOxc} = await import('vite')
  const source = fs.readFileSync(componentFile,'utf8')
  const patched = source.replace(
    "import { useEffect, useRef, useState } from 'react'",
    'const {useEffect,useRef,useState}=globalThis.subscriptionHooks',
  )
  assert.notEqual(source,patched,'Somente os hooks do componente sao substituidos no teste.')
  compiled.set(componentUrl,(await transformWithOxc(patched,componentFile,{jsx:{runtime:'automatic'}})).code)
  return (await import(componentUrl)).AdminSubscriptionPanel
})()

function children(node) { return React.Children.toArray(node?.props?.children) }
function walk(node) {
  if (node == null || typeof node !== 'object') return []
  return [node,...children(node).flatMap(walk)]
}
function text(node) {
  if (node == null || typeof node === 'boolean') return ''
  if (typeof node !== 'object') return String(node)
  return children(node).map(text).join('')
}
function freeze(value) {
  if (value && typeof value === 'object') {
    Object.values(value).forEach(freeze); Object.freeze(value)
  }
  return value
}
function savedSubscription(status,periodicidade,overrides={}) {
  return {id:40,plano_id:1,plano_nome:'Plano anterior',status,periodicidade,
    valor:777.77,forma_pagamento_id:1,forma_pagamento_nome:'PIX existente',
    data_inicio_trial:'2026-01-01',data_fim_trial:'2026-01-08',
    data_inicio_assinatura:'2026-01-08',data_vencimento:'2026-02-08',...overrides}
}
async function mount(planPeriod='PERSONALIZADO',subscription=null,payments=[]) {
  const Component = await ready
  const calls = []
  const company = freeze({empresa:{id:7},assinatura:subscription,modulos:[],
    pagamentos:payments,cobrancas_assinatura:payments})
  const before = JSON.stringify(company)
  const props = {
    company, plans:[{id:1,codigo:'P1',nome:'Plano teste',produto:'ERP',
      periodicidade:planPeriod,valor:99.90,dias_trial:0,ativo:true},
      {id:2,codigo:'P2',nome:'Outro plano',produto:'ERP',
      periodicidade:'ANUAL',valor:999.99,dias_trial:0,ativo:true}],
    permissions:['ASSINATURAS_EDITAR','FINANCEIRO_EDITAR'],
    paymentMethods:[{id:1,nome:'PIX teste'}],paymentMethodsError:'',paymentMethodId:'',
    onPaymentMethodChange:id=>{props.paymentMethodId=id},
    onRegisterPaymentMethod:()=>{throw new Error('Cadastro de pagamento nao esperado')},
    onRefresh:async()=>{},
  }
  globalThis.subscriptionApi = {
    create:async(...args)=>{calls.push(['create',...args]);return {assinatura_id:901}},
    charge:async(...args)=>{calls.push(['charge',...args]);return {}},
    confirm:async(...args)=>{calls.push(['confirm',...args]);return {}},
    trial:async(...args)=>{calls.push(['trial',...args]);return {}},
  }
  const host = {cursor:0,slots:[],effects:[]}
  let tree
  function render() {
    host.cursor=0;current=host
    try { tree=Component(props) } finally { current=null }
    host.effects.splice(0).forEach(effect=>effect())
    return tree
  }
  function control(label,type='select') {
    const node=walk(render()).find(node=>node.type==='label' && text(node).startsWith(label))
    assert.ok(node,'Campo ausente: '+label)
    const field=walk(node).find(node=>node.type===type)
    assert.ok(field,'Controle ausente: '+label)
    return field
  }
  function change(label,value,type='select') {
    control(label,type).props.onChange({target:{value}})
    render()
  }
  async function click(label) {
    const button=walk(render()).find(node=>node.type==='button' && text(node)===label)
    assert.ok(button,'Botao ausente: '+label)
    assert.ok(!button.props.disabled,'Botao desabilitado: '+label)
    button.props.onClick()
    await new Promise(resolve=>setImmediate(resolve))
    render()
  }
  render()
  return {calls,props,render,control,change,click,
    html:()=>renderToStaticMarkup(render()),
    unchanged:()=>{assert.equal(JSON.stringify(company),before);assert.deepEqual(networkAttempts,[])},
    complete:cycle=>{change('Plano','1');change('Periodicidade',cycle);
      change('Valor contratado','123,45','input');change('Forma de pagamento','1')},
  }
}

for (const planPeriod of ['MENSAL','ANUAL','PERSONALIZADO']) {
  test('plano '+planPeriod+' exige ciclo explicito e nao importa preco do catalogo',async()=>{
    const ui=await mount(planPeriod)
    ui.change('Plano','1')
    assert.equal(ui.control('Periodicidade').props.value,'')
    assert.equal(ui.control('Valor contratado','input').props.value,'')
    ui.change('Valor contratado','99,90','input');ui.change('Forma de pagamento','1')
    await ui.click('Gerar contrato e cobrança')
    assert.deepEqual(ui.calls,[])
    assert.match(ui.html(),/Selecione a periodicidade mensal ou anual/)
    ui.unchanged()
  })
}
for (const cycle of ['MENSAL','ANUAL']) {
  test('contrato novo envia somente o ciclo '+cycle+' escolhido e o valor informado',async()=>{
    const ui=await mount('PERSONALIZADO')
    ui.complete(cycle)
    await ui.click('Gerar contrato e cobrança')
    const [create,charge]=ui.calls
    assert.equal(create[0],'create');assert.equal(create[1],7)
    assert.equal(create[2].periodicidade,cycle);assert.equal(create[2].valor,123.45)
    assert.equal(charge[0],'charge');assert.equal(charge[1],901)
    assert.equal(ui.calls.length,2)
    ui.unchanged()
  })
}
test('mudar MENSAL/ANUAL e trocar plano limpam preco e exigem nova confirmacao',async()=>{
  const ui=await mount('MENSAL')
  ui.complete('MENSAL')
  ui.change('Periodicidade','ANUAL')
  assert.equal(ui.control('Valor contratado','input').props.value,'')
  await ui.click('Gerar contrato e cobrança')
  assert.deepEqual(ui.calls,[])
  ui.change('Valor contratado','959,04','input')
  ui.change('Periodicidade','MENSAL')
  assert.equal(ui.control('Valor contratado','input').props.value,'')
  ui.change('Valor contratado','99,90','input')
  ui.change('Plano','2')
  assert.equal(ui.control('Periodicidade').props.value,'')
  assert.equal(ui.control('Valor contratado','input').props.value,'')
  ui.unchanged()
})
for (const cycle of ['MENSAL','ANUAL']) {
  test('contrato PENDENTE '+cycle+' preserva termos e gera apenas cobranca existente',async()=>{
    const ui=await mount('PERSONALIZADO',savedSubscription('PENDENTE',cycle))
    assert.equal(ui.control('Periodicidade').props.value,cycle)
    assert.equal(ui.control('Valor contratado','input').props.value,'777.77')
    await ui.click('Gerar cobrança inicial')
    assert.equal(ui.calls.length,1);assert.equal(ui.calls[0][0],'charge');assert.equal(ui.calls[0][1],40)
    assert.match(ui.html(),new RegExp(cycle))
    ui.unchanged()
  })
}
test('assinatura ATIVA conserva exibicao e nao produz requisicao ao renderizar',async()=>{
  const ui=await mount('MENSAL',savedSubscription('ATIVA','ANUAL'))
  assert.match(ui.html(),/ANUAL/);assert.match(ui.html(),/777,77/)
  assert.deepEqual(ui.calls,[])
  ui.unchanged()
})
test('contrato PERSONALIZADO existente continua visivel sem conversao para MENSAL',async()=>{
  const ui=await mount('PERSONALIZADO',savedSubscription('PENDENTE','PERSONALIZADO'))
  assert.match(ui.html(),/PERSONALIZADO/)
  assert.equal(ui.control('Periodicidade').props.value,'')
  assert.deepEqual(ui.calls,[])
  ui.unchanged()
})
test('trial anterior sem contrato exige ciclo e conserva datas ao preparar conversao',async()=>{
  const trial=savedSubscription('TRIAL','MENSAL',{valor:null,forma_pagamento_id:null})
  const ui=await mount('MENSAL',trial)
  assert.equal(ui.control('Periodicidade').props.value,'')
  assert.match(ui.html(),/01\/01\/2026/);assert.match(ui.html(),/08\/01\/2026/)
  ui.complete('ANUAL')
  await ui.click('Preparar contrato e cobrança')
  assert.equal(ui.calls[0][2].trial_id,40)
  assert.equal(ui.calls[0][2].periodicidade,'ANUAL')
  ui.unchanged()
})
test('trial anterior ja preparado preserva ciclo/valor e nao recria contrato',async()=>{
  const ui=await mount('PERSONALIZADO',savedSubscription('TRIAL','ANUAL'))
  assert.equal(ui.control('Periodicidade').props.value,'ANUAL')
  assert.equal(ui.control('Valor contratado','input').props.value,'777.77')
  await ui.click('Gerar cobrança inicial')
  assert.equal(ui.calls.length,1);assert.equal(ui.calls[0][0],'charge');assert.equal(ui.calls[0][1],40)
  ui.unchanged()
})
test('nova contratacao apos CANCELADA nao herda ciclo nem preco anteriores',async()=>{
  const ui=await mount('ANUAL',savedSubscription('CANCELADA','ANUAL'))
  assert.equal(ui.control('Periodicidade').props.value,'')
  assert.equal(ui.control('Valor contratado','input').props.value,'')
  assert.match(ui.html(),/ANUAL/);assert.match(ui.html(),/777,77/)
  assert.deepEqual(ui.calls,[])
  ui.unchanged()
})
