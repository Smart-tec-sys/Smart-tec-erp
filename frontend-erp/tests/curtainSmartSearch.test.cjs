const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { pathToFileURL } = require('node:url')
const { registerHooks } = require('node:module')
const compiled = new Map()
registerHooks({
  resolve(spec, context, next) {
    try { return next(spec, context) } catch (error) {
      if (spec.startsWith('.') && !path.extname(spec)) return next(spec + '.ts', context)
      throw error
    }
  },
  load(url, context, next) {
    if (compiled.has(url)) return { format: 'module', source: compiled.get(url), shortCircuit: true }
    return next(url, context)
  },
})
;(async () => {
  const { transformWithOxc } = await import('vite')
  const file = path.join(__dirname, '../src/components/BudgetProductRow.tsx')
  let source = fs.readFileSync(file, 'utf8')
    .replace("import { useEffect, useMemo, useState } from 'react'", `const useMemo = f => f(); const useEffect = f => { globalThis.__effects.push(f) }; const useState = initial => [globalThis.__query ?? initial, value => { globalThis.__query = value }]`)
    .replace(/import \{ ZeroNumberInput, zeroInputValue \} from '[^']+'/g, 'const ZeroNumberInput = () => null; const zeroInputValue = v => v')
    .replace(/import \{ (\w+Simulation) \} from '[^']+'/g, 'const $1 = () => null')
  compiled.set(pathToFileURL(file).href, (await transformWithOxc(source, file, { jsx: { runtime: 'automatic' } })).code)
  const { BudgetProductRow } = await import(pathToFileURL(file))
  const { emptyProduct } = await import(pathToFileURL(path.join(__dirname, '../src/types/budget.ts')))

  const helpers = await import(pathToFileURL(path.join(__dirname, '../src/utils/curtainFabricCatalog.ts')))
  const { curtainSuggestions, DEFAULT_CURTAIN, fabricVariants, curtainFabricCatalog } = helpers
  const base = { id: 99, nome: 'Cortina de tecido', modelo_tecnico: 'CORTINA', grupo_tecnico: 'TECIDOS_CORTINA' }
  const fabric = { grupo_produto: 'Tecidos', grupo_tecnico: 'TECIDOS_CORTINA', situacao: 'Ativo' }
  const catalog = [base,
    {...fabric,id:1,nome:'GAZE DE LINHO - BRANCO',nome_fornecedor:'AÇÃO DISTRIBUIDORA'},
    {...fabric,id:2,nome:'VOIL BORA BORA - BRANCO',nome_fornecedor:'AÇÃO DISTRIBUIDORA'},
    {...fabric,id:3,nome:'WILER - COZUMEL - ARCA (01)',nome_fornecedor:'Wiler'},
    {...fabric,id:4,nome:'WILER - COZUMEL - ARCA (02)',nome_fornecedor:'Wiler'},
    {...fabric,id:5,nome:'BLACKOUT - BRANCO',nome_fornecedor:'AÇÃO DISTRIBUIDORA'},
    {...fabric,id:6,nome:'TECIDO VELUDO - PRETO - 3,00M',nome_fornecedor:'AÇÃO DISTRIBUIDORA',grupo_tecnico:'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL',tipo_cortina_persiana:'TECIDO PARA CORTINA'},
    {...fabric,id:7,nome:'RATTAN - BEGE',nome_fornecedor:'JP'},
    {...fabric,id:8,nome:'MOTOR BLACKOUT',nome_fornecedor:'Wiler'},
    {...fabric,id:9,nome:'VOIL INATIVO',situacao:'Inativo'},
  ]
  let changed
  const nodes = tree => !tree || typeof tree !== 'object' ? [] : Array.isArray(tree) ? tree.flatMap(nodes) : [tree, ...nodes(tree.props?.children)]
  const render = (query, product = emptyProduct(1)) => {
    globalThis.__query=query; globalThis.__effects=[]
    return BudgetProductRow({product,catalog,commercialType:'Varejo',onChange:value=>changed=value,onRemove(){},onCurtain(){},onRomana(){},onRomanaTeto(){},onRolo(){},onDoubleVision(){}})
  }
  const buttons = tree => nodes(tree).filter(n=>n.type==='div' && n.props.className==='product-suggestions').flatMap(n=>nodes(n).filter(c=>c.type==='button'))
  let count=0
  const check=(label,fn)=>{fn(); count++; console.log('OK '+label)}
  check('cortina de',()=>assert.ok(curtainSuggestions(catalog,'cortina de').length>1))
  for(const [query,id] of [['gaze linho',1],['bora bora',2],['wiler cozumel',3],['cortina veludo preto',6],['  LÍNHO   gaze cortina ',1]]) check(query,()=>assert.ok(curtainSuggestions(catalog,query).some(s=>s.fabric?.id===id)))
  check('sugestão mantém produto-base e ID técnico',()=>{
    buttons(render('wiler cozumel')).find(b=>b.key==='curtain-3').props.onClick()
    assert.equal(changed.productId,null); assert.equal(changed.product,'Cortina de tecido'); assert.equal(changed.curtain.tecidoProdutoId,3); assert.equal(changed.color,'01')
  })
  const selected=changed
  check('forro blackout preserva tecido principal',()=>{
    buttons(render('cortina de tecido forro blackout',selected))[0].props.onClick()
    assert.equal(changed.curtain.tecidoProdutoId,3);assert.equal(changed.curtain.possuiForro,true);assert.equal(changed.curtain.tipoForro,'BLACKOUT - BRANCO');assert.equal(changed.productId,null)
  })
  check('blackout sem forro é principal',()=>{
    buttons(render('cortina de tecido blackout'))[0].props.onClick()
    assert.equal(changed.curtain.tecidoProdutoId,5);assert.equal(changed.curtain.possuiForro,false)
  })
  check('combinação tecido e forro',()=>{
    buttons(render('cortina gaze linho forro blackout'))[0].props.onClick()
    assert.equal(changed.curtain.tecidoProdutoId,1);assert.equal(changed.curtain.possuiForro,true)
  })
  check('forro inexistente não inventa combinação',()=>assert.equal(curtainSuggestions(catalog,'cortina forro inexistente').length,0))
  check('Cor principal lista apenas variantes reais e atualiza ID',()=>{
    const color=nodes(render(undefined,selected)).find(n=>n.type==='select' && n.props['aria-label']==='Cor do tecido')
    assert.deepEqual(nodes(color).filter(n=>n.type==='option').map(n=>n.props.value),['',3,4])
    color.props.onChange({target:{value:'4'}})
    assert.equal(changed.curtain.tecidoProdutoId,4);assert.equal(changed.color,'02');assert.equal(changed.curtain.cor,'02');assert.equal(changed.productId,null)
  })
  check('Ação/Wiler; JP excluído; histórico e componentes',()=>{
    assert.deepEqual(curtainFabricCatalog(catalog).filter(p=>[1,3,6,7].includes(p.id)).map(p=>p.id),[1,3,6])
    assert.ok(!curtainFabricCatalog(catalog).some(p=>[7,8,9].includes(p.id)))
  })
  check('JP excluído de sugestões e variantes de Cortina',()=>{
    assert.equal(curtainSuggestions(catalog,'JP').length,0)
    assert.equal(curtainSuggestions(catalog,'RATTAN').length,0)
    assert.deepEqual(fabricVariants(catalog,{...DEFAULT_CURTAIN,fornecedorTecido:'JP PERSIANAS',colecaoTecido:'RATTAN',tecidoNome:'RATTAN',tecidoProdutoId:7}),[])
    assert.equal(catalog.find(p=>p.id===7).nome_fornecedor,'JP')
  })
  check('Ação: CAMBURI e LINHO VOIL I reais, sem nomes inventados',()=>{
    const records=[
      {...fabric,id:3072,nome:'12246 - CAMBURI - (60)LINHO - 3,00M',linha:'CORTINA',cor:'Linho',material_tecido:'12246 - CAMBURI - (60)LINHO - 3,00M'},
      {...fabric,id:3065,nome:'12230 - LINHO VOIL I - (60)LINHO - 2,80M',linha:'CORTINA',cor:'Linho',nome_fornecedor:'AÃ‡ÃƒO DISTRIBUIDORA',material_tecido:'12230 - LINHO VOIL I - (60)LINHO - 2,80M'},
    ]
    for(const [record,name] of records.map((p,i)=>[p,['CAMBURI','LINHO VOIL I'][i]])) {
      assert.equal(helpers.getFabricCollection(record.nome,helpers.getFabricSupplier(record)),record.id===3072?'CAMBURI':'LINHO')
      assert.equal(helpers.getFabricVariant(record).name,name)
      assert.equal(helpers.getFabricVariant(record).color,'Linho')
      assert.equal(helpers.getFabricSupplier(record),'AÇÃO DISTRIBUIDORA')
      assert.equal(helpers.fabricState(DEFAULT_CURTAIN,record).tecidoProdutoId,record.id)
      const separateModel={...record,modelo:'Modelo cadastrado'}
      assert.equal(helpers.getFabricCollection(separateModel.nome,helpers.getFabricSupplier(separateModel)),record.id===3072?'CAMBURI':'LINHO')
      assert.equal(helpers.getFabricVariant(separateModel).name,'Modelo cadastrado')
    }
  })
  check('Wiler COZUMEL preserva nomes e faixas',()=>{
    for(const name of ['ALCOR','ALGEDI','ANITA','AQUILA','ARCA','CASTOR']) {
      const p={...fabric,id:123,nome:'WILER - COZUMEL - '+name+' (01 AO 04)',nome_fornecedor:'Wiler'}
      assert.equal(helpers.getFabricCollection(p.nome,'Wiler'),'COZUMEL')
      assert.deepEqual(helpers.getFabricVariant(p),{name,color:'01 AO 04'})
    }
  })
  // Real technical section render with effects/network disabled, no color control.
  const curtainFile=path.join(__dirname,'../src/components/CurtainSimulation.tsx')
  const curtainSource=fs.readFileSync(curtainFile,'utf8').replace("import { useEffect } from 'react'",'const useEffect = () => {}').replace("import { simulateCurtain } from '../services/api'",'const simulateCurtain = () => { throw Error("unexpected network") }')
  compiled.set(pathToFileURL(curtainFile).href,(await transformWithOxc(curtainSource,curtainFile,{jsx:{runtime:'automatic'}})).code)
  const { CurtainSimulation }=await import(pathToFileURL(curtainFile))
  let technical
  const section=()=>CurtainSimulation({product:selected,catalog,profile:'Varejo',onResult:(_,s)=>technical=s})
  check('um único campo Cor visível',()=>{
    assert.equal(nodes(render(undefined,selected)).filter(n=>n.type==='span' && n.props.children==='Cor').length,1)
    assert.equal(nodes(section()).filter(n=>n.type==='span' && n.props.children==='Cor').length,0)
  })
  check('trocar tecido limpa cor incompatível',()=>{
    const selects=nodes(section()).filter(n=>n.type==='select'); selects[2].props.onChange({target:{value:'INEXISTENTE'}})
    assert.equal(technical.cor,'');assert.equal(technical.tecidoProdutoId,undefined)
  })
  check('cor compatível é mantida ao selecionar o mesmo tecido',()=>{
    nodes(section()).filter(n=>n.type==='select')[2].props.onChange({target:{value:'ARCA'}})
    assert.equal(technical.tecidoProdutoId,3);assert.equal(technical.cor,'01')
  })
  check('Budget e Sale compartilham fluxo e sincronizam cor',()=>{
    for(const page of ['NewBudgetPage','NewSalePage']) {
      const source=fs.readFileSync(path.join(__dirname,'../src/pages/'+page+'.tsx'),'utf8')
      assert.ok(source.includes('<BudgetProductRow'));assert.ok(source.includes('color: state.cor'))
    }
  })
  console.log(count+' cenários de busca/forro/cor aprovados.')
})().catch(error=>{console.error(error);process.exitCode=1})
