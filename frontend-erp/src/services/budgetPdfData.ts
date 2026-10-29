import type { ApiBudget,ApiBudgetItem,ApiClient } from '../types/budget'
export type BudgetPdfMode='direct'|'reseller_internal'|'reseller_client'
export type BudgetPdfContext={companyName?:string;client?:ApiClient;resellerName?:string;sellerName?:string;representativeName?:string}
type Item={description:string;observation:string;measure:string;quantity:number;unit:string;color:string}
type PricedItem=Item&{unitPrice:number|null;discount:number|null;subtotal:number|null}
type Common={number:string;date:string;validity:string;company:string;customer:{name:string;document:string;phone:string;email:string;address:string};notes:string}
export type BudgetPdfData=Common&(
 |{mode:'reseller_client';products:Item[];services:Item[];finance:{kind:'customer';customerTotal:number|null}}
 |{mode:'direct';products:PricedItem[];services:PricedItem[];finance:{kind:'direct';total:number|null;discount:number|null;finalTotal:number|null}}
 |{mode:'reseller_internal';products:PricedItem[];services:PricedItem[];reseller:string;seller:string;representative:string;finance:{kind:'internal';smartTotal:number|null;resellerValue:number|null;rt:number|null;bankFee:number|null;customerTotal:number|null}}
)
const numeric=(value:unknown)=>value==null||value===''||!Number.isFinite(Number(value))?null:Number(value)
const date=(value?:string|null)=>value?value.slice(0,10).split('-').reverse().join('/'):'—'
const quantity=(value:unknown)=>numeric(value)??0
const measure=(item:ApiBudgetItem)=>[numeric(item.largura),numeric(item.altura)].some(value=>value!=null&&value>0)?`${numeric(item.largura)?.toLocaleString('pt-BR')??'—'} x ${numeric(item.altura)?.toLocaleString('pt-BR')??'—'} m`:''
export function budgetFinancialVisibility(mode:BudgetPdfMode){return {itemPrices:mode!=='reseller_client',internalComposition:mode==='reseller_internal',customerTotal:mode!=='direct'}}
export function prepareBudgetPdfData(budget:ApiBudget,mode:BudgetPdfMode,context:BudgetPdfContext={}):BudgetPdfData{
 if(!['direct','reseller_internal','reseller_client'].includes(mode))throw new Error('Modo de PDF inválido.')
 if((mode==='direct')!==(budget.parceiro_id==null))throw new Error('Modo de PDF incompatível com a origem do orçamento.')
 const customer=mode==='direct'?{name:budget.cliente_nome||context.client?.nome||(budget.cliente_id==null?'—':`Cliente #${budget.cliente_id}`),document:context.client?.documento||'',phone:context.client?.telefone_celular||context.client?.telefone_comercial||'',email:context.client?.email||'',address:[context.client?.logradouro,context.client?.numero,context.client?.complemento,context.client?.bairro,context.client?.cidade,context.client?.estado,context.client?.cep].filter(Boolean).join(', ')}:{name:budget.cliente_final_nome||'—',document:budget.cliente_final_documento||'',phone:budget.cliente_final_telefone||'',email:budget.cliente_final_email||'',address:budget.cliente_final_endereco||''}
 const common:Common={number:String(budget.numero||budget.id),date:date(budget.criado_em),validity:date(budget.validade),company:context.companyName||'Smart-tec Sistemas',customer,notes:budget.observacao||''}
 const itemData=(item:ApiBudgetItem):Item=>({description:item.descricao,observation:item.observacao_item||'',measure:measure(item),quantity:quantity(item.quantidade),unit:item.unidade||'—',color:item.cor||''})
 const products=budget.itens.filter(item=>item.tipo_item!=='SERVICO'),services=budget.itens.filter(item=>item.tipo_item==='SERVICO')
 // Strict allowlist: customer document never receives the source budget or internal item prices.
 if(mode==='reseller_client')return {...common,mode,products:products.map(itemData),services:services.map(itemData),finance:{kind:'customer',customerTotal:numeric(budget.total_cliente_final)}}
 const priced=(item:ApiBudgetItem):PricedItem=>({...itemData(item),unitPrice:numeric(item.preco_unitario),discount:numeric(item.desconto),subtotal:numeric(item.subtotal)})
 if(mode==='direct')return {...common,mode,products:products.map(priced),services:services.map(priced),finance:{kind:'direct',total:numeric(budget.total),discount:numeric(budget.desconto),finalTotal:numeric(budget.total_final)}}
 return {...common,mode,products:products.map(priced),services:services.map(priced),reseller:context.resellerName||`Revenda #${budget.parceiro_id}`,seller:context.sellerName||(budget.vendedor_id==null?'':`Funcionário #${budget.vendedor_id}`),representative:context.representativeName||(budget.representante_id==null?'':`Representante #${budget.representante_id}`),finance:{kind:'internal',smartTotal:numeric(budget.total_final),resellerValue:numeric(budget.valor_parceiro),rt:budget.incluir_rt===true?numeric(budget.valor_rt):null,bankFee:budget.incluir_taxa_bancaria===true?numeric(budget.valor_taxa_bancaria):null,customerTotal:numeric(budget.total_cliente_final)}}
}
export function budgetPdfFilename(number:string,mode:BudgetPdfMode){const safe=number.replace(/[^a-zA-Z0-9_-]/g,'-')||'sem-numero';return `Orcamento-${safe}${mode==='reseller_internal'?'-Revenda-Interno':mode==='reseller_client'?'-Cliente-Final':''}.pdf`}
