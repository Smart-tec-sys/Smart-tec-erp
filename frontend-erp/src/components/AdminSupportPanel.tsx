import { useEffect,useRef,useState } from 'react'
import type { FormEvent } from 'react'
import { createAdminSupport,getAdminSupport,getAdminSupportOptions,updateAdminSupport } from '../services/admin'
import type { AdminSupportTicket,AdminSupportOptions,AdminSupportCreate,AdminSupportUpdate } from '../services/admin'
import { AdminSupportCard } from './AdminSupportCard'
import { supportMatches,supportPriorities } from '../utils/adminSupport'
import './adminSupport.css'
type Mode={kind:'new'}|{kind:'edit';ticket:AdminSupportTicket}|{kind:'status';ticket:AdminSupportTicket;status:string}
export function AdminSupportPanel({companyId,permissions,onRefresh}:{companyId:number;permissions:string[];onRefresh:()=>Promise<void>}){
 const [tickets,setTickets]=useState<AdminSupportTicket[]>([]),[options,setOptions]=useState<AdminSupportOptions>({solicitantes:[],responsaveis:[]})
 const [loading,setLoading]=useState(true),[error,setError]=useState(''),[optionError,setOptionError]=useState(''),[busy,setBusy]=useState(false),[filter,setFilter]=useState('todos'),[mode,setMode]=useState<Mode|null>(null),[formError,setFormError]=useState(''),[notice,setNotice]=useState('')
 const dialog=useRef<HTMLDialogElement>(null),trigger=useRef<HTMLElement|null>(null),inFlight=useRef(false)
 const canView=permissions.includes('SUPORTE_VER'),canAttend=permissions.includes('SUPORTE_ATENDER'),canClose=permissions.includes('SUPORTE_ENCERRAR'),canLogs=permissions.includes('SUPORTE_LOGS')
 useEffect(()=>{
  let active=true
  if(!canView){setLoading(false);return}
  setLoading(true);setError('')
  getAdminSupport(companyId).then(data=>{if(active)setTickets(data.items)}).catch(err=>{if(active)setError(err instanceof Error?err.message:'Falha ao carregar chamados.')}).finally(()=>{if(active)setLoading(false)})
  if(canAttend)getAdminSupportOptions(companyId).then(data=>{if(active){setOptions(data);setOptionError('')}}).catch(()=>{if(active)setOptionError('Não foi possível carregar solicitantes e responsáveis. Tente novamente antes de atribuir.')})
  return()=>{active=false}
 },[companyId,canView,canAttend])
 useEffect(()=>{if(mode)dialog.current?.showModal();else {dialog.current?.close();trigger.current?.focus()}},[mode])
 function open(value:Mode){trigger.current=document.activeElement as HTMLElement;setFormError('');setMode(value)}
 async function submit(event:FormEvent<HTMLFormElement>){
  event.preventDefault();if(!mode||inFlight.current)return
  const data=new FormData(event.currentTarget),value=(key:string)=>String(data.get(key)??'').trim(),id=(key:string)=>value(key)?Number(value(key)):null
  let payload:AdminSupportCreate|AdminSupportUpdate
  if(mode.kind==='new')payload={titulo:value('titulo'),descricao:value('descricao'),prioridade:value('prioridade'),usuario_id:id('usuario_id'),responsavel_equipe_id:id('responsavel_equipe_id'),pagina:value('pagina'),erro_codigo:value('erro_codigo'),erro_mensagem:value('erro_mensagem')}
  else if(mode.kind==='edit')payload={prioridade:value('prioridade'),...(optionError?{}:{responsavel_equipe_id:id('responsavel_equipe_id')})}
  else payload={status:mode.status,...(mode.status==='RESOLVIDO'?{resolucao:value('resolucao')}:{})}
  inFlight.current=true;setBusy(true);setFormError('');setNotice('')
  try{
   const ticket=mode.kind==='new'?await createAdminSupport(companyId,payload as AdminSupportCreate):await updateAdminSupport(companyId,mode.ticket.id,payload as AdminSupportUpdate)
   setTickets(current=>[ticket,...current.filter(item=>item.id!==ticket.id)].sort((a,b)=>b.id-a.id));setMode(null);setNotice('Chamado salvo.')
   try{await onRefresh()}catch{setNotice('Chamado salvo. O resumo da empresa não pôde ser atualizado.')}
  }catch(err){setFormError(err instanceof Error?err.message:'Não foi possível salvar o chamado.')}
  finally{inFlight.current=false;setBusy(false)}
 }
 if(!canView)return <article className="panel admin-support"><h3>Suporte</h3><p>Sem permissão para consultar chamados.</p></article>
 return <article className="panel admin-support">
  <div className="admin-support-top"><div><h3>Suporte</h3><p>Atendimento e acompanhamento dos chamados desta empresa.</p></div>{canAttend&&<button type="button" disabled={busy} onClick={()=>open({kind:'new'})}>Novo chamado</button>}</div>
  {notice&&<p role="status">{notice}</p>}{error&&<p role="alert">{error}</p>}
  <label className="admin-support-filter">Exibir<select value={filter} onChange={event=>setFilter(event.target.value)}><option value="todos">Todos</option><option value="abertos">Abertos</option><option value="andamento">Em andamento</option><option value="cliente">Aguardando cliente</option><option value="resolvidos">Resolvidos/Fechados</option></select></label>
  {loading?<p role="status">Carregando chamados…</p>:!error&&<div className="admin-support-list">{tickets.filter(ticket=>supportMatches(ticket.status,filter)).map(ticket=><AdminSupportCard key={ticket.id} ticket={ticket} canAttend={canAttend} canClose={canClose} canLogs={canLogs} busy={busy} onAction={(ticket,status)=>open({kind:'status',ticket,status})} onEdit={ticket=>open({kind:'edit',ticket})}/>)}{!tickets.filter(ticket=>supportMatches(ticket.status,filter)).length&&<p>{tickets.length?'Nenhum chamado neste filtro.':'Nenhum chamado registrado.'}</p>}</div>}
  <dialog ref={dialog} className="admin-support-dialog" aria-labelledby="support-dialog-title" onCancel={event=>{event.preventDefault();if(!busy)setMode(null)}}>
   {mode&&<form onSubmit={event=>void submit(event)}><h3 id="support-dialog-title">{mode.kind==='new'?'Novo chamado':mode.kind==='edit'?'Responsável e prioridade':mode.status==='RESOLVIDO'?'Resolver chamado':mode.status==='FECHADO'?'Fechar chamado':'Alterar situação'}</h3>
   {mode.kind!=='new'&&<p>{mode.ticket.codigo} · {mode.ticket.titulo}</p>}
   {mode.kind==='new'&&<><label>Título<input name="titulo" required maxLength={200} autoFocus /></label><label>Descrição<textarea name="descricao" maxLength={10000}/></label></>}
   {mode.kind!=='status'&&<><label>Prioridade<select name="prioridade" defaultValue={mode.kind==='edit'?mode.ticket.prioridade:'NORMAL'}>{Object.entries(supportPriorities).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>{optionError&&<p role="alert">{optionError}</p>}{mode.kind==='new'&&<label>Solicitante<select name="usuario_id" disabled={Boolean(optionError)}><option value="">Não informado</option>{options.solicitantes.map(item=><option value={item.id} key={item.id}>{item.nome}</option>)}</select></label>}<label>Responsável<select name="responsavel_equipe_id" disabled={Boolean(optionError)} defaultValue={mode.kind==='edit'?mode.ticket.responsavel_equipe_id??'':''}><option value="">Não atribuído</option>{mode.kind==='edit'&&mode.ticket.responsavel_equipe_id&&!options.responsaveis.some(item=>item.id===mode.ticket.responsavel_equipe_id)&&<option value={mode.ticket.responsavel_equipe_id}>{mode.ticket.responsavel_nome||'Responsável atual'} (indisponível)</option>}{options.responsaveis.map(item=><option value={item.id} key={item.id}>{item.nome}</option>)}</select></label></>}
   {mode.kind==='new'&&<details><summary>Dados técnicos (opcionais)</summary><label>Página<input name="pagina" maxLength={200}/></label><label>Código de erro<input name="erro_codigo" maxLength={100}/></label><label>Mensagem de erro<textarea name="erro_mensagem" maxLength={10000}/></label><small>Não informe senhas, tokens ou cabeçalhos de autenticação.</small></details>}
   {mode.kind==='status'&&(mode.status==='RESOLVIDO'?<label>Resolução<textarea name="resolucao" required maxLength={10000} autoFocus/></label>:<p>Confirmar {mode.status==='FECHADO'?'fechamento definitivo do chamado':'mudança de situação do chamado'}?</p>)}
   {formError&&<p role="alert">{formError}</p>}<footer><button type="button" disabled={busy} onClick={()=>setMode(null)}>Cancelar</button><button type="submit" disabled={busy}>{busy?'Salvando…':'Salvar'}</button></footer></form>}
  </dialog>
 </article>
}
