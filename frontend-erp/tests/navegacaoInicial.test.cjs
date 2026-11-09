const assert=require('node:assert/strict')
const fs=require('node:fs')
const {pathToFileURL}=require('node:url')
const path=require('node:path')
;(async()=>{
 const {navegacaoDoHash,hashDaNavegacao,urlSemHash,ESTADO_INICIAL,ROTULOS_CADASTRO}=await import(pathToFileURL(path.join(__dirname,'../src/navigation/rotas.ts')))

 // URL principal, login e hashes que não são rotas internas abrem a Dashboard.
 for(const hash of ['','#','#/','#/inexistente','#/cadastros/','#/cadastros/outro','#/__proto__','#/constructor','#/cadastros/__proto__',
  '#access_token=abc&refresh_token=def&type=recovery','#type=signup&access_token=x','#error=access_denied','orcamentos','/orcamentos','#orcamentos'])
  assert.deepEqual(navegacaoDoHash(hash),ESTADO_INICIAL,hash)
 assert.deepEqual(ESTADO_INICIAL,{view:'dashboard',activePage:'Início',cadastro:null})

 // URL interna explícita é respeitada.
 const esperado={
  '#/inicio':['dashboard','Início'],'#/orcamentos':['budgets','Orçamentos'],'#/orcamentos/novo':['new-budget','Novo orçamento'],
  '#/vendas':['sales','Vendas'],'#/vendas/nova':['new-sale','Vendas'],'#/financeiro':['finance','Financeiro'],
  '#/contabilidade':['accounting','Contabilidade'],'#/produtos':['products','Produtos'],'#/agenda':['agenda','Agenda'],
  '#/perfil':['profile','Meus dados'],'#/configuracoes':['settings','Configurações'],'#/admin':['admin','Administração Smart-tec'],
 }
 for(const [hash,[view,activePage]] of Object.entries(esperado)) assert.deepEqual(navegacaoDoHash(hash),{view,activePage,cadastro:null},hash)
 for(const [cadastro,rotulo] of Object.entries(ROTULOS_CADASTRO))
  assert.deepEqual(navegacaoDoHash(`#/cadastros/${cadastro}`),{view:'cadastro',activePage:rotulo,cadastro})
 assert.equal(navegacaoDoHash('#/cadastros/revendas').activePage,'Revendas')
 assert.equal(navegacaoDoHash('#/Orcamentos/').view,'budgets')
 assert.equal(navegacaoDoHash('#/vendas?x=1').view,'sales')

 // Ida e volta: toda tela gera um hash que reabre a mesma tela (detalhes voltam à lista).
 for(const view of ['budgets','sales','new-sale','finance','accounting','products','agenda','profile','settings','admin','new-budget'])
  assert.equal(navegacaoDoHash(hashDaNavegacao(view,null)).view,view,view)
 for(const cadastro of Object.keys(ROTULOS_CADASTRO)) assert.deepEqual(navegacaoDoHash(hashDaNavegacao('cadastro',cadastro)).cadastro,cadastro)
 assert.equal(hashDaNavegacao('dashboard',null),'')
 assert.equal(hashDaNavegacao('sale-detail',null),'#/vendas')
 assert.equal(hashDaNavegacao('new-budget',null,{orcamentoExistente:true}),'#/orcamentos')
 assert.equal(hashDaNavegacao('new-budget',null,{orcamentoExistente:false}),'#/orcamentos/novo')
 assert.equal(urlSemHash('/','?a=1'),'/?a=1')
 assert.equal(urlSemHash('',''),'/')

 // App: tela inicial vem só da URL; localStorage não restaura mais a última tela.
 const app=fs.readFileSync(path.join(__dirname,'../src/App.tsx'),'utf8')
 assert.doesNotMatch(app,/localStorage\.getItem\(\s*'smarttec:last-/)
 assert.doesNotMatch(app,/localStorage\.setItem\(\s*'smarttec:last-/)
 assert.match(app,/navegacaoDoHash\(window\.location\.hash\)/)
 assert.match(app,/addEventListener\('hashchange'/)
 assert.match(app,/view === 'admin' && adminChecked && !adminAvailable/)
 const logout=app.slice(app.indexOf('const handleLogout'),app.indexOf('const navigate ='))
 assert.match(logout,/localStorage\.removeItem/)
 assert.ok(logout.indexOf('urlSemHash')<logout.indexOf('window.location.reload()'),'logout limpa a rota antes de recarregar')
 console.log('Navegação: URL principal/login abrem a Dashboard; rotas #/ explícitas respeitadas; callbacks do Supabase ignorados; admin protegido; logout limpa a rota.')
})().catch(error=>{console.error(error);process.exitCode=1})
