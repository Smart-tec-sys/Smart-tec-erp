export const supportStatuses:Record<string,string>={ABERTO:'Aberto',EM_ANALISE:'Em análise',AGUARDANDO_CLIENTE:'Aguardando cliente',EM_CORRECAO:'Em correção',RESOLVIDO:'Resolvido',FECHADO:'Fechado'}
export const supportPriorities:Record<string,string>={BAIXA:'Baixa',NORMAL:'Normal',ALTA:'Alta',CRITICA:'Crítica'}
export const supportActions:Record<string,Array<{status:string;label:string}>>={
 ABERTO:[{status:'EM_ANALISE',label:'Iniciar análise'}],
 EM_ANALISE:[{status:'AGUARDANDO_CLIENTE',label:'Aguardar cliente'},{status:'EM_CORRECAO',label:'Iniciar correção'}],
 AGUARDANDO_CLIENTE:[{status:'EM_ANALISE',label:'Retomar análise'},{status:'EM_CORRECAO',label:'Iniciar correção'}],
 EM_CORRECAO:[{status:'AGUARDANDO_CLIENTE',label:'Aguardar cliente'},{status:'RESOLVIDO',label:'Resolver'}],
 RESOLVIDO:[{status:'FECHADO',label:'Fechar'}],FECHADO:[]
}
export function visibleSupportActions(status:string,attend:boolean,close:boolean){return attend?(supportActions[status]??[]).filter(action=>!['RESOLVIDO','FECHADO'].includes(action.status)||close):[]}
export function supportMatches(status:string,filter:string){return filter==='todos'||(filter==='abertos'&&status==='ABERTO')||(filter==='andamento'&&['EM_ANALISE','EM_CORRECAO'].includes(status))||(filter==='cliente'&&status==='AGUARDANDO_CLIENTE')||(filter==='resolvidos'&&['RESOLVIDO','FECHADO'].includes(status))}
export function supportText(value?:string|null){return value && /traceback|stack\s*trace|(?:^|\n)\s*at\s+\S+\s*\([^)]*:\d+|bearer\s|authorization|password|senha|secret|token|api[_ -]?key|eyJ[\w-]+\.|^\s*[\{\[]/i.test(value)?'Detalhes técnicos sensíveis não são exibidos.':value}
