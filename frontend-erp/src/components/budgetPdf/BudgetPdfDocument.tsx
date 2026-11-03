import { Document, Image, Page, Text, View } from '@react-pdf/renderer'
import type { DocumentProps } from '@react-pdf/renderer'
import type { BudgetPdfData } from '../../services/budgetPdfData'
import { budgetFinancialVisibility } from '../../services/budgetPdfData'
import { styles as s } from './budgetPdfStyles'

const money = (value: number | null) => value == null ? '—' : new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value)

function ItemTable({ items, prices, services = false, finalPrices = false }: { items: BudgetPdfData['products']; prices: boolean; services?: boolean; finalPrices?: boolean }) {
  const discounts = prices && !finalPrices && items.some(item => 'discount' in item && typeof item.discount === 'number' && item.discount > 0)
  const widths = services
    ? !prices ? ['83%', '17%'] : finalPrices ? ['66%', '17%', '17%'] : discounts ? ['51%', '10%', '13%', '12%', '14%'] : ['59%', '11%', '15%', '15%']
    : !prices ? ['60%', '23%', '17%'] : finalPrices ? ['43%', '23%', '17%', '17%'] : discounts ? ['34%', '17%', '10%', '13%', '12%', '14%'] : ['42%', '17%', '11%', '15%', '15%']
  const quantityColumn = services ? 1 : 2
  const priceColumn = quantityColumn + 1
  const headers = ['Descrição', ...(!services ? ['Medidas'] : []), 'Qtd. / un.', ...(prices ? finalPrices ? ['Preço final'] : ['Valor unit.', ...(discounts ? ['Desconto'] : []), 'Total'] : [])]
  return <View>
    <View style={s.tableHead} minPresenceAhead={45}>
      {headers.map((header, column) => <Text key={header} style={[s.cell, s.headText, column >= quantityColumn ? s.numeric : {}, { width: widths[column] }]}>{header}</Text>)}
    </View>
    {items.map((item, index) => <View key={index} style={s.row}>
          <View style={[s.cell, { width: widths[0] }]}>
            <Text style={s.itemName}>{item.description}</Text>
            {!services && item.material && <Text style={s.secondary}>Material / tecido: {item.material}</Text>}
            {!services && item.color && <Text style={s.secondary}>Cor: {item.color}</Text>}
            {item.observation && <Text style={s.secondary}>{item.observation}</Text>}
          </View>
          {!services && <Text style={[s.cell, { width: widths[1] }]}>{item.measure || '—'}</Text>}
          <Text style={[s.cell, s.numeric, { width: widths[quantityColumn] }]}>{item.quantity.toLocaleString('pt-BR')} {item.unit}</Text>
          {prices && 'unitPrice' in item && <>
            {!finalPrices && <Text style={[s.cell, s.numeric, { width: widths[priceColumn] }]}>{money(item.unitPrice)}</Text>}
            {discounts && <Text style={[s.cell, s.numeric, { width: widths[priceColumn + 1] }]}>{item.discount != null && item.discount > 0 ? money(item.discount) : '—'}</Text>}
            <Text style={[s.cell, s.numeric, { width: widths[priceColumn + (finalPrices ? 0 : discounts ? 2 : 1)] }]}>{money(item.subtotal)}</Text>
          </>}
    </View>)}
    {!items.length && <Text style={s.empty}>Nenhum item informado.</Text>}
  </View>
}

function Summary({ data }: { data: BudgetPdfData }) {
  const f = data.finance
  const rows: Array<[string, number | null]> = f.kind === 'customer'
    ? [['Total cliente final', f.customerTotal]]
    : f.kind === 'direct'
      ? [['Subtotal', f.total], ...(f.discount != null && f.discount > 0 ? [['Desconto', f.discount] as [string, number | null]] : []), ['Total', f.finalTotal]]
      : [['Valor-base Smart-tec', f.smartTotal], [`Acréscimo parceiro / revenda${f.resellerPercent != null ? ` (${f.resellerPercent.toLocaleString('pt-BR')}%)` : ''}`, f.resellerValue], ...(f.kind==='internal'&&f.rt !== null ? [['RT', f.rt] as [string, number | null]] : []), ...(f.kind==='internal'&&f.bankFee !== null ? [['Taxa bancária', f.bankFee] as [string, number | null]] : []), ['Total cliente final', f.customerTotal]]
  return <View style={s.summary} wrap={false}>
    {rows.map(([label, value], index) => <View key={label} style={index === rows.length - 1 ? [s.summaryRow, s.final] : s.summaryRow}>
      <Text style={s.summaryLabel}>{label}</Text>
      <Text style={index === rows.length - 1 ? s.finalValue : s.summaryValue}>{money(value)}</Text>
    </View>)}
  </View>
}

export function BudgetPdfDocument({ data }: DocumentProps & { data: BudgetPdfData }) {
  const visibility = budgetFinancialVisibility(data.mode)
  return <Document title={`Orçamento ${data.number}`} author={data.company} subject={data.mode === 'reseller_internal' ? 'Interno Smart-tec' : data.mode==='reseller_commercial'?'Comercial da revenda':'Proposta comercial'}>
    <Page size="A4" style={s.page} wrap>
      <View style={s.header} wrap={false}>
        <View style={s.identity}>
          {data.companyLogo && <Image src={data.companyLogo} style={s.logo} />}
          <View style={s.companyBlock}>
            <Text style={s.brand}>{data.company}</Text>
            {data.companyDocument && <Text style={s.secondary}>Documento: {data.companyDocument}</Text>}
          </View>
        </View>
        <View style={s.meta}>
          <Text style={s.title}>ORÇAMENTO Nº {data.number}</Text>
          <Text>Data: {data.date}</Text>
          <Text>Validade: {data.validity}</Text>
          {(data.mode === 'direct'||data.mode === 'reseller_internal') && <Text>Tabela comercial: {data.commercialTable}</Text>}
        </View>
      </View>
      {data.mode === 'reseller_internal' && <Text style={s.internal}>DOCUMENTO INTERNO - NÃO ENVIAR AO CLIENTE</Text>}
      {data.mode === 'reseller_commercial' && <Text style={s.internal}>DEMONSTRATIVO COMERCIAL DA REVENDA - NÃO ENVIAR AO CLIENTE FINAL</Text>}
      <Text style={s.section} minPresenceAhead={45}>CLIENTE</Text>
      <View style={s.customer}>
        <Text style={s.customerName}>{data.customer.name}</Text>
        {data.customer.document && <Text style={s.line}>Documento: {data.customer.document}</Text>}
        {(data.customer.phone || data.customer.email) && <Text style={s.line}>{[data.customer.phone ? `Telefone: ${data.customer.phone}` : '', data.customer.email ? `E-mail: ${data.customer.email}` : ''].filter(Boolean).join('   •   ')}</Text>}
        {data.customer.address && <Text style={s.line}>{data.customer.address}</Text>}
        {data.mode === 'reseller_internal' && <View style={s.commercial}>
          <Text>Revenda: {data.reseller}</Text>
          {data.seller && <Text>Vendedor: {data.seller}</Text>}
          {data.representative && <Text>Representante: {data.representative}</Text>}
        </View>}
        {data.mode === 'reseller_commercial' && <Text style={s.line}>Revenda: {data.reseller}</Text>}
      </View>
      <Text style={s.section} minPresenceAhead={65}>ITENS</Text>
      <ItemTable items={data.products} prices={visibility.itemPrices} finalPrices={data.mode==='reseller_client'||data.mode==='reseller_commercial'} />
      {data.services.length > 0 && <>
        <Text style={s.section} minPresenceAhead={65}>SERVIÇOS</Text>
        <ItemTable items={data.services} prices={visibility.itemPrices} services finalPrices={data.mode==='reseller_client'||data.mode==='reseller_commercial'} />
      </>}
      <Summary data={data} />
      {data.notes && <>
        <Text style={s.section} minPresenceAhead={35}>OBSERVAÇÕES</Text>
        {data.mode==='reseller_client'||data.mode==='reseller_commercial'
          ? data.notes.split('\n\n').map((paragraph,index)=><View key={index} wrap={false}><Text style={s.notes}>{paragraph}</Text></View>)
          : <Text style={s.notes}>{data.notes}</Text>}
      </>}
      {data.mode === 'reseller_internal' && data.internalNotes && <>
        <Text style={s.section} minPresenceAhead={35}>DEMONSTRATIVO E OBSERVAÇÕES INTERNAS — NÃO ENVIAR AO CLIENTE</Text>
        <Text style={s.notes}>{data.internalNotes}</Text>
      </>}
      {data.mode === 'reseller_internal' && data.technicalNotes && <>
        <Text style={s.section} minPresenceAhead={35}>FICHA TÉCNICA INTERNA SMART-TEC</Text>
        {data.technicalNotes.split('\n\n').map((paragraph,index)=><View key={index} wrap={false}><Text style={s.notes}>{paragraph}</Text></View>)}
      </>}
      <View style={s.acceptance} wrap={false}>
        <View style={s.acceptanceFields}>
          <View>
            <View style={s.signature} />
            <Text style={s.acceptanceText}>Nome / assinatura</Text>
          </View>
          <View>
            <View style={s.acceptanceDate} />
            <Text style={s.acceptanceText}>Data: ____ / ____ / ______</Text>
          </View>
        </View>
        {data.validity !== '—' && <Text style={s.acceptanceText}>Proposta válida até {data.validity}.</Text>}
      </View>
      <View style={s.footer} fixed>
        <Text>{data.company} · Orçamento {data.number}</Text>
        <Text render={({ pageNumber, totalPages }) => `${pageNumber} / ${totalPages}`} />
      </View>
    </Page>
  </Document>
}
