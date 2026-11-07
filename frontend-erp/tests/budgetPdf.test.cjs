const assert=require('node:assert/strict')
const fs=require('node:fs')
const path=require('node:path')
const {pathToFileURL}=require('node:url')
const {registerHooks}=require('node:module')
const compiled=new Map()
const calls=[]
let mockBudget,mockCompany,mockClients=[],mockResellers=[],mockSellers=[{id:10,nome:'André'}],mockRepresentatives=[],queryFailure=false,activeCompanyId=1,switchCompanyDuringLoad=false
global.__budgetPdfMocks={
 getBudget:async()=>{calls.push('budget');if(queryFailure)throw new Error('simulated');return mockBudget},
 getClients:async()=>{calls.push('clients');if(queryFailure)throw new Error('simulated');return mockClients},
 getCommercialPartners:async()=>{calls.push('resellers');return mockResellers},
 getFuncionariosCadastro:async()=>{calls.push('sellers');return mockSellers},
 getRepresentatives:async()=>{calls.push('representatives');return mockRepresentatives},
 getAuthMe:async()=>{throw new Error('PDF deve consultar o perfil da empresa ativa, não /auth/me')},
 getCurrentCompany:async()=>{calls.push('company');if(queryFailure)throw new Error('simulated');if(switchCompanyDuringLoad)activeCompanyId=2;return mockCompany},
 getEmpresaId:()=>activeCompanyId,
 getApiAuthHeaders:async()=>({'X-Empresa-ID':String(activeCompanyId)}),
 request:async path=>{assert.equal(path,'/empresa/atual');calls.push('local-company');if(queryFailure)throw new Error('simulated');return mockCompany},
}
registerHooks({
 resolve(spec,context,next){try{return next(spec,context)}catch(error){if(spec.startsWith('.')&&!path.extname(spec)){for(const extension of ['.ts','.tsx']){try{return next(spec+extension,context)}catch{}}}throw error}},
 load(url,context,next){if(url.endsWith('.css'))return {format:'module',source:'',shortCircuit:true};if(compiled.has(url))return {format:'module',source:compiled.get(url),shortCircuit:true};return next(url,context)}
})
;(async()=>{
 const {transformWithOxc}=await import('vite')
 const apiUrl=pathToFileURL(path.join(__dirname,'../src/services/api.ts')).href
 const authUrl=pathToFileURL(path.join(__dirname,'../src/services/auth.ts')).href
 compiled.set(apiUrl,`const m=globalThis.__budgetPdfMocks; export const apiConfig={baseUrl:'https://api.example.invalid'}; export const {getBudget,getClients,getCommercialPartners,getFuncionariosCadastro,getRepresentatives,request,getCurrentCompany}=m;`)
 compiled.set(authUrl,`const m=globalThis.__budgetPdfMocks; export const {getAuthMe,getEmpresaId,getApiAuthHeaders}=m; export let authEnabled=true; export function setAuthEnabled(value){authEnabled=value}`)
 for(const file of ['src/services/budgetPdfVisibility.ts','src/services/budgetPdfData.ts','src/services/budgetPdf.ts','src/components/budgetPdf/BudgetPdfDocument.tsx','src/components/budgetPdf/budgetPdfStyles.ts']){
  const filename=path.join(__dirname,'..',file)
  compiled.set(pathToFileURL(filename).href,(await transformWithOxc(fs.readFileSync(filename,'utf8'),filename,{jsx:{runtime:'automatic'}})).code)
 }
 const React=require('react'),{renderToStaticMarkup}=require('react-dom/server')
 const {prepareBudgetPdfData,budgetFinancialVisibility,budgetPdfFilename}=await import(pathToFileURL(path.join(__dirname,'../src/services/budgetPdfData.ts')))
 const {finalItemPrices}=await import(pathToFileURL(path.join(__dirname,'../src/services/budgetPdfVisibility.ts')))
 const {generateBudgetPdf,downloadBudgetPdf,loadBudgetPdfContext,prepareSavedBudgetPdf}=await import(pathToFileURL(path.join(__dirname,'../src/services/budgetPdf.ts')))
 const {BudgetPdfDocument}=await import(pathToFileURL(path.join(__dirname,'../src/components/budgetPdf/BudgetPdfDocument.tsx')))

 const item={tipo_item:'PRODUTO',descricao:'Persiana Screen 1% ECO IMPORTADA',material:'Screen sintético',observacao_item:'Sala de estar',largura:2.5,altura:1.7,quantidade:2,unidade:'M²',preco_unitario:321.45,desconto:12.34,subtotal:987.65,cor:'Cinza',dados_tecnicos:{secret:'NAO EXPOR SIMULACAO'}}
 const budget={id:1004,numero:'1004',cliente_id:null,parceiro_id:1,vendedor_id:10,representante_id:3,cliente_final_nome:'Cliente Final Teste',cliente_final_documento:'Documento de teste',cliente_final_telefone:'Telefone de teste',cliente_final_email:'cliente@example.invalid',cliente_final_endereco:'Endereço de teste',criado_em:'2026-10-07T12:00:00',validade:'2026-10-20',total:1234.56,desconto:23.45,total_final:1211.11,valor_parceiro:234.56,percentual_parceiro:19.87,incluir_rt:true,tipo_rt:'PERCENTUAL',percentual_rt:4.56,valor_rt:67.89,incluir_taxa_bancaria:true,taxa_bancaria_percentual:3.21,valor_taxa_bancaria:45.67,total_cliente_final:1559.23,observacao:'Condições comerciais de teste. Instalação mediante agendamento.',observacao_interna:'SEGREDO INTERNO NÃO ENVIAR',itens:[item,{...item,tipo_item:'SERVICO',descricao:'Instalação',observacao_item:'Agendamento prévio',largura:0,altura:0,quantidade:1,unidade:'UN'}]}
 const logo='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aL1sAAAAASUVORK5CYII='
 const context={companyName:'Razão Social Teste',companyTradeName:'Empresa de teste',companyDocument:'Documento sintético da empresa',companyLogo:logo,companyAddress:'Rua Sintética, 123, Centro, Cidade Teste, SP, 01000-000',companyPhones:['(11) 3333-4444','(11) 99999-8888'],companyEmail:'vendas@example.invalid',companySite:'https://example.invalid',resellerName:'Revenda Teste',sellerName:'André',representativeName:'Representante Teste'}
 const text=node=>{if(node==null||typeof node==='boolean')return '';if(typeof node==='string'||typeof node==='number')return String(node);if(Array.isArray(node))return node.map(text).join(' ');if(typeof node.type==='function')return text(node.type(node.props));return text(node.props?.children)}
 const frozen=JSON.stringify(budget)
 const customer=prepareBudgetPdfData(budget,'reseller_client',context),serialized=JSON.stringify(customer)
 for(const field of ['valor_parceiro','valor_rt','valor_taxa_bancaria','percentual_parceiro','percentual_rt','taxa_bancaria_percentual','smartTotal','representative','seller','base_protegida','dados_tecnicos','observacao_interna','internalNotes','technicalNotes'])assert.ok(!serialized.includes(`"${field}":`),field)
 assert.equal(customer.finance.customerTotal,1559.23)
 assert.equal(customer.company,'Empresa de teste');assert.equal(customer.companyDocument,context.companyDocument);assert.equal(customer.companyLogo,logo)
 assert.equal(customer.products[0].material,item.material)
 assert.equal(customer.companyLegalName,'Razão Social Teste')
 assert.equal(customer.companyAddress,context.companyAddress)
 assert.deepEqual(customer.companyPhones,context.companyPhones)
 assert.equal(prepareBudgetPdfData(budget,'reseller_client').company,'')
 assert.equal(prepareBudgetPdfData(budget,'reseller_client').companyLegalName,'')
 assert.equal(prepareBudgetPdfData(budget,'reseller_client',{companyName:'Somente razão social'}).company,'Somente razão social')
 assert.equal(prepareBudgetPdfData(budget,'reseller_client').companyLogo,undefined)
 const customerText=text(React.createElement(BudgetPdfDocument,{data:customer}))
 for(const value of ['Valor-base Smart-tec','Acréscimo parceiro / revenda','Taxa bancária','Tabela comercial:','1.211,11','234,56','67,89','45,67','321,45','987,65','SEGREDO','NAO EXPOR'])assert.ok(!customerText.includes(value),value)
 assert.doesNotMatch(customerText,/\bRT\b/)
 for(const expected of ['Razão Social Teste',context.companyAddress,...context.companyPhones,context.companyEmail,context.companySite,'Vendedor: André'])assert.ok(customerText.replace(/\s+/g,' ').includes(expected),expected)
 const headerTree=BudgetPdfDocument({data:customer}).props.children.props.children[0]
 assert.equal(headerTree.props.children.length,3)
 assert.equal(headerTree.props.children[0].props.children.type,'IMAGE')
 assert.ok(text(headerTree.props.children[1]).includes('Razão Social Teste'))
 assert.ok(text(headerTree.props.children[2]).replace(/\s+/g,' ').includes('Vendedor: André'))
 const noOptional=prepareBudgetPdfData(budget,'reseller_client',{companyName:'Empresa sem dados opcionais'})
 assert.equal(noOptional.companyDocument,'');assert.equal(noOptional.companyAddress,'');assert.deepEqual(noOptional.companyPhones,[])
 assert.equal(noOptional.companyEmail,'');assert.equal(noOptional.companySite,'');assert.equal(noOptional.companySeller,'')
 assert.match(customerText,/1.559,23/);assert.match(customerText,/Sala de estar/);assert.match(customerText,/2,5 x 1,7 m/);assert.match(customerText,/SERVIÇOS/)
 assert.equal(budgetFinancialVisibility('reseller_client').itemPrices,true)
 assert.equal(customer.products[0].subtotal+customer.services[0].subtotal,1559.23)
 assert.ok(customer.warnings.some(warning=>warning.includes('Observações livres')))
 const internal=prepareBudgetPdfData(budget,'reseller_internal',context),internalText=text(React.createElement(BudgetPdfDocument,{data:internal}))
 for(const label of ['Revenda Teste','André','Representante Teste','Valor-base Smart-tec','Acréscimo parceiro / revenda','RT','Taxa bancária','Total cliente final','SEGREDO INTERNO'])assert.ok(internalText.includes(label),label)
 const excluded=text(React.createElement(BudgetPdfDocument,{data:prepareBudgetPdfData({...budget,incluir_rt:false,incluir_taxa_bancaria:false},'reseller_internal')}))
 assert.doesNotMatch(excluded,/\bRT\b/);assert.ok(!excluded.includes('Taxa bancária'))
 const corrected={...budget,total:2854.21,total_final:2854.21,percentual_parceiro:50,valor_parceiro:1427.11,
  base_protegida:4281.32,total_cliente_final:4281.32,incluir_rt:false,incluir_taxa_bancaria:false,
  observacao:'Instrucao de fabricacao: fator 2,5, barra dupla 15 cm, entretela TNT.\nPRAZO DE ENTREGA: 12 dias uteis a partir da aprovacao do orcamento, confirmacao das medidas e confirmacao do pagamento inicial.\nGARANTIA: 2 anos contra defeitos de fabricacao.\n\nCONDICOES DE PAGAMENTO (alternativas, nao cumulativas):\nValor comercial: R$ 4.281,32.\nA vista via Pix: 5% de desconto (R$ 214,07); total R$ 4.067,25.\nEntrada e saldo na instalacao: 5% de desconto; total R$ 4.067,25; entrada de R$ 2.033,63 e saldo na instalacao de R$ 2.033,62.\nCartao ou link de pagamento em ate 3x: total R$ 4.589,58. Em 3x: R$ 1.529,86 + R$ 1.529,86 + R$ 1.529,86.',
  observacao_interna:'Costureira, rodizios, margem, lucro e SEGREDO FABRICA.\nBase Smart-tec R$ 2.854,21. Acrescimo Lidia 50% = R$ 1.427,11. Acrescimo cartao 7,2% = R$ 308,26, nao lucro.\nPix / entrada e saldo: desconto proporcional de 5% = R$ 214,07. Cliente paga R$ 4.067,25; Smart-tec recebe R$ 2.711,50; parceira recebe R$ 1.355,75.'}
 const correctedClient=prepareBudgetPdfData(corrected,'reseller_client',context)
 const correctedClientText=text(React.createElement(BudgetPdfDocument,{data:correctedClient}))
 for(const forbidden of ['50%','7,2%','1.427,11','2.854,21','308,26','2.711,50','1.355,75','Lidia','Smart-tec','Base Smart-tec','Tabela comercial:','internalNotes','resellerPercent']){
  assert.ok(!correctedClientText.includes(forbidden),forbidden)
  assert.ok(!JSON.stringify(correctedClient).includes(forbidden),forbidden)
 }
 for(const expected of ['4.281,32','4.067,25','4.589,58','1.529,86','2.033,63','2.033,62','5%','12 dias úteis','2 anos'])assert.ok(correctedClientText.includes(expected),expected)
 const correctedInternalText=text(React.createElement(BudgetPdfDocument,{data:prepareBudgetPdfData(corrected,'reseller_internal',context)}))
 for(const expected of ['50%','7,2%','1.427,11','2.854,21','308,26','2.711,50','1.355,75','nao lucro'])assert.ok(correctedInternalText.includes(expected),expected)
 const reseller=prepareBudgetPdfData(corrected,'reseller_commercial',context)
 const resellerText=text(React.createElement(BudgetPdfDocument,{data:reseller}))
 for(const expected of ['Revenda Teste','50%','2.854,21','1.427,11','4.281,32','2.711,50','1.355,75','4.589,58','308,26'])assert.ok(resellerText.includes(expected),expected)
 for(const mode of ['reseller_client','reseller_commercial']){
  const projection=prepareBudgetPdfData(corrected,mode,context)
  const rendered=text(React.createElement(BudgetPdfDocument,{data:projection}))
  for(const forbidden of ['Costureira','rodizios','margem','lucro','SEGREDO FABRICA','fator 2,5','barra dupla','entretela','Instrucao de fabricacao','internalNotes','technicalNotes']){
   assert.ok(!rendered.includes(forbidden),`${mode}: ${forbidden}`)
   assert.ok(!JSON.stringify(projection).includes(forbidden),`${mode} DTO: ${forbidden}`)
  }
 }
 const unsafeItem={...item,observacao_item:'Costureira R$ 140,00; margem privada'}
 for(const mode of ['reseller_client','reseller_commercial']){
  const projection=prepareBudgetPdfData({...corrected,itens:[unsafeItem]},mode,context)
  assert.equal(projection.products[0].observation,'')
  assert.ok(projection.warnings.some(warning=>warning.includes('ambiente')))
  assert.throws(()=>prepareBudgetPdfData({...corrected,observacao:corrected.observacao.replace('4.281,32','4.281,33')},mode,context),/divergentes/)
  assert.throws(()=>prepareBudgetPdfData({...corrected,observacao:corrected.observacao+'\nSEGREDO'},mode,context),/estrutura/)
  assert.throws(()=>prepareBudgetPdfData({...corrected,itens:[{...item,quantidade:0}]},mode,context),/insuficientes/)
 }
 assert.throws(()=>prepareBudgetPdfData({...corrected,observacao_interna:corrected.observacao_interna.replace('2.711,50','2.711,51')},'reseller_commercial',context),/Repasses/)
 assert.deepEqual(finalItemPrices({...corrected,total_cliente_final:4281.32,itens:[1111.97,809.66,553.23,379.35].map(subtotal=>({...item,quantidade:1,subtotal}))}),[1667.96,1214.49,829.85,569.02])
 for(const [subtotals,total] of [[[1,1,1],1],[[0,5,0],7.01],[[0.01,0.01],0.01],[[10.01,2.13,8.77],0],[[0.01,9999.99],12345.67]]){
  const prices=finalItemPrices({...corrected,total_cliente_final:total,itens:subtotals.map(subtotal=>({...item,subtotal}))})
  assert.equal(prices.reduce((sum,price)=>sum+Math.round(price*100),0),Math.round(total*100))
  assert.ok(prices.every(price=>price>=0))
 }
 const direct={...budget,parceiro_id:null,cliente_id:20,cliente_nome:'Cliente direto teste',itens:[item]}
 const directData=prepareBudgetPdfData(direct,'direct',context),directText=text(React.createElement(BudgetPdfDocument,{data:directData}))
 for(const [perfil,label] of [['CONSUMIDOR_FINAL','Consumidor Final'],['VAREJO','Varejo'],['DECORADOR','Decorador']]){
  const data=prepareBudgetPdfData({...direct,perfil_comercial:perfil},'direct',context)
  assert.equal(data.commercialTable,label)
  assert.ok(text(React.createElement(BudgetPdfDocument,{data})).replace(/\s+/g,' ').includes(`Tabela comercial: ${label}`))
 }
 assert.equal(prepareBudgetPdfData(direct,'direct',context).commercialTable,'Não informada')
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
  assert.match(serviceText,/Serviço sintético/);assert.equal(serviceText.includes('Observação do serviço'),mode!=='reseller_client');assert.match(serviceText,/2\s+UN/)
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
 const legitimateObservation='Instalação mediante agendamento. Pagamento via Pix. Garantia de dois anos.'
 const legitimate=prepareBudgetPdfData({...direct,observacao:legitimateObservation},'direct',context)
 assert.ok(legitimate.notes.includes(legitimateObservation))
 for(const note of ['Custos industriais: R$ 350,00','Comissão do vendedor: 5%','Margem de lucro: 30%','Taxa bancária: 3%','CUSTO_TOTAL=200','RT: R$ 40,00']){
  assert.throws(()=>prepareBudgetPdfData({...direct,observacao:note},'direct',context),/composição financeira interna/)
  assert.throws(()=>prepareBudgetPdfData({...direct,itens:[{...item,observacao_item:note}]},'direct',context),/composição financeira interna/)
 }
 const cnpjData=prepareBudgetPdfData(direct,'direct',{...context,companyDocument:'12.345.678/0001-95'})
 assert.match(text(BudgetPdfDocument({data:cnpjData})),/CNPJ\s*:\s*12\.345\.678\/0001-95/)
 assert.match(directText,/Documento sintético da empresa/);assert.ok(!directText.includes('Ambiente / obs.'))
 const noDiscount={...direct,desconto:0,itens:[{...item,desconto:0}]}
 const noDiscountText=text(React.createElement(BudgetPdfDocument,{data:prepareBudgetPdfData(noDiscount,'direct',context)}))
 assert.ok(!noDiscountText.includes('Desconto'))
 assert.ok(directText.includes('Desconto'))
 const missingData=prepareBudgetPdfData({...direct,itens:[{...item,material:null,cor:null}]},'direct')
 assert.equal(missingData.products[0].material,'');assert.equal(missingData.products[0].color,'')
 for(const mode of ['direct','reseller_internal','reseller_client']){
  const data=prepareBudgetPdfData(mode==='direct'?direct:budget,mode,context)
  assert.equal(JSON.stringify(data).includes('SEGREDO'),mode==='reseller_internal');assert.ok(!JSON.stringify(data).includes('NAO EXPOR'))
 }
 assert.throws(()=>prepareBudgetPdfData(budget,'direct'));assert.throws(()=>prepareBudgetPdfData(direct,'reseller_client'))
 assert.throws(()=>prepareBudgetPdfData({...budget,total_cliente_final:undefined},'reseller_client'),/insuficientes/)
 assert.equal(budgetPdfFilename('1004','direct'),'Orcamento-1004.pdf');assert.equal(budgetPdfFilename('1004','reseller_internal'),'Orcamento-1004-Interno-Smart-tec.pdf');assert.equal(budgetPdfFilename('1004','reseller_commercial'),'Orcamento-1004-Revenda.pdf');assert.equal(budgetPdfFilename('1004','reseller_client'),'Orcamento-1004-Cliente-Final.pdf')
 const samples=[['direct',direct,'direct'],['reseller-internal',budget,'reseller_internal'],['reseller-client',budget,'reseller_client'],['corrected-reseller-internal',corrected,'reseller_internal'],['corrected-reseller-client',corrected,'reseller_client'],['corrected-reseller-commercial',corrected,'reseller_commercial'],['many-items',{...direct,itens:Array.from({length:90},(_,index)=>({...item,descricao:`Item ${index+1} - Persiana comercial`,observacao_item:`Ambiente ${index+1}`}))},'direct'],['long-text',{...direct,observacao:'Condição comercial longa. '.repeat(180),itens:[{...item,descricao:'Descrição comercial extensa e legível. '.repeat(160),observacao_item:'Observação do ambiente. '.repeat(40)}]},'direct']]
 for(const [name,value,mode] of samples){
  const sampleContext=name==='long-text'?{...context,companyName:'Empresa Sintética de Persianas e Cortinas Sob Medida Ltda',companyAddress:'Avenida Sintética de Testes de Layout, 12345, Sala 123, Bairro Industrial, Cidade de Nome Extenso, SP, 01000-000',companyEmail:'atendimento.comercial@example.invalid',companySite:'https://empresa-sintetica.example.invalid'}:name==='many-items'?{companyName:'Empresa sem opcionais'}:context
  const blob=await generateBudgetPdf(value,mode,sampleContext)
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
 if(process.env.CURTAIN_PDF_FIXTURE_OUTPUT){
  for(const [profile,price,total,label] of [['DECORADOR',259.5,519,'Decorador'],['VAREJO',346,692,'Varejo'],['CONSUMIDOR_FINAL',432.5,865,'Consumidor Final']]){
   const fixture=JSON.parse(fs.readFileSync(path.join(process.env.CURTAIN_PDF_FIXTURE_OUTPUT,`cortina-${profile}.json`),'utf8'))
   assert.equal(fixture.budget.perfil_comercial,profile)
   assert.equal(fixture.budget.total_final,total)
   assert.equal(fixture.budget.itens[0].preco_unitario,price)
   const data=prepareBudgetPdfData(fixture.budget,'direct',fixture.context)
   const rendered=text(React.createElement(BudgetPdfDocument,{data})).replace(/\s+/g,' ')
   for(const expected of ['Tabela comercial: '+label,'Cortina Wave','2 x 2 m','Branco','Sala','NAO COMERCIAL'])assert.ok(rendered.includes(expected),expected)
   assert.ok(!rendered.includes('CUSTOS INTERNOS'))
   const blob=await generateBudgetPdf(fixture.budget,'direct',fixture.context)
   const buffer=Buffer.from(await blob.arrayBuffer())
   assert.equal(buffer.subarray(0,5).toString(),'%PDF-')
   fs.writeFileSync(path.join(process.env.CURTAIN_PDF_FIXTURE_OUTPUT,`Cortina-TESTE-${profile}.pdf`),buffer)
   console.log(`Cortina salva/reaberta ${label}: unitario ${price}, total ${total}, PDF ${blob.size} bytes`)
  }
 }

 if(process.env.BUDGET_PDF_APPROVAL_FIXTURE){
  const fixture=JSON.parse(fs.readFileSync(process.env.BUDGET_PDF_APPROVAL_FIXTURE,'utf8'))
  assert.equal(fixture.budget.total_final,2854.21)
  assert.equal(fixture.budget.percentual_parceiro,50)
  assert.equal(fixture.budget.valor_parceiro,1427.11)
  assert.equal(fixture.budget.total_cliente_final,4281.32)
  for(const mode of ['reseller_internal','reseller_client','reseller_commercial']){
   const data=prepareBudgetPdfData(fixture.budget,mode,fixture.context)
   const rendered=text(React.createElement(BudgetPdfDocument,{data})).replace(/\s+/g,' ')
   for(const expected of ['4.281,32','4.067,25','4.589,58','1.529,86','2.033,63','2.033,62','2 anos'])assert.ok(rendered.includes(expected),expected)
   assert.ok(rendered.includes(mode==='reseller_internal'?'12 dias uteis':'12 dias úteis'))
   for(const privateText of ['7,2%','Costureira:','2.029,25','824,96','682,25','barra dupla de 15','entretela TNT']){
    assert.equal(rendered.includes(privateText),mode==='reseller_internal',`${mode}: ${privateText}`)
   }
   for(const commercialText of ['50%','1.427,11','2.711,50','1.355,75'])assert.equal(rendered.includes(commercialText),mode!=='reseller_client',`${mode}: ${commercialText}`)
   const externalItems=[...data.products,...data.services]
   if(mode!=='reseller_internal')assert.equal(externalItems.reduce((sum,item)=>sum+Math.round(item.subtotal*100),0),428132)
   const blob=await generateBudgetPdf(fixture.budget,mode,fixture.context)
   fs.writeFileSync(path.join(path.dirname(process.env.BUDGET_PDF_APPROVAL_FIXTURE),`prevalidado-${mode}.pdf`),Buffer.from(await blob.arrayBuffer()))
  }
  console.log('Pre-validacao do orcamento1006: valores aprovados, condicoes e sigilo dos tres PDFs OK; nenhum dado gravado no ERP.')
 }

 mockBudget={...direct,numero:'2001',total_final:700};mockCompany={id:1,nome:'Razão real',nome_fantasia:'Nome fantasia real',documento:'Documento real',logo_url:null,perfil_publico:{logradouro:'Rua Tenant 1',numero:'123',cidade:'Cidade A',estado:'SP',telefone_comercial:'1133334444',telefone_celular:'11999998888',email:'empresa1@example.invalid',site:'https://empresa1.example.invalid'}}
 mockClients=[{id:20,nome:'Cliente cadastro',documento:'Doc cliente',email:'email@example.invalid'}]
 calls.length=0
 const saved=await prepareSavedBudgetPdf(1004,'direct')
 assert.equal(saved.budget,mockBudget);assert.equal(saved.budget.total_final,700);assert.equal(saved.filename,'Orcamento-2001.pdf')
 assert.equal(calls[0],'budget');assert.deepEqual(calls.slice(1).sort(),['clients','company','sellers'])
 const companyContext=await loadBudgetPdfContext(direct,'direct')
 assert.equal(companyContext.companyTradeName,mockCompany.nome_fantasia);assert.equal(companyContext.companyDocument,mockCompany.documento)
 assert.equal(companyContext.companyLogo,undefined);assert.deepEqual(companyContext.warnings,[])
 assert.equal(companyContext.companyAddress,'Rua Tenant 1, 123, Cidade A, SP')
 assert.deepEqual(companyContext.companyPhones,['1133334444','11999998888'])
 assert.equal(companyContext.companyEmail,'empresa1@example.invalid')
 assert.equal(companyContext.companySite,'https://empresa1.example.invalid')
 assert.equal(companyContext.sellerName,'André')
 assert.equal((await loadBudgetPdfContext({...direct,vendedor_id:999},'direct')).sellerName,undefined)
 const firstCompany=mockCompany
 activeCompanyId=2;mockCompany={id:2,nome:'Razão do Tenant 2',documento:'98.765.432/0001-10',perfil_publico:{cidade:'Cidade B',email:'tenant2@example.invalid'}}
 const secondContext=await loadBudgetPdfContext(direct,'direct')
 const secondPdf=prepareBudgetPdfData(direct,'direct',secondContext)
 assert.equal(secondPdf.companyLegalName,'Razão do Tenant 2');assert.equal(secondPdf.companyAddress,'Cidade B')
 assert.ok(!JSON.stringify(secondPdf).includes('empresa1'));assert.ok(!JSON.stringify(secondPdf).includes('Tenant 1'))
 activeCompanyId=1;mockCompany=firstCompany
 switchCompanyDuringLoad=true
 await assert.rejects(loadBudgetPdfContext(direct,'direct'),/empresa ativa mudou/)
 switchCompanyDuringLoad=false;activeCompanyId=1
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
 calls.length=0;mockBudget=corrected
 const commercialPdf=await prepareSavedBudgetPdf(1004,'reseller_commercial')
 assert.deepEqual(calls,['budget','resellers','sellers','company'])
 assert.equal(commercialPdf.filename,'Orcamento-1004-Revenda.pdf')
 assert.deepEqual(commercialPdf.warnings,[])
 calls.length=0;mockBudget=budget
 await prepareSavedBudgetPdf(1004,'reseller_client')
 assert.deepEqual(calls,['budget','sellers','company'])
 const authModule=await import(authUrl)
 authModule.setAuthEnabled(false)
 mockBudget=direct
 calls.length=0
 const localPdf=await prepareSavedBudgetPdf(1004,'direct')
 assert.equal(localPdf.blob.type,'application/pdf')
 assert.deepEqual(calls,['budget','clients','sellers','company'])
 queryFailure=true
 await assert.rejects(loadBudgetPdfContext(direct,'direct'),/carregar os dados/)
 queryFailure=false
 activeCompanyId=0
 await assert.rejects(loadBudgetPdfContext(direct,'direct'),/Empresa local/)
 activeCompanyId=1
 authModule.setAuthEnabled(true)
 const dialog=fs.readFileSync(path.join(__dirname,'../src/components/BudgetPreviewDialog.tsx'),'utf8')
 assert.match(dialog,/await prepareSavedBudgetPdf\(id, mode\)/)
 assert.ok(dialog.indexOf('await prepareSavedBudgetPdf(id, mode)')<dialog.indexOf('downloadBudgetPdf(result.blob'))
 assert.match(dialog,/generating\.current/);assert.match(dialog,/Gerando PDF/)
 for(const label of ['PDF Revenda','PDF Interno Smart-tec','PDF Cliente Final'])assert.ok(dialog.includes(label),label)
 assert.ok(!dialog.includes('PDF interno da Revenda'))
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
 console.log('PDF orçamento: 3 destinos separados e fluxo direto; preços finais, repasses, sigilo no DTO/renderização, erros e PDFs A4 aprovados.')
})().catch(error=>{console.error(error);process.exitCode=1})
