export type OrderDestination = 'EM_ANALISE' | 'AGUARDANDO_PAGAMENTO' | 'PAGO' | 'ATIVADO' | 'CANCELADO'
const next: Record<string, { label: string; destination: OrderDestination }> = {
  SOLICITADO: { label: 'Iniciar análise', destination: 'EM_ANALISE' },
  EM_ANALISE: { label: 'Aprovar', destination: 'AGUARDANDO_PAGAMENTO' },
  AGUARDANDO_PAGAMENTO: { label: 'Confirmar pagamento', destination: 'PAGO' },
  PAGO: { label: 'Ativar módulo', destination: 'ATIVADO' },
}
export function orderPresentation(status: string) {
  return {
    primary: next[status],
    cancel: ['SOLICITADO', 'EM_ANALISE', 'AGUARDANDO_PAGAMENTO'].includes(status),
    tone: ({ SOLICITADO: 'neutral', EM_ANALISE: 'review', AGUARDANDO_PAGAMENTO: 'waiting', PAGO: 'paid', ATIVADO: 'active', CANCELADO: 'cancelled' } as Record<string,string>)[status] ?? 'neutral',
  }
}
