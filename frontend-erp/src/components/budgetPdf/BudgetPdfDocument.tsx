import { Document,Page,Text,View } from '@react-pdf/renderer'
import type { DocumentProps } from '@react-pdf/renderer'
import type { BudgetPdfData } from '../../services/budgetPdfData'
import { budgetFinancialVisibility } from '../../services/budgetPdfData'
import { styles as s } from './budgetPdfStyles'
const money=(value:number|null)=>value==null?'—':new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(value)
function ItemTable({items,prices}:{items:BudgetPdfData['products'];prices:boolean}){
 const widths=prices?['24%','17%','12%','5%','7%','12%','10%','13%']:['34%','26%','18%','10%','12%']
 const headers=prices?['Descrição','Ambiente / obs.','Medidas','Qtd.','Unid.','Valor unit.','Desconto','Subtotal']:['Descrição','Ambiente / observação','Medidas','Qtd.','Unidade']
 return <View><View style={s.tableHead} minPresenceAhead={45}>{headers.map((header,index)=><Text key={header} style={[s.cell,s.headText,{width:widths[index]}]}>{header}</Text>)}</View>{items.map((item,index)=>{
  const values=[item.description,item.observation,item.measure||'—',item.quantity.toLocaleString('pt-BR'),item.unit]
  if(prices&&'unitPrice' in item)values.push(money(item.unitPrice),money(item.discount),money(item.subtotal))
  return <View key={index} style={s.row} wrap={false}>{values.map((value,column)=><View key={column} style={[s.cell,{width:widths[column]}]}><Text>{value}</Text>{column===0&&item.color&&<Text style={s.secondary}>Cor: {item.color}</Text>}</View>)}</View>
 })}{!items.length&&<Text style={s.empty}>Nenhum produto informado.</Text>}</View>
}
function Summary({data}:{data:BudgetPdfData}){
 const f=data.finance
 const rows:Array<[string,number|null]>=f.kind==='customer'?[['Valor Cliente Final',f.customerTotal]]:f.kind==='direct'?[['Total',f.total],['Desconto',f.discount],['Total final',f.finalTotal]]:[['Valor Smart-tec',f.smartTotal],['Valor da Revenda',f.resellerValue],...(f.rt!==null?[['RT Representante',f.rt] as [string,number|null]]:[]),...(f.bankFee!==null?[['Taxa bancária',f.bankFee] as [string,number|null]]:[]),['Valor Cliente Final',f.customerTotal]]
 return <View style={s.summary} wrap={false}>{rows.map(([label,value],index)=><View key={label} style={index===rows.length-1?[s.summaryRow,s.final]:s.summaryRow}><Text style={s.summaryLabel}>{label}</Text><Text style={index===rows.length-1?s.finalValue:s.summaryValue}>{money(value)}</Text></View>)}</View>
}
export function BudgetPdfDocument({data}:DocumentProps&{data:BudgetPdfData}){
 const visibility=budgetFinancialVisibility(data.mode)
 return <Document title={`Orçamento ${data.number}`} author="Smart-tec Sistemas" subject={data.mode==='reseller_internal'?'Orçamento interno da revenda':'Proposta comercial'}><Page size="A4" style={s.page} wrap>
  <View style={s.header} wrap={false}><Text style={s.brand}>Smart-tec Sistemas</Text>{data.company!=='Smart-tec Sistemas'&&<Text style={s.company}>{data.company}</Text>}<Text style={s.title}>ORÇAMENTO Nº {data.number}</Text><View style={s.meta}><Text>Data: {data.date}</Text><Text>Validade: {data.validity}</Text></View>{data.mode==='reseller_internal'&&<Text style={s.internal}>DOCUMENTO INTERNO DA REVENDA</Text>}</View>
  <Text style={s.section} minPresenceAhead={60}>DADOS DO CLIENTE</Text><View style={s.customer} wrap={false}><Text style={s.customerName}>{data.mode==='direct'?'Cliente':'Cliente Final'}: {data.customer.name}</Text>{[data.customer.document,data.customer.phone,data.customer.email,data.customer.address].filter(Boolean).map((line,index)=><Text key={index} style={s.line}>{line}</Text>)}{data.mode==='reseller_internal'&&<><Text style={s.line}>Revenda: {data.reseller}</Text>{data.seller&&<Text style={s.line}>Vendedor Smart-tec: {data.seller}</Text>}{data.representative&&<Text style={s.line}>Representante: {data.representative}</Text>}</>}</View>
  <Text style={s.section} minPresenceAhead={65}>PRODUTOS / ITENS</Text><ItemTable items={data.products} prices={visibility.itemPrices}/>
  {data.services.length>0&&<><Text style={s.section} minPresenceAhead={65}>SERVIÇOS</Text><ItemTable items={data.services} prices={visibility.itemPrices}/></>}
  <Summary data={data}/>
  {data.notes&&<><Text style={s.section} minPresenceAhead={35}>OBSERVAÇÕES COMERCIAIS</Text><Text style={s.notes}>{data.notes}</Text></>}
  <Text style={s.footer} fixed>Smart-tec Sistemas · Orçamento {data.number}</Text>
 </Page></Document>
}
