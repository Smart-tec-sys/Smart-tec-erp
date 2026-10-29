import { curtainKey } from "../types/budget"
import { technicalItemData } from '../utils/technicalSimulation'
import { ZeroNumberInput } from '../components/ZeroNumberInput'
import { CommercialRegistrationDialog, CREATE_COMMERCIAL_VALUE, type CommercialRegistration } from '../components/CommercialRegistrationDialog'
import { selectZeroOnFocus } from '../utils/selectZeroOnFocus'
import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { ArrowLeft, FileText, Loader2, PackagePlus, Plus, ReceiptText, UserPlus, WalletCards, X } from 'lucide-react'
import { BudgetProductRow } from '../components/BudgetProductRow'
import { BudgetServiceRow } from '../components/BudgetServiceRow'
import { BudgetSummary } from '../components/BudgetSummary'
import { createClient, createOrder, getAllProducts, getClients, getCommercialPartners, getFuncionariosCadastro, getRepresentatives,
  type ApiCommercialPartner, type ApiRepresentative, type ApiOrder, type OrderCreate } from '../services/api'
import { commercialPrice, emptyProduct, parseDecimal, productLineSubtotal, profileLabel, roundHalfUp,
  type ApiClient, type ApiProduct, type BudgetProduct, type BudgetService, type CommercialProfile, type CurtainState } from '../types/budget'
import { romanaKey, type RomanaState } from '../types/romana'
import { romanaTetoKey, type RomanaTetoState } from '../types/romana_teto'
import { roloKey, type RoloState } from '../types/rolo'
import { doubleVisionKey, type DoubleVisionState } from '../types/double_vision'

function Section({ title, subtitle, icon, children }: { title: string; subtitle: string; icon: ReactNode; children: ReactNode }) {
  return <section className="form-section panel"><div className="section-title"><div className="section-icon">{icon}</div><div><h2>{title}</h2><p>{subtitle}</p></div></div>{children}</section>
}
function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="field"><span>{label}</span>{children}</label>
}
const CREATE_CLIENT_VALUE = '__CREATE_CLIENT__'
const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}` }

export function NewSalePage({ onBack, onSaved }: { onBack: () => void; onSaved: (sale: ApiOrder) => void }) {
  const [clients, setClients] = useState<ApiClient[]>([])
  const [catalog, setCatalog] = useState<ApiProduct[]>([])
  const [commercialRegistration, setCommercialRegistration] = useState<CommercialRegistration | null>(null)
  const [partners, setPartners] = useState<ApiCommercialPartner[]>([])
  const [representatives, setRepresentatives] = useState<ApiRepresentative[]>([])
  const [sellers, setSellers] = useState<{ id: number; nome?: unknown }[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [warning, setWarning] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const savingRef = useRef(false)
  const nextId = useRef(1)
  const [attempted, setAttempted] = useState(false)
  const [saleType, setSaleType] = useState<'DIRETA' | 'PARCEIRO'>('DIRETA')
  const [clientId, setClientId] = useState<number | null>(null)
  const [showClientModal, setShowClientModal] = useState(false)
  const [clientForm, setClientForm] = useState({ tipo: '', nome: '' })
  const [clientModalError, setClientModalError] = useState('')
  const [clientModalSaving, setClientModalSaving] = useState(false)
  const [partnerId, setPartnerId] = useState<number | null>(null)
  const [sellerId, setSellerId] = useState<number | null>(null)
  const [representativeId, setRepresentativeId] = useState<number | null>(null)
  const [showPartnerRepresentative, setShowPartnerRepresentative] = useState(false)
  const [showDirectRepresentative, setShowDirectRepresentative] = useState(false)
  const [partnerFinalClient, setPartnerFinalClient] = useState('')
  const [partnerFinalClientFull, setPartnerFinalClientFull] = useState(false)
  const [partnerFinalDocument, setPartnerFinalDocument] = useState('')
  const [partnerFinalPhone, setPartnerFinalPhone] = useState('')
  const [partnerFinalEmail, setPartnerFinalEmail] = useState('')
  const [partnerFinalAddress, setPartnerFinalAddress] = useState('')
  const [profile, setProfile] = useState<CommercialProfile>('VAREJO')
  const [saleDate, setSaleDate] = useState(today)
  const [deadline, setDeadline] = useState('')
  const [channel, setChannel] = useState('')
  const [observation, setObservation] = useState('')
  const [internalObservation, setInternalObservation] = useState('')
  const [products, setProducts] = useState<BudgetProduct[]>([])
  const [services, setServices] = useState<BudgetService[]>([])
  const [discount, setDiscount] = useState(0)
  const [partnerPercent, setPartnerPercent] = useState(0)
  const [includeRt, setIncludeRt] = useState(false)
  const [rtType, setRtType] = useState<'PERCENTUAL' | 'VALOR_FIXO'>('VALOR_FIXO')
  const [rtPercent, setRtPercent] = useState(0)
  const [rtValue, setRtValue] = useState(0)
  const [includeBankFee, setIncludeBankFee] = useState(false)
  const [bankFeePercent, setBankFeePercent] = useState(0)
  const [collapsed, setCollapsed] = useState(false)

  useEffect(() => {
    let cancelled = false
    void Promise.all([getClients(), getAllProducts(), Promise.allSettled([getFuncionariosCadastro(), getCommercialPartners(), getRepresentatives()])])
      .then(([loadedClients, loadedCatalog, names]) => {
        if (cancelled) return
        setClients(loadedClients); setCatalog(loadedCatalog)
        if (names[0].status === 'fulfilled') setSellers(names[0].value)
        if (names[1].status === 'fulfilled') setPartners(names[1].value)
        if (names[2].status === 'fulfilled') setRepresentatives(names[2].value)
        if (names.some(n => n.status === 'rejected')) setWarning('Algumas listas comerciais não foram carregadas. Reabra a página para tentar novamente.')
      }).catch(e => { if (!cancelled) setLoadError(e instanceof Error ? e.message : String(e)) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])
  useEffect(() => {
    setProducts(rows => rows.map(row => {
      const found = catalog.find(p => p.id === row.productId)
      return found && !(row.romanaKind || row.romanaTetoKind || row.roloKind || row.doubleVisionKind)
        ? { ...row, price: Number(found.custo_final || found.valor_custo || 0) > 0 ? commercialPrice(found, profileLabel[profile]) : roundHalfUp(Number(found.valor_venda || 0)) } : row
    }))
  }, [profile, catalog])
  const onRomana = useCallback((id: number, state: RomanaState) => setProducts(rows => rows.map(p => p.id === id ? { ...p, romana: state, price: Number(state.result?.preco_unitario ?? p.price) } : p)), [])
  const onRomanaTeto = useCallback((id: number, state: RomanaTetoState) => setProducts(rows => rows.map(p => p.id === id ? { ...p, romanaTeto: state, price: Number(state.result?.preco_unitario ?? p.price) } : p)), [])
  const onRolo = useCallback((id: number, state: RoloState) => setProducts(rows => rows.map(p => p.id === id ? { ...p, rolo: state, price: Number(state.result?.preco_unitario ?? p.price) } : p)), [])
  const onDoubleVision = useCallback((id: number, state: DoubleVisionState) => setProducts(rows => rows.map(p => p.id === id ? { ...p, doubleVision: state, price: Number(state.result?.preco_unitario ?? p.price) } : p)), [])
  const onCurtain = useCallback((id: number, state: CurtainState) => setProducts(rows => rows.map(p => p.id === id ? { ...p, color: state.cor, curtain: state, price: Number(state.result?.preco_unitario ?? p.price) } : p)), [])

  function changeType(value: 'DIRETA' | 'PARCEIRO') {
    setSaleType(value)
    setError('')

    if (value === 'DIRETA') {
      setPartnerId(null)
      setPartnerPercent(0)
      setShowPartnerRepresentative(false)
      changeRepresentative(null)
      setPartnerFinalClient('')
      setPartnerFinalDocument('')
      setPartnerFinalPhone('')
      setPartnerFinalEmail('')
      setPartnerFinalAddress('')
      setPartnerFinalClientFull(false)
      setIncludeRt(false)
      setRtValue(0)
      setRtPercent(0)
    } else {
      setClientId(null)
    }
  }

  function handleOpenClientModal() {
    setClientForm({ tipo: '', nome: '' })
    setClientModalError('')
    setShowClientModal(true)
  }

  function handleCloseClientModal() {
    if (clientModalSaving) return
    setShowClientModal(false)
    setClientForm({ tipo: '', nome: '' })
    setClientModalError('')
  }

  function handleClientSelectChange(value: string) {
    if (value === CREATE_CLIENT_VALUE) {
      handleOpenClientModal()
      return
    }
    setClientId(Number(value) || null)
  }

  async function handleCreateClient() {
    if (!clientForm.tipo.trim() || !clientForm.nome.trim()) {
      setClientModalError('Tipo e Nome são obrigatórios')
      return
    }
    setClientModalSaving(true)
    setClientModalError('')
    try {
      const newClient = await createClient({
        tipo: clientForm.tipo.trim(),
        nome: clientForm.nome.trim(),
      })
      setClients(rows => [newClient, ...rows])
      setClientId(newClient.id)
      setShowClientModal(false)
      setClientForm({ tipo: '', nome: '' })
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e)
      setClientModalError(
        message.includes('409') || message.toLowerCase().includes('duplic') || message.toLowerCase().includes('unique')
          ? 'Cliente já cadastrado com estes dados'
          : message
      )
    } finally {
      setClientModalSaving(false)
    }
  }

  function changeRepresentative(id: number | null) {
    setRepresentativeId(id)
    if (id === null) {
      setIncludeRt(false)
      setRtType('VALOR_FIXO')
      setRtValue(0)
      setRtPercent(0)
    }
  }

  function handleRepresentativeSelect(value: string) {
    if (value === CREATE_COMMERCIAL_VALUE) {
      setCommercialRegistration('representante')
      return
    }
    changeRepresentative(value ? Number(value) : null)
  }
  function updateProduct(next: BudgetProduct) {
    const previous = products.find(row => row.id === next.id)
    const found = catalog.find(p => p.id === next.productId)
    if (previous?.productId !== next.productId && found && !(next.romanaKind || next.romanaTetoKind || next.roloKind || next.doubleVisionKind || next.curtain)) {
      next = { ...next, price: Number(found.custo_final || found.valor_custo || 0) > 0 ? commercialPrice(found, profileLabel[profile]) : roundHalfUp(Number(found.valor_venda || 0)) }
    }
    setProducts(rows => rows.map(row => row.id === next.id ? next : row))
  }
  function addProduct() { const row = emptyProduct(nextId.current++); setProducts(rows => [...rows, row]) }
  function addService() { const row: BudgetService = { id: nextId.current++, service: 'Instalação', details: '', quantity: 1, value: 0, discount: 0 }; setServices(rows => [...rows, row]) }
  const productsTotal = roundHalfUp(products.reduce((sum, p) => sum + productLineSubtotal(p,profileLabel[profile]), 0))
  const servicesTotal = roundHalfUp(services.reduce((sum, s) => sum + roundHalfUp(Math.max(0, s.quantity * s.value - s.discount)), 0))
  const internalValue = roundHalfUp(Math.max(0, productsTotal + servicesTotal - discount))
  const partnerValue = partnerId ? roundHalfUp(internalValue * partnerPercent / 100) : 0
  const rtEnabled = representativeId !== null && includeRt
  const rtAmount = rtEnabled ? roundHalfUp(rtType === 'PERCENTUAL' ? internalValue * rtPercent / 100 : rtValue) : 0
  const base = roundHalfUp(internalValue + partnerValue + rtAmount)
  const clientTotal = includeBankFee && bankFeePercent > 0 && bankFeePercent < 100 ? roundHalfUp(base / (1 - bankFeePercent / 100)) : base
  const pending = products.some(p =>
    (p.romanaKind && (p.romanaKind === 'MOTORIZADA' || p.romana?.key !== romanaKey(p, profileLabel[profile]) || p.romana?.error || !p.romana?.result?.preco_disponivel)) ||
    (p.romanaTetoKind && (p.romanaTetoKind === 'MOTORIZADA' || p.romanaTeto?.key !== romanaTetoKey(p, profileLabel[profile]) || p.romanaTeto?.error || !p.romanaTeto?.result?.preco_disponivel)) ||
    (p.roloKind && (p.roloKind === 'MOTORIZADA' || p.rolo?.key !== roloKey(p, profileLabel[profile]) || p.rolo?.error || !p.rolo?.result?.preco_disponivel)) ||
    (p.doubleVisionKind && (p.doubleVisionKind === 'MOTORIZADA' || p.doubleVision?.key !== doubleVisionKey(p, profileLabel[profile]) || p.doubleVision?.error || !p.doubleVision?.result?.preco_disponivel || p.doubleVision.result.estado_validacao !== 'permitido')) ||
    (p.curtain && (!p.curtain.result?.preco_disponivel || p.curtain.error || p.curtain.simulationKey !== curtainKey(p,profileLabel[profile]))))

  async function save() {
    if (savingRef.current || loading || loadError) return
    setAttempted(true); setError('')
    if (saleType === 'DIRETA' && !clientId) { setError('Venda direta exige cliente.'); return }
    if (saleType === 'PARCEIRO' && !partnerId) { setError('Selecione a revenda.'); return }
    if ((!products.length && !services.length) || products.some(p => !p.productId && !p.curtain?.tecidoProdutoId) || services.some(s => !s.service.trim() || s.quantity <= 0)) { setError('Inclua pelo menos um item válido e complete os itens adicionados.'); return }
    if (discount < 0 || partnerPercent < 0 || partnerPercent > 1000 ||
        services.some(s => s.value < 0 || s.discount < 0) ||
        products.some(p => p.quantity <= 0 || p.price < 0 || p.discount < 0 || parseDecimal(p.width) < 0 || parseDecimal(p.height) < 0)) {
      setError('Revise quantidades, preços e descontos: os valores não podem ser negativos.'); return
    }
    if (pending) { setError('Confirme as medidas e aguarde as simulações dos produtos antes de salvar.'); return }
    if (includeRt && representativeId === null) { setError('Selecione um representante para informar RT.'); return }
    if (rtEnabled && (rtType === 'PERCENTUAL' ? rtPercent <= 0 || rtPercent > 100 : rtValue <= 0)) { setError('Informe um RT válido e maior que zero.'); return }
    if (includeBankFee && (bankFeePercent < 0 || bankFeePercent >= 100)) { setError('Taxa bancária deve ficar entre 0 e menos de 100%.'); return }
    const payload: OrderCreate = {
      cliente_id: saleType === 'DIRETA' ? clientId : null, parceiro_id: saleType === 'PARCEIRO' ? partnerId : null,
      vendedor_id: sellerId, representante_id: representativeId,
      cliente_final_nome: saleType === 'PARCEIRO' ? partnerFinalClient.trim() || null : null,
      cliente_final_documento: saleType === 'PARCEIRO' ? partnerFinalDocument.trim() || null : null,
      cliente_final_telefone: saleType === 'PARCEIRO' ? partnerFinalPhone.trim() || null : null,
      cliente_final_email: saleType === 'PARCEIRO' ? partnerFinalEmail.trim() || null : null,
      cliente_final_endereco: saleType === 'PARCEIRO' ? partnerFinalAddress.trim() || null : null,
      perfil_comercial: profile, status: 'ABERTO', data_venda: saleDate || null, prazo_entrega: deadline || null, canal_venda: channel.trim() || null,
      observacao: observation.trim() || null, observacao_interna: internalObservation.trim() || null,
      desconto: discount, percentual_parceiro: partnerId ? partnerPercent : 0, incluir_rt: rtEnabled, tipo_rt: rtEnabled ? rtType : null,
      percentual_rt: rtEnabled && rtType === 'PERCENTUAL' ? rtPercent : 0, valor_rt: rtEnabled && rtType === 'VALOR_FIXO' ? rtValue : 0,
      incluir_taxa_bancaria: includeBankFee, taxa_bancaria_percentual: includeBankFee ? bankFeePercent : 0,
      itens: [
        ...products.map(p => ({ tipo_item: 'PRODUTO', produto_id: p.productId, descricao: p.product, codigo_interno: p.code || null,
          grupo_tecnico: p.groupTechnical || null, modelo_tecnico: p.modelTechnical || null, unidade: p.unit || null,
          quantidade: p.quantity, largura: parseDecimal(p.width), altura: parseDecimal(p.height), area: parseDecimal(p.width) * parseDecimal(p.height) * p.quantity,
          preco_unitario: p.price, desconto: p.discount, subtotal: productLineSubtotal(p,profileLabel[profile]), observacao_item: p.details || null, cor: p.color || null,
          acionamento: p.acao_acionamento || p.acionamento || null, lado_comando: p.lado_comando || null,
          dados_tecnicos: technicalItemData(p) })),
        ...services.map(s => ({ tipo_item: 'SERVICO', produto_id: null, descricao: s.service.trim(), quantidade: s.quantity,
          largura: 0, altura: 0, area: 0, preco_unitario: s.value, desconto: s.discount,
          subtotal: Math.max(0, s.quantity * s.value - s.discount), observacao_item: s.details || null })),
      ],
    }
    savingRef.current = true; setSaving(true)
    try { const sale = await createOrder(payload); onSaved(sale) }
    catch (e) { setError(e instanceof Error ? e.message : String(e)) }
    finally { savingRef.current = false; setSaving(false) }
  }

  if (loading) return <div className="panel loading-state">Carregando nova venda...</div>
  if (loadError) return <div className="panel"><button className="back-button" onClick={onBack}>← Voltar para Vendas</button><p className="api-message error" role="alert">{loadError}</p></div>
  return <div className="new-budget-page" onFocusCapture={selectZeroOnFocus}>
    <section className="new-budget-heading page-heading"><div><button type="button" className="back-button page-back" onClick={onBack} disabled={saving}><ArrowLeft size={15} /> Voltar para Vendas</button><p className="eyebrow">VENDA COMERCIAL</p><h1>Nova venda <span className="draft-badge">Em aberto</span></h1><p className="heading-subtitle">Preencha os dados comerciais, os itens e confira o resumo antes de salvar.</p></div><div className="budget-number"><span>Número da venda</span><strong>Gerado ao salvar</strong></div></section>
    {warning && <div className="api-message" role="status">{warning}</div>}
    {error && <div className="api-message error" role="alert">{error}</div>}
    <div className={`new-budget-layout ${collapsed ? 'summary-collapsed' : ''}`}>
      <fieldset className="new-budget-main" disabled={saving} style={{ margin: 0, padding: 0, border: 0, minWidth: 0 }}>
        <Section title="Perfil comercial" subtitle="Tabela de preço aplicada aos produtos da venda." icon={<FileText size={17} />}><Field label="Tabela de preço"><select value={profile} onChange={e => setProfile(e.target.value as CommercialProfile)}>{Object.entries(profileLabel).map(([key,label]) => <option key={key} value={key}>{label}</option>)}</select></Field></Section>
        <Section title="Fluxo comercial" subtitle="Controle interno." icon={<WalletCards size={17} />}>
          <div className="form-grid general-grid">
            <Field label="Vendedor Smart-tec">
              <select value={sellerId ?? ''} onChange={e => setSellerId(e.target.value ? Number(e.target.value) : null)}>
                <option value="">Sem vendedor definido</option>
                {sellers.map(s => <option key={s.id} value={s.id}>{String(s.nome ?? `Funcionário ${s.id}`)}</option>)}
              </select>
            </Field>

            <Field label="Tipo de venda">
              <select value={saleType} onChange={e => changeType(e.target.value as 'DIRETA' | 'PARCEIRO')}>
                <option value="DIRETA">Venda direta</option>
                <option value="PARCEIRO">Venda por revenda</option>
              </select>
            </Field>

            {saleType === 'DIRETA' ? (
              <>
                <Field label="Cliente">
                  <div className="product-search-box">
                    <select value={clientId ?? 0} onChange={e => handleClientSelectChange(e.target.value)}>
                      <option value={0}>Selecione o cliente</option>
                      {clients.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
                      <option value={CREATE_CLIENT_VALUE}>+ Cadastrar novo cliente</option>
                    </select>
                  </div>
                </Field>

                <Field label="Representante?">
                  <select value={showDirectRepresentative ? 'SIM' : 'NAO'} onChange={e => {
                    const active = e.target.value === 'SIM'
                    setShowDirectRepresentative(active)
                    if (!active) {
                      changeRepresentative(null)
                      setIncludeRt(false)
                      setRtType('VALOR_FIXO')
                      setRtValue(0)
                      setRtPercent(0)
                    }
                  }}>
                    <option value="NAO">Não</option>
                    <option value="SIM">Sim</option>
                  </select>
                </Field>

                {showDirectRepresentative && (
                  <>
                    <Field label="Representante">
                      <select value={representativeId ?? ''} onChange={e => handleRepresentativeSelect(e.target.value)}>
                        <option value="">Selecione o representante</option>
                        {representatives.map(r => <option key={r.id} value={r.id}>{r.nome}</option>)}
                        <option value={CREATE_COMMERCIAL_VALUE}>+ Cadastrar novo representante</option>
                      </select>
                    </Field>

                    <Field label="RT">
                      <select disabled={representativeId === null} value={includeRt ? 'SIM' : 'NAO'} onChange={e => {
                        const active = e.target.value === 'SIM'
                        setIncludeRt(active)
                        if (!active) {
                          setRtType('VALOR_FIXO')
                          setRtValue(0)
                          setRtPercent(0)
                        }
                      }}>
                        <option value="NAO">Sem RT</option>
                        <option value="SIM">Incluir RT</option>
                      </select>
                    </Field>

                    {includeRt && (
                      <>
                        <Field label="Tipo de RT">
                          <select value={rtType} onChange={e => {
                            const type = e.target.value as 'VALOR_FIXO' | 'PERCENTUAL'
                            setRtType(type)
                            if (type === 'VALOR_FIXO') setRtPercent(0)
                            else setRtValue(0)
                          }}>
                            <option value="VALOR_FIXO">Valor fixo</option>
                            <option value="PERCENTUAL">Percentual</option>
                          </select>
                        </Field>

                        {rtType === 'VALOR_FIXO' ? (
                          <Field label="Valor RT">
                            <ZeroNumberInput min="0" step="0.01" value={rtValue === 0 ? '' : rtValue} onValueChange={setRtValue} />
                          </Field>
                        ) : (
                          <Field label="RT %">
                            <ZeroNumberInput min="0" max="100" step="0.01" value={rtPercent === 0 ? '' : rtPercent} onValueChange={setRtPercent} />
                          </Field>
                        )}
                      </>
                    )}
                  </>
                )}
              </>
            ) : (
              <>
                <Field label="Revenda">
                  <select value={partnerId ?? ''} onChange={e => {
                    if (e.target.value === CREATE_COMMERCIAL_VALUE) {
                      setCommercialRegistration('revenda')
                      return
                    }
                    const id = e.target.value ? Number(e.target.value) : null
                    setPartnerId(id)
                    setPartnerPercent(Number(partners.find(p => p.id === id)?.percentual_padrao ?? 0))
                  }}>
                    <option value="">Selecione a revenda</option>
                    {partners.map(p => <option key={p.id} value={p.id}>{p.nome}</option>)}
                    <option value={CREATE_COMMERCIAL_VALUE}>+ Cadastrar nova revenda</option>
                  </select>
                </Field>

                <Field label="% revenda">
                  <ZeroNumberInput min="0" step="0.01" disabled={!partnerId} value={partnerPercent === 0 ? '' : partnerPercent} onValueChange={setPartnerPercent} />
                </Field>

                <Field label="Representante?">
                  <select value={showPartnerRepresentative ? 'SIM' : 'NAO'} onChange={e => {
                    const active = e.target.value === 'SIM'
                    setShowPartnerRepresentative(active)
                    if (!active) {
                      changeRepresentative(null)
                      setIncludeRt(false)
                      setRtValue(0)
                      setRtPercent(0)
                    }
                  }}>
                    <option value="NAO">Não</option>
                    <option value="SIM">Sim</option>
                  </select>
                </Field>

                {showPartnerRepresentative && (
                  <>
                    <Field label="Representante">
                      <select value={representativeId ?? ''} onChange={e => handleRepresentativeSelect(e.target.value)}>
                        <option value="">Selecione o representante</option>
                        {representatives.map(r => <option key={r.id} value={r.id}>{r.nome}</option>)}
                        <option value={CREATE_COMMERCIAL_VALUE}>+ Cadastrar novo representante</option>
                      </select>
                    </Field>

                    <Field label="RT">
                      <select disabled={representativeId === null} value={includeRt ? 'SIM' : 'NAO'} onChange={e => {
                        const active = e.target.value === 'SIM'
                        setIncludeRt(active)
                        if (!active) {
                          setRtValue(0)
                          setRtPercent(0)
                        }
                      }}>
                        <option value="NAO">Sem RT</option>
                        <option value="SIM">Incluir RT</option>
                      </select>
                    </Field>

                    {includeRt && (
                      <>
                        <Field label="Tipo de RT">
                          <select value={rtType} onChange={e => {
                            const type = e.target.value as 'VALOR_FIXO' | 'PERCENTUAL'
                            setRtType(type)
                            if (type === 'VALOR_FIXO') setRtPercent(0)
                            else setRtValue(0)
                          }}>
                            <option value="VALOR_FIXO">Valor fixo</option>
                            <option value="PERCENTUAL">Percentual</option>
                          </select>
                        </Field>

                        {rtType === 'VALOR_FIXO' ? (
                          <Field label="Valor RT">
                            <ZeroNumberInput min="0" step="0.01" value={rtValue === 0 ? '' : rtValue} onValueChange={setRtValue} />
                          </Field>
                        ) : (
                          <Field label="RT %">
                            <ZeroNumberInput min="0" max="100" step="0.01" value={rtPercent === 0 ? '' : rtPercent} onValueChange={setRtPercent} />
                          </Field>
                        )}
                      </>
                    )}
                  </>
                )}

                <Field label="Cliente">
                  <input type="text" placeholder="Nome ou referência" value={partnerFinalClient} onChange={e => setPartnerFinalClient(e.target.value)} />
                </Field>

                <Field label="Dados completos?">
                  <select disabled={!partnerFinalClient.trim()} value={partnerFinalClientFull ? 'SIM' : 'NAO'} onChange={e => setPartnerFinalClientFull(e.target.value === 'SIM')}>
                    <option value="NAO">Não</option>
                    <option value="SIM">Sim</option>
                  </select>
                </Field>

                {partnerFinalClientFull && partnerFinalClient.trim() && (
                  <>
                    <Field label="CPF / CNPJ">
                      <input type="text" value={partnerFinalDocument} onChange={e => setPartnerFinalDocument(e.target.value)} />
                    </Field>
                    <Field label="Telefone">
                      <input type="text" value={partnerFinalPhone} onChange={e => setPartnerFinalPhone(e.target.value)} />
                    </Field>
                    <Field label="E-mail">
                      <input type="email" value={partnerFinalEmail} onChange={e => setPartnerFinalEmail(e.target.value)} />
                    </Field>
                    <Field label="Endereço">
                      <input type="text" value={partnerFinalAddress} onChange={e => setPartnerFinalAddress(e.target.value)} />
                    </Field>
                  </>
                )}

                <div style={{ gridColumn: '1 / -1', border: '1px solid #d9dee7', borderRadius: 12, padding: '16px 18px', background: '#fafafa' }}>
                  <div style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 10, opacity: .65 }}>
                    Prévia do cabeçalho da venda
                  </div>
                  {partnerFinalClient.trim() && <div style={{ marginBottom: 6 }}><strong>Cliente:</strong>{' '}{partnerFinalClient}</div>}
                  {showPartnerRepresentative && representativeId && <div style={{ marginBottom: 6 }}><strong>Representante:</strong>{' '}{representatives.find(r => r.id === representativeId)?.nome ?? `Representante #${representativeId}`}</div>}
                  {sellerId && <div style={{ marginBottom: 6 }}><strong>Vendedor Smart-tec:</strong>{' '}{String(sellers.find(s => s.id === sellerId)?.nome ?? '')}</div>}
                  {partnerId && <div><strong>Revenda:</strong>{' '}{partners.find(p => p.id === partnerId)?.nome ?? ''}</div>}
                  {!partnerFinalClient.trim() && !representativeId && !partnerId && <span style={{ opacity: .6 }}>Selecione a revenda para visualizar.</span>}
                </div>
              </>
            )}
          </div>
        </Section>
        <Section title="Dados da venda" subtitle="Venda manual, sem vínculo com orçamento de origem." icon={<FileText size={17} />}><div className="form-grid general-grid"><Field label="Situação"><input value="Em aberto" readOnly /></Field><Field label="Data da venda"><input type="date" value={saleDate} onChange={e => setSaleDate(e.target.value)} /></Field><Field label="Prazo de entrega"><input type="date" value={deadline} onChange={e => setDeadline(e.target.value)} /></Field><Field label="Canal de venda"><input maxLength={100} value={channel} onChange={e => setChannel(e.target.value)} /></Field></div></Section>

        <Section title="Produtos" subtitle="Selecione produtos e configure suas medidas e detalhes." icon={<PackagePlus size={17} />}><div className="product-rows">{products.map(p => <BudgetProductRow key={p.id} product={p} catalog={catalog} commercialType={profileLabel[profile]} validationAttempted={attempted} onRomana={onRomana} onRomanaTeto={onRomanaTeto} onRolo={onRolo} onDoubleVision={onDoubleVision} onCurtain={onCurtain} onChange={updateProduct} onRemove={() => setProducts(rows => rows.filter(row => row.id !== p.id))} />)}</div><button type="button" className="secondary-button add-product" onClick={addProduct}><Plus size={16} /> Adicionar produto</button></Section>
        <Section title="Serviços" subtitle="Descrição, quantidade, valor e desconto de cada serviço." icon={<ReceiptText size={17} />}><div className="service-rows">{services.map(s => <BudgetServiceRow key={s.id} service={s} onChange={next => setServices(rows => rows.map(row => row.id === next.id ? next : row))} onRemove={() => setServices(rows => rows.filter(row => row.id !== s.id))} />)}</div><button type="button" className="secondary-button add-product" onClick={addService}><Plus size={16} /> Adicionar serviço</button></Section>
        <Section title="Observações" subtitle="Informações da venda e notas de uso interno." icon={<FileText size={17} />}><div className="budget-observations-grid"><Field label="Observações"><textarea value={observation} onChange={e => setObservation(e.target.value)} /></Field><Field label="Observação interna"><textarea value={internalObservation} onChange={e => setInternalObservation(e.target.value)} /></Field></div></Section>
      </fieldset>
      <BudgetSummary products={productsTotal} services={servicesTotal} freight={0} showFreight={false} discount={discount} onDiscount={value => { if (!savingRef.current) setDiscount(value) }} includeBankFee={includeBankFee} onIncludeBankFee={value => { if (!savingRef.current) setIncludeBankFee(value) }} bankFeePercent={bankFeePercent} onBankFeePercent={value => { if (!savingRef.current) setBankFeePercent(value) }} internalValue={internalValue} partnerValue={partnerValue} rtValue={rtAmount} bankFeeValue={roundHalfUp(clientTotal-base)} clientTotal={clientTotal} onCancel={() => { if (!savingRef.current) onBack() }} onSave={() => void save()} saving={saving} saveLabel="Salvar venda" isCollapsed={collapsed} onToggle={() => setCollapsed(value => !value)} />
    </div>
    {commercialRegistration && <CommercialRegistrationDialog entity={commercialRegistration} onClose={() => setCommercialRegistration(null)} onCreated={record => {
      if (commercialRegistration === 'revenda') { setPartners(rows => [record, ...rows]); setPartnerId(record.id); setPartnerPercent(Number(record.percentual_padrao ?? 0)) }
      else { setRepresentatives(rows => [record, ...rows]); changeRepresentative(record.id) }
    }} />}
    {showClientModal && <div className="modal-overlay" onClick={handleCloseClientModal}>
      <div className="modal-container" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3><UserPlus size={16} /> Cadastrar novo cliente</h3>
          <button type="button" className="modal-close" onClick={handleCloseClientModal}><X size={16} /></button>
        </div>
        <form className="modal-form" onSubmit={e => { e.preventDefault(); void handleCreateClient() }}>
          <div className="modal-field">
            <label>Tipo *</label>
            <select value={clientForm.tipo} onChange={e => { setClientForm(current => ({ ...current, tipo: e.target.value })); setClientModalError('') }}>
              <option value="">Selecione</option>
              <option value="Pessoa Física">Pessoa Física</option>
              <option value="Pessoa Jurídica">Pessoa Jurídica</option>
            </select>
          </div>
          <div className="modal-field">
            <label>Nome *</label>
            <input type="text" value={clientForm.nome} onChange={e => { setClientForm(current => ({ ...current, nome: e.target.value })); setClientModalError('') }} placeholder="Nome do cliente" autoFocus disabled={clientModalSaving} />
          </div>
          {clientModalError && <div className="modal-error" role="alert">{clientModalError}</div>}
          <div className="modal-actions">
            <button type="button" className="secondary-button" onClick={handleCloseClientModal} disabled={clientModalSaving}>Cancelar</button>
            <button type="submit" className="primary-button" disabled={clientModalSaving || !clientForm.tipo.trim() || !clientForm.nome.trim()}>
              {clientModalSaving ? <><Loader2 size={14} className="spinning" /> Salvando...</> : <><UserPlus size={14} /> Salvar e selecionar</>}
            </button>
          </div>
        </form>
      </div>
    </div>}
  </div>
}
