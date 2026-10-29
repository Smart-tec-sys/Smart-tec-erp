export function localDate(today = new Date()) {
  return `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')}`
}
export function trialDays(end: string | null | undefined, today = localDate()) {
  if (!end) return 0
  return Math.max(0, Math.ceil((Date.parse(end + 'T00:00:00Z') - Date.parse(today + 'T00:00:00Z')) / 86400000))
}
export function subscriptionError(error: unknown) {
  const message = error instanceof Error ? error.message : String(error)
  if (/AVULSO|CORTESIA/.test(message)) return `O plano inclui um módulo com vínculo independente. Revise os módulos antes de continuar. ${message}`
  return message
}
// Save the ID before billing: a failed second request must never recreate the contract.
export async function prepareAndCharge(
  create: () => Promise<{assinatura_id: number}>,
  charge: (id: number) => Promise<unknown>,
  remember: (id: number) => void,
) {
  const contract = await create()
  remember(contract.assinatura_id)
  await charge(contract.assinatura_id)
}
