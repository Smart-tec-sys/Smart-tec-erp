import type { AdminCompanyDetail, AdminPayment } from '../services/admin'
import { financePresentation } from '../utils/adminFinance'
import './adminFinance.css'
const date=(value?:string|null)=>value?.slice(0,10).split('-').reverse().join('/') || '—'
const money=(value:number)=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(value)
type Props={payment:AdminPayment;company:AdminCompanyDetail;canEdit:boolean;busy:boolean;onConfirm:(payment:AdminPayment)=>void}
export function AdminPaymentCard({payment,company,canEdit,busy,onConfirm}:Props){
 const view=financePresentation(payment,company.pedidos_modulos,company.pagamentos,canEdit)
 const order=company.pedidos_modulos.find(item=>item.id===payment.pedido_modulo_id)
 const subscription=company.assinatura?.id===payment.assinatura_id?company.assinatura:null
 return <article className="admin-payment-card">
  <header className="admin-payment-header"><h4>Pagamento #{payment.id}</h4><span className={`admin-payment-badge admin-payment-badge--${view.tone}`}>{payment.status.replaceAll('_',' ')}</span></header>
  <dl className="admin-payment-identity">
   <div><dt>Empresa cliente</dt><dd>{company.empresa.nome}</dd></div>
   <div><dt>Origem</dt><dd>{view.origin}</dd></div>
   <div><dt>Referência</dt><dd>{payment.tipo==='MODULO_AVULSO' ? (payment.pedido_modulo_id ? `Pedido #${payment.pedido_modulo_id}${order?.modulo_nome ? ` · ${order.modulo_nome}` : ''}`:'—') : payment.tipo==='ASSINATURA' ? (payment.assinatura_id ? `Assinatura #${payment.assinatura_id}${subscription?.plano_nome ? ` · ${subscription.plano_nome}` : ''}`:'—') : payment.referencia_externa || '—'}</dd></div>
  </dl>
  {payment.tipo==='ASSINATURA' && <p className="admin-payment-cycle">Ciclo: {date(payment.ciclo_inicio)} → {date(payment.ciclo_fim)}{subscription?.periodicidade && ` · ${subscription.periodicidade}`}</p>}
  <dl className="admin-payment-values"><div><dt>Valor</dt><dd className="admin-payment-amount">{money(payment.valor)}</dd></div><div><dt>Forma de pagamento</dt><dd>{payment.forma_pagamento_nome || payment.forma_pagamento || 'Não informada'}</dd></div></dl>
  <dl className="admin-payment-dates"><div className={payment.status==='ATRASADO'?'admin-payment-overdue':undefined}><dt>Vencimento</dt><dd>{date(payment.vencimento)}</dd></div>{payment.pago_em && <div><dt>Pago em</dt><dd>{date(payment.pago_em)}</dd></div>}</dl>
  {payment.observacoes && <p className="admin-payment-notes">{payment.observacoes}</p>}
  {view.confirm && <footer className="admin-payment-actions"><button type="button" disabled={busy} onClick={()=>onConfirm(payment)}>Confirmar pagamento</button></footer>}
 </article>
}
