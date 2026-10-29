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
 for(const file of ['src/utils/adminSupport.ts','src/components/AdminSupportCard.tsx']){
  const filename=path.join(__dirname,'..',file)
  compiled.set(pathToFileURL(filename).href,(await transformWithOxc(fs.readFileSync(filename,'utf8'),filename,{jsx:{runtime:'automatic'}})).code)
 }
 const React=require('react'),{renderToStaticMarkup}=require('react-dom/server')
 const {supportStatuses,supportPriorities,visibleSupportActions,supportMatches,supportText}=await import(pathToFileURL(path.join(__dirname,'../src/utils/adminSupport.ts')))
 const {AdminSupportCard}=await import(pathToFileURL(path.join(__dirname,'../src/components/AdminSupportCard.tsx')))


 const html=[]
 const buttons=node=>{if(!node||typeof node!=='object')return [];return [...(node.type==='button'?[node]:[]),...React.Children.toArray(node.props?.children).flatMap(buttons)]}
 for(const status of Object.keys(supportStatuses))for(const prioridade of Object.keys(supportPriorities)){
  const ticket={id:1,codigo:'SUP-000001',empresa_nome:'Empresa cliente teste',titulo:'Dúvida sobre uso do cadastro',status,prioridade,responsavel_nome:'Agente teste',solicitante_nome:'Solicitante teste',criado_em:'2026-10-07T10:00:00',atualizado_em:'2026-10-07T10:15:00',resolucao:['RESOLVIDO','FECHADO'].includes(status)?'Orientação concluída.':null,resolvido_em:'2026-10-07T11:00:00',pagina:'/cadastros',erro_mensagem:'Confira o campo informado.'}
  let called,edited
  const props={ticket,canAttend:true,canClose:true,canLogs:true,busy:false,onAction:(t,s)=>{called=[t,s]},onEdit:t=>{edited=t}}
  const tree=AdminSupportCard(props),markup=renderToStaticMarkup(tree),actions=visibleSupportActions(status,true,true)
  assert.ok(markup.includes(supportStatuses[status]));assert.ok(markup.includes(supportPriorities[prioridade]));assert.match(markup,/Empresa cliente teste/);assert.match(markup,/Agente teste/)
  assert.equal(buttons(tree).length,actions.length+(status==='FECHADO'?0:1))
  actions.forEach((action,index)=>{buttons(tree)[index].props.onClick();assert.deepEqual(called,[ticket,action.status])})
  if(status!=='FECHADO'){buttons(tree).at(-1).props.onClick();assert.equal(edited,ticket)}
  assert.equal(buttons(AdminSupportCard({...props,canAttend:false})).length,0)
  assert.ok(buttons(AdminSupportCard({...props,busy:true})).every(button=>button.props.disabled))
  assert.ok(!renderToStaticMarkup(React.createElement(AdminSupportCard,{...props,canLogs:false})).includes('Dados técnicos'))
  if(['RESOLVIDO','FECHADO'].includes(status))assert.match(markup,/Orientação concluída/)
  html.push(markup)
 }
 assert.equal(visibleSupportActions('EM_CORRECAO',true,false).some(a=>a.status==='RESOLVIDO'),false)
 assert.equal(visibleSupportActions('RESOLVIDO',true,false).length,0)
 assert.equal(supportMatches('EM_ANALISE','andamento'),true);assert.equal(supportMatches('AGUARDANDO_CLIENTE','cliente'),true);assert.equal(supportMatches('FECHADO','resolvidos'),true);assert.equal(supportMatches('EM_CORRECAO','abertos'),false)
 for(const value of ['Authorization: Bearer abc','Traceback test','token=123'])assert.notEqual(supportText(value),value)
 const panel=fs.readFileSync(path.join(__dirname,'../src/components/AdminSupportPanel.tsx'),'utf8')
 assert.match(panel,/Nenhum chamado registrado/);assert.match(panel,/<textarea name="resolucao" required/);assert.match(panel,/setFormError/);assert.match(panel,/inFlight.current/)
 const css=fs.readFileSync(path.join(__dirname,'../src/components/adminSupport.css'),'utf8')
 assert.match(css,/@media\(max-width:600px\)/);assert.match(css,/overflow-wrap:anywhere/)
 console.log('Suporte: 24 combinações de status/prioridade, ações, permissões, resolução, responsável, filtros e dados técnicos aprovados.')
})().catch(error=>{console.error(error);process.exitCode=1})
