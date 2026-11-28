import type { BudgetPdfMode } from './budgetPdfData'

export type BudgetShareChannel = 'whatsapp' | 'email'

export function budgetShareOptions(hasReseller: boolean): { mode: BudgetPdfMode; label: string }[] {
  return hasReseller
    ? [{ mode: 'reseller_client', label: 'PDF Cliente Final' }, { mode: 'reseller_commercial', label: 'PDF Revenda' }, { mode: 'reseller_internal', label: 'PDF Interno Smart-tec' }]
    : [{ mode: 'direct', label: 'PDF Cliente Final' }]
}

export function budgetShareUrl(channel: BudgetShareChannel, recipient: string, number: string, internal: boolean, documentType = 'Or\u00e7amento') {
  const subject = `${internal ? 'Interno Smart-tec' : documentType} #${number.replace(/[\r\n]/g, ' ')}`
  const message = `${subject}. ${internal ? 'Uso exclusivo da equipe interna. Não encaminhar ao cliente. ' : ''}O PDF será anexado manualmente.`
  if (channel === 'whatsapp') {
    const phone = recipient.replace(/\D/g, '')
    if (recipient.trim() && (!/^\+?[\d\s().-]+$/.test(recipient.trim()) || phone.length < 8 || phone.length > 15)) {
      throw new Error('Informe o telefone com DDI e DDD, ou deixe em branco para escolher no WhatsApp.')
    }
    return `https://wa.me/${phone}?text=${encodeURIComponent(message)}`
  }
  const email = recipient.trim()
  if (email && !/^[^\s@<>,;?&#]+@[^\s@<>,;?&#]+\.[^\s@<>,;?&#]+$/.test(email)) throw new Error('Informe um e-mail válido ou deixe o destinatário em branco.')
  return `mailto:${encodeURIComponent(email)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(message)}`
}

export async function downloadBudgetForShare(id: number, mode: BudgetPdfMode, internalConfirmed: boolean) {
  if (mode === 'reseller_internal' && !internalConfirmed) throw new Error('Confirme que o PDF interno será enviado apenas à equipe Smart-tec.')
  const { prepareSavedBudgetPdf, downloadBudgetPdf } = await import('./budgetPdf')
  const result = await prepareSavedBudgetPdf(id, mode)
  downloadBudgetPdf(result.blob, result.filename)
  return result
}
