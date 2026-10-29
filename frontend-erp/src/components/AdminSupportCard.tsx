import type { AdminSupportTicket } from '../services/admin'
import { supportStatuses,supportPriorities,visibleSupportActions,supportText } from '../utils/adminSupport'
import './adminSupport.css'
const date=(value?:string|null)=>value?new Date(value).toLocaleString('pt-BR'):'—'
const technicalFields=['pagina','request_id','navegador','dispositivo','versao_frontend','versao_backend','erro_codigo','erro_mensagem'] as const
const technicalLabels=['Página','Request ID','Navegador','Dispositivo','Versão frontend','Versão backend','Código de erro','Mensagem de erro']
export function AdminSupportCard({ticket,canAttend,canClose,canLogs,busy,onAction,onEdit}:{ticket:AdminSupportTicket;canAttend:boolean;canClose:boolean;canLogs:boolean;busy:boolean;onAction:(ticket:AdminSupportTicket,status:string)=>void;onEdit:(ticket:AdminSupportTicket)=>void}){
 const actions=visibleSupportActions(ticket.status,canAttend,canClose)
 return <article className="admin-support-card">
  <header><strong>{ticket.codigo||`Chamado #${ticket.id}`}</strong><span className="admin-support-badge">{supportStatuses[ticket.status]??ticket.status}</span></header>
  <h4>{supportText(ticket.titulo)}</h4>
  <dl><div><dt>Empresa cliente</dt><dd>{ticket.empresa_nome}</dd></div><div><dt>Prioridade</dt><dd><span className={`admin-support-badge priority-${ticket.prioridade.toLowerCase()}`}>{supportPriorities[ticket.prioridade]}</span></dd></div><div><dt>Responsável</dt><dd>{ticket.responsavel_nome||'Não atribuído'}</dd></div><div><dt>Solicitante</dt><dd>{ticket.solicitante_nome||'—'}</dd></div><div><dt>Criado em</dt><dd>{date(ticket.criado_em)}</dd></div><div><dt>Atualizado em</dt><dd>{date(ticket.atualizado_em)}</dd></div></dl>
  {ticket.descricao&&<p className="admin-support-text">{supportText(ticket.descricao)}</p>}
  {ticket.resolucao&&<div className="admin-support-resolution"><strong>Resolução</strong><p>{supportText(ticket.resolucao)}</p>{ticket.resolvido_em&&<small>Resolvido em {date(ticket.resolvido_em)}</small>}</div>}
  {canLogs&&technicalFields.some(field=>ticket[field])&&<details><summary>Dados técnicos</summary><dl>{technicalFields.map((field,index)=>ticket[field]&&<div key={field}><dt>{technicalLabels[index]}</dt><dd>{supportText(ticket[field])}</dd></div>)}</dl></details>}
  {(actions.length>0||(canAttend&&ticket.status!=='FECHADO'))&&<footer>{actions.map(action=><button type="button" key={action.status} disabled={busy} onClick={()=>onAction(ticket,action.status)}>{action.label}</button>)}{canAttend&&ticket.status!=='FECHADO'&&<button type="button" disabled={busy} onClick={()=>onEdit(ticket)}>Responsável / prioridade</button>}</footer>}
 </article>
}
