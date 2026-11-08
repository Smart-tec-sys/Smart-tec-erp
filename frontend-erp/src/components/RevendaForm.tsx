import { commercialDisplayText } from '../utils/commercialDisplay'
import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { createPortal } from 'react-dom'
import { Loader2, X } from 'lucide-react'
import { getFuncionariosCadastro } from '../services/api'
import { consultarCep, consultarCnpj, cnpjValido, cepValido, normalizarCep, normalizarCnpj, consultaAindaAtual } from '../services/cadastroConsultas'
import { aplicarConsulta, editarCampo, iniciarPreenchimento } from '../services/preenchimentoAssistido'
import {
  atualizarRevenda, criarRevenda, formularioDaRevenda, payloadDaRevenda, validarFormularioRevenda,
  camposConsultaCep, camposConsultaCnpj, type CampoRevenda, type FormularioRevenda, type Revenda, type RevendaPayload,
} from '../services/revendas'
import { EnderecoPrincipalFields } from './EnderecoPrincipalFields'

type Props = {
  revenda?: Revenda
  initialValues?: Partial<Revenda>
  somenteLeitura?: boolean
  consultasExternas?: boolean
  camposOriginaisSomenteLeitura?: boolean
  titulo?: string
  descricao?: string
  textoSalvar?: string
  onSubmit?: (payload: RevendaPayload) => Promise<Revenda>
  onClose: () => void
  onSaved: (revenda: Revenda) => void
}
type Vendedor = { id: number; nome: string; ativo: boolean }
type ConsultaStatus = { carregando: boolean; mensagem: string; erro: string }
const statusInicial: ConsultaStatus = { carregando: false, mensagem: '', erro: '' }
const labels: Partial<Record<CampoRevenda, string>> = {
  nome: 'Nome de exibição', razao_social: 'Razão social', nome_fantasia: 'Nome fantasia',
  situacao_cadastral: 'Situação cadastral', email: 'E-mail', telefone: 'Telefone comercial',
  inscricao_estadual: 'Inscrição estadual', cep: 'CEP', logradouro: 'Logradouro', numero: 'Número',
  complemento: 'Complemento', bairro: 'Bairro', cidade: 'Cidade', estado: 'UF',
}

export function RevendaForm({
  revenda, initialValues, somenteLeitura = false, consultasExternas = true,
  camposOriginaisSomenteLeitura = false,
  titulo, descricao, textoSalvar, onSubmit, onClose, onSaved,
}: Props) {
  const [assistido, setAssistido] = useState(() => iniciarPreenchimento(formularioDaRevenda(revenda ?? initialValues), Boolean(revenda)))
  const current = useRef(assistido)
  const mounted = useRef(true)
  const [sugestoes, setSugestoes] = useState<Partial<FormularioRevenda>>({})
  const [cnpjStatus, setCnpjStatus] = useState(statusInicial)
  const [cepStatus, setCepStatus] = useState(statusInicial)
  const lastCnpj = useRef('')
  const lastCep = useRef('')
  const requests = useRef({ cnpj: 0, cep: 0 })
  const [vendedores, setVendedores] = useState<Vendedor[]>([])
  const [vendedorErro, setVendedorErro] = useState('')
  const [erro, setErro] = useState('')
  const [saving, setSaving] = useState(false)
  const savingRef = useRef(false)
  const dialogRef = useRef<HTMLDivElement>(null)
  const scrollBodyRef = useRef<HTMLDivElement>(null)
  const form = assistido.valores
  const disabled = somenteLeitura || saving

  useEffect(() => {
    const body = document.body
    const html = document.documentElement
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const scrollX = window.scrollX
    const scrollY = window.scrollY
    const previousBody = {
      position: body.style.position, top: body.style.top, left: body.style.left,
      width: body.style.width, overflow: body.style.overflow,
      paddingRight: body.style.paddingRight, boxSizing: body.style.boxSizing,
    }
    const previousOverflow = html.style.overflow
    const previousScrollBehavior = html.style.scrollBehavior
    const scrollbarWidth = window.innerWidth - html.clientWidth
    const paddingRight = Number.parseFloat(window.getComputedStyle(body).paddingRight) || 0
    Object.assign(body.style, {
      position: 'fixed', top: '-' + scrollY + 'px', left: '-' + scrollX + 'px',
      width: '100%', overflow: 'hidden', boxSizing: 'border-box',
      paddingRight: paddingRight + scrollbarWidth + 'px',
    })
    html.style.overflow = 'hidden'
    scrollBodyRef.current?.focus({ preventScroll: true })
    return () => {
      Object.assign(body.style, previousBody)
      html.style.overflow = previousOverflow
      html.style.scrollBehavior = 'auto'
      window.scrollTo(scrollX, scrollY)
      html.style.scrollBehavior = previousScrollBehavior
      if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true })
    }
  }, [])

  useEffect(() => {
    mounted.current = true
    let cancelled = false
    void getFuncionariosCadastro().then(rows => {
      const options = rows.map(row => {
        if (!Number.isInteger(row.id) || typeof row.nome !== 'string') throw new Error('Resposta inválida ao carregar vendedores.')
        return { id: row.id, nome: row.nome, ativo: typeof row.situacao === 'string' && row.situacao.toLowerCase() === 'ativo' }
      })
      if (!cancelled) setVendedores(options)
    }).catch(error => {
      if (!cancelled) setVendedorErro(error instanceof Error ? error.message : 'Não foi possível carregar vendedores.')
    })
    return () => { cancelled = true; mounted.current = false; requests.current.cnpj++; requests.current.cep++ }
  }, [])

  function atualizar(next: typeof assistido) {
    current.current = next
    setAssistido(next)
  }
  function change(campo: CampoRevenda, value: string) {
    if (savingRef.current || somenteLeitura) return
    atualizar(editarCampo(current.current, campo, value))
    setSugestoes(previous => { const next = { ...previous }; delete next[campo]; return next })
    setErro('')
    if (campo === 'documento' || campo === 'tipo_pessoa') {
      requests.current.cnpj++
      setCnpjStatus(statusInicial)
      setSugestoes({})
      lastCnpj.current = ''
    }
    if (campo === 'cep') {
      requests.current.cep++
      setCepStatus(statusInicial)
      lastCep.current = ''
      setSugestoes(previous => {
        const next = { ...previous }
        for (const key of ['cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado'] as const) delete next[key]
        return next
      })
    }
  }

  async function consultar(origem: 'cnpj' | 'cep', repetir = false) {
    if (savingRef.current || somenteLeitura || !consultasExternas) return
    const snapshot = current.current
    const cnpj = origem === 'cnpj'
    const key = cnpj ? normalizarCnpj(snapshot.valores.documento) : normalizarCep(snapshot.valores.cep)
    const setStatus = cnpj ? setCnpjStatus : setCepStatus
    if ((cnpj && (snapshot.valores.tipo_pessoa !== 'JURIDICA' || !cnpjValido(key))) || (!cnpj && !cepValido(key))) {
      setStatus({ ...statusInicial, erro: cnpj ? 'Informe um CNPJ válido para consultar. O cadastro manual continua disponível.' : 'Informe um CEP com oito dígitos para consultar.' })
      return
    }
    const last = cnpj ? lastCnpj : lastCep
    if (!repetir && last.current === key) return
    last.current = key
    const requestId = ++requests.current[origem]
    setStatus({ ...statusInicial, carregando: true })
    const validaResposta = () => mounted.current && !savingRef.current && consultaAindaAtual(origem, key, requestId, {
      ...current.current.valores, requestId: requests.current[origem],
    })
    try {
      const response = cnpj ? await consultarCnpj(key) : await consultarCep(key)
      if (!validaResposta()) return
      const dados = cnpj ? camposConsultaCnpj(response.dados) : camposConsultaCep(response.dados)
      if (cnpj && !revenda && current.current.origens.nome !== 'manual'
        && (!current.current.valores.nome.trim() || current.current.origens.nome === 'cnpj')) {
        dados.nome = dados.nome_fantasia || dados.razao_social
      }
      const applied = aplicarConsulta(current.current, dados, origem, snapshot.versao)
      atualizar(applied.estado)
      setSugestoes(previous => ({ ...previous, ...applied.sugestoes }))
      const ausentes = cnpj
        ? (['nome_fantasia', 'email', 'telefone', 'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado'] as const)
          .filter(campo => !dados[campo]?.trim()).map(campo => labels[campo])
        : []
      setStatus({
        ...statusInicial,
        mensagem: `Dados consultados em ${response.fonte}. Revise antes de salvar.${ausentes.length
          ? ` A fonte não informou: ${ausentes.join(', ')}. Complete apenas o que for necessário.` : ''}${
          Object.values(response.fontes_campos ?? {}).includes('cnpja')
            ? ' Contatos ausentes complementados pela CNPJá; campos manuais foram preservados.' : ''
        }${response.avisos?.length ? ` ${response.avisos.join(' ')}` : ''}`,
      })
    } catch (error) {
      if (validaResposta()) setStatus({ ...statusInicial, erro: `${error instanceof Error ? error.message : 'Consulta indisponível.'} Você pode continuar o cadastro manualmente.` })
    }
  }

  useEffect(() => {
    if (disabled || !consultasExternas || form.tipo_pessoa !== 'JURIDICA' || assistido.origens.documento !== 'manual' || !cnpjValido(form.documento)) return
    const timer = setTimeout(() => { void consultar('cnpj') }, 500)
    return () => clearTimeout(timer)
  }, [form.documento, form.tipo_pessoa, disabled])

  useEffect(() => {
    if (disabled || !consultasExternas || !cepValido(form.cep) || !['manual', 'cnpj'].includes(assistido.origens.cep ?? '')) return
    const timer = setTimeout(() => { void consultar('cep') }, 500)
    return () => clearTimeout(timer)
  }, [form.cep, disabled])

  function close() { if (!savingRef.current) onClose() }
  function dialogKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape') {
      event.preventDefault()
      event.stopPropagation()
      close()
    }
    if (event.key !== 'Tab') return
    const focusable = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>(
      'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href], [tabindex="0"]',
    ) ?? []).filter(element => element.getClientRects().length > 0)
    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last?.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first?.focus()
    }
  }
  async function save() {
    if (savingRef.current || somenteLeitura) return
    const failure = validarFormularioRevenda(current.current.valores)
    if (failure) { setErro(failure); return }
    savingRef.current = true
    setSaving(true)
    setErro('')
    requests.current.cnpj++; requests.current.cep++
    try {
      const payload = payloadDaRevenda(current.current.valores)
      const result = onSubmit
        ? await onSubmit(payload)
        : revenda
          ? await atualizarRevenda(revenda.id, payload)
          : await criarRevenda(payload)
      if (mounted.current) onSaved(result)
    } catch (error) {
      if (mounted.current) setErro(error instanceof Error ? error.message : 'Não foi possível salvar a revenda.')
    } finally {
      savingRef.current = false
      if (mounted.current) { setSaving(false); setCnpjStatus(previous => ({ ...previous, carregando: false })); setCepStatus(previous => ({ ...previous, carregando: false })) }
    }
  }

  function field(campo: CampoRevenda, label: string, options: { value: string; label: string }[] | undefined = undefined, maxLength = 255, type = 'text') {
    const origemBloqueada = camposOriginaisSomenteLeitura && [
      'tipo_pessoa', 'documento', 'nome', 'email', 'telefone', 'telefone_celular',
      'site', 'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade',
      'estado', 'limite_credito',
    ].includes(campo)
    return <label className="cad-field" key={campo}>
      <span>{label}{campo === 'nome' ? ' *' : ''}</span>
      {options
        ? <select name={campo} value={form[campo]} disabled={disabled || origemBloqueada} onChange={event => change(campo, event.target.value)}>
          {options.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
        : <input className={['nome', 'razao_social', 'nome_fantasia', 'responsavel'].includes(campo) && commercialDisplayText(form[campo]) === form[campo].toLocaleUpperCase('pt-BR') ? 'commercial-name' : undefined} name={campo} type={type} value={form[campo]} required={campo === 'nome'} disabled={disabled || origemBloqueada} maxLength={maxLength}
          step={campo === 'percentual_padrao' ? '0.0001' : type === 'number' ? '0.01' : undefined}
          min={type === 'number' ? 0 : undefined} max={campo === 'percentual_padrao' ? 100 : undefined}
          onChange={event => change(campo, event.target.value)} />}
    </label>
  }
  function checkbox(campo: CampoRevenda, label: string) {
    return <label className="cad-checkbox"><input type="checkbox" name={campo} checked={form[campo] === 'true'} disabled={disabled || (camposOriginaisSomenteLeitura && campo === 'permitir_exceder_limite')}
      onChange={event => change(campo, String(event.target.checked))} /><span>{label}</span></label>
  }
  function consultaStatus(status: ConsultaStatus, origem: 'cnpj' | 'cep') {
    return <div className="revenda-query" aria-live="polite">
      {status.carregando && <span><Loader2 size={14} className="spinning" /> Consultando {origem.toUpperCase()}...</span>}
      {status.mensagem && <p>{status.mensagem}</p>}
      {status.erro && <p className="revenda-warning" role="status">{status.erro}</p>}
      {!somenteLeitura && consultasExternas && <button type="button" className="cad-secondary" disabled={saving || status.carregando}
        onClick={() => void consultar(origem, true)}>{status.erro || status.mensagem ? 'Consultar novamente' : `Consultar ${origem.toUpperCase()}`}</button>}
    </div>
  }
  const hasSugestoes = Object.keys(sugestoes).length > 0
  const modal = <div className="cad-modal-backdrop revenda-modal-backdrop" onMouseDown={close}>
    <div ref={dialogRef} className="cad-modal revenda-modal" role="dialog" aria-modal="true" aria-label={titulo || (somenteLeitura ? 'Visualizar revenda' : revenda ? 'Editar revenda' : 'Nova revenda')}
      onMouseDown={event => event.stopPropagation()} onKeyDown={dialogKeyDown}>
      <div className="cad-modal-header"><div><span>{titulo || (somenteLeitura ? 'VISUALIZAR CADASTRO' : revenda ? 'EDITAR CADASTRO' : 'NOVA REVENDA')}</span>
        <h2>{commercialDisplayText(revenda?.nome || initialValues?.nome || 'Cadastro de revenda')}</h2><p className="revenda-hint">{descricao || 'Informe CNPJ e CEP para agilizar. Apenas o nome de exibição é obrigatório.'}</p></div>
        <button type="button" aria-label="Fechar" disabled={saving} onClick={close}><X size={19} /></button>
      </div>
      <form className="revenda-modal-form" onSubmit={event => { event.preventDefault(); void save() }}>
        <div ref={scrollBodyRef} className="revenda-modal-body" role="region" aria-label="Formulário da revenda" tabIndex={0}>
        <section className="revenda-section"><h3 className="commercial-title">1. Dados gerais</h3><div className="revenda-fields">
          {field('tipo_pessoa', 'Tipo de pessoa', [{ value: '', label: 'Não informado' }, { value: 'FISICA', label: 'Pessoa física' }, { value: 'JURIDICA', label: 'Pessoa jurídica' }])}
          {field('ativo', 'Situação', [{ value: 'true', label: 'Ativo' }, { value: 'false', label: 'Inativo' }])}
          {field('documento', 'CPF / CNPJ', undefined, 30)}
          {field('nome', 'Nome de exibição')}
          {field('nome_fantasia', 'Nome fantasia')}{field('razao_social', 'Razão social')}
          {field('email', 'E-mail', undefined, 255, 'email')}{field('situacao_cadastral', 'Situação cadastral (fonte CNPJ)', undefined, 100)}
        </div>{form.tipo_pessoa === 'JURIDICA' && consultaStatus(cnpjStatus, 'cnpj')}</section>
        {hasSugestoes && !somenteLeitura && <section className="revenda-suggestions" aria-label="Sugestões da consulta">
          <h3 className="commercial-title">Dados preservados</h3><p>Seus campos não foram substituídos. Aplique uma sugestão somente se desejar.</p>
          {(Object.keys(sugestoes) as CampoRevenda[]).map(campo => <div key={campo}>
            <span>{labels[campo] || campo}: <strong>{['nome', 'razao_social', 'nome_fantasia', 'responsavel', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado'].includes(campo) ? commercialDisplayText(sugestoes[campo] || '') : sugestoes[campo]}</strong></span>
            <button type="button" className="cad-secondary" disabled={saving} onClick={() => change(campo, sugestoes[campo] || '')}>Aplicar</button>
          </div>)}
        </section>}
        <section className="revenda-section"><h3 className="commercial-title">2. Contato</h3><div className="revenda-fields">
          {field('telefone', 'Telefone comercial', undefined, 50, 'tel')}{field('telefone_celular', 'Telefone celular', undefined, 50, 'tel')}
          {field('responsavel', 'Contato responsável na revenda', undefined, 120)}{field('site', 'Site', undefined, 500)}
        </div></section>
        <section className="revenda-section"><h3 className="commercial-title">3. Endereço principal</h3>
          <EnderecoPrincipalFields valores={form} disabled={disabled || camposOriginaisSomenteLeitura} onChange={change} />
          {consultaStatus(cepStatus, 'cep')}
        </section>
        <details className="revenda-section"><summary>4. Fiscal</summary><div className="revenda-fields">
          {field('inscricao_estadual', 'Inscrição estadual', undefined, 80)}{field('inscricao_municipal', 'Inscrição municipal', undefined, 80)}
          {field('tipo_contribuinte', 'Tipo de contribuinte', [{ value: '', label: 'Não informado' }, { value: 'CONTRIBUINTE', label: 'Contribuinte' }, { value: 'ISENTO', label: 'Isento' }, { value: 'NAO_CONTRIBUINTE', label: 'Não contribuinte' }])}
          {checkbox('isento_ie', 'Isento de inscrição estadual')}
        </div></details>
        <section className="revenda-section"><h3 className="commercial-title">5. Comercial Smart-tec</h3><div className="revenda-fields">
          {field('percentual_padrao', '% revenda padrão', undefined, 12, 'number')}
          <label className="cad-field"><span>Vendedor responsável</span><select name="vendedor_responsavel_id" value={form.vendedor_responsavel_id}
            disabled={disabled || Boolean(vendedorErro)} onChange={event => change('vendedor_responsavel_id', event.target.value)}>
            <option value="">Não vinculado</option>
            {form.vendedor_responsavel_id && !vendedores.some(vendedor => String(vendedor.id) === form.vendedor_responsavel_id)
              && <option value={form.vendedor_responsavel_id}>Vendedor #{form.vendedor_responsavel_id} (vínculo atual)</option>}
            {vendedores.filter(vendedor => vendedor.ativo || String(vendedor.id) === form.vendedor_responsavel_id)
              .map(vendedor => <option key={vendedor.id} value={vendedor.id}>{commercialDisplayText(vendedor.nome)}{vendedor.ativo ? '' : ' (inativo)'}</option>)}
          </select></label>
        </div>{vendedorErro && <p className="revenda-warning" role="status">{vendedorErro} O vínculo atual será preservado.</p>}</section>
        <details className="revenda-section"><summary>6. Financeiro / Crédito</summary><p className="revenda-hint">Informação cadastral. Não bloqueia orçamento ou venda e não calcula crédito disponível.</p>
          <div className="revenda-fields">{field('limite_credito', 'Limite de crédito (R$)', undefined, 16, 'number')}
            {checkbox('permitir_exceder_limite', 'Permitir exceder limite')}</div>
          <p className="revenda-hint">Vazio = limite não definido. Zero = limite explicitamente definido como zero.</p>
        </details>
        <section className="revenda-section"><h3 className="commercial-title">7. Observações</h3><label className="cad-field">
          <span>Observações</span><textarea name="observacao" value={form.observacao} disabled={disabled} onChange={event => change('observacao', event.target.value)} />
        </label></section>
        {erro && <div className="cad-error" role="alert">{erro}</div>}
        </div>
        <div className="cad-modal-footer"><button type="button" className="cad-secondary" disabled={saving} onClick={close}>{somenteLeitura ? 'Voltar' : 'Cancelar'}</button>
          {!somenteLeitura && <button type="submit" className="primary-button" disabled={saving}>{saving ? 'Salvando...' : textoSalvar || 'Salvar revenda'}</button>}
        </div>
      </form>
    </div>
  </div>
  return typeof document === 'undefined' ? modal : createPortal(modal, document.body)
}
