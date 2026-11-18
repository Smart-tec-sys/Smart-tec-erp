const assert=require('node:assert/strict')
const fs=require('node:fs')
const path=require('node:path')
const {pathToFileURL}=require('node:url')
const {registerHooks}=require('node:module')
const compiled=new Map()
registerHooks({
 resolve(spec,context,next){try{return next(spec,context)}catch(error){if(spec.startsWith('.')&&!path.extname(spec)){for(const ext of ['.ts','.tsx']){try{return next(spec+ext,context)}catch{}}}throw error}},
 load(url,context,next){if(compiled.has(url))return {format:'module',source:compiled.get(url),shortCircuit:true};return next(url,context)},
})
;(async()=>{
 const {transformWithOxc}=await import('vite')
 const root=path.join(__dirname,'..'),src=path.join(root,'src')
 compiled.set(pathToFileURL(path.join(src,'services/api.ts')).href,"export function simulateRolo(){throw new Error('Teste de renderização não deve consultar API')} export class ApiError extends Error{}")
 const files=[
  ...fs.readdirSync(path.join(src,'types')).filter(file=>file.endsWith('.ts')).map(file=>`types/${file}`),
  'utils/technicalSimulation.ts','utils/productSuggestionRank.ts','utils/fabricDisplay.ts','utils/commercialDisplay.ts',
  'components/RoloSimulation.tsx','services/budgetPdf.ts','services/budgetPdfData.ts','services/budgetPdfVisibility.ts',
  'components/budgetPdf/BudgetPdfDocument.tsx','components/budgetPdf/budgetPdfStyles.ts',
 ]
 for(const file of files){
  const filename=path.join(src,file)
  compiled.set(pathToFileURL(filename).href,(await transformWithOxc(fs.readFileSync(filename,'utf8'),filename,{jsx:{runtime:'automatic'}})).code)
 }
 const load=file=>import(pathToFileURL(path.join(src,file)).href)
 const {roloKind,roloKey}=await load('types/rolo.ts')
 const {rankProductSuggestions}=await load('utils/productSuggestionRank.ts')
 const {commercialVariantKey}=await load('utils/fabricDisplay.ts')
 const {RoloSimulation}=await load('components/RoloSimulation.tsx')
 const {prepareBudgetPdfData}=await load('services/budgetPdfData.ts')
 const {BudgetPdfDocument}=await load('components/budgetPdf/BudgetPdfDocument.tsx')
 const {generateBudgetPdf}=await load('services/budgetPdf.ts')
 const {renderToStaticMarkup}=require('react-dom/server'),React=require('react')
 const manifesto=JSON.parse(fs.readFileSync(path.join(root,'../docs/rolo-picasso-acao-v1.json'),'utf8'))
 const acabados=manifesto.modelos.flatMap(model=>model.variacoes.map((v,index)=>({
  id:1000+index,nome:`${model.nome} - ${v.cor}`,modelo_tecnico:'ROLO',modelo:'MANUAL',produto_base:model.nome,
  grupo_produto:'Persianas',grupo_tecnico:'PERSIANA ROLO',familia_tecnica:'ROLO',tipo_produto:'Produto Fabricado',unidade_venda:'M2',cor:v.cor,
 })))
 const componentes=Array.from({length:20},(_,id)=>({id,nome:'Tecido Rolô Picasso',tipo_produto:'Componente',modelo_tecnico:'ROLO'}))
 for(const p of acabados)assert.equal(roloKind(p),'MANUAL')
 for(const p of componentes)assert.equal(roloKind(p),null)
 for(const p of acabados){
  const variants=[...componentes,...acabados].filter(item=>commercialVariantKey(item)===commercialVariantKey(p))
  assert.equal(variants.length,5)
  assert.equal(new Set(variants.map(v=>v.cor)).size,5)
  assert.ok(variants.every(v=>v.produto_base===p.produto_base&&v.tipo_produto==='Produto Fabricado'))
 }
 const rowSource=fs.readFileSync(path.join(src,'components/BudgetProductRow.tsx'),'utf8')
 assert.ok(rowSource.includes('commercialVariantKey(p) === commercialKey'))
 for(const query of ['rolô picasso','rolo','persiana rolô']){
  const ranked=rankProductSuggestions([...componentes,...acabados],query,p=>roloKind(p)!==null).slice(0,12)
  assert.equal(ranked.slice(0,10).filter(p=>p.tipo_produto==='Produto Fabricado').length,10,query)
 }
 const product={id:1,productId:10,width:'1,90',height:'1,70',quantity:1,discount:0,color:'AMENDOA',acionamento:'manual',roloKind:'MANUAL'}
 const result={custo_tecnico:123.45,custo_cadastrado:null,bitola_tecnica:'38mm',quantidade_pecas:1,area_real_m2:3.23,area_faturavel_m2:3.23,
  preco_unitario:95.55,subtotal:308.63,preco_disponivel:true,componentes_tecnicos:{tecido:{quantidade_compra_ml:1.9425,largura_bobina_m:2.5}},fabricacao_por_peca:{},alertas:[]}
 product.rolo={key:roloKey(product,'Consumidor final'),result}
 const html=renderToStaticMarkup(React.createElement(RoloSimulation,{product,profile:'Consumidor final',onResult(){}}))
 assert.match(html,/123,45/);assert.match(html,/38mm/);assert.doesNotMatch(html,/Custo técnico: indisponível/)
 assert.match(html,/1,9425/);assert.match(html,/Faixa integral por peça/)
 const stale=renderToStaticMarkup(React.createElement(RoloSimulation,{product:{...product,width:'1,80'},profile:'Consumidor final',onResult(){}}))
 assert.match(stale,/Calculando/);assert.doesNotMatch(stale,/123,45/)
 const medidas=[['Sala',1.38,2.52,2],['Escritório',1.65,1.65,1],['Quarto 1',1.79,1.70,1],['Quarto 2',1.90,1.70,1]]
 const fixture={id:0,numero:'PREVIA-TESTE-PICASSO',cliente_id:null,cliente_nome:'Cliente sintético de teste',perfil_comercial:'CONSUMIDOR_FINAL',status:'EM_ABERTO',
  total:400,desconto:0,total_final:400,observacao:'Prévia de teste, não enviar.',
  itens:medidas.map(([ambiente,largura,altura,quantidade],i)=>({
   tipo_item:'PRODUTO',descricao:i===0?'Rolô Picasso Blackout - AMENDOA':'Rolô Picasso Translúcido - AMENDOA',
   largura,altura,quantidade,unidade:'M2',cor:'AMENDOA',preco_unitario:10,desconto:0,subtotal:100,observacao_item:ambiente,
  }))}
 const input=process.argv[2]?JSON.parse(fs.readFileSync(process.argv[2],'utf8')):fixture
 const context={companyName:process.argv[2]?'Smart-tec Persianas':'Empresa sintética de teste'}
 const data=prepareBudgetPdfData(input,'direct',context)
 assert.equal(data.products.reduce((n,p)=>n+p.quantity,0),5)
 assert.equal(data.products.length,4)
 assert.equal(Number(data.products.reduce((n,p)=>n+p.subtotal,0).toFixed(2)),data.finance.total)
 assert.equal(data.finance.finalTotal,input.total_final)
 for(let i=0;i<medidas.length;i++){
  assert.equal(data.products[i].quantity,medidas[i][3])
  assert.equal(data.products[i].observation,medidas[i][0])
 }
 const text=node=>node==null?'':Array.isArray(node)?node.map(text).join(' '):
  typeof node!=='object'?String(node):typeof node.type==='function'?text(node.type(node.props)):text(node.props?.children)
 const pdfText=text(BudgetPdfDocument({data})).replace(/\s+/g,' ')
 for(const measure of ['1,38 x 2,52 m','1,65 x 1,65 m','1,79 x 1,7 m','1,9 x 1,7 m'])assert.ok(pdfText.includes(measure),measure)
 const blob=await generateBudgetPdf(input,'direct',context)
 const buffer=Buffer.from(await blob.arrayBuffer())
 assert.equal(buffer.subarray(0,5).toString(),'%PDF-')
 assert.ok(buffer.length>1000)
 if(process.argv[3])fs.writeFileSync(process.argv[3],buffer)
 console.log(`Picasso: 10 variações, relevância, custo técnico, 38mm, cinco peças e PDF (${buffer.length} bytes) aprovados.`)
})().catch(error=>{console.error(error);process.exitCode=1})
