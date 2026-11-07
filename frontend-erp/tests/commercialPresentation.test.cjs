const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const React = require('react')
const { renderToStaticMarkup } = require('react-dom/server')

const css = fs.readFileSync(path.join(__dirname,'../src/styles.css'),'utf8')
const marker = '/* Apresentação comercial: somente campos explicitamente marcados. */'
const block = css.slice(css.indexOf(marker))
assert.ok(css.includes(marker),'estilo comercial deve existir')
const uppercaseRule = block.match(/([^{}]+)\{\s*text-transform:\s*uppercase;\s*\}/)
assert.ok(uppercaseRule,'classes opt-in devem aplicar uppercase')
const selectors = uppercaseRule[1].replace(/\/\*[\s\S]*?\*\//g,'').split(',').map(value=>value.trim())
assert.deepEqual(selectors,['.commercial-name','.commercial-address','.commercial-title'])
for (const protectedSelector of ['input[type="email"]','input[type="url"]','input[type="password"]','textarea','pre','code','a[href^="mailto:"]','a[href^="http"]','.commercial-literal']) {
  assert.ok(block.includes(protectedSelector),`${protectedSelector} precisa preservar grafia`)
}
assert.match(block,/text-transform:\s*none;/)
assert.ok(!/!important/.test(block),'opt-in não deve impor estilo a outros módulos')

const original = Object.freeze({
  name:'João da Silva',address:'Rua São José, 42 - São Paulo',title:'Novo orçamento',
  email:'Contato.Pessoal@Exemplo.test',url:'https://Exemplo.test/CaseSensitive',
  code:'Abc-xYz-42',password:'SeNhA-AbC',notes:'Instalar após as 14h; cliente prefere contato por e-mail.',
})
const elements = [
  React.createElement('input',{key:'name',className:'commercial-name',value:original.name,readOnly:true}),
  React.createElement('input',{key:'address',className:'commercial-address',value:original.address,readOnly:true}),
  React.createElement('h1',{key:'title',className:'commercial-title'},original.title),
  React.createElement('input',{key:'email',type:'email',value:original.email,readOnly:true}),
  React.createElement('a',{key:'url',href:original.url},original.url),
  React.createElement('code',{key:'code',className:'commercial-literal'},original.code),
  React.createElement('input',{key:'password',type:'password',value:original.password,readOnly:true}),
  React.createElement('textarea',{key:'notes',value:original.notes,readOnly:true}),
]
const tree = React.createElement('section',null,...elements)
const html = renderToStaticMarkup(tree)
for (const value of Object.values(original)) assert.ok(html.includes(value),`valor serializado preservado: ${value}`)
assert.equal(elements[0].props.value,original.name)
assert.equal(elements[1].props.value,original.address)
assert.equal(elements[2].props.children,original.title)
assert.ok(!html.includes('JOÃO DA SILVA'),'CSS deve alterar aparência, não valor armazenado')
assert.ok(!html.includes('CASE SENSITIVE'),'URL não é texto comercial normalizável')
console.log('Apresentação comercial: classes seletivas e valores originais de nome/endereço/contatos/códigos/senha/observação preservados em SSR.')


// Componentes reais: apresentação não altera props, valores controlados nem callbacks.
const { pathToFileURL } = require('node:url')
const { registerHooks } = require('node:module')
const compiled = new Map()
registerHooks({
  resolve(specifier, context, next) {
    try { return next(specifier,context) } catch (error) {
      if (specifier.startsWith('.') && !path.extname(specifier)) {
        for (const extension of ['.ts','.tsx']) { try { return next(specifier+extension,context) } catch {} }
      }
      throw error
    }
  },
  load(url, context, next) {
    if (compiled.has(url)) return {format:'module',source:compiled.get(url),shortCircuit:true}
    return next(url,context)
  },
})
const walk = tree => !tree || typeof tree !== 'object' ? [] : Array.isArray(tree) ? tree.flatMap(walk) : [tree,...walk(tree.props?.children)]
const contents = tree => tree == null || typeof tree === 'boolean' ? '' : Array.isArray(tree) ? tree.map(contents).join('') : typeof tree === 'object' ? contents(tree.props?.children) : String(tree)
;(async () => {
  const { transformWithOxc } = await import('vite')
  const sourceRoot = path.join(__dirname,'../src')
  const { commercialDisplayText } = await import(pathToFileURL(path.join(sourceRoot,'utils/commercialDisplay.ts')))
  assert.equal(commercialDisplayText('Contato Fatima@Example.test em https://Exemplo.test/CaseSensitive'),
    'CONTATO Fatima@Example.test EM https://Exemplo.test/CaseSensitive')
  const hooks = 'const useEffect=()=>{};const useRef=value=>({current:value});const useState=value=>[typeof value==="function"?value():value,next=>globalThis.presentationWrites.push(next)]'
  globalThis.presentationWrites=[]
  async function compile(relative,change=source=>source) {
    const file=path.join(sourceRoot,relative)
    compiled.set(pathToFileURL(file).href,(await transformWithOxc(change(fs.readFileSync(file,'utf8')),file,{jsx:{runtime:'automatic'}})).code)
    return import(pathToFileURL(file))
  }
  const { ProductCommercialForm }=await compile('components/ProductCommercialForm.tsx',source=>source
    .replace("import { useEffect, useRef, useState } from 'react'",hooks)
    .replace(/^import \{.*\} from '..\/services\/api'$/m,'const createProduct=()=>{throw Error("API inesperada")};const getProductGroups=createProduct,getProductUnits=createProduct,updateProductCommercial=createProduct;'))
  const product=Object.freeze({id:1,nome:'Tubo rtS-100 Natural',codigo_interno:'rtS-100',valor_custo:10,valor_venda:20})
  const productProps={product,catalog:[],onCancel(){},onSaved(){},onBusy(){}}
  let tree=ProductCommercialForm(productProps)
  let name=walk(tree).find(node=>node.type==='input'&&node.props.required&&node.props.autoFocus)
  assert.equal(name.props.value,product.nome)
  assert.equal(name.props.className,undefined,'código embutido impede CSS sobre o campo inteiro')
  name.props.onChange({target:{value:'Novo nome Misturado rtS-100'}})
  assert.equal(globalThis.presentationWrites.at(-1).nome,'Novo nome Misturado rtS-100')
  assert.equal(product.nome,'Tubo rtS-100 Natural')
  tree=ProductCommercialForm({...productProps,product:{...product,nome:'Cortina Natural',codigo_interno:null}})
  name=walk(tree).find(node=>node.type==='input'&&node.props.required&&node.props.autoFocus)
  assert.equal(name.props.className,'commercial-name')
  assert.equal(name.props.value,'Cortina Natural')

  const { BudgetServiceRow }=await compile('components/BudgetServiceRow.tsx',source=>source.replace("import { ZeroNumberInput } from './ZeroNumberInput'",'const ZeroNumberInput=()=>null'))
  const service=Object.freeze({id:1,service:'Instalação rtS-100',details:'Preservar anotação com Case Sensitive.',quantity:1,value:100,discount:0})
  let updated
  tree=BudgetServiceRow({service,onChange:value=>updated=value,onRemove(){}})
  assert.ok(walk(tree).some(node=>node.type==='strong'&&contents(node)==='INSTALAÇÃO rtS-100'))
  const serviceInput=walk(tree).find(node=>node.type==='input'&&node.props.placeholder==='Descrição do serviço')
  assert.equal(serviceInput.props.value,'Instalação rtS-100')
  assert.equal(serviceInput.props.className,undefined)
  serviceInput.props.onChange({target:{value:'Serviço MiSto novo'}})
  assert.equal(updated.service,'Serviço MiSto novo')
  assert.equal(updated.details,service.details)
  const details=walk(tree).find(node=>node.type==='input'&&node.props.value===service.details)
  assert.equal(details.props.className,undefined,'observação permanece texto livre')

  const { EnderecoPrincipalFields }=await compile('components/EnderecoPrincipalFields.tsx')
  const address=Object.freeze({cep:'01001000',logradouro:'Rua João da Silva',numero:'rtS-100',complemento:'Casa de Fundos',bairro:'Centro',cidade:'São Paulo',estado:'sp'})
  let changed
  tree=EnderecoPrincipalFields({valores:address,onChange:(...args)=>changed=args})
  const inputs=walk(tree).filter(node=>node.type==='input')
  const street=inputs.find(node=>node.props.name==='logradouro')
  assert.equal(street.props.className,'commercial-address')
  assert.equal(street.props.value,address.logradouro)
  street.props.onChange({target:{value:'Avenida João MiSto'}})
  assert.deepEqual(changed,['logradouro','Avenida João MiSto'])
  assert.equal(inputs.find(node=>node.props.name==='numero').props.className,undefined,'código em endereço não muda de caixa')
  assert.equal(inputs.find(node=>node.props.name==='cep').props.className,undefined)
  assert.equal(address.logradouro,'Rua João da Silva')

  const { BudgetTable }=await compile('components/BudgetTable.tsx',source=>source
    .replace("import { useMemo, useState } from 'react'",'const useMemo=fn=>fn();const useState=value=>[value,()=>{}]')
    .replace("import { ColumnManager } from './ColumnManager'",'const ColumnManager=({children})=>children')
    .replace("import { RowActionsMenu } from './RowActionsMenu'",'const RowActionsMenu=()=>null'))
  const budget=Object.freeze({id:1,numero:'Orc-Abc',cliente_id:1,cliente_nome:'João da Silva',status:'EM_ABERTO',total_final:100,observacao:'Anotação MiSta com código rtS-100.',itens:[]})
  tree=BudgetTable({budgets:[budget],onNew(){},onOpen(){},onView(){},onDelete(){},onGenerateSale(){},deletingId:null})
  const rendered=renderToStaticMarkup(tree)
  assert.ok(rendered.includes('JOÃO DA SILVA'))
  assert.ok(rendered.includes('Orc-Abc'),'número técnico continua original')
  assert.ok(rendered.includes(budget.observacao),'observação de orçamento continua original')
  assert.equal(budget.cliente_nome,'João da Silva')
  console.log('Componentes reais aprovados: inputs/onChange preservados, nomes comerciais, códigos embutidos, endereços e observações.')
})().catch(error=>{console.error(error);process.exitCode=1})
