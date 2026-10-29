import type { AdminCompanyDetail, AdminFiscalNote } from '../services/admin'
import { fiscalStatus, fiscalDocumentUrl, fiscalErrorText } from '../utils/adminFiscal'
import './adminFiscal.css'
const date=(value?:string|null)=>value?.slice(0,10).split('-').reverse().join('/') || '—'
const money=(value?:number|null)=>value==null?'—':new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(value)
export function AdminFiscalNoteCard({note,company}:{note:AdminFiscalNote;company:AdminCompanyDetail}) {
 const status=fiscalStatus(note.status)
 const payment=company.pagamentos.find(item=>item.id===note.pagamento_id)
 const order=company.pedidos_modulos.find(item=>item.id===payment?.pedido_modulo_id)
 const subscriptionId=note.assinatura_id ?? payment?.assinatura_id
 const subscription=subscriptionId && company.assinatura?.id===subscriptionId?company.assinatura:null
 const origin=payment?.tipo==='MODULO_AVULSO'?'Módulo avulso':subscriptionId?'Assinatura':payment?.tipo==='AJUSTE'?'Ajuste':'—'
 const reference=payment?.tipo==='MODULO_AVULSO' && payment.pedido_modulo_id ? `Pedido #${payment.pedido_modulo_id}${order?.modulo_nome?` · ${order.modulo_nome}`:''}` : subscriptionId ? `Assinatura #${subscriptionId}${subscription?.plano_nome?` · ${subscription.plano_nome}`:''}` : note.referencia_externa || '—'
 const xml=note.status==='EMITIDA'?fiscalDocumentUrl(note.xml_url):null
 const pdf=note.status==='EMITIDA'?fiscalDocumentUrl(note.pdf_url):null
 const error=fiscalErrorText(note.erro_mensagem)
 const errorCode=note.erro_codigo && /^[a-z0-9_.-]{1,100}$/i.test(note.erro_codigo)?note.erro_codigo:null
 const details=[['Número',note.numero],['Série',note.serie],['Protocolo',note.protocolo],['Data de emissão',note.data_emissao?date(note.data_emissao):null]].filter(([,value])=>Boolean(value))
 return <article className="admin-fiscal-card">
  <header className="admin-fiscal-header"><h4>{note.tipo_documento==='NFSE'?'NFS-e':note.tipo_documento} #{note.id}</h4><span className={`admin-fiscal-badge admin-fiscal-badge--${status.tone}`}>{status.label}</span></header>
  <dl className="admin-fiscal-identity"><div><dt>Empresa cliente</dt><dd>{company.empresa.nome}</dd></div><div><dt>Origem</dt><dd>{origin}</dd></div><div><dt>Referência</dt><dd>{reference}</dd>{order?.periodicidade && <dd>{order.periodicidade}</dd>}{subscription?.periodicidade && <dd>{subscription.periodicidade}</dd>}</div></dl>
  {note.pagamento_id && <p className="admin-fiscal-help">Pagamento #{note.pagamento_id}</p>}
  {subscriptionId && (payment?.ciclo_inicio || payment?.ciclo_fim) && <p className="admin-fiscal-help">Ciclo: {date(payment?.ciclo_inicio)} → {date(payment?.ciclo_fim)}</p>}
  <dl className="admin-fiscal-values"><div><dt>Valor do serviço</dt><dd>{money(note.valor_servico)}</dd></div><div><dt>Desconto</dt><dd>{money(note.valor_desconto)}</dd></div><div><dt>Total</dt><dd className="admin-fiscal-total">{money(note.valor_total)}</dd></div></dl>
  {note.status==='PENDENTE' && <p className="admin-fiscal-notice">Este registro ainda não representa uma NFS-e emitida na prefeitura.</p>}
  {note.status==='PROCESSANDO' && <p className="admin-fiscal-notice">Em processamento.</p>}
  {details.length>0 && <dl className="admin-fiscal-details">{details.map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>}
  {note.descricao_servico && <p className="admin-fiscal-help">{note.descricao_servico}</p>}
  {note.status==='ERRO' && (errorCode || error) && <div className="admin-fiscal-error">{errorCode && <strong>Código: {errorCode}</strong>}{error && <p>{error}</p>}</div>}
  {(xml || pdf) && <footer className="admin-fiscal-documents">{xml && <a href={xml} target="_blank" rel="noopener noreferrer">Abrir XML</a>}{pdf && <a href={pdf} target="_blank" rel="noopener noreferrer">Abrir PDF</a>}</footer>}
 </article>
}
