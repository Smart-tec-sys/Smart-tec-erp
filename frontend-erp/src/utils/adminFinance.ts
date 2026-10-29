type Payment = {id:number; tipo:string; status:string; pedido_modulo_id?:number|null; assinatura_id?:number|null; ciclo_inicio?:string|null; ciclo_fim?:string|null}
type Order = {id:number;status:string}
export function financePresentation(payment: Payment, orders: Order[], payments: Payment[], canEdit: boolean) {
  const origin = ({MODULO_AVULSO:'Módulo avulso',ASSINATURA:'Assinatura',AJUSTE:'Ajuste'} as Record<string,string>)[payment.tipo] ?? payment.tipo.replaceAll('_',' ')
  const tone = ({PENDENTE:'pending',PROCESSANDO:'processing',PAGO:'paid',ATRASADO:'late',CANCELADO:'cancelled',ESTORNADO:'refunded'} as Record<string,string>)[payment.status] ?? 'processing'
  const open = ['PENDENTE','PROCESSANDO','ATRASADO'].includes(payment.status)
  const order = orders.find(item=>item.id===payment.pedido_modulo_id)
  const latest = Math.max(0,...payments.filter(item=>item.pedido_modulo_id===payment.pedido_modulo_id).map(item=>item.id))
  const confirm = canEdit && open && (payment.tipo==='ASSINATURA'
    ? Boolean(payment.assinatura_id && payment.ciclo_inicio && payment.ciclo_fim)
    : payment.tipo==='MODULO_AVULSO' && order?.status==='AGUARDANDO_PAGAMENTO' && payment.id===latest)
  return {origin,tone,confirm}
}
