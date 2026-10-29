export function moduleAction(origin: string, status: string) {
  if (origin === 'PLANO') return {cancel:false, message:'Este módulo é gerenciado pela assinatura.'}
  if (origin === 'TRIAL') return {cancel:false, message:'Este acesso é gerenciado pelo trial.'}
  return {cancel:['AVULSO','CORTESIA'].includes(origin) && ['ATIVO','PENDENTE'].includes(status), message:''}
}
export function requestModuleOrder(moduleId: string, select: (id: string) => void, openOrders: () => void) {
  select(moduleId)
  openOrders()
}
export function grantCourtesy<T>(activate: (company: number, module: number, input: {
  origem:'CORTESIA'; periodicidade:'CORTESIA'; valor:null; data_fim:string | null; observacoes:string | null
}) => Promise<T>, companyId: number, moduleId: number, end: string, notes: string) {
  return activate(companyId,moduleId,{origem:'CORTESIA',periodicidade:'CORTESIA',valor:null,data_fim:end || null,observacoes:notes.trim() || null})
}
