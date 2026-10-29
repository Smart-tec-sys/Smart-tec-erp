import { useEffect, useRef, useState } from 'react'
import { createAdminSubscription, createAdminSubscriptionCharge, confirmAdminSubscriptionPayment, startAdminTrial,
  type AdminCompanyDetail, type AdminPlan, type AdminPaymentMethod } from '../services/admin'
import { localDate, trialDays, subscriptionError, prepareAndCharge } from '../utils/adminSubscription'
import './adminSubscriptionPanel.css'

type Props = {
  company: AdminCompanyDetail; plans: AdminPlan[]; permissions: string[]
  paymentMethods: AdminPaymentMethod[]; paymentMethodsError: string; paymentMethodId: string
  onPaymentMethodChange: (id: string) => void; onRegisterPaymentMethod: () => void
  onRefresh: () => Promise<void>
}
const money = (value?: number | null) => value == null ? '—' : new Intl.NumberFormat('pt-BR', {style:'currency',currency:'BRL'}).format(value)
const date = (value?: string | null) => !value ? '—' : new Intl.DateTimeFormat('pt-BR').format(new Date(value.slice(0,10)+'T12:00:00'))
const payable = ['PENDENTE','PROCESSANDO','ATRASADO']
export function AdminSubscriptionPanel(props: Props) {
  const {company, plans, permissions, paymentMethods, paymentMethodsError, paymentMethodId, onPaymentMethodChange, onRegisterPaymentMethod, onRefresh} = props
  const subscription = company.assinatura
  const canContract = permissions.includes('ASSINATURAS_EDITAR')
  const canBill = permissions.includes('FINANCEIRO_EDITAR')
  const trial = !!subscription && ['TRIAL','TRIAL_EXPIRADO'].includes(subscription.status)
  const renewal = !!subscription && ['ATIVA','PROXIMA_VENCIMENTO'].includes(subscription.status)
  const history = (company.cobrancas_assinatura ?? company.pagamentos).filter(p => p.tipo === 'ASSINATURA')
  const currentCharges = history.filter(p => p.assinatura_id === subscription?.id)
  const openCharge = currentCharges.some(p => payable.includes(p.status))
  const contractTerms = subscription && subscription.status !== 'CANCELADA' && (!trial || (subscription.forma_pagamento_id != null && subscription.valor != null)) ? subscription : null
  const [planId,setPlanId] = useState(String(subscription?.plano_id ?? ''))
  const [period,setPeriod] = useState<''|'MENSAL'|'ANUAL'>(contractTerms?.periodicidade === 'MENSAL' || contractTerms?.periodicidade === 'ANUAL' ? contractTerms.periodicidade : '')
  const [value,setValue] = useState(contractTerms?.valor == null ? '' : String(contractTerms.valor))
  const [auto,setAuto] = useState(subscription?.renovacao_automatica ?? false)
  const [notes,setNotes] = useState(subscription?.observacoes ?? '')
  const [start,setStart] = useState(subscription?.data_fim_trial && subscription.data_fim_trial > localDate() ? subscription.data_fim_trial : localDate())
  const [due,setDue] = useState(localDate())
  const [preparedId,setPreparedId] = useState<number | null>(null)
  const [busy,setBusy] = useState(false)
  const lock = useRef(false)
  const [error,setError] = useState('')
  const [message,setMessage] = useState('')
  const [refreshRequired,setRefreshRequired] = useState(false)
  const formLocked = (trial && subscription?.forma_pagamento_id != null && subscription.valor != null) || preparedId != null || (!!subscription && !trial && subscription.status !== 'CANCELADA') || currentCharges.some(p => p.status !== 'CANCELADO')
  const existingId = preparedId ?? (subscription?.status === 'PENDENTE' || (trial && subscription?.forma_pagamento_id && subscription.valor != null) ? subscription.id : null)
  const initialAvailable = !subscription || trial || subscription.status === 'CANCELADA' || subscription.status === 'PENDENTE'
  useEffect(() => { onPaymentMethodChange(String(subscription?.forma_pagamento_id ?? '')) }, [company.empresa.id, subscription?.forma_pagamento_id, onPaymentMethodChange])

  async function refresh() {
    try { await onRefresh(); setRefreshRequired(false) }
    catch { setRefreshRequired(true); setError('A operação foi salva, mas a consulta não foi atualizada. Atualize os dados antes de continuar.') }
  }
  async function action(operation: () => Promise<unknown>, success: string) {
    if (lock.current) return
    lock.current = true; setBusy(true); setError(''); setMessage('')
    try { await operation(); setMessage(success); await refresh() }
    catch (err) { setError(subscriptionError(err)); await refresh() }
    finally { lock.current = false; setBusy(false) }
  }
  async function generateInitial() {
    if (!start || !due || due > start || start < localDate() || (trial && subscription?.data_fim_trial && start < subscription.data_fim_trial)) {
      setError('Informe início válido e vencimento da cobrança até o início do ciclo, respeitando o fim do trial.'); return
    }
    const charge = (id: number) => createAdminSubscriptionCharge(id,{ciclo_inicio:start,vencimento:due})
    if (existingId) { await action(() => charge(existingId),'Cobrança inicial criada. O acesso permanece inalterado até a confirmação.'); return }
    if (period !== 'MENSAL' && period !== 'ANUAL') { setError('Selecione a periodicidade mensal ou anual para o contrato.'); return }
    const amount = Number(value.replace(',','.'))
    if (!planId || !paymentMethodId || !Number.isFinite(amount) || amount <= 0) { setError('Informe plano, valor contratado maior que zero e forma de pagamento.'); return }
    await action(() => prepareAndCharge(
      () => createAdminSubscription(company.empresa.id,{plano_id:Number(planId),periodicidade:period,valor:amount,forma_pagamento_id:Number(paymentMethodId),renovacao_automatica:auto,observacoes:notes || null,...(trial ? {trial_id:subscription!.id} : {})}),
      charge, setPreparedId,
    ),'Contrato preparado e cobrança criada. Os módulos serão ativados somente após a confirmação.')
  }
  const additional = company.modulos.filter(m => m.status === 'ATIVO' && ['AVULSO','CORTESIA'].includes(m.origem))
  return <article className="panel admin-subscription">
    <header><h3>Assinatura e trial</h3><p>Contrato, cobranças e renovação do plano da empresa cliente.</p></header>
    {error && <p role="alert" className="subscription-error">{error}</p>}
    {message && <p role="status" className="subscription-message">{message}</p>}
    {refreshRequired && <button type="button" className="secondary-button" disabled={busy} onClick={() => void action(async () => {}, 'Dados consultados novamente.')}>Atualizar dados</button>}
    {subscription ? <section><h4>Resumo da assinatura</h4><dl className="subscription-grid">
      {[
        ['Plano base',subscription.plano_nome ?? subscription.plano_codigo ?? '—'],['Status',subscription.status],
        ['Periodicidade',subscription.periodicidade ?? '—'],['Valor contratado',money(subscription.valor)],
        ['Forma de pagamento',subscription.forma_pagamento_nome ?? (subscription.forma_pagamento_id ? `Forma #${subscription.forma_pagamento_id}` : '—')],
        ['Início',date(subscription.data_inicio_assinatura)],['Próximo vencimento',date(subscription.data_vencimento)],
        ['Renovação automática',subscription.renovacao_automatica ? 'Sim' : 'Não'],
        ...(subscription.data_inicio_trial ? [['Início do trial',date(subscription.data_inicio_trial)],['Fim do trial',date(subscription.data_fim_trial)],...(trial ? [['Dias restantes',String(trialDays(subscription.data_fim_trial))]] : [])] : []),
        ['Observações',subscription.observacoes || '—'],
      ].map(([label,content]) => <div key={label}><dt>{label}</dt><dd>{content}</dd></div>)}
    </dl></section> : <p>Nenhuma assinatura ou trial cadastrado.</p>}
    {initialAvailable && <section><h4>{trial ? 'Conversão do trial' : existingId ? 'Cobrança inicial' : 'Nova contratação'}</h4>
      <p>O contrato e a cobrança não antecipam o acesso. O trial mantém suas datas.</p>
      <fieldset disabled={busy || refreshRequired || !canContract || formLocked} className="subscription-grid">
        <label>Plano<select value={planId} onChange={e => { setPlanId(e.target.value); setPeriod(''); setValue('') }}><option value="">Selecione o plano</option>{plans.filter(p=>p.ativo).map(p=><option key={p.id} value={p.id}>{p.nome} · {p.periodicidade}</option>)}</select></label>
        <label>Periodicidade<select value={period} onChange={e=>{ const next = e.target.value as ''|'MENSAL'|'ANUAL'; if (next !== period) setValue(''); setPeriod(next) }}><option value="">Selecione a periodicidade</option><option value="MENSAL">Mensal</option><option value="ANUAL">Anual</option></select></label>
        <label>Valor contratado<input inputMode="decimal" value={value} onChange={e=>setValue(e.target.value)} placeholder="0,00" /></label>
        <label>Forma de pagamento<select value={paymentMethodId} onChange={e => e.target.value==='__new__' ? onRegisterPaymentMethod() : onPaymentMethodChange(e.target.value)}><option value="">Selecione a forma de pagamento</option>{paymentMethods.map(m=><option key={m.id} value={m.id}>{m.nome}</option>)}{canBill && <option value="__new__">+ Cadastrar nova forma de pagamento</option>}</select>{paymentMethodsError && <small role="alert">{paymentMethodsError}</small>}</label>
        <label className="subscription-check"><input type="checkbox" checked={auto} onChange={e=>setAuto(e.target.checked)} />Renovação automática</label>
        <label>Observações<textarea rows={2} value={notes} onChange={e=>setNotes(e.target.value)} /></label>
      </fieldset>
      {!plans.some(p=>p.ativo) && <p>Nenhum plano comercial cadastrado. O trial pode ser iniciado sem plano.</p>}
      {formLocked && <p>A composição do contrato está salva. Gere a cobrança usando os valores contratados.</p>}
      <div className="subscription-grid">
        <label>Início do período<input type="date" value={start} min={trial && subscription?.data_fim_trial && subscription.data_fim_trial>localDate() ? subscription.data_fim_trial : localDate()} disabled={busy || openCharge} onChange={e=>setStart(e.target.value)} /></label>
        <label>Vencimento da cobrança<input type="date" value={due} max={start} disabled={busy || openCharge} onChange={e=>setDue(e.target.value)} /></label>
      </div>
      <div className="subscription-actions">
        {canContract && canBill && <button className="primary-button" disabled={busy || refreshRequired || openCharge} onClick={()=>void generateInitial()}>{existingId ? 'Gerar cobrança inicial' : trial ? 'Preparar contrato e cobrança' : 'Gerar contrato e cobrança'}</button>}
        {canContract && !subscription && <button className="secondary-button" disabled={busy || refreshRequired} onClick={()=>void action(()=>startAdminTrial(company.empresa.id,{plano_id:planId ? Number(planId):null,dias:7}),'Teste gratuito de 7 dias iniciado.')}>Iniciar teste grátis — 7 dias</button>}
      </div>
      {openCharge && <p>Já existe cobrança em aberto. Consulte o histórico abaixo.</p>}
    </section>}
    {renewal && <section><h4>Renovação</h4><p>Próximo ciclo começa em {date(subscription.data_vencimento)}. O vencimento do contrato só avança após o pagamento.</p>
      <label>Vencimento da próxima cobrança<input type="date" value={due} max={subscription.data_vencimento ?? undefined} disabled={busy || openCharge} onChange={e=>setDue(e.target.value)} /></label>
      {canBill && <button className="primary-button" disabled={busy || refreshRequired || openCharge || !due || !subscription.data_vencimento || due>subscription.data_vencimento} onClick={()=>void action(()=>createAdminSubscriptionCharge(subscription.id,{vencimento:due}),'Próxima cobrança criada. O vencimento do contrato foi preservado.')}>Gerar próxima cobrança</button>}
      {openCharge && <p>Existe cobrança em aberto para esta assinatura.</p>}
    </section>}
    <section><h4>Histórico de cobranças</h4>{!history.length ? <p>Nenhuma cobrança de assinatura registrada.</p> : <div className="subscription-history">{history.map(p=><article key={p.id} className="subscription-charge" aria-label={`Cobrança #${p.id}`}>
      <strong>Cobrança #{p.id} · Assinatura #{p.assinatura_id}</strong><span className="subscription-status">{p.status}</span>
      <dl className="subscription-grid">
        {[
          ['Ciclo',p.ciclo_inicio && p.ciclo_fim ? `${date(p.ciclo_inicio)} → ${date(p.ciclo_fim)}` : '—'],
          ['Vencimento',date(p.vencimento)],['Valor',money(p.valor)],['Forma de pagamento',p.forma_pagamento_nome ?? p.forma_pagamento ?? '—'],['Pago em',date(p.pago_em)],
        ].map(([label,content])=><div key={label}><dt>{label}</dt><dd>{content}</dd></div>)}
      </dl>
      {canBill && payable.includes(p.status) && <button className="secondary-button" disabled={busy || refreshRequired} onClick={()=>{
        if(window.confirm(`Confirmar o pagamento da cobrança #${p.id} de ${money(p.valor)}?`)) void action(()=>confirmAdminSubscriptionPayment(p.id),'Pagamento confirmado. Assinatura e módulos atualizados pelo ciclo F1.')
      }}>Confirmar pagamento</button>}
    </article>)}</div>}</section>
    <section><h4>Módulos adicionais ativos</h4><p>Contratações independentes do plano. Valores mensais e anuais permanecem separados.</p>{!additional.length ? <p>Nenhum módulo adicional ativo.</p> : <div className="subscription-additional">{additional.map(m=><div key={m.id}><strong>{m.nome}</strong><span>{m.periodicidade ?? '—'} · {money(m.valor)} · {m.origem}</span></div>)}</div>}</section>
  </article>
}
