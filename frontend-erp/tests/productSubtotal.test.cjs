const assert = require('node:assert/strict')
const { registerHooks } = require('node:module')
const { pathToFileURL } = require('node:url')
const path = require('node:path')
registerHooks({ resolve(specifier, context, next) {
  return next(specifier.startsWith('.') && !path.extname(specifier) ? specifier + '.ts' : specifier, context)
} })
;(async () => {
  const { emptyProduct, productLineSubtotal } = await import(pathToFileURL(path.join(__dirname, '../src/types/budget.ts')))
  const { romanaKey } = await import(pathToFileURL(path.join(__dirname, '../src/types/romana.ts')))
  const { roloKey } = await import(pathToFileURL(path.join(__dirname, '../src/types/rolo.ts')))
  const base = { ...emptyProduct(1), productId: 1, price: 100, quantity: 2, modelTechnical: 'COMPONENTE' }
  assert.equal(productLineSubtotal(base, 'Varejo'), 200)
  assert.equal(productLineSubtotal({...base, quantity:3}, 'Varejo'), 300)
  assert.equal(productLineSubtotal({...base, price:150}, 'Varejo'), 300)
  assert.equal(productLineSubtotal({...base, discount:20}, 'Varejo'), 180)
  assert.equal(productLineSubtotal({...base, modelTechnical:'ROMANA_LEGADO', width:'2,00',height:'3,00'}, 'Varejo'), 1200)
  const technical = {...base, modelTechnical:'ROMANA', romanaKind:'MANUAL',width:'1,00',height:'2,00'}
  technical.romana = { key:romanaKey(technical, 'Varejo'),result:{subtotal:400} }
  assert.equal(productLineSubtotal(technical, 'Varejo'), 400)
  for (const change of [{width:'3,00'},{height:'4,00'},{quantity:3},{discount:10},{productId:2}]) assert.equal(productLineSubtotal({...technical,...change},'Varejo'),0)
  assert.equal(productLineSubtotal(technical, 'Decorador'), 0)
  assert.equal(productLineSubtotal({...technical,romana:{...technical.romana,error:'Falha'}},'Varejo'),0)
  const rolo={...base,roloKind:'MANUAL',color:'Branco'}
  rolo.rolo={key:roloKey(rolo,'Varejo'),result:{subtotal:200}}
  assert.equal(productLineSubtotal({...rolo,color:'Preto'},'Varejo'),0)
  const c={fator:2,larguraTecido:3,modeloPrega:'WAVE',possuiForro:false,cabecaCm:10,barraCm:20,barraDupla:false,usaEntretela:false,fixacaoCortina:'RODIZIO',trilhoComCordas:false,sistemaWave:'PREGA_PRONTA',espacamentoBotaoCm:10,aberturaCortina:'ESQUERDA',result:{preco_disponivel:true,subtotal:500}}
  c.simulationKey=JSON.stringify(['VAREJO',base.discount,base.productId,0,0,2,c.fator,c.larguraTecido,c.modeloPrega,c.possuiForro,'','','','',c.cabecaCm,c.barraCm,c.barraDupla,c.usaEntretela,null,c.fixacaoCortina,c.trilhoComCordas,c.sistemaWave,c.espacamentoBotaoCm,c.aberturaCortina])
  // Campo opcional ausente é serializado como null pela simulação existente.
  c.tipoEntretela=null
  assert.equal(productLineSubtotal({...base,curtain:c},'Varejo'),500)
  assert.equal(productLineSubtotal({...base,curtain:{...c,fator:3}},'Varejo'),0)
  assert.equal(productLineSubtotal({...base,curtain:c,width:'2'},'Varejo'),0)
  console.log('17 verificações de subtotal e invalidação de simulação aprovadas.')
})().catch(error=>{console.error(error);process.exitCode=1})
