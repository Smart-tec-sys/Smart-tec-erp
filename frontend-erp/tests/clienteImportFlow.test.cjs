const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { pathToFileURL } = require('node:url')
const { registerHooks } = require('node:module')
const file = path.join(__dirname,'../src/components/ClienteImportPanel.tsx')
let compiled
registerHooks({
  resolve(spec,context,next){try{return next(spec,context)}catch(error){if(spec.startsWith('.')&&!path.extname(spec))return next(spec+'.ts',context);throw error}},
  load(url,context,next){return url===pathToFileURL(file).href?{format:'module',source:compiled,shortCircuit:true}:next(url,context)},
})
const nodes=tree=>!tree||typeof tree!=='object'?[]:Array.isArray(tree)?tree.flatMap(nodes):[tree,...nodes(tree.props?.children)]
const text=tree=>tree==null||typeof tree==='boolean'?'':Array.isArray(tree)?tree.map(text).join(' '):typeof tree==='object'?text(tree.props?.children):String(tree)
;(async()=>{
  const {transformWithOxc}=await import('vite')
  let cells=[],slot=0,company=1,apiCalls=[],completed=0,busyEvents=[],deferred=null
  let preview={colunas:['Código','Nome','Documento'],abas:[],aba:null,separador:';',total:2,amostra:[],previa_hash:'snapshot-seguro',inserir:1,complementar:1,ignorados:0,inconsistencias:0,erros:0,
    fontes:{clientes:{total:670},enderecos:{total:541,vinculados:541,sem_vinculo:0},contatos:{total:7,vinculados:7,sem_vinculo:0}},
    ocorrencias:[],
    linhas:[{linha:2,codigo_cliente:'GC-1',dados:{nome:'Fátima Zanetti',email:'Fatima@Example.test',logradouro:'Rua das Flores'},status:'complementar',cliente_existente_id:7,campos_complementar:{logradouro:'Rua das Flores'},conflitos:[],motivos:['Documento coincide'],avisos:[]},
      {linha:3,codigo_cliente:'GC-2',dados:{nome:'Novo cliente'},status:'inserir',campos_complementar:{},conflitos:[],motivos:[],avisos:[]}]}
  globalThis.importFlow={
    useState(initial){const index=slot++;if(!(index in cells))cells[index]=typeof initial==='function'?initial():initial;return[cells[index],value=>cells[index]=typeof value==='function'?value(cells[index]):value]},
    useRef(initial){const index=slot++;return cells[index]??(cells[index]={current:initial})},
    getEmpresaId:()=>company,
    async inspectClientImport(file,config){apiCalls.push({action:'inspect',file,config});return{colunas:file.name==='clientes.csv'?['Código','Nome','Documento']:file.name==='enderecos.xlsx'?['Código','Rua','Cidade','UF']:['Código','Contato','Tipo'],abas:file.name.endsWith('.xlsx')?['Dados']:[],aba:file.name.endsWith('.xlsx')?'Dados':null,separador:';',total:file.name==='clientes.csv'?670:file.name==='enderecos.xlsx'?541:7,amostra:[]}},
    async previewClientImport(file,config,related){apiCalls.push({action:'preview',file,config,related});return deferred?deferred:preview},
    async confirmClientImport(file,config,hash,related){apiCalls.push({action:'confirm',file,config,hash,related});return{concluido:true,mensagem:'Lote confirmado',total:2,inseridos:1,complementados:1,ignorados:0,inconsistencias:0,erros:0,nao_importados:0,linhas:preview.linhas.map(row=>({...row,status:row.status==='complementar'?'complementado':'inserido'}))}},
  }
  const source=fs.readFileSync(file,'utf8')
    .replace("import { useRef, useState } from 'react'",'const {useRef,useState}=globalThis.importFlow')
    .replace(/import \{\r?\n[\s\S]*?\} from '\.\.\/services\/clienteImport'/,'const {inspectClientImport,previewClientImport,confirmClientImport}=globalThis.importFlow')
    .replace("import { getEmpresaId } from '../services/auth'",'const {getEmpresaId}=globalThis.importFlow')
    .replace("import './clienteImport.css'",'')
  compiled=(await transformWithOxc(source,file,{jsx:{runtime:'automatic'}})).code
  const {ClienteImportPanel}=await import(pathToFileURL(file))
  let tree
  const render=()=>{slot=0;return tree=ClienteImportPanel({onComplete:async()=>{completed++},onClose(){},onBusyChange:value=>busyEvents.push(value)})}
  const findLabel=(tree,start)=>nodes(tree).find(node=>node.type==='label'&&text(node).trim().startsWith(start))
  function select(start,value,scope=tree){nodes(findLabel(scope,start)).find(node=>node.type==='select').props.onChange({target:{value:String(value)}});render()}
  function check(start,value){const input=nodes(findLabel(tree,start)).find(node=>node.type==='input');input.props.onChange({target:{checked:value}});render()}
  async function click(label){const node=nodes(tree).find(node=>node.type==='button'&&text(node).trim()===label);assert.ok(node,label);assert.ok(!node.props.disabled,label+' habilitado');node.props.onClick();await new Promise(setImmediate);render()}
  function auxiliary(name){return nodes(tree).find(node=>node.type?.name==='RelatedSource'&&node.props.source===name)}
  const clients=new File(['Código;Nome;Documento\nGC-1;Fátima Zanetti;52998224725'],'clientes.csv',{type:'text/csv'})
  const addresses=new File(['xlsx sintético'],'enderecos.xlsx')
  const contacts=new File(['Código;Contato;Tipo\nGC-1;Fatima@Example.test;E-mail'],'contatos.csv')
  render()
  assert.ok(text(tree).includes('sem classificação comercial obrigatória'))
  nodes(tree).find(node=>node.type==='input'&&node.props.type==='file').props.onChange({target:{files:[clients]}});render()
  await click('Ler colunas')
  select('Código do cliente no backup',0)
  select('Nome *',1)
  select('CPF / CNPJ',2)
  for(const [name,file,mapping] of [['enderecos',addresses,{logradouro:1,cidade:2,estado:3}],['contatos',contacts,{contato:1,tipo_contato:2}]]){
    auxiliary(name).props.onFile(file);render()
    auxiliary(name).props.onInspect();await new Promise(setImmediate);render()
    const component=auxiliary(name),view=component.type(component.props)
    assert.ok(text(view).includes(name==='enderecos'?'541':'7'))
    component.props.onConfig({...component.props.config,codigo_cliente:0,mapeamento:mapping});render()
  }
  check('Permitir complementar somente campos vazios',true)
  assert.equal(cells[1].ignorar_inconsistencias,false)
  await click('Gerar prévia sem gravar')
  const request=apiCalls.find(call=>call.action==='preview')
  assert.equal(request.file,clients);assert.equal(request.related.enderecos,addresses);assert.equal(request.related.contatos,contacts)
  assert.equal(request.config.codigo_cliente,0)
  assert.deepEqual(request.config.enderecos.mapeamento,{logradouro:1,cidade:2,estado:3})
  assert.equal(apiCalls.filter(call=>call.action==='confirm').length,0,'prévia não grava')
  assert.ok(text(tree).includes('FÁTIMA ZANETTI'))
  assert.match(text(tree),/541\s+linha\(s\)/)
  assert.match(text(tree),/7 vinculada\(s\)/)
  assert.ok(text(tree).includes('Fatima@Example.test'),'e-mail mantém grafia')
  assert.ok(text(tree).includes('ID ERP:  7')||text(tree).includes('ID ERP: 7'))
  assert.ok(nodes(tree).find(node=>node.type==='button'&&text(node).includes('Confirmar 2')).props.disabled)
  check('Conferi a prévia',true)
  await click('Confirmar 2 cliente(s)')
  assert.equal(completed,1)
  const confirmed=apiCalls.find(call=>call.action==='confirm')
  assert.equal(confirmed.hash,'snapshot-seguro');assert.equal(confirmed.related.contatos,contacts)
  assert.deepEqual(busyEvents.slice(-2),[true,false])
  assert.match(text(tree),/1\s+complementado\(s\)/)

  // Alterações de configuração invalidam a prévia e exigem nova confirmação.
  await click('Gerar prévia sem gravar')
  check('Conferi a prévia',true)
  select('Código do cliente no backup',0)
  assert.ok(!nodes(tree).some(node=>node.type==='button'&&text(node).includes('Confirmar 2')))

  preview={...preview,inconsistencias:1,ocorrencias:['enderecos, linha 7: código sem correspondência no arquivo principal.'],linhas:[...preview.linhas,{linha:4,dados:{nome:'Fátima Zaneti'},status:'revisar',motivos:['Nome semelhante não é correspondência segura.'],avisos:[],conflitos:[]}]}
  await click('Gerar prévia sem gravar')
  assert.ok(nodes(findLabel(tree,'Conferi a prévia')).find(node=>node.type==='input').props.disabled,'revisão bloqueia por padrão')
  assert.ok(text(tree).includes('enderecos, linha 7: código sem correspondência'))
  check('Processar somente as linhas validadas',true)
  await click('Gerar prévia sem gravar')
  assert.ok(!nodes(findLabel(tree,'Conferi a prévia')).find(node=>node.type==='input').props.disabled,'ignorar exige opção explícita')
  assert.ok(text(tree).includes('As linhas inconsistentes serão ignoradas por sua escolha'))

  let resolvePreview
  deferred=new Promise(resolve=>resolvePreview=resolve)
  const previousConfirmCalls=apiCalls.filter(call=>call.action==='confirm').length
  const button=nodes(tree).find(node=>node.type==='button'&&text(node).trim()==='Gerar prévia sem gravar')
  button.props.onClick();company=2;resolvePreview(preview);await new Promise(setImmediate);render()
  assert.ok(nodes(tree).some(node=>node.props?.role==='alert'&&text(node).includes('empresa ativa mudou')))
  assert.equal(apiCalls.filter(call=>call.action==='confirm').length,previousConfirmCalls)
  console.log('Importação frontend aprovada: três arquivos, código de vínculo, complementação explícita, IDs visíveis, revisão/skip, prévia sem gravação, invalidação e troca de tenant.')
})().catch(error=>{console.error(error);process.exitCode=1})
