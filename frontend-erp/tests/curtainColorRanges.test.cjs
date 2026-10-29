const assert=require('node:assert/strict'),path=require('node:path')
const {pathToFileURL}=require('node:url'),{registerHooks}=require('node:module')
registerHooks({resolve(spec,ctx,next){try{return next(spec,ctx)}catch(e){if(spec.startsWith('.')&&!path.extname(spec))return next(spec+'.ts',ctx);throw e}}})
;(async()=>{
 const root=path.join(__dirname,'../src')
 const h=await import(pathToFileURL(path.join(root,'utils/curtainColors.ts')))
 const cat=await import(pathToFileURL(path.join(root,'utils/curtainFabricCatalog.ts')))
 const {emptyProduct}=await import(pathToFileURL(path.join(root,'types/budget.ts')))
 const catalog=[
  {id:1,nome:'WILER - FILIPINAS - 50.073-01 AO 50.073-17 (ALGODÃO)',nome_fornecedor:'Wiler',grupo_tecnico:'TECIDOS_CORTINA'},
  {id:2,nome:'WILER - FILIPINAS - 50.072-01 AO 50.072-04',nome_fornecedor:'Wiler',grupo_tecnico:'TECIDOS_CORTINA'},
  {id:3,nome:'WILER - FILIPINAS - 50.073-02',nome_fornecedor:'Wiler',grupo_tecnico:'TECIDOS_CORTINA'},
 ]
 const before=JSON.stringify(catalog)
 const row=fabric=>({...emptyProduct(1),product:'Cortina de tecido',modelTechnical:'CORTINA',groupTechnical:'TECIDOS_CORTINA',curtain:cat.fabricState(cat.DEFAULT_CURTAIN,fabric)})
 const first=row(catalog[0]),second=row(catalog[1])
 assert.deepEqual(h.curtainColorSuggestions(catalog,first,[]).map(v=>v.value),['02']);console.log('OK 1: 50.073 sem 01 AO 17; referência real 02 mantida')
 assert.deepEqual(h.curtainColorSuggestions(catalog,second,[]),[]);console.log('OK 2: 50.072 sem 01 AO 04')
 assert.deepEqual(h.curtainColorSuggestions(catalog,second,['CAFÉ','BRANCO']).map(v=>v.value),['CAFÉ','BRANCO']);console.log('OK 3: grade CORES mantida')
 const individual=h.applyCurtainColor(second,catalog,'01');assert.equal(individual.curtain.cor,'01');assert.equal(individual.curtain.tecidoProdutoId,2);console.log('OK 4: 01 livre sem ID inventado')
 const free=h.applyCurtainColor(second,catalog,'COR ESPECIAL CLIENTE');assert.equal(free.curtain.cor,'COR ESPECIAL CLIENTE');assert.equal(free.curtain.tecidoProdutoId,2);assert.equal(JSON.stringify(catalog),before);console.log('OK 5: texto livre e catálogo intactos')
 console.log('5 testes focados aprovados')
})().catch(e=>{console.error(e);process.exitCode=1})
