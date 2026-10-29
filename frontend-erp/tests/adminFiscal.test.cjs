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
 for(const file of ['src/utils/adminFiscal.ts','src/components/AdminFiscalNoteCard.tsx']){
  const filename=path.join(__dirname,'..',file)
  compiled.set(pathToFileURL(filename).href,(await transformWithOxc(fs.readFileSync(filename,'utf8'),filename,{jsx:{runtime:'automatic'}})).code)
 }
 const React=require('react'),{renderToStaticMarkup}=require('react-dom/server')
 const {fiscalStatus, fiscalDocumentUrl, fiscalErrorText}=await import(pathToFileURL(path.join(__dirname,'../src/utils/adminFiscal.ts')))
 const {AdminFiscalNoteCard}=await import(pathToFileURL(path.join(__dirname,'../src/components/AdminFiscalNoteCard.tsx')))

 const statuses=['PENDENTE','PROCESSANDO','EMITIDA','ERRO','CANCELADA'],html=[]
 const labels=['Preparada para emissão','Em processamento','Emitida','Erro na emissão','Cancelada']
 for(const tipo of ['MODULO_AVULSO','ASSINATURA'])for(const status of statuses){
 const payment={id:1,tipo,pedido_modulo_id:tipo==='MODULO_AVULSO'?2:null,assinatura_id:tipo==='ASSINATURA'?3:null,ciclo_inicio:'2026-10-07',ciclo_fim:'2026-11-07'}
 const company={empresa:{id:2,nome:'Empresa cliente de teste com nome longo'},pedidos_modulos:[{id:2,modulo_nome:'Clientes',periodicidade:'ANUAL'}],pagamentos:[payment],assinatura:{id:3,plano_nome:'Plano de teste',periodicidade:'MENSAL'}}
 const note={id:1,pagamento_id:1,tipo_documento:'NFSE',status,valor_servico:40,valor_desconto:0,valor_total:40,numero:'123',serie:'A',protocolo:'protocolo-123',data_emissao:'2026-10-07',pdf_url:'https://example.com/nota.pdf',xml_url:'https://example.com/nota.xml',erro_codigo:'E001',erro_mensagem:'Confira a inscrição municipal.'}
 const markup=renderToStaticMarkup(React.createElement(AdminFiscalNoteCard,{note,company}))
 assert.match(markup,/Empresa cliente de teste/);assert.ok(markup.includes(labels[statuses.indexOf(status)]));assert.ok(!markup.includes('<button'))
 assert.match(markup,tipo==='MODULO_AVULSO'?/Pedido #2 · Clientes/:/Assinatura #3 · Plano de teste/)
 assert.equal(markup.includes('Abrir PDF'),status==='EMITIDA');assert.equal(markup.includes('Abrir XML'),status==='EMITIDA')
 if(status==='EMITIDA')assert.match(markup,/target="_blank" rel="noopener noreferrer"/)
 if(status==='PENDENTE')assert.match(markup,/ainda não representa uma NFS-e emitida/)
 if(status==='ERRO')assert.match(markup,/Confira a inscrição municipal/)
 if(status==='CANCELADA')assert.match(markup,/protocolo-123/)
 html.push(markup)
 }
 for(const url of ['javascript:alert(1)','data:text/html,test','https://user:password@example.com'])assert.equal(fiscalDocumentUrl(url),null)
 for(const text of ['Traceback (most recent call last)','{"payload":"secret"}','Authorization Bearer abc','token=secret'])assert.ok(!fiscalErrorText(text).includes(text))
 assert.equal(fiscalErrorText(null),null)
 const css=fs.readFileSync(path.join(__dirname,'../src/components/adminFiscal.css'),'utf8')
 assert.match(css,/@media\(max-width:600px\)/)
 if(process.env.ADMIN_FISCAL_PREVIEW)fs.writeFileSync(process.env.ADMIN_FISCAL_PREVIEW,`<!doctype html><html lang="pt-BR"><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0;background:#f5f6f8;font-family:Arial,sans-serif}main{max-width:1000px;box-sizing:border-box;padding:20px;margin:auto}section{display:grid;gap:12px}${css}</style><main class="admin-fiscal"><h2>Notas fiscais · validação em memória</h2><p>Duas origens e cinco status. Sem dados reais.</p><section>${html.join('')}</section></main></html>`)
 console.log('Fiscal: 10 combinações, referências, documentos, históricos e mensagens seguras aprovados.')
})().catch(error=>{console.error(error);process.exitCode=1})
