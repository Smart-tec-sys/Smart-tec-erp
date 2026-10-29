const assert=require('node:assert/strict'),path=require('node:path')
const {pathToFileURL}=require('node:url'),{registerHooks}=require('node:module')
registerHooks({resolve(spec,ctx,next){try{return next(spec,ctx)}catch(e){if(spec.startsWith('.')&&!path.extname(spec))return next(spec+'.ts',ctx);throw e}}})
;(async()=>{
 const root=path.join(__dirname,'../src')
 const {emptyProduct,curtainKey,productLineSubtotal}=await import(pathToFileURL(path.join(root,'types/budget.ts')))
 const {DEFAULT_CURTAIN}=await import(pathToFileURL(path.join(root,'utils/curtainFabricCatalog.ts')))
 const {applyCurtainColor}=await import(pathToFileURL(path.join(root,'utils/curtainColors.ts')))
 const row={...emptyProduct(1),product:'Cortina de tecido',width:'2',height:'2',quantity:2,curtain:{...DEFAULT_CURTAIN,tecidoProdutoId:3710}}
 const key=curtainKey(row,'Varejo');row.curtain.simulationKey=key;row.curtain.result={preco_disponivel:true,preco_unitario:236,subtotal:472}
 assert.equal(productLineSubtotal(row,'Varejo'),472)
 for(const change of [{tecidoProdutoId:3711},{fator:3},{barraCm:30},{trilhoModelo:'duplo'},{possuiForro:true,forroProdutoId:2}]) {
  const changed={...row,curtain:{...row.curtain,...change}};assert.notEqual(curtainKey(changed,'Varejo'),key);assert.equal(productLineSubtotal(changed,'Varejo'),0)
 }
 const free=applyCurtainColor(row,[],'VERDE ESPECIAL');assert.equal(curtainKey(free,'Varejo'),key);assert.equal(free.curtain.tecidoProdutoId,3710);assert.equal(productLineSubtotal(free,'Varejo'),472)
 const fs=require('node:fs');const budget=fs.readFileSync(path.join(root,'pages/NewBudgetPage.tsx'),'utf8'),sale=fs.readFileSync(path.join(root,'pages/NewSalePage.tsx'),'utf8')
 assert.ok(budget.includes('curtainKey(p, profileLabel[profile])'));assert.ok(sale.includes('curtainKey(p,profileLabel[profile])'))
 assert.ok(budget.includes('.filter(p=>p.productId || p.curtain?.tecidoProdutoId)'))
 const ui=fs.readFileSync(path.join(root,'components/CurtainSimulation.tsx'),'utf8');assert.ok(ui.includes('tecido_produto_id: resolvedProductId!'));assert.ok(!ui.includes('selectedCatalogProduct'))
 console.log('9 verificacoes: subtotal, 5 entradas reativas, cor livre, paridade dos formularios e motor virtual aprovadas')
})().catch(e=>{console.error(e);process.exitCode=1})
