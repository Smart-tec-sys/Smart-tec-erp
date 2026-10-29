type Factor = {id?: string; factor_type?: string; status?: string}
type Steps<T> = {
  factors: () => Promise<Factor[]>
  challenge: (factorId: string) => Promise<{id?: string}>
  profile: () => Promise<T>
  markProfile: () => void
}
export class LoginAccessError extends Error {
  readonly stage: 'security' | 'profile'
  constructor(stage: 'security' | 'profile', cause: unknown) {
    const detail = cause instanceof Error ? cause.message : String(cause)
    const safeDetail = /invalid login credentials/i.test(detail) ? '' : ` ${detail}`
    super(`Login confirmado, mas não foi possível ${stage === 'security' ? 'concluir a verificação de segurança' : 'carregar seu acesso ao ERP'}.${safeDetail} Tente novamente.`)
    this.stage = stage
    this.cause = cause
  }
}
export async function resolveLoginAccess<T>(steps: Steps<T>, checkSecurity: boolean): Promise<
  {kind:'mfa';factorId:string;challengeId:string} | {kind:'ready';session:T}
> {
  if (checkSecurity) {
    try {
      const factor = (await steps.factors()).find(item => item.factor_type === 'totp' && item.status === 'verified')
      if (factor?.id) {
        const challenge = await steps.challenge(factor.id)
        if (!challenge.id) throw new Error('Confirmação de segurança indisponível.')
        return {kind:'mfa',factorId:factor.id,challengeId:challenge.id}
      }
      steps.markProfile()
    } catch (error) { throw new LoginAccessError('security',error) }
  }
  try { return {kind:'ready',session:await steps.profile()} }
  catch (error) { throw new LoginAccessError('profile',error) }
}
