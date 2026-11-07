const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { pathToFileURL } = require('node:url')
const { registerHooks } = require('node:module')
const compiled = new Map()
registerHooks({
  resolve(spec, context, next) {
    try { return next(spec, context) } catch (error) {
      if (spec.startsWith('.') && !path.extname(spec)) { try { return next(spec + '.ts', context) } catch { return next(spec + '.tsx', context) } }
      throw error
    }
  },
  load(url, context, next) {
    if (compiled.has(url)) return { format:'module', source:compiled.get(url), shortCircuit:true }
    return next(url, context)
  },
})
const root = path.join(__dirname, '../src')
const nodes = tree => !tree || typeof tree !== 'object' ? [] : Array.isArray(tree) ? tree.flatMap(nodes) : [tree, ...nodes(tree.props?.children)]
const text = tree => tree == null || typeof tree === 'boolean' ? '' : Array.isArray(tree) ? tree.map(text).join(' ') : typeof tree === 'object' ? text(tree.props?.children) : String(tree)
;(async () => {
  const { transformWithOxc } = await import('vite')
  async function compile(name, change) {
    const file = path.join(root, name)
    compiled.set(pathToFileURL(file).href, (await transformWithOxc(change(fs.readFileSync(file,'utf8')),file,{jsx:{runtime:'automatic'}})).code)
    return import(pathToFileURL(file))
  }
  const pricing = await import(pathToFileURL(path.join(root,'types/budget.ts')))
  const { emptyProduct, commercialPrice, applySuggestedProductPrice, negotiateProductPrice, restoreSuggestedProductPrice, productLineSubtotal, curtainKey } = pricing
  const { romanaKey } = await import(pathToFileURL(path.join(root,'types/romana.ts')))
  const { romanaTetoKey } = await import(pathToFileURL(path.join(root,'types/romana_teto.ts')))
  const { roloKey } = await import(pathToFileURL(path.join(root,'types/rolo.ts')))
  const { doubleVisionKey } = await import(pathToFileURL(path.join(root,'types/double_vision.ts')))
  const catalog = [{id:10,nome:'Acessório',modelo_tecnico:'ACESSORIO',unidade_venda:'UN',custo_final:100},{id:11,nome:'Romana',modelo_tecnico:'ROMANA',unidade_venda:'M2',custo_final:100}]
  assert.equal(commercialPrice({id:1,nome:'Sem custo',valor_venda:70},'Varejo'),70)
  assert.equal(commercialPrice(catalog[0],'Varejo'),200)
  const base={...emptyProduct(1),productId:10,product:'Acessório',unit:'UN',quantity:2,suggestedPrice:200,price:200}
  const manual=negotiateProductPrice(base,37.1256)
  assert.equal(applySuggestedProductPrice(manual,240).price,37.1256)
  assert.equal(productLineSubtotal({...manual,quantity:3},'Varejo'),111.38)
  assert.equal(restoreSuggestedProductPrice(applySuggestedProductPrice(manual,240),'Varejo').price,240)
  assert.equal(productLineSubtotal({...manual,unit:'ML',width:'1,25'},'Varejo'),92.81)
  assert.equal(productLineSubtotal({...manual,unit:'M2',width:'0,50',height:'0,50'},'Varejo'),111.38)
  for (const [field,kind,key] of [['romana','romanaKind',romanaKey],['romanaTeto','romanaTetoKind',romanaTetoKey],['rolo','roloKind',roloKey],['doubleVision','doubleVisionKind',doubleVisionKey]]) {
    const row={...manual,modelTechnical:'ROMANA',unit:'M2',width:'0,50',height:'0,50',[kind]:'MANUAL'}
    row[field]={key:key(row,'Varejo'),result:{area_faturavel_m2:3,preco_disponivel:true,preco_unitario:200,subtotal:600}}
    assert.equal(productLineSubtotal(row,'Varejo'),111.38,field)
    assert.equal(productLineSubtotal({...row,width:'2,00'},'Varejo'),0,field+' aguarda cálculo atual')
    assert.equal(restoreSuggestedProductPrice(row,'Varejo').price,200)
    assert.equal(restoreSuggestedProductPrice({...row,width:'2,00'},'Varejo').price,37.1256)
  }
  const curtain={...manual,modelTechnical:'CORTINA',curtain:{tecido:'Sintético',fator:2,larguraTecido:3,modeloPrega:'WAVE',possuiForro:false,cabecaCm:10,barraCm:20,barraDupla:false,usaEntretela:false,fixacaoCortina:'RODIZIO',trilhoComCordas:false,sistemaWave:'PREGA_PRONTA',espacamentoBotaoCm:10,aberturaCortina:'CENTRAL',result:{preco_disponivel:true,preco_unitario:200,subtotal:400}}}
  curtain.curtain.simulationKey=curtainKey(curtain,'Varejo')
  assert.equal(productLineSubtotal(curtain,'Varejo'),74.25)

  let query='',changed,confirmations=0,confirmResult=true
  globalThis.window={confirm(){confirmations++;return confirmResult}}
  const {BudgetProductRow}=await compile('components/BudgetProductRow.tsx',source=>source
    .replace("import { useEffect, useMemo, useState } from 'react'",'const useEffect=()=>{};const useMemo=f=>f();const useState=v=>[globalThis.priceQuery??v,()=>{}]')
    .replace("import { CurtainColorField } from './CurtainColorField'",'const CurtainColorField=()=>null')
    .replace(/import \{ ZeroNumberInput, zeroInputValue \} from '[^']+'/,'const ZeroNumberInput=()=>null;const zeroInputValue=v=>v')
    .replace(/import \{ (\w+Simulation) \} from '[^']+'/g,'const $1=()=>null'))
  function rowTree(product=manual){globalThis.priceQuery=query;return BudgetProductRow({product,catalog,commercialType:'Varejo',allowManualPrice:true,onChange:p=>changed=p,onRemove(){},onRomana(){},onRomanaTeto(){},onRolo(){},onDoubleVision(){},onCurtain(){}})}
  let tree=rowTree(curtain)
  const priceInput=nodes(tree).find(n=>n.props?.['aria-label']?.startsWith('Valor unitário'))
  assert.equal(priceInput.props.readOnly,false)
  priceInput.props.onValueChange(90.1234)
  assert.equal(changed.price,90.1234);assert.equal(changed.priceManual,true)
  nodes(rowTree(manual)).find(n=>n.type==='button'&&text(n)==='Restaurar preço sugerido').props.onClick()
  assert.equal(changed.price,200);assert.equal(changed.priceManual,false)
  query='Romana';confirmResult=false;changed=undefined
  let suggestion=nodes(rowTree(manual)).find(n=>n.type==='div'&&n.props.className==='product-suggestions')
  nodes(suggestion).find(n=>n.type==='button').props.onClick()
  assert.equal(changed,undefined);assert.equal(confirmations,1)
  confirmResult=true
  nodes(suggestion).find(n=>n.type==='button').props.onClick()
  assert.equal(changed.productId,11);assert.equal(changed.priceManual,false)

  const {BudgetSummary}=await compile('components/BudgetSummary.tsx',source=>source.replace("import { ZeroNumberInput } from './ZeroNumberInput'",'const ZeroNumberInput=()=>null'))
  const summary=BudgetSummary({products:100,services:0,freight:0,discount:0,onDiscount(){},includeBankFee:false,onIncludeBankFee(){},bankFeePercent:0,onBankFeePercent(){},internalValue:100,partnerValue:0,rtValue:0,bankFeeValue:0,clientTotal:100,onCancel(){},onSave(){},saveLabel:'Salvar alterações',saveError:'Falha ao salvar'})
  assert.ok(nodes(summary).some(n=>n.props?.role==='alert'&&text(n)==='Falha ao salvar'))
  const saveButton=nodes(summary).find(n=>n.props?.className==='primary-button summary-action')
  assert.equal(saveButton.props['aria-describedby'],'budget-save-error')
  assert.ok(text(saveButton).includes('Salvar alterações'))

  // Exercita a página real com hooks controlados e API simulada; sem rede ou banco.
  let cells=[],index=0,pending=[],dirty=false,pageProps,apiCalls=[],savedEvents=[],sourceBudget=null,saveMode='ok',resolveSave,rejectSave
  globalThis.budgetHooks={
    useState(initial){const slot=index++;if(!(slot in cells))cells[slot]=initial;return[cells[slot],value=>{cells[slot]=typeof value==='function'?value(cells[slot]):value;dirty=true}]},
    useRef(initial){const slot=index++;return cells[slot]??(cells[slot]={current:initial})},
    useMemo:fn=>fn(),useCallback:fn=>fn,
    useEffect(fn,deps){const slot=index++;const old=cells[slot];if(!old||deps.some((v,i)=>v!==old[i])){cells[slot]=deps;pending.push(fn)}},
  }
  globalThis.budgetApi={
    getAllProducts:async()=>catalog,getClients:async()=>[{id:1,nome:'Cliente',tipo:'Pessoa Física',documento:'52998224725',email:'cliente@example.test',telefone_celular:'11999998888',cep:'01001000',logradouro:'Rua A',numero:'1',bairro:'Centro',cidade:'São Paulo',estado:'SP'}],
    getBudget:async()=>sourceBudget,getProductGroups:async()=>[],getProductUnits:async()=>['UN','M2'],getCommercialPartners:async()=>[],getRepresentatives:async()=>[],getFuncionariosCadastro:async()=>[],
    async createBudget(payload){return saveApi(null,payload)},async updateBudget(id,payload){return saveApi(id,payload)},
  }
  function saveApi(id,payload){apiCalls.push({id,payload});if(saveMode==='pending')return new Promise((resolve,reject)=>{resolveSave=resolve;rejectSave=reject});return Promise.resolve({...payload,id:id??99,numero:'SINTETICO'})}
  await compile('components/BudgetPaymentSection.tsx',source=>source.replace("import { listFinanceRecords, type FinanceRecord } from '../services/api'",'const listFinanceRecords=async()=>[];type FinanceRecord=any'))
  const {NewBudgetPage}=await compile('pages/NewBudgetPage.tsx',source=>source
    .replace("import { useCallback, useEffect, useMemo, useRef, useState } from 'react'",'const {useCallback,useEffect,useMemo,useRef,useState}=globalThis.budgetHooks')
    .replace(/^import \{.*\} from '..\/services\/api'$/m,'const {createBudget,getAllProducts,getBudget,getClients,updateBudget,createClient,createProduct,getProductGroups,getProductUnits,convertBudgetToOrder,getCommercialPartners,getRepresentatives,getFuncionariosCadastro}=globalThis.budgetApi')
    .replace(/^import \{ (BudgetProductRow|BudgetServiceRow|BudgetSummary|ZeroNumberInput) \} from '[^']+'$/gm,'function $1(){return null}')
    .replace(/^import \{ CommercialRegistrationDialog,.*$/m,"function CommercialRegistrationDialog(){return null};const CREATE_COMMERCIAL_VALUE='__CREATE__'"))
  let page
  function render(){index=0;dirty=false;page=NewBudgetPage(pageProps);return page}
  async function settle(){for(let i=0;i<8;i++){render();const effects=pending.splice(0);effects.forEach(fn=>fn());await new Promise(setImmediate);if(!dirty&&!pending.length)break}return render()}
  async function mount(budget){cells=[];pending=[];sourceBudget=budget;apiCalls=[];savedEvents=[];pageProps={budgetId:budget?.id,onBack(){throw Error('Navegação indevida')},onSaved:(...args)=>savedEvents.push(args)};return settle()}
  const findComponent=name=>nodes(page).find(n=>n.type?.name===name)
  function chooseProfile(value){const section=nodes(page).find(n=>n.props?.title==='Perfil comercial');nodes(section).find(n=>n.type==='select').props.onChange({target:{value}})}
  const existing={id:5,numero:'5',cliente_id:1,perfil_comercial:'VAREJO',status:'EM_ABERTO',desconto:0,itens:[{tipo_item:'PRODUTO',produto_id:10,descricao:'Acessório',unidade:'UN',quantidade:1,largura:0,altura:0,preco_unitario:77.5,preco_unitario_manual:true,desconto:0,subtotal:77.5}]}
  await mount(existing)
  assert.equal(findComponent('BudgetProductRow').props.product.price,77.5)
  assert.equal(findComponent('BudgetSummary').props.saveLabel,'Salvar alterações')
  assert.ok(!nodes(page).some(n=>n.props?.title==='Payload da API'))
  confirmResult=false;chooseProfile('DECORADOR');await settle()
  assert.equal(findComponent('BudgetProductRow').props.product.price,77.5)
  confirmResult=true;chooseProfile('DECORADOR');await settle()
  assert.equal(findComponent('BudgetProductRow').props.product.price,150)
  assert.equal(findComponent('BudgetProductRow').props.product.priceManual,false)
  await mount({...existing,itens:[{...existing.itens[0],preco_unitario_manual:null}]})
  assert.equal(findComponent('BudgetProductRow').props.product.price,77.5,'legado preservado')
  assert.equal(findComponent('BudgetProductRow').props.product.priceManual,true)

  await mount({...existing,itens:[{...existing.itens[0],produto_id:11,modelo_tecnico:'ROMANA',unidade:'M2',largura:.5,altura:.5}]})
  let row=findComponent('BudgetProductRow').props
  row.onRomana(1,{key:romanaKey(row.product,'Varejo'),result:{preco_unitario:200,subtotal:300,preco_disponivel:true,area_faturavel_m2:1.5}})
  await settle();row=findComponent('BudgetProductRow').props
  assert.equal(row.product.price,77.5,'simulação mantém negociação')
  assert.equal(findComponent('BudgetSummary').props.products,116.25)
  const stale={key:romanaKey(row.product,'Varejo'),result:{preco_unitario:999,subtotal:999,preco_disponivel:true,area_faturavel_m2:1.5}}
  row.onChange({...row.product,quantity:2});await settle();row=findComponent('BudgetProductRow').props
  row.onRomana(1,stale);await settle()
  assert.equal(findComponent('BudgetSummary').props.products,0,'resposta antiga é ignorada')
  row=findComponent('BudgetProductRow').props
  row.onRomana(1,{...stale,key:romanaKey(row.product,'Varejo'),result:{...stale.result,area_faturavel_m2:3}});await settle()
  assert.equal(findComponent('BudgetSummary').props.products,232.5)

  await mount(null)
  assert.equal(findComponent('BudgetSummary').props.saveLabel,'Salvar orçamento')
  chooseProfile('VAREJO')
  const clientField=nodes(page).find(n=>n.props?.label==='Cliente')
  nodes(clientField).find(n=>n.type==='select').props.onChange({target:{value:'1'}})
  row=findComponent('BudgetProductRow').props
  row.onChange({...base,quantity:1,price:88,priceManual:true})
  await settle()
  saveMode='pending'
  let attempt=findComponent('BudgetSummary').props.onSave()
  await new Promise(setImmediate)
  assert.equal(apiCalls.length,1);assert.equal(savedEvents.length,0,'aguarda confirmação da API')
  rejectSave(new Error('Falha sintética de rede'));await attempt;await settle()
  assert.equal(savedEvents.length,0)
  assert.equal(findComponent('BudgetProductRow').props.product.price,88)
  assert.equal(findComponent('BudgetSummary').props.saveError,'Falha sintética de rede')
  attempt=findComponent('BudgetSummary').props.onSave();await new Promise(setImmediate)
  assert.equal(savedEvents.length,0)
  resolveSave({id:99,numero:'99',...apiCalls.at(-1).payload});await attempt;await settle()
  assert.deepEqual(savedEvents,[[99,'created']])
  assert.equal(apiCalls.at(-1).payload.itens[0].preco_unitario_manual,true)
  saveMode='ok'

  await mount({...existing,itens:[{...existing.itens[0],preco_unitario:100}],pagamento_modalidade:'PARCELADO',pagamento_numero_parcelas:2,pagamento_intervalo_dias:30,pagamento_primeiro_vencimento:'2026-11-10',pagamento_parcelas:[{numero:1,tipo:'PARCELA',valor:50,vencimento:'2026-11-10',forma_pagamento_id:1},{numero:2,tipo:'PARCELA',valor:50,vencimento:'2026-12-10',forma_pagamento_id:1}]})
  row=findComponent('BudgetProductRow').props
  row.onChange({...row.product,price:80,priceManual:true});await settle()
  await findComponent('BudgetSummary').props.onSave();await settle()
  assert.equal(apiCalls.length,0,'parcelas divergentes bloqueiam envio')
  assert.ok(findComponent('BudgetSummary').props.saveError.includes('parcelas'))
  const payment=findComponent('BudgetPaymentSection').props
  payment.onChange({...payment.value,installments:payment.value.installments.map(i=>({...i,valor:40}))});await settle()
  await findComponent('BudgetSummary').props.onSave();await settle()
  assert.deepEqual(savedEvents,[[5,'updated']])
  assert.equal(apiCalls[0].payload.itens[0].preco_unitario,80)
  console.log('Liberdade comercial: cálculo UN/ML/M² e cinco motores, edição/restauração, catálogo, respostas assíncronas, criação, legado, falha de API e parcelas aprovados.')
})().catch(error=>{console.error(error);process.exitCode=1})
