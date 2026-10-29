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
 for(const file of ['src/services/budgetPdfData.ts','src/services/budgetPdf.ts','src/components/budgetPdf/BudgetPdfDocument.tsx','src/components/budgetPdf/budgetPdfStyles.ts']){
  const filename=path.join(__dirname,'..',file)
  compiled.set(pathToFileURL(filename).href,(await transformWithOxc(fs.readFileSync(filename,'utf8'),filename,{jsx:{runtime:'automatic'}})).code)
 }
 const React=require('react'),{renderToStaticMarkup}=require('react-dom/server')
 const {prepareBudgetPdfData,budgetFinancialVisibility,budgetPdfFilename}=await import(pathToFileURL(path.join(__dirname,'../src/services/budgetPdfData.ts')))
 const {generateBudgetPdf,downloadBudgetPdf}=await import(pathToFileURL(path.join(__dirname,'../src/services/budgetPdf.ts')))
 const {BudgetPdfDocument}=await import(pathToFileURL(path.join(__dirname,'../src/components/budgetPdf/BudgetPdfDocument.tsx')))

 const item={tipo_item:'PRODUTO',descricao:'Persiana Screen 1% ECO IMPORTADA',observacao_item:'Sala de estar',largura:2.5,altura:1.7,quantidade:2,unidade:'M²',preco_unitario:321.45,desconto:12.34,subtotal:987.65,cor:'Cinza',dados_tecnicos:{secret:'NAO EXPOR SIMULACAO'}}
 const budget={id:1004,numero:'1004',cliente_id:null,parceiro_id:1,vendedor_id:10,representante_id:3,cliente_final_nome:'Cliente Final Teste',cliente_final_documento:'Documento de teste',cliente_final_telefone:'Telefone de teste',cliente_final_email:'cliente@example.invalid',cliente_final_endereco:'Endereço de teste',criado_em:'2026-10-07T12:00:00',validade:'2026-10-20',total:1234.56,desconto:23.45,total_final:1211.11,valor_parceiro:234.56,percentual_parceiro:19.87,incluir_rt:true,tipo_rt:'PERCENTUAL',percentual_rt:4.56,valor_rt:67.89,incluir_taxa_bancaria:true,taxa_bancaria_percentual:3.21,valor_taxa_bancaria:45.67,total_cliente_final:1559.23,observacao:'Condições comerciais de teste. Instalação mediante agendamento.',observacao_interna:'SEGREDO INTERNO NÃO ENVIAR',itens:[item,{...item,tipo_item:'SERVICO',descricao:'Instalação',observacao_item:'Agendamento prévio',largura:0,altura:0,quantidade:1,unidade:'UN'}]}
 const context={companyName:'Empresa de teste',resellerName:'Revenda Teste',sellerName:'André',representativeName:'Representante Teste'}
 const text=node=>{if(node==null||typeof node==='boolean')return '';if(typeof node==='string'||typeof node==='number')return String(node);if(Array.isArray(node))return node.map(text).join(' ');if(typeof node.type==='function')return text(node.type(node.props));return text(node.props?.children)}
 const frozen=JSON.stringify(budget)
 const customer=prepareBudgetPdfData(budget,'reseller_client',context),serialized=JSON.stringify(customer)
 for(const field of ['valor_parceiro','valor_rt','valor_taxa_bancaria','percentual_parceiro','percentual_rt','taxa_bancaria_percentual','smartTotal','unitPrice','subtotal','discount','representative','seller','base_protegida','dados_tecnicos','observacao_interna'])assert.ok(!serialized.includes(`"${field}":`),field)
 assert.equal(customer.finance.customerTotal,1559.23)
 const customerText=text(React.createElement(BudgetPdfDocument,{data:customer}))
 for(const value of ['Valor Smart-tec','Valor da Revenda','RT Representante','Taxa bancária','1.211,11','234,56','67,89','45,67','321,45','987,65','SEGREDO','NAO EXPOR'])assert.ok(!customerText.includes(value),value)
 assert.match(customerText,/1.559,23/);assert.match(customerText,/Sala de estar/);assert.match(customerText,/2,5 x 1,7 m/);assert.match(customerText,/SERVIÇOS/)
 assert.equal(budgetFinancialVisibility('reseller_client').itemPrices,false)
 const internal=prepareBudgetPdfData(budget,'reseller_internal',context),internalText=text(React.createElement(BudgetPdfDocument,{data:internal}))
 for(const label of ['Revenda Teste','André','Representante Teste','Valor Smart-tec','Valor da Revenda','RT Representante','Taxa bancária','Valor Cliente Final'])assert.ok(internalText.includes(label),label)
 const excluded=text(React.createElement(BudgetPdfDocument,{data:prepareBudgetPdfData({...budget,incluir_rt:false,incluir_taxa_bancaria:false},'reseller_internal')}))
 assert.ok(!excluded.includes('RT Representante'));assert.ok(!excluded.includes('Taxa bancária'))
 const direct={...budget,parceiro_id:null,cliente_id:20,cliente_nome:'Cliente direto teste',itens:[item]}
 const directData=prepareBudgetPdfData(direct,'direct',context),directText=text(React.createElement(BudgetPdfDocument,{data:directData}))
 assert.match(directText,/Cliente direto teste/);assert.match(directText,/Total final/);assert.ok(!directText.includes('Taxa bancária'));assert.ok(!directText.includes('SERVIÇOS'))
 assert.throws(()=>prepareBudgetPdfData(budget,'direct'));assert.throws(()=>prepareBudgetPdfData(direct,'reseller_client'))
 assert.equal(prepareBudgetPdfData({...budget,total_cliente_final:undefined},'reseller_client').finance.customerTotal,null)
 assert.equal(budgetPdfFilename('1004','direct'),'Orcamento-1004.pdf');assert.equal(budgetPdfFilename('1004','reseller_internal'),'Orcamento-1004-Revenda-Interno.pdf');assert.equal(budgetPdfFilename('1004','reseller_client'),'Orcamento-1004-Cliente-Final.pdf')
 const samples=[['direct',direct,'direct'],['reseller-internal',budget,'reseller_internal'],['reseller-client',budget,'reseller_client'],['many-items',{...direct,itens:Array.from({length:90},(_,index)=>({...item,descricao:`Item ${index+1} - Persiana comercial`,observacao_item:`Ambiente ${index+1}`}))},'direct']]
 for(const [name,value,mode] of samples){const blob=await generateBudgetPdf(value,mode,context);assert.equal(blob.type,'application/pdf');assert.ok(blob.size>1000);const buffer=Buffer.from(await blob.arrayBuffer());assert.equal(buffer.subarray(0,5).toString(),'%PDF-');if(process.env.BUDGET_PDF_OUTPUT){fs.mkdirSync(process.env.BUDGET_PDF_OUTPUT,{recursive:true});fs.writeFileSync(path.join(process.env.BUDGET_PDF_OUTPUT,`${name}.pdf`),buffer)}}

 let clicked=false,removed=false,appended=false,revoked=false,revoke
 const originalDocument=global.document,originalTimeout=global.setTimeout,originalCreate=URL.createObjectURL,originalRevoke=URL.revokeObjectURL
 const link={href:'',download:'',click(){clicked=true},remove(){removed=true}}
 try{
  global.document={createElement:()=>link,body:{appendChild(){appended=true}}}
  URL.createObjectURL=()=> 'blob:budget-test';URL.revokeObjectURL=url=>{assert.equal(url,'blob:budget-test');revoked=true}
  global.setTimeout=callback=>{revoke=callback;return 1}
  downloadBudgetPdf(new Blob(['test'],{type:'application/pdf'}),'Orcamento-1004.pdf')
  assert.ok(clicked&&removed&&appended);assert.equal(link.download,'Orcamento-1004.pdf');assert.equal(link.href,'blob:budget-test');assert.equal(revoked,false);revoke();assert.equal(revoked,true)
 }finally{global.document=originalDocument;global.setTimeout=originalTimeout;URL.createObjectURL=originalCreate;URL.revokeObjectURL=originalRevoke}
 assert.equal(JSON.stringify(budget),frozen)
 console.log('PDF orçamento: 3 modos, proteção comercial, flags RT/taxa, Blob real, serviços, medidas, nomes, campos ausentes e 90 itens aprovados.')
})().catch(error=>{console.error(error);process.exitCode=1})
