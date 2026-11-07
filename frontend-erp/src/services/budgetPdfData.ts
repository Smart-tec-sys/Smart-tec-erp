import type { ApiBudget,ApiBudgetItem,ApiClient } from '../types/budget'
import { externalBudgetNotes, externalItemObservation, finalItemPrices, structuredPaymentNotes, assertCustomerTextSafe } from './budgetPdfVisibility'
export type BudgetPdfMode='direct'|'reseller_internal'|'reseller_client'|'reseller_commercial'
export type BudgetPdfContext={companyName?:string;companyTradeName?:string;companyDocument?:string;companyLogo?:string;companyAddress?:string;companyPhones?:string[];companyEmail?:string;companySite?:string;warnings?:string[];client?:ApiClient;resellerName?:string;sellerName?:string;representativeName?:string}
type Item={description:string;internalCode:string;material:string;observation:string;measure:string;quantity:number;unit:string;color:string}
type PricedItem=Item&{unitPrice:number|null;discount:number|null;subtotal:number|null}
type Common={number:string;date:string;validity:string;commercialTable:string;company:string;companyDocument:string;companyLegalName:string;companyLogo?:string;companyAddress:string;companyPhones:string[];companyEmail:string;companySite:string;companySeller:string;customer:{name:string;document:string;phone:string;email:string;address:string};notes:string;warnings:string[]}
export type BudgetPdfData=Common&(
 |{mode:'reseller_client';products:PricedItem[];services:PricedItem[];finance:{kind:'customer';customerTotal:number|null}}
 |{mode:'reseller_commercial';products:PricedItem[];services:PricedItem[];reseller:string;finance:{kind:'reseller';smartTotal:number|null;resellerValue:number|null;resellerPercent:number|null;customerTotal:number|null}}
 |{mode:'direct';products:PricedItem[];services:PricedItem[];finance:{kind:'direct';total:number|null;discount:number|null;finalTotal:number|null}}
 |{mode:'reseller_internal';products:PricedItem[];services:PricedItem[];reseller:string;seller:string;representative:string;internalNotes:string;technicalNotes:string;finance:{kind:'internal';smartTotal:number|null;resellerValue:number|null;resellerPercent:number|null;rt:number|null;bankFee:number|null;customerTotal:number|null}}
)
const numeric=(value:unknown)=>value==null||value===''||!Number.isFinite(Number(value))?null:Number(value)
const date=(value?:string|null)=>value?value.slice(0,10).split('-').reverse().join('/'):'—'
const quantity=(value:unknown)=>numeric(value)??0
const formatNumber=(value:number)=>value.toLocaleString('pt-BR',{maximumFractionDigits:4})
const money=(value:number)=>value.toLocaleString('pt-BR',{style:'currency',currency:'BRL'})
const measure=(item:ApiBudgetItem)=>[numeric(item.largura),numeric(item.altura)].some(value=>value!=null&&value>0)?`${numeric(item.largura)?.toLocaleString('pt-BR')??'—'} x ${numeric(item.altura)?.toLocaleString('pt-BR')??'—'} m`:''
export function budgetFinancialVisibility(mode:BudgetPdfMode){return {itemPrices:true,internalComposition:mode==='reseller_internal',customerTotal:mode!=='direct'}}
export function prepareBudgetPdfData(budget:ApiBudget,mode:BudgetPdfMode,context:BudgetPdfContext={}):BudgetPdfData{
 if(!['direct','reseller_internal','reseller_client','reseller_commercial'].includes(mode))throw new Error('Modo de PDF inválido.')
 if((mode==='direct')!==(budget.parceiro_id==null))throw new Error('Modo de PDF incompatível com a origem do orçamento.')
 const customer=mode==='direct'?{name:budget.cliente_nome||context.client?.nome||(budget.cliente_id==null?'—':`Cliente #${budget.cliente_id}`),document:context.client?.documento||'',phone:context.client?.telefone_celular||context.client?.telefone_comercial||'',email:context.client?.email||'',address:[context.client?.logradouro,context.client?.numero,context.client?.complemento,context.client?.bairro,context.client?.cidade,context.client?.estado,context.client?.cep].filter(Boolean).join(', ')}:{name:budget.cliente_final_nome||'—',document:budget.cliente_final_documento||'',phone:budget.cliente_final_telefone||'',email:budget.cliente_final_email||'',address:budget.cliente_final_endereco||''}
 const commercialTables={CONSUMIDOR_FINAL:'Consumidor Final',VAREJO:'Varejo',DECORADOR:'Decorador'}
 const commercialTable=budget.perfil_comercial?commercialTables[budget.perfil_comercial]:'Não informada'
 const external=mode==='reseller_client'||mode==='reseller_commercial'
 if(mode==='direct')assertCustomerTextSafe([budget.observacao,...budget.itens.map(item=>item.observacao_item)])
 const paymentNotes=structuredPaymentNotes(budget)
 const directNotes=[budget.observacao||'',paymentNotes].filter(Boolean).join('\n\n')
 const projection=external?externalBudgetNotes(budget,mode==='reseller_commercial'):{notes:directNotes,warnings:[]}
 if(external&&budget.itens.some(item=>item.observacao_item&&item.tipo_item!=='SERVICO'&&!externalItemObservation(item)))projection.warnings.push('Observações de itens sem ambiente reconhecido foram omitidas do PDF externo. Confira os ambientes antes de enviar.')
 const common:Common={number:String(budget.numero||budget.id),date:date(budget.criado_em),validity:date(budget.validade),commercialTable:external?'':commercialTable,company:context.companyTradeName?.trim()||context.companyName?.trim()||'',companyLegalName:context.companyName?.trim()||context.companyTradeName?.trim()||'',companyDocument:context.companyDocument?.trim()||'',companyLogo:context.companyLogo,companyAddress:context.companyAddress?.trim()||'',companyPhones:(context.companyPhones??[]).map(phone=>phone.trim()).filter(Boolean),companyEmail:context.companyEmail?.trim()||'',companySite:context.companySite?.trim()||'',companySeller:context.sellerName?.trim()||'',customer,notes:projection.notes,warnings:projection.warnings}
 const itemData=(item:ApiBudgetItem):Item=>{
  const curtain=item.modelo_tecnico?.trim().toUpperCase()==='CORTINA'?item.dados_tecnicos?.cortina:undefined
  const models:Record<string,string>={WAVE:'Wave',FRANZIDO:'Franzido',PREGA_MACHO:'Prega macho',PREGA_FEMEA:'Prega fêmea'}
  const model=curtain?.modeloPrega?models[curtain.modeloPrega]:undefined
  return {internalCode:item.codigo_interno??'',description:model&&!item.descricao.toLocaleLowerCase('pt-BR').includes(model.toLocaleLowerCase('pt-BR'))?`${item.descricao} — ${model}`:item.descricao,
   material:('material' in item&&typeof item.material==='string'?item.material.trim():'')||curtain?.tecido||'',
   observation:external?externalItemObservation(item):item.observacao_item||'',measure:measure(item),quantity:quantity(item.quantidade),
   unit:curtain?'UN':item.unidade||'—',color:item.cor||curtain?.cor||''}
 }
 const products=budget.itens.filter(item=>item.tipo_item!=='SERVICO'),services=budget.itens.filter(item=>item.tipo_item==='SERVICO')
 if(mode==='reseller_client'||mode==='reseller_commercial'){
  const prices=finalItemPrices(budget)
  const projected=budget.itens.map((item,index):PricedItem=>({...itemData(item),unitPrice:prices[index]/item.quantidade,discount:null,subtotal:prices[index]}))
  const externalProducts=projected.filter((_,index)=>budget.itens[index].tipo_item!=='SERVICO')
  const externalServices=projected.filter((_,index)=>budget.itens[index].tipo_item==='SERVICO')
  if(mode==='reseller_client')return {...common,mode,products:externalProducts,services:externalServices,finance:{kind:'customer',customerTotal:numeric(budget.total_cliente_final)}}
  return {...common,mode,products:externalProducts,services:externalServices,reseller:context.resellerName||`Revenda #${budget.parceiro_id}`,finance:{kind:'reseller',smartTotal:numeric(budget.total_final),resellerValue:numeric(budget.valor_parceiro),resellerPercent:numeric(budget.percentual_parceiro),customerTotal:numeric(budget.total_cliente_final)}}
 }
 const priced=(item:ApiBudgetItem):PricedItem=>({...itemData(item),unitPrice:numeric(item.preco_unitario),discount:numeric(item.desconto),subtotal:numeric(item.subtotal)})
 if(mode==='direct')return {...common,mode,products:products.map(priced),services:services.map(priced),finance:{kind:'direct',total:numeric(budget.total),discount:numeric(budget.desconto),finalTotal:numeric(budget.total_final)}}
 const technicalNotes=products.map(item=>{
  const c=item.dados_tecnicos?.cortina
  if(!c)return ''
  const r=c.result
  const opening={CENTRAL:'central, duas folhas',LATERAL_ESQUERDA:'lateral esquerda',LATERAL_DIREITA:'lateral direita',DUAS_LATERAIS:'duas laterais'}
  return [
   `${item.observacao_item||item.descricao} — ESPECIFICAÇÕES DE FABRICAÇÃO`,
   `Tecido: ${c.tecido}; cor ${c.cor}; largura do tecido ${formatNumber(c.larguraTecido)} m; ${c.possuiForro?'com forro':'sem forro'}.`,
   `Modelo ${c.modeloPrega}; fator ${formatNumber(c.fator)}; sistema ${c.sistemaWave}; abertura ${opening[c.aberturaCortina]}.`,
   `Cabeça ${c.cabecaCm} cm; barra ${c.barraCm} cm ${c.barraDupla?'dupla':'simples'}; entretela ${c.usaEntretela?c.tipoEntretela:'não utiliza'}; fixação ${c.fixacaoCortina}; trilho ${c.trilhoComCordas?'com cordas':'sem cordas'}.`,
   ...(r?[
    `Tecido: ${r.tecido.quantidade_alturas} alturas, ${formatNumber(r.tecido.consumo_por_altura_m)} m por altura; consumo ${formatNumber(r.tecido.consumo_total_ml)} ML. Entretela ${formatNumber(r.entretela.quantidade_ml)} ML.`,
    `Costureira: ${r.mao_de_obra.quantidade_alturas} alturas × ${money(r.mao_de_obra.valor_por_altura)} = ${money(r.mao_de_obra.total)}.`,
    `Rodízios: ${r.rodizios.quantidade_total_un} unidades. Wave: ${r.wave.quantidade_folhas} folhas, ${r.wave.quantidade_pontos_total} pontos, espaçamento ${r.wave.espacamento_cm??'não informado'} cm.`,
    ...(r.composicao||[]).map(component=>`${component.componente}: ${formatNumber(component.quantidade)} × R$ ${component.custo_unitario.toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:4})} = ${money(component.custo_total)}${component.unidades_por_embalagem?`; embalagem ${component.unidades_por_embalagem} por ${component.custo_embalagem==null?'não informado':money(component.custo_embalagem)}`:''}.`),
   ]:[]),
   ...(c.observacaoTecnica?[c.observacaoTecnica]:[]),
  ].join('\n')
 }).filter(Boolean).join('\n\n')
 return {...common,mode,products:products.map(priced),services:services.map(priced),reseller:context.resellerName||`Revenda #${budget.parceiro_id}`,seller:context.sellerName||(budget.vendedor_id==null?'':`Funcionário #${budget.vendedor_id}`),representative:context.representativeName||(budget.representante_id==null?'':`Representante #${budget.representante_id}`),internalNotes:budget.observacao_interna||'',technicalNotes,finance:{kind:'internal',smartTotal:numeric(budget.total_final),resellerValue:numeric(budget.valor_parceiro),resellerPercent:numeric(budget.percentual_parceiro),rt:budget.incluir_rt===true?numeric(budget.valor_rt):null,bankFee:budget.incluir_taxa_bancaria===true?numeric(budget.valor_taxa_bancaria):null,customerTotal:numeric(budget.total_cliente_final)}}
}
export function budgetPdfFilename(number:string,mode:BudgetPdfMode){const safe=number.replace(/[^a-zA-Z0-9_-]/g,'-')||'sem-numero';return `Orcamento-${safe}${mode==='reseller_internal'?'-Interno-Smart-tec':mode==='reseller_commercial'?'-Revenda':mode==='reseller_client'?'-Cliente-Final':''}.pdf`}
