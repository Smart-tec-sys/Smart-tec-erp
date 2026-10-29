const assert = require('node:assert/strict')
const { registerHooks } = require('node:module')
const { pathToFileURL } = require('node:url')
const path = require('node:path')
registerHooks({resolve(specifier,context,next){return next(specifier.startsWith('.') && !path.extname(specifier)?specifier+'.ts':specifier,context)}})
;(async()=>{
 const {fabricDisplay,fabricVariantKey,groupFabricSuggestions}=await import(pathToFileURL(path.join(__dirname,'../src/utils/fabricDisplay.ts')))
 const gray={id:1,nome:'SCREEN 1% ECO IMPORTADA - CINZA - 2,50M',cor:'CINZA',modelo_tecnico:'COMPONENTE',valor_custo:100}
 const beige={...gray,id:2,nome:'SCREEN 1% ECO IMPORTADA - BEGE - 2,50M',cor:'BEGE',valor_custo:150}
 const narrow={...beige,id:3,nome:'SCREEN 1% ECO IMPORTADA - BEGE - 1,70M'}
 const standard={...gray,id:4,nome:'SCREEN 1% STANDARD - CINZA - 2,50M'}
 assert.equal(fabricDisplay(gray).name,'SCREEN 1% ECO IMPORTADA')
 assert.equal(fabricDisplay(gray).width,'2,50M')
 assert.equal(fabricVariantKey(gray),fabricVariantKey(beige))
 assert.notEqual(fabricVariantKey(gray),fabricVariantKey(narrow))
 assert.notEqual(fabricVariantKey(gray),fabricVariantKey(standard))
 assert.deepEqual(groupFabricSuggestions([gray,beige,narrow,standard]).map(p=>p.id),[1,3,4])
 assert.equal(groupFabricSuggestions([gray,{...gray,id:5}]).length,2)
 assert.equal(groupFabricSuggestions([{...gray,cor:null},{...beige,cor:null}]).length,2)
 assert.equal(fabricDisplay({id:9,nome:'SUPORTE - BRANCO - 2,50M',cor:'BRANCO'}).name,'SUPORTE - BRANCO - 2,50M')
 assert.equal(fabricDisplay({...gray,nome:'SCREEN 1% ECO IMPORTADA - ANTICHAMA'}).name,'SCREEN 1% ECO IMPORTADA - ANTICHAMA')
 assert.equal(gray.nome,'SCREEN 1% ECO IMPORTADA - CINZA - 2,50M')
 assert.equal(beige.valor_custo,150)
 const jp={...gray,id:20,nome:'SCREEN 3% JP IMPORTADA - CINZA - 2,50M',nome_fornecedor:'JP PERSIANAS'}
 const jpBeige={...jp,id:21,nome:'SCREEN 3% JP IMPORTADA - BEGE - 2,50M',cor:'BEGE'}
 assert.equal(fabricDisplay(jp).name,'SCREEN 3% JP IMPORTADA')
 assert.equal(fabricVariantKey(jp),fabricVariantKey(jpBeige))
 assert.deepEqual(groupFabricSuggestions([jp,jpBeige]).map(p=>p.id),[20])
 assert.equal(jp.nome_fornecedor,'JP PERSIANAS')
 console.log('16 verificações de nome, coleção, cor, fornecimento, agrupamento e dados preservados aprovadas.')
})().catch(error=>{console.error(error);process.exitCode=1})
