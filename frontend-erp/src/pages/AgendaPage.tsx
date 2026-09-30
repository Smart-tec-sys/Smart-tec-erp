import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ArrowLeft, CalendarDays, MapPin, Pencil, Plus, RefreshCw, Trash2 } from 'lucide-react'
import {
  AGENDA_LIMIT, atualizarAgenda, criarAgenda, dataHoraLocal, dataLocal,
  limiteDia, listarAgenda, removerAgenda, type AgendaCampos, type AgendaEvento,
} from '../services/agenda'
import './agendaPage.css'

const CATEGORIAS = ['GERAL', 'REUNIAO', 'VISITA', 'ATENDIMENTO', 'SERVICO', 'INSTALACAO', 'ENTREGA', 'MANUTENCAO', 'TREINAMENTO', 'COBRANCA', 'TAREFA']
const STATUS = ['AGENDADO', 'CONFIRMADO', 'EM_ANDAMENTO', 'CONCLUIDO', 'CANCELADO', 'ARQUIVADO']
const nomes: Record<string, string> = {
  GERAL: 'Geral', REUNIAO: 'Reunião', VISITA: 'Visita', ATENDIMENTO: 'Atendimento',
  SERVICO: 'Serviço', INSTALACAO: 'Instalação', ENTREGA: 'Entrega', MANUTENCAO: 'Manutenção',
  TREINAMENTO: 'Treinamento', COBRANCA: 'Cobrança', TAREFA: 'Tarefa',
  AGENDADO: 'Agendado', CONFIRMADO: 'Confirmado', EM_ANDAMENTO: 'Em andamento',
  CONCLUIDO: 'Concluído', CANCELADO: 'Cancelado', ARQUIVADO: 'Arquivado',
}
const nome = (value: string) => nomes[value] || value
const normalize = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR')
const mensagemErro = (error: unknown) => error instanceof Error ? error.message : 'Não foi possível concluir a operação.'

function novoFormulario(): AgendaCampos {
  const now = new Date()
  now.setSeconds(0, 0)
  return {
    titulo: '', categoria: 'GERAL', status: 'AGENDADO', inicio: dataHoraLocal(now.toISOString()),
    fim: '', dia_inteiro: false, cliente_nome: '', responsavel_nome: '',
    local: '', endereco: '', descricao: '', observacoes: '',
  }
}

function periodoInicial() {
  const now = new Date()
  return { de: dataLocal(new Date(now.getFullYear(), now.getMonth(), 1)), ate: dataLocal(new Date(now.getFullYear(), now.getMonth() + 1, 0)) }
}

export function AgendaPage({ newRequest, onChanged, onBack }: {
  newRequest: number
  onChanged: () => void
  onBack: () => void
}) {
  const [periodo, setPeriodo] = useState(periodoInicial)
  const [categoria, setCategoria] = useState('')
  const [status, setStatus] = useState('')
  const [busca, setBusca] = useState('')
  const [events, setEvents] = useState<AgendaEvento[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [revision, setRevision] = useState(0)
  const [editing, setEditing] = useState<AgendaEvento | null>(null)
  const [form, setForm] = useState<AgendaCampos>(novoFormulario)
  const [formOpen, setFormOpen] = useState(newRequest > 0)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)
  const busyRef = useRef(false)
  const [deleting, setDeleting] = useState<AgendaEvento | null>(null)
  const titleRef = useRef<HTMLInputElement>(null)
  const invalidPeriod = Boolean(periodo.de && periodo.ate && periodo.de > periodo.ate)

  useEffect(() => {
    if (newRequest > 0 && !busyRef.current) {
      setEditing(null); setForm(novoFormulario()); setFormError(''); setFormOpen(true)
      titleRef.current?.focus()
    }
  }, [newRequest])

  useEffect(() => {
    if (formOpen) titleRef.current?.focus()
  }, [formOpen, editing])

  useEffect(() => {
    const controller = new AbortController()
    if (invalidPeriod) { setLoading(false); return () => controller.abort() }
    setLoading(true)
    setError('')
    listarAgenda({
      inicio_de: periodo.de ? limiteDia(periodo.de) : undefined,
      inicio_ate: periodo.ate ? limiteDia(periodo.ate, true) : undefined,
      categoria, status,
    }, controller.signal).then(data => {
      if (!controller.signal.aborted) setEvents([...data].sort((a, b) => Date.parse(a.inicio) - Date.parse(b.inicio)))
    }).catch(err => {
      if (!controller.signal.aborted) setError(mensagemErro(err))
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false)
    })
    return () => controller.abort()
  }, [periodo.de, periodo.ate, categoria, status, revision, invalidPeriod])

  function openForm(event?: AgendaEvento) {
    if (saving) return
    setEditing(event || null)
    setForm(event ? {
      titulo: event.titulo, categoria: event.categoria, status: event.status,
      inicio: dataHoraLocal(event.inicio), fim: event.fim ? dataHoraLocal(event.fim) : '',
      dia_inteiro: event.dia_inteiro, cliente_nome: event.cliente_nome || '',
      responsavel_nome: event.responsavel_nome || '', local: event.local || '',
      endereco: event.endereco || '', descricao: event.descricao || '', observacoes: event.observacoes || '',
    } : novoFormulario())
    setFormError(''); setFormOpen(true); setNotice('')
    titleRef.current?.scrollIntoView({ block: 'center', behavior: 'smooth' })
    titleRef.current?.focus()
  }

  function field<K extends keyof AgendaCampos>(key: K, value: AgendaCampos[K]) {
    setForm(current => ({ ...current, [key]: value }))
  }

  async function save(event: FormEvent) {
    event.preventDefault()
    if (busyRef.current) return
    setFormError('')
    if (!form.titulo.trim() || !form.categoria.trim() || !form.status.trim()) {
      setFormError('Informe título, categoria e status.'); return
    }
    const inicio = form.dia_inteiro ? limiteDia(form.inicio.slice(0, 10)) : new Date(form.inicio).toISOString()
    const fim = form.fim ? (form.dia_inteiro ? limiteDia(form.fim.slice(0, 10), true) : new Date(form.fim).toISOString()) : null
    if (fim && Date.parse(fim) < Date.parse(inicio)) {
      setFormError('O fim não pode ser anterior ao início.'); return
    }
    const optional = (value: string | null) => value?.trim() || null
    const payload: AgendaCampos = {
      ...form, titulo: form.titulo.trim(), categoria: form.categoria.trim(), status: form.status.trim(),
      inicio, fim, cliente_nome: optional(form.cliente_nome), responsavel_nome: optional(form.responsavel_nome),
      local: optional(form.local), endereco: optional(form.endereco),
      descricao: optional(form.descricao), observacoes: optional(form.observacoes),
    }
    busyRef.current = true
    setSaving(true)
    try {
      if (editing) await atualizarAgenda(editing.id, payload)
      else await criarAgenda(payload)
      setFormOpen(false)
      setNotice('Compromisso salvo. A lista respeita os filtros selecionados.')
      setRevision(value => value + 1)
      onChanged()
    } catch (err) { setFormError(mensagemErro(err)) }
    finally { busyRef.current = false; setSaving(false) }
  }

  async function remove() {
    if (!deleting || busyRef.current) return
    busyRef.current = true
    setSaving(true); setError(''); setNotice('')
    try {
      await removerAgenda(deleting.id)
      if (editing?.id === deleting.id) setFormOpen(false)
      setDeleting(null)
      setNotice('Compromisso removido.')
      setRevision(value => value + 1)
      onChanged()
    } catch (err) { setError(mensagemErro(err)) }
    finally { busyRef.current = false; setSaving(false) }
  }

  const query = normalize(busca.trim())
  const filtered = events.filter(event => normalize([event.titulo, event.cliente_nome, event.responsavel_nome].filter(Boolean).join(' ')).includes(query))
  const categories = Array.from(new Set([...CATEGORIAS, ...events.map(event => event.categoria), categoria].filter(Boolean)))
  const statuses = Array.from(new Set([...STATUS, ...events.map(event => event.status), status].filter(Boolean)))
  const formatDate = (value: string, allDay: boolean) => new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short', ...(allDay ? {} : { timeStyle: 'short' as const }),
  }).format(new Date(value))

  return <div className="agenda-page">
    <section className="page-heading">
      <div><p className="eyebrow">ORGANIZAÇÃO DO DIA A DIA</p><h1>Agenda</h1><p className="heading-subtitle">Compromissos, atendimentos e tarefas da sua empresa.</p></div>
      <div className="agenda-page-actions">
        <button className="secondary-button" onClick={onBack} disabled={saving}><ArrowLeft size={16} /> Voltar</button>
        <button className="primary-button" onClick={() => openForm()} disabled={saving}><Plus size={17} /> Novo compromisso</button>
      </div>
    </section>

    {notice && <p className="agenda-page-notice" role="status">{notice}</p>}

    {formOpen && <section className="panel agenda-page-editor" aria-labelledby="agenda-form-title">
      <h2 id="agenda-form-title">{editing ? 'Editar compromisso' : 'Novo compromisso'}</h2>
      <form onSubmit={save}>
        <fieldset disabled={saving} className="agenda-page-form">
          <label className="agenda-page-wide">Título *<input ref={titleRef} required maxLength={180} value={form.titulo} onChange={e => field('titulo', e.target.value)} /></label>
          <label>Categoria *<input required list="agenda-categories" maxLength={80} value={form.categoria} onChange={e => field('categoria', e.target.value)} /><small>Escolha uma sugestão ou escreva outra categoria.</small></label>
          <label>Status *<input required list="agenda-statuses" maxLength={40} value={form.status} onChange={e => field('status', e.target.value)} /></label>
          <label className="agenda-page-check agenda-page-wide"><input type="checkbox" checked={form.dia_inteiro} onChange={e => field('dia_inteiro', e.target.checked)} /> Dia inteiro</label>
          <label>Início *<input required type={form.dia_inteiro ? 'date' : 'datetime-local'} value={form.dia_inteiro ? form.inicio.slice(0, 10) : form.inicio} onChange={e => field('inicio', form.dia_inteiro ? e.target.value + 'T00:00' : e.target.value)} /></label>
          <label>Fim (opcional)<input type={form.dia_inteiro ? 'date' : 'datetime-local'} value={form.dia_inteiro ? form.fim?.slice(0, 10) || '' : form.fim || ''} onChange={e => field('fim', e.target.value ? (form.dia_inteiro ? e.target.value + 'T23:59' : e.target.value) : '')} /></label>
          <label>Cliente (opcional)<input maxLength={180} value={form.cliente_nome || ''} onChange={e => field('cliente_nome', e.target.value)} /></label>
          <label>Responsável (opcional)<input maxLength={180} value={form.responsavel_nome || ''} onChange={e => field('responsavel_nome', e.target.value)} /></label>
          <label>Local<input maxLength={220} value={form.local || ''} onChange={e => field('local', e.target.value)} /></label>
          <label>Endereço<input value={form.endereco || ''} onChange={e => field('endereco', e.target.value)} /></label>
          <label>Descrição<textarea rows={3} value={form.descricao || ''} onChange={e => field('descricao', e.target.value)} /></label>
          <label>Observações<textarea rows={3} value={form.observacoes || ''} onChange={e => field('observacoes', e.target.value)} /></label>
          {formError && <p className="agenda-page-error agenda-page-wide" role="alert">{formError}</p>}
          <div className="agenda-page-actions agenda-page-wide">
            <button type="button" className="secondary-button" onClick={() => setFormOpen(false)}>Cancelar</button>
            <button className="primary-button" type="submit">{saving ? 'Salvando...' : 'Salvar compromisso'}</button>
          </div>
        </fieldset>
      </form>
    </section>}

    <datalist id="agenda-categories">{categories.map(value => <option key={value} value={value}>{nome(value)}</option>)}</datalist>
    <datalist id="agenda-statuses">{statuses.map(value => <option key={value} value={value}>{nome(value)}</option>)}</datalist>

    <section className="panel agenda-page-results" aria-label="Compromissos">
      <div className="agenda-page-filters">
        <label>Data inicial<input type="date" value={periodo.de} onChange={e => setPeriodo(current => ({ ...current, de: e.target.value }))} /></label>
        <label>Data final<input type="date" value={periodo.ate} onChange={e => setPeriodo(current => ({ ...current, ate: e.target.value }))} /></label>
        <label>Categoria<input list="agenda-categories" placeholder="Todas" value={categoria} onChange={e => setCategoria(e.target.value)} /></label>
        <label>Status<select value={status} onChange={e => setStatus(e.target.value)}><option value="">Todos</option>{statuses.map(value => <option key={value} value={value}>{nome(value)}</option>)}</select></label>
        <label className="agenda-page-search">Buscar<input type="search" placeholder="Título, cliente ou responsável" value={busca} onChange={e => setBusca(e.target.value)} /></label>
        <div className="agenda-page-actions">
          <button className="secondary-button" onClick={() => { setPeriodo({ de: '', ate: '' }); setCategoria(''); setStatus(''); setBusca('') }}>Limpar filtros</button>
          <button className="secondary-button" disabled={loading} onClick={() => setRevision(value => value + 1)}><RefreshCw size={14} /> Atualizar</button>
        </div>
      </div>
      {invalidPeriod && <p className="agenda-page-error" role="alert">A data final deve ser igual ou posterior à data inicial.</p>}
      {error && <p className="agenda-page-error" role="alert">{error}</p>}
      {deleting && <div className="agenda-page-confirm" role="group" aria-label="Confirmar remoção">
        <p>Remover o compromisso <strong>{deleting.titulo}</strong>? Esta ação não pode ser desfeita.</p>
        <div className="agenda-page-actions">
          <button className="secondary-button" disabled={saving} onClick={() => setDeleting(null)}>Cancelar</button>
          <button className="primary-button" disabled={saving} onClick={() => void remove()}>{saving ? 'Removendo...' : 'Confirmar remoção'}</button>
        </div>
      </div>}
      {loading ? <p className="agenda-page-empty" role="status">Carregando compromissos...</p> : !error && !invalidPeriod && <>
        {events.length >= AGENDA_LIMIT && <p className="agenda-page-warning" role="status">O limite de {AGENDA_LIMIT} compromissos foi atingido. Refine o período ou os filtros para consultar os demais. A busca considera os resultados carregados.</p>}
        <div className="agenda-page-count">{filtered.length} compromisso(s) · Ordem cronológica · Período pelo início</div>
        {filtered.length === 0 ? <div className="agenda-page-empty"><CalendarDays size={28} /><p>Nenhum compromisso encontrado.</p></div> :
          <div className="agenda-page-list">{filtered.map(event => <article className="agenda-page-event" key={event.id}>
            <div className="agenda-page-when"><strong>{formatDate(event.inicio, event.dia_inteiro)}</strong>{event.fim && <span>até {formatDate(event.fim, event.dia_inteiro)}</span>}{event.dia_inteiro && <span>Dia inteiro</span>}</div>
            <div className="agenda-page-copy">
              <h3>{event.titulo}</h3><div className="agenda-page-tags"><span>{nome(event.categoria)}</span><span>{nome(event.status)}</span></div>
              {(event.cliente_nome || event.responsavel_nome) && <p>{[event.cliente_nome && 'Cliente: ' + event.cliente_nome, event.responsavel_nome && 'Responsável: ' + event.responsavel_nome].filter(Boolean).join(' · ')}</p>}
              {(event.local || event.endereco) && <p><MapPin size={13} /> {[event.local, event.endereco].filter(Boolean).join(' · ')}</p>}
              {event.descricao && <p className="agenda-page-description">{event.descricao}</p>}
              {event.observacoes && <p className="agenda-page-description">Observações: {event.observacoes}</p>}
            </div>
            <div className="agenda-page-actions">
              <button className="secondary-button" disabled={saving} aria-label={'Editar ' + event.titulo} onClick={() => openForm(event)}><Pencil size={14} /> Editar</button>
              <button className="secondary-button" disabled={saving} aria-label={'Remover ' + event.titulo} onClick={() => { setDeleting(event); setError('') }}><Trash2 size={14} /> Remover</button>
            </div>
          </article>)}</div>}
      </>}
    </section>
  </div>
}