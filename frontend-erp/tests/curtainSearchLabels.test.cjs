const assert=require('node:assert/strict'),path=require('node:path')
const {pathToFileURL}=require('node:url'),{registerHooks}=require('node:module')
registerHooks({resolve(s,c,n){try{return n(s,c)}catch(e){if(s.startsWith('.')&&!path.extname(s))return n(s+'.ts',c);throw e}}})
;(async()=>{
 const h=await import(pathToFileURL(path.join(__dirname,'../src/utils/curtainFabricCatalog.ts')))
 for(const [id,reference,range] of [[1,'50.073','17'],[2,'50.072','04'],[3,'50.071','08']]){
  const fabric={id,nome:'WILER - FILIPINAS - '+reference+'-01 AO '+reference+'-'+range,nome_fornecedor:'Wiler',grupo_tecnico:'TECIDOS_CORTINA'}
  const suggestion=h.curtainSuggestions([fabric],reference)[0]
  assert.ok(suggestion);assert.ok(suggestion.label.endsWith(' · '+reference));assert.ok(!suggestion.label.includes(' AO '))
  assert.equal(suggestion.fabric.id,id);assert.equal(suggestion.normalized.color,'01 AO '+range)
  const state=h.applyCurtainSuggestion(h.DEFAULT_CURTAIN,suggestion);assert.equal(state.tecidoProdutoId,id);assert.equal(state.cor,'01 AO '+range)
  console.log('OK Wiler '+reference+': rótulo limpo, dados técnicos preservados')
 }
 const individual={id:4,nome:'WILER - FILIPINAS - 50.073-02',nome_fornecedor:'Wiler',grupo_tecnico:'TECIDOS_CORTINA'}
 assert.ok(h.curtainSuggestions([individual],'50.073')[0].label.endsWith(' · 02'))
 const action={id:5,nome:'VOIL LISO - BRANCO - 3,00M',cor:'BRANCO',nome_fornecedor:'AÇÃO DISTRIBUIDORA',grupo_tecnico:'TECIDOS_CORTINA'}
 assert.ok(h.curtainSuggestions([action],'voil')[0].label.endsWith(' · VOIL LISO · BRANCO'))
 console.log('OK referências individuais e Ação intactas; 5 testes aprovados')
})().catch(e=>{console.error(e);process.exitCode=1})
