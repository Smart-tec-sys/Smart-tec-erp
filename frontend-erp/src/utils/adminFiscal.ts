export function fiscalStatus(status:string) {
 return ({PENDENTE:{label:'Preparada para emissão',tone:'pending'},PROCESSANDO:{label:'Em processamento',tone:'processing'},EMITIDA:{label:'Emitida',tone:'issued'},ERRO:{label:'Erro na emissão',tone:'error'},CANCELADA:{label:'Cancelada',tone:'cancelled'}} as Record<string,{label:string;tone:string}>)[status] ?? {label:status.replaceAll('_',' '),tone:'processing'}
}
export function fiscalDocumentUrl(value?:string|null) {
 if(!value) return null
 try { const url=new URL(value); return ['http:','https:'].includes(url.protocol) && !url.username && !url.password ? url.href : null } catch { return null }
}
export function fiscalErrorText(value?:string|null) {
 if(!value?.trim()) return null
 const text=value.trim()
 if(/traceback|stack\s*trace|\bat\s+\S+\s*\([^)]*:\d+|bearer\s|eyJ[A-Za-z0-9_-]+\.|password|senha|secret|token|api[_ -]?key|authorization|payload|^[{[]/i.test(text)) return 'Não foi possível concluir a emissão. Detalhes técnicos não são exibidos nesta tela.'
 return text.slice(0,1200)
}
