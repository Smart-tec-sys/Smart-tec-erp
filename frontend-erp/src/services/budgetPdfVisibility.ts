import type { ApiBudget, ApiBudgetItem } from '../types/budget'

const brl = (value: number) => value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
const amount = '(\\d{1,3}(?:\\.\\d{3})*,\\d{2})'
const value = (text: string) => Number(text.replace(/\./g, '').replace(',', '.'))
const cents = (number: number) => Math.round(number * 100)

export function structuredPaymentNotes(budget: ApiBudget) {
 const parcels = budget.pagamento_parcelas || []
 if (!budget.pagamento_modalidade || parcels.length === 0) return ''
 const total = parcels.reduce((sum, parcel) => sum + cents(parcel.valor), 0)
 if (total !== cents(budget.total_cliente_final ?? budget.total_final) || parcels.some(parcel => !parcel.vencimento || !parcel.forma_pagamento_nome)) {
  throw new Error('Condição de pagamento estruturada divergente do total do orçamento.')
 }
 const labels = { PARCELA: 'Parcela', ENTRADA: 'Entrada', SALDO: 'Saldo' }
 return ['CONDIÇÃO DE PAGAMENTO:', ...parcels.map(parcel => {
  const due = parcel.vencimento.slice(0, 10).split('-').reverse().join('/')
  return `${labels[parcel.tipo]} ${parcel.numero}/${parcels.length} — ${due} — ${parcel.forma_pagamento_nome}: ${brl(parcel.valor)}.`
 })].join('\n')
}

export function externalBudgetNotes(budget: ApiBudget, reseller: boolean) {
 const source = budget.observacao || ''
 const warnings: string[] = []
 const lines: string[] = []
 const prazo = source.match(/^PRAZO DE ENTREGA: (\d+) dias uteis a partir da aprovacao do orcamento, confirmacao das medidas e confirmacao do pagamento inicial\.$/m)
 const garantia = source.match(/^GARANTIA: (\d+) anos contra defeitos de fabricacao\.$/m)
 if (prazo) lines.push(`Prazo de entrega: ${prazo[1]} dias úteis após aprovação, confirmação das medidas e pagamento inicial.`)
 if (garantia) lines.push(`Garantia: ${garantia[1]} anos contra defeitos de fabricação.`)
 const structured = structuredPaymentNotes(budget)
 if (structured) {
  lines.push('', structured)
  if (!reseller) return { notes: lines.join('\n'), warnings }
 }
 const marker = 'CONDICOES DE PAGAMENTO (alternativas, nao cumulativas):\n'
 const payment = source.includes(marker) ? source.slice(source.indexOf(marker) + marker.length) : ''
 if (!payment) {
  if (source.includes(marker)) throw new Error('Condições de pagamento vazias. Revise antes de exportar.')
  if (source) warnings.push('Observações livres não foram incluídas no PDF externo. Confira prazo, garantia e pagamentos antes de enviar.')
  return { notes: lines.join('\n'), warnings }
 }
 // Only the canonical saved payment block is accepted; free text is never copied externally.
 const pattern = new RegExp(
  `^Valor comercial: R\\$ ${amount}\\.\\n` +
  `A vista via Pix: (\\d+(?:,\\d+)?)% de desconto \\(R\\$ ${amount}\\); total R\\$ ${amount}\\.\\n` +
  `Entrada e saldo na instalacao: (\\d+(?:,\\d+)?)% de desconto; total R\\$ ${amount}; entrada de R\\$ ${amount} e saldo na instalacao de R\\$ ${amount}\\.\\n` +
  `Cartao ou link de pagamento em ate (\\d+)x: total R\\$ ${amount}\\. Em (\\d+)x: ((?:R\\$ ${amount})(?: \\+ R\\$ ${amount})*)\\.$`
 )
 const match = payment.match(pattern)
 if (!match) throw new Error('Condições de pagamento sem estrutura reconhecida. Revise o orçamento antes de gerar o PDF externo.')
 const [, priceText, discountText, discountValue, pixText, entryDiscount, entryTotal, entryText, balanceText, countText, cardText, repeatCount, installmentsText] = match
 const price = value(priceText), pix = value(pixText), card = value(cardText)
 const installments = [...installmentsText.matchAll(/R\$ ([\d.,]+)/g)].map(entry => value(entry[1]))
 const count = Number(countText), discount = Number(discountText.replace(',', '.'))
 if (cents(price) !== cents(budget.total_cliente_final ?? NaN) || discount < 0 || discount >= 100 || card < price ||
     cents(price * (1 - discount / 100)) !== cents(pix) ||
     cents(price) - cents(value(discountValue)) !== cents(pix) || value(entryTotal) !== pix ||
     discountText !== entryDiscount || cents(value(entryText)) + cents(value(balanceText)) !== cents(pix) ||
     count < 1 || count > 12 || countText !== repeatCount || installments.length !== count ||
     installments.reduce((sum, item) => sum + cents(item), 0) !== cents(card)) {
  throw new Error('Condições de pagamento divergentes dos valores salvos. Revise antes de exportar.')
 }
 if (!structured) lines.push('', 'CONDIÇÕES DE PAGAMENTO — alternativas, não cumulativas:',
   `Valor comercial: ${brl(price)}.`,
   `À vista via Pix: ${discountText}% de desconto (${brl(value(discountValue))}); total ${brl(pix)}.`,
   `Entrada e saldo na instalação: total ${brl(pix)}; entrada ${brl(value(entryText))} e saldo ${brl(value(balanceText))}.`,
   `Cartão ou link em ${count}x: total ${brl(card)}; parcelas ${installments.map(brl).join(' + ')}.`)
 if (reseller) {
  const repasse = (budget.observacao_interna || '').match(new RegExp(
   `^Pix / entrada e saldo: desconto proporcional de (\\d+(?:,\\d+)?)% = R\\$ ${amount}\\. Cliente paga R\\$ ${amount}; Smart-tec recebe R\\$ ${amount}; parceira recebe R\\$ ${amount}\\.$`, 'm'))
  const base = budget.total_final, partner = budget.valor_parceiro, percent = budget.percentual_parceiro
  if (!repasse || partner == null || !Number.isFinite(base) || !Number.isFinite(partner) ||
      repasse[1] !== discountText || value(repasse[2]) !== value(discountValue) || value(repasse[3]) !== pix ||
      cents(value(repasse[4])) + cents(value(repasse[5])) !== cents(pix) ||
      cents(base) + cents(partner) !== cents(price) || percent == null || !Number.isFinite(percent) ||
      cents(base * percent / 100) !== cents(partner) ||
      cents(base * (1 - discount / 100)) !== cents(value(repasse[4]))) {
   throw new Error('Repasses comerciais não conferem com o orçamento salvo. Revise antes de gerar o PDF da revenda.')
  }
  lines.push('', 'REPASSES COMERCIAIS — projeção, não é recibo:',
   `Sem desconto: Smart-tec ${brl(base)}; revenda ${brl(partner)}.`,
   `Pix ou entrada/saldo: Smart-tec ${brl(value(repasse[4]))}; revenda ${brl(value(repasse[5]))}.`,
   `Cartão: Smart-tec ${brl(base)}; revenda ${brl(partner)}; reserva financeira separada ${brl(card - price)}.`,
   'Os repasses de entrada/saldo referem-se ao pagamento completo. A reserva financeira será conciliada no recebimento.')
 }
 return { notes: lines.join('\n'), warnings }
}

export function externalItemObservation(item: ApiBudgetItem) {
 if (item.tipo_item === 'SERVICO') return ''
 const observation = item.observacao_item?.trim() || ''
 const environment = /^(?:su[ií]te|sala|quarto|cozinha|banheiro|lavabo|escrit[oó]rio|varanda|dormit[oó]rio|[aá]rea)(?: (?:tv|de estar|de jantar|h[oó]spede|h[oó]spedes|casal|infantil|social|gourmet|de servi[cç]o|\d+))*$/i
 return environment.test(observation) ? observation : ''
}

export function finalItemPrices(budget: ApiBudget): number[] {
 const total = budget.total_cliente_final
 const weights = budget.itens.map(item => cents(item.subtotal))
 const sum = weights.reduce((acc, weight) => acc + weight, 0)
 if (total == null || !Number.isFinite(total) || total < 0 || !Number.isSafeInteger(cents(total)) ||
     weights.some(weight => !Number.isSafeInteger(weight) || weight < 0) || !Number.isSafeInteger(sum) || sum <= 0 ||
     budget.itens.some(item => !Number.isFinite(item.quantidade) || item.quantidade <= 0)) {
  throw new Error('Valores dos itens insuficientes para distribuir o preço final. Confira o orçamento.')
 }
 const shares = weights.map(weight => weight / sum * cents(total))
 const result = shares.map(Math.floor)
 const remainder = cents(total) - result.reduce((acc, share) => acc + share, 0)
 const order = shares.map((share, index) => ({ index, fraction: share - result[index] }))
  .sort((a, b) => b.fraction - a.fraction || a.index - b.index)
 for (let index = 0; index < remainder; index++) result[order[index].index]++
 return result.map(share => share / 100)
}
