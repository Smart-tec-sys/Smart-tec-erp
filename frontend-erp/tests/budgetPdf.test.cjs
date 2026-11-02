const assert=require('node:assert/strict')
const fs=require('node:fs')
const path=require('node:path')
const {pathToFileURL}=require('node:url')
const {registerHooks}=require('node:module')
const compiled=new Map()
const calls=[]
let mockBudget,mockCompany,mockClients=[],mockResellers=[],mockSellers=[],mockRepresentatives=[],queryFailure=false,activeCompanyId=1
global.__budgetPdfMocks={
 getBudget:async()=>{calls.push('budget');if(queryFailure)throw new Error('simulated');return mockBudget},
 getClients:async()=>{calls.push('clients');if(queryFailure)throw new Error('simulated');return mockClients},
 getCommercialPartners:async()=>{calls.push('resellers');return mockResellers},
 getFuncionariosCadastro:async()=>{calls.push('sellers');return mockSellers},
 getRepresentatives:async()=>{calls.push('representatives');return mockRepresentatives},
 getAuthMe:async()=>{calls.push('company');if(queryFailure)throw new Error('simulated');return {empresas:[mockCompany]}},
 getEmpresaId:()=>activeCompanyId,
}
registerHooks({
 resolve(spec,context,next){try{return next(spec,context)}catch(error){if(spec.startsWith('.')&&!path.extname(spec)){for(const extension of ['.ts','.tsx']){try{return next(spec+extension,context)}catch{}}}throw error}},
 load(url,context,next){if(url.endsWith('.css'))return {format:'module',source:'',shortCircuit:true};if(compiled.has(url))return {format:'module',source:compiled.get(url),shortCircuit:true};return next(url,context)}
})
;(async()=>{
 const {transformWithOxc}=await import('vite')
 const apiUrl=pathToFileURL(path.join(__dirname,'../src/services/api.ts')).href
 const authUrl=pathToFileURL(path.join(__dirname,'../src/services/auth.ts')).href
 compiled.set(apiUrl,`const m=globalThis.__budgetPdfMocks; export const apiConfig={baseUrl:'https://api.example.invalid'}; export const {getBudget,getClients,getCommercialPartners,getFuncionariosCadastro,getRepresentatives}=m;`)
 compiled.set(authUrl,`const m=globalThis.__budgetPdfMocks; export const {getAuthMe,getEmpresaId}=m;`)
 for(const file of ['src/services/budgetPdfData.ts','src/services/budgetPdf.ts','src/components/budgetPdf/BudgetPdfDocument.tsx','src/components/budgetPdf/budgetPdfStyles.ts']){
  const filename=path.join(__dirname,'..',file)
  compiled.set(pathToFileURL(filename).href,(await transformWithOxc(fs.readFileSync(filename,'utf8'),filename,{jsx:{runtime:'automatic'}})).code)
 }
 const React=require('react'),{renderToStaticMarkup}=require('react-dom/server')
 const {prepareBudgetPdfData,budgetFinancialVisibility,budgetPdfFilename}=await import(pathToFileURL(path.join(__dirname,'../src/services/budgetPdfData.ts')))
 const {generateBudgetPdf,downloadBudgetPdf,loadBudgetPdfContext,prepareSavedBudgetPdf}=await import(pathToFileURL(path.join(__dirname,'../src/services/budgetPdf.ts')))
 const {BudgetPdfDocument}=await import(pathToFileURL(path.join(__dirname,'../src/components/budgetPdf/BudgetPdfDocument.tsx')))

 const item={tipo_item:'PRODUTO',descricao:'Persiana Screen 1% ECO IMPORTADA',material:'Screen sintético',observacao_item:'Sala de estar',largura:2.5,altura:1.7,quantidade:2,unidade:'M²',preco_unitario:321.45,desconto:12.34,subtotal:987.65,cor:'Cinza',dados_tecnicos:{secret:'NAO EXPOR SIMULACAO'}}
 const budget={id:1004,numero:'1004',cliente_id:null,parceiro_id:1,vendedor_id:10,representante_id:3,cliente_final_nome:'Cliente Final Teste',cliente_final_documento:'Documento de teste',cliente_final_telefone:'Telefone de teste',cliente_final_email:'cliente@example.invalid',cliente_final_endereco:'Endereço de teste',criado_em:'2026-10-07T12:00:00',validade:'2026-10-20',total:1234.56,desconto:23.45,total_final:1211.11,valor_parceiro:234.56,percentual_parceiro:19.87,incluir_rt:true,tipo_rt:'PERCENTUAL',percentual_rt:4.56,valor_rt:67.89,incluir_taxa_bancaria:true,taxa_bancaria_percentual:3.21,valor_taxa_bancaria:45.67,total_cliente_final:1559.23,observacao:'Condições comerciais de teste. Instalação mediante agendamento.',observacao_interna:'SEGREDO INTERNO NÃO ENVIAR',itens:[item,{...item,tipo_item:'SERVICO',descricao:'Instalação',observacao_item:'Agendamento prévio',largura:0,altura:0,quantidade:1,unidade:'UN'}]}
 const logo='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aL1sAAAAASUVORK5CYII='
 const context={companyName:'Razão Social Teste',companyTradeName:'Empresa de teste',companyDocument:'Documento sintético da empresa',companyLogo:logo,resellerName:'Revenda Teste',sellerName:'André',representativeName:'Representante Teste'}
 const text=node=>{if(node==null||typeof node==='boolean')return '';if(typeof node==='string'||typeof node==='number')return String(node);if(Array.isArray(node))return node.map(text).join(' ');if(typeof node.type==='function')return text(node.type(node.props));return text(node.props?.children)}
 const frozen=JSON.stringify(budget)
 const customer=prepareBudgetPdfData(budget,'reseller_client',context),serialized=JSON.stringify(customer)
 for(const field of ['valor_parceiro','valor_rt','valor_taxa_bancaria','percentual_parceiro','percentual_rt','taxa_bancaria_percentual','smartTotal','unitPrice','subtotal','discount','representative','seller','base_protegida','dados_tecnicos','observacao_interna'])assert.ok(!serialized.includes(`"${field}":`),field)
 assert.equal(customer.finance.customerTotal,1559.23)
 assert.equal(customer.company,'Empresa de teste');assert.equal(customer.companyDocument,context.companyDocument);assert.equal(customer.companyLogo,logo)
 assert.equal(customer.products[0].material,item.material)
 assert.equal(prepareBudgetPdfData(budget,'reseller_client',{companyName:'Somente razão social'}).company,'Somente razão social')
 assert.equal(prepareBudgetPdfData(budget,'reseller_client').companyLogo,undefined)
 const customerText=text(React.createElement(BudgetPdfDocument,{data:customer}))
 for(const value of ['Total interno','Valor parceiro / revenda','Taxa bancária','1.211,11','234,56','67,89','45,67','321,45','987,65','SEGREDO','NAO EXPOR'])assert.ok(!customerText.includes(value),value)
 assert.doesNotMatch(customerText,/\bRT\b/)
 assert.match(customerText,/1.559,23/);assert.match(customerText,/Sala de estar/);assert.match(customerText,/2,5 x 1,7 m/);assert.match(customerText,/SERVIÇOS/)
 assert.equal(budgetFinancialVisibility('reseller_client').itemPrices,false)
 const internal=prepareBudgetPdfData(budget,'reseller_internal',context),internalText=text(React.createElement(BudgetPdfDocument,{data:internal}))
 for(const label of ['Revenda Teste','André','Representante Teste','Total interno','Valor parceiro / revenda','RT','Taxa bancária','Total cliente final'])assert.ok(internalText.includes(label),label)
 const excluded=text(React.createElement(BudgetPdfDocument,{data:prepareBudgetPdfData({...budget,incluir_rt:false,incluir_taxa_bancaria:false},'reseller_internal')}))
 assert.doesNotMatch(excluded,/\bRT\b/);assert.ok(!excluded.includes('Taxa bancária'))
 const direct={...budget,parceiro_id:null,cliente_id:20,cliente_nome:'Cliente direto teste',itens:[item]}
 const directData=prepareBudgetPdfData(direct,'direct',context),directText=text(React.createElement(BudgetPdfDocument,{data:directData}))
 assert.match(directText,/Cliente direto teste/);assert.match(directText,/Subtotal/);assert.ok(!directText.includes('Taxa bancária'));assert.ok(!directText.includes('SERVIÇOS'))
 assert.match(directText,/Screen sintético/);assert.match(directText,/Nome \/ assinatura/)
 assert.match(directText,/Data: ____ \/ ____ \/ ______/)
 assert.match(internalText,/DOCUMENTO INTERNO - NÃO ENVIAR AO CLIENTE/)
 assert.ok(!internalText.includes('DOCUMENTO INTERNO DA REVENDA'))
 assert.ok(!directText.includes('DOCUMENTO INTERNO - NÃO ENVIAR AO CLIENTE'))
 assert.ok(!customerText.includes('DOCUMENTO INTERNO - NÃO ENVIAR AO CLIENTE'))
 const tables=node=>{
  if(node==null||typeof node!=='object')return []
  if(Array.isArray(node))return node.flatMap(tables)
  if(typeof node.type==='function'&&node.type.name==='ItemTable')return [node]
  return tables(node.props?.children)
 }
 for(const mode of ['direct','reseller_internal','reseller_client']){
  const source={...(mode==='direct'?direct:budget),itens:[item,{...item,tipo_item:'SERVICO',descricao:'Serviço sintético',observacao_item:'Observação do serviço',material:'MATERIAL EXCLUSIVO DO SERVICO',cor:'COR EXCLUSIVA DO SERVICO',largura:9.123,altura:8.456,unidade:'UN'}]}
  const data=prepareBudgetPdfData(source,mode,context)
  const tree=BudgetPdfDocument({data})
  const productTable=tables(tree).find(node=>node.props.items===data.products)
  const serviceTable=tables(tree).find(node=>node.props.items===data.services)
  assert.ok(productTable&&serviceTable)
  const serviceText=text(serviceTable),productText=text(productTable)
  for(const forbidden of ['Material / tecido','Cor:','Medidas','MATERIAL EXCLUSIVO DO SERVICO','COR EXCLUSIVA DO SERVICO','9,123','8,456'])assert.ok(!serviceText.includes(forbidden),`${mode}: ${forbidden}`)
  assert.match(serviceText,/Serviço sintético/);assert.match(serviceText,/Observação do serviço/);assert.match(serviceText,/2\s+UN/)
  assert.match(productText,/Material \/ tecido:\s+Screen sintético/);assert.match(productText,/Cor:\s+Cinza/);assert.match(productText,/2,5 x 1,7 m/)
  if(mode==='reseller_client'){
   for(const forbidden of ['Valor unit.','Desconto','321,45','987,65'])assert.ok(!serviceText.includes(forbidden))
  }else{
   assert.match(serviceText,/321,45/);assert.match(serviceText,/12,34/);assert.match(serviceText,/987,65/)
   const noServiceDiscount=prepareBudgetPdfData({...source,itens:source.itens.map(entry=>({...entry,desconto:0}))},mode,context)
   const withoutDiscount=tables(BudgetPdfDocument({data:noServiceDiscount})).find(node=>node.props.items===noServiceDiscount.services)
   assert.ok(!text(withoutDiscount).includes('Desconto'))
   assert.match(text(withoutDiscount),/321,45/);assert.match(text(withoutDiscount),/987,65/)
  }
 }
 assert.match(directText,/Documento sintético da empresa/);assert.ok(!directText.includes('Ambiente / obs.'))
 const noDiscount={...direct,desconto:0,itens:[{...item,desconto:0}]}
 const noDiscountText=text(React.createElement(BudgetPdfDocument,{data:prepareBudgetPdfData(noDiscount,'direct',context)}))
 assert.ok(!noDiscountText.includes('Desconto'))
 assert.ok(directText.includes('Desconto'))
 const missingData=prepareBudgetPdfData({...direct,itens:[{...item,material:null,cor:null}]},'direct')
 assert.equal(missingData.products[0].material,'');assert.equal(missingData.products[0].color,'')
 for(const mode of ['direct','reseller_internal','reseller_client']){
  const data=prepareBudgetPdfData(mode==='direct'?direct:budget,mode,context)
  assert.ok(!JSON.stringify(data).includes('SEGREDO'));assert.ok(!JSON.stringify(data).includes('NAO EXPOR'))
 }
 assert.throws(()=>prepareBudgetPdfData(budget,'direct'));assert.throws(()=>prepareBudgetPdfData(direct,'reseller_client'))
 assert.equal(prepareBudgetPdfData({...budget,total_cliente_final:undefined},'reseller_client').finance.customerTotal,null)
 assert.equal(budgetPdfFilename('1004','direct'),'Orcamento-1004.pdf');assert.equal(budgetPdfFilename('1004','reseller_internal'),'Orcamento-1004-Revenda-Interno.pdf');assert.equal(budgetPdfFilename('1004','reseller_client'),'Orcamento-1004-Cliente-Final.pdf')
 const samples=[['direct',direct,'direct'],['reseller-internal',budget,'reseller_internal'],['reseller-client',budget,'reseller_client'],['many-items',{...direct,itens:Array.from({length:90},(_,index)=>({...item,descricao:`Item ${index+1} - Persiana comercial`,observacao_item:`Ambiente ${index+1}`}))},'direct'],['long-text',{...direct,observacao:'Condição comercial longa. '.repeat(180),itens:[{...item,descricao:'Descrição comercial extensa e legível. '.repeat(160),observacao_item:'Observação do ambiente. '.repeat(40)}]},'direct']]
 for(const [name,value,mode] of samples){
  const blob=await generateBudgetPdf(value,mode,context)
  assert.equal(blob.type,'application/pdf');assert.ok(blob.size>1000)
  const buffer=Buffer.from(await blob.arrayBuffer());assert.equal(buffer.subarray(0,5).toString(),'%PDF-')
  const raw=buffer.toString('latin1'),pages=(raw.match(/\/Type \/Page\b/g)||[]).length
  assert.ok(pages>=1)
  const boxes=[...raw.matchAll(/\/MediaBox \[0 0 ([\d.]+) ([\d.]+)\]/g)]
  assert.equal(boxes.length,pages)
  for(const box of boxes){assert.ok(Math.abs(Number(box[1])-595.28)<0.01);assert.ok(Math.abs(Number(box[2])-841.89)<0.01)}
  if(['many-items','long-text'].includes(name))assert.ok(pages>1,`${name}: esperado multiplas paginas`)
  console.log(`${name}: ${pages} pagina(s) A4, ${blob.size} bytes`)
  if(process.env.BUDGET_PDF_OUTPUT){fs.mkdirSync(process.env.BUDGET_PDF_OUTPUT,{recursive:true});fs.writeFileSync(path.join(process.env.BUDGET_PDF_OUTPUT,`${name}.pdf`),buffer)}
 }

 mockBudget={...direct,numero:'2001',total_final:700};mockCompany={id:1,nome:'Razão real',nome_fantasia:'Nome fantasia real',documento:'Documento real',logo_url:null}
 mockClients=[{id:20,nome:'Cliente cadastro',documento:'Doc cliente',email:'email@example.invalid'}]
 calls.length=0
 const saved=await prepareSavedBudgetPdf(1004,'direct')
 assert.equal(saved.budget,mockBudget);assert.equal(saved.budget.total_final,700);assert.equal(saved.filename,'Orcamento-2001.pdf')
 assert.equal(calls[0],'budget');assert.deepEqual(calls.slice(1).sort(),['clients','company'])
 const companyContext=await loadBudgetPdfContext(direct,'direct')
 assert.equal(companyContext.companyTradeName,mockCompany.nome_fantasia);assert.equal(companyContext.companyDocument,mockCompany.documento)
 assert.equal(companyContext.companyLogo,undefined);assert.deepEqual(companyContext.warnings,[])
 const companyWithoutOptional={id:1,nome:'Empresa sem opcionais'}
 const completeCompany=mockCompany
 mockCompany=companyWithoutOptional
 const optional=await loadBudgetPdfContext(direct,'direct')
 assert.equal(optional.companyTradeName,undefined);assert.equal(optional.companyDocument,undefined);assert.equal(optional.companyLogo,undefined)
 mockCompany=completeCompany
 const originalFetch=global.fetch,originalBitmap=global.createImageBitmap,logoDocument=global.document
 try{
  mockCompany.logo_url='/media/empresas/empresa-1.png'
  global.fetch=async()=>({ok:false})
  const invalid=await loadBudgetPdfContext(direct,'direct')
  assert.equal(invalid.companyLogo,undefined);assert.equal(invalid.warnings.length,1)
  for(const response of [
   {ok:true,blob:async()=>new Blob(['invalid'],{type:'text/html'})},
   {ok:true,blob:async()=>new Blob([],{type:'image/png'})},
   {ok:true,blob:async()=>new Blob([new Uint8Array(5*1024*1024+1)],{type:'image/png'})},
  ]){
   global.fetch=async()=>response
   assert.equal((await loadBudgetPdfContext(direct,'direct')).warnings.length,1)
  }
  global.fetch=async()=>({ok:true,blob:async()=>new Blob(['png'],{type:'image/png'})})
  let closed=false
  global.createImageBitmap=async()=>({width:10,height:20,close(){closed=true}})
  global.document={createElement:()=>({getContext:()=>({drawImage(){}}),toDataURL:()=>logo})}
  const withLogo=await loadBudgetPdfContext(direct,'direct')
  assert.equal(withLogo.companyLogo,logo);assert.ok(closed);assert.deepEqual(withLogo.warnings,[])
  global.createImageBitmap=async()=>{throw new Error('image decode failed')}
  assert.equal((await loadBudgetPdfContext(direct,'direct')).warnings.length,1)
 }finally{global.fetch=originalFetch;global.createImageBitmap=originalBitmap;global.document=logoDocument;mockCompany.logo_url=null}
 queryFailure=true
 await assert.rejects(loadBudgetPdfContext(direct,'direct'),/carregar os dados/)
 await assert.rejects(prepareSavedBudgetPdf(1004,'direct'),/recarregar o orçamento/)
 queryFailure=false
 mockClients=[]
 await assert.rejects(loadBudgetPdfContext(direct,'direct'),/Cadastro vinculado/)
 mockClients=[{id:20,nome:'Cliente'}];activeCompanyId=99
 await assert.rejects(loadBudgetPdfContext(direct,'direct'),/Empresa ativa/)
 activeCompanyId=1
 mockBudget=budget;mockResellers=[{id:1,nome:'Revenda Teste'}];mockSellers=[{id:10,nome:'André'}];mockRepresentatives=[{id:3,nome:'Representante Teste'}]
 const internalContext=await loadBudgetPdfContext(budget,'reseller_internal')
 assert.equal(internalContext.resellerName,'Revenda Teste');assert.equal(internalContext.sellerName,'André');assert.equal(internalContext.representativeName,'Representante Teste')
 calls.length=0;mockBudget=budget
 await prepareSavedBudgetPdf(1004,'reseller_client')
 assert.deepEqual(calls,['budget','company'])
 const dialog=fs.readFileSync(path.join(__dirname,'../src/components/BudgetPreviewDialog.tsx'),'utf8')
 assert.match(dialog,/await prepareSavedBudgetPdf\(id, mode\)/)
 assert.ok(dialog.indexOf('await prepareSavedBudgetPdf(id, mode)')<dialog.indexOf('downloadBudgetPdf(result.blob'))
 assert.match(dialog,/generating\.current/);assert.match(dialog,/Gerando PDF/)
 delete global.__budgetPdfMocks

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
 console.log('PDF orçamento: identidade/logo/material, desconto condicional, sigilo dos 3 modos, PDFs A4 reais, textos longos/multiplas paginas e recarga antes da exportacao aprovados.')
})().catch(error=>{console.error(error);process.exitCode=1})
