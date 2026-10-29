import { ArrowLeft, FileText, WalletCards, PackagePlus, ReceiptText, Truck, ChevronRight, ChevronLeft } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import {
  getOrder,
  getClients,
  getFuncionariosCadastro,
  getCommercialPartners,
  getRepresentatives,
  type ApiOrder,
  type ApiCommercialPartner,
  type ApiRepresentative,
  type CadastroRecord,
} from '../services/api'
import { formatCurrency, type ApiClient } from '../types/budget'
import './saleDetailPage.css'

type Props = { saleId: number; onBack: () => void }

function text(value: unknown): string {
  return typeof value === 'string' && value.trim() ? value.trim() : '—'
}

function recordName(records: { id: number; nome?: unknown }[], id: number | null | undefined, fallback: string) {
  if (id == null) return '—'
  const name = text(records.find(record => record.id === id)?.nome)
  return name === '—' ? `${fallback} #${id}` : name
}

function dateLabel(value?: string | null) {
  if (!value) return '—'
  const date = new Date(`${value.slice(0, 10)}T12:00:00`)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('pt-BR')
}

function numberLabel(value: number | string | null | undefined) {
  if (value == null || value === '') return '—'
  const number = Number(value)
  return Number.isFinite(number)
    ? number.toLocaleString('pt-BR', { maximumFractionDigits: 4 })
    : String(value)
}

function moneyLabel(value: number | string | null | undefined) {
  if (value == null || value === '') return '—'
  const number = Number(value)
  return Number.isFinite(number) ? formatCurrency(number) : String(value)
}

function statusLabel(status?: string | null) {
  if (!status?.trim()) return '—'
  const value = status.toUpperCase()
  const labels: Record<string, string> = {
    ABERTO: 'Em aberto', CONCLUIDO: 'Concluído', CANCELADO: 'Cancelado', FATURADO: 'Faturado',
  }
  return labels[value] ?? value.replaceAll('_', ' ')
}

// Mesmo JSX dos componentes locais de NewBudgetPage, sem alterar o orçamento.
function BudgetSection({icon,title,subtitle,count,children}:{icon:ReactNode;title:string;subtitle:string;count?:string;children:ReactNode}){return <section className="form-section panel"><div className="section-title"><div className="section-icon">{icon}</div><div><h2>{title}</h2><p>{subtitle}</p></div>{count&&<span className="section-count">{count}</span>}</div>{children}</section>}
function Field({label,children}:{label:string;children:ReactNode}){return <label className="field"><span>{label}</span>{children}</label>}
function ReadOnlyField({ label, value }: { label: string; value: string }) {
  return <Field label={label}><input value={value} readOnly /></Field>
}
function SaleItems({ items, services = false }: { items: ApiOrder['itens']; services?: boolean }) {
  return <div className={services ? 'service-rows' : 'product-rows'}>{items.map((item, index) => (
    <div className={services ? 'budget-service-row' : 'budget-product-row'} key={item.id}>
      <div className={services ? 'service-row-title' : 'product-row-head'}>
        <span className="product-row-index">{index + 1}</span>
        <strong>{text(item.descricao)}</strong>
      </div>
      <div className={services ? 'service-fields' : 'product-fields'}>
        <ReadOnlyField label={services ? 'Serviço' : 'Produto'} value={text(item.descricao)} />
        <ReadOnlyField label="Código" value={text(item.codigo_interno)} />
        <ReadOnlyField label="Detalhe" value={text(item.observacao_item)} />
        <ReadOnlyField label="Quant." value={numberLabel(item.quantidade)} />
        <ReadOnlyField label="Unidade" value={text(item.unidade)} />
        <ReadOnlyField label="Largura" value={numberLabel(item.largura)} />
        <ReadOnlyField label="Altura" value={numberLabel(item.altura)} />
        <ReadOnlyField label="Valor unitário" value={moneyLabel(item.preco_unitario)} />
        <ReadOnlyField label="Desconto" value={moneyLabel(item.desconto)} />
        <div className="product-subtotal"><span>Subtotal</span><strong>{moneyLabel(item.subtotal)}</strong></div>
      </div>
      <details className="sale-item-technical">
        <summary>Dados técnicos</summary>
        <div className="form-grid general-grid">
          <ReadOnlyField label="Grupo técnico" value={text(item.grupo_tecnico)} />
          <ReadOnlyField label="Modelo" value={text(item.modelo_tecnico)} />
          <ReadOnlyField label="Material" value={text(item.material)} />
          <ReadOnlyField label="Cor" value={text(item.cor)} />
          <ReadOnlyField label="Acionamento" value={text(item.acionamento)} />
          <ReadOnlyField label="Lado do comando" value={text(item.lado_comando)} />
          <ReadOnlyField label="Área" value={numberLabel(item.area)} />
        </div>
      </details>
    </div>
  ))}</div>
}

export function SaleDetailPage({ saleId, onBack }: Props) {
  const [order, setOrder] = useState<ApiOrder | null>(null)
  const [clients, setClients] = useState<ApiClient[]>([])
  const [sellers, setSellers] = useState<CadastroRecord[]>([])
  const [partners, setPartners] = useState<ApiCommercialPartner[]>([])
  const [representatives, setRepresentatives] = useState<ApiRepresentative[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notFound, setNotFound] = useState(false)
  const [isSummaryCollapsed, setIsSummaryCollapsed] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    setNotFound(false)
    setOrder(null)
    setClients([])
    setSellers([])
    setPartners([])
    setRepresentatives([])

    void Promise.all([
      getOrder(saleId),
      Promise.allSettled([
        getClients(), getFuncionariosCadastro(), getCommercialPartners(), getRepresentatives(),
      ]),
    ]).then(([sale, names]) => {
      if (cancelled) return
      if (!sale) { setNotFound(true); return }
      setOrder(sale)
      const [clientResult, sellerResult, partnerResult, representativeResult] = names
      if (clientResult.status === 'fulfilled') setClients(clientResult.value)
      if (sellerResult.status === 'fulfilled') setSellers(sellerResult.value)
      if (partnerResult.status === 'fulfilled') setPartners(partnerResult.value)
      if (representativeResult.status === 'fulfilled') setRepresentatives(representativeResult.value)
      names.forEach(result => {
        if (result.status === 'rejected') console.warn('Falha ao carregar nomes da venda', result.reason)
      })
    }).catch(err => {
      if (cancelled) return
      const message = err instanceof Error ? err.message : String(err)
      if (message.startsWith('API 404:')) setNotFound(true)
      else setError(message)
    }).finally(() => {
      if (!cancelled) setLoading(false)
    })

    return () => { cancelled = true }
  }, [saleId])

  const items = order?.itens ?? []
  const services = items.filter(item => item.tipo_item?.toUpperCase() === 'SERVICO')
  const products = items.filter(item => item.tipo_item?.toUpperCase() !== 'SERVICO')
  // Apenas agrupa subtotais persistidos; não recalcula preços ou o total do pedido.
  const productsSubtotal = products.reduce((sum, item) => sum + Number(item.subtotal), 0)
  const servicesSubtotal = services.reduce((sum, item) => sum + Number(item.subtotal), 0)
  const budget = order?.orcamento_numero
    ? `#${order.orcamento_numero}`
    : order?.orcamento_id != null ? `ID ${order.orcamento_id}` : '—'

  return <div className="new-budget-page sale-detail-page">
    {loading ? <><button type="button" className="back-button page-back" onClick={onBack}><ArrowLeft size={15} /> Voltar para vendas</button><div className="panel loading-state" role="status">Carregando venda...</div></>
      : notFound ? <><button type="button" className="back-button page-back" onClick={onBack}><ArrowLeft size={15} /> Voltar para vendas</button><div className="panel loading-state" role="status">Venda não encontrada.</div></>
      : error ? <><button type="button" className="back-button page-back" onClick={onBack}><ArrowLeft size={15} /> Voltar para vendas</button><div className="api-message error" role="alert">Não foi possível carregar a venda. {error}</div></>
      : order && <>
        <section className="new-budget-heading page-heading">
          <div>
            <button type="button" className="back-button page-back" onClick={onBack}><ArrowLeft size={15} /> Voltar para vendas</button>
            <p className="eyebrow">OPERAÇÃO COMERCIAL CONECTADA</p>
            <h1>Venda {order.numero || `#${order.id}`} <span className="draft-badge">{statusLabel(order.status)}</span></h1>
            <p className="heading-subtitle">Dados comerciais e operacionais da venda.</p>
          </div>
          <div className="budget-number"><span>NÚMERO</span><strong>{order.numero || `#${order.id}`}</strong></div>
        </section>
        <div className={`new-budget-layout ${isSummaryCollapsed ? 'summary-collapsed' : ''}`}>
          <div className="new-budget-main">
            <BudgetSection icon={<FileText size={17}/>} title="Dados da venda" subtitle="Número, cliente, vendedor, situação e datas.">
              <div className="form-grid general-grid">
                <ReadOnlyField label="Número" value={order.numero || `#${order.id}`} />
                {order.parceiro_id == null && <ReadOnlyField label="Cliente direto" value={recordName(clients, order.cliente_id, 'Cliente')} />}
                <ReadOnlyField label="Situação" value={statusLabel(order.status)} />
                <ReadOnlyField label="Vendedor Smart-tec" value={recordName(sellers, order.vendedor_id, 'Funcionário')} />
                <ReadOnlyField label="Data" value={dateLabel(order.data_venda)} />
                <ReadOnlyField label="Prazo de entrega" value={dateLabel(order.prazo_entrega)} />
                <ReadOnlyField label="Canal de venda" value={text(order.canal_venda)} />
                <ReadOnlyField label="Orçamento de origem" value={budget} />
              </div>
            </BudgetSection>
            <BudgetSection icon={<WalletCards size={17}/>} title="Fluxo comercial" subtitle="Controle interno.">
              <div className="form-grid general-grid">
                {order.parceiro_id != null && <>
                  <ReadOnlyField label="Revenda" value={recordName(partners, order.parceiro_id, 'Revenda')} />
                  {order.cliente_final_nome?.trim() && <ReadOnlyField label="Cliente final" value={text(order.cliente_final_nome)} />}
                  {order.cliente_final_documento?.trim() && <ReadOnlyField label="Documento" value={text(order.cliente_final_documento)} />}
                  {order.cliente_final_telefone?.trim() && <ReadOnlyField label="Telefone" value={text(order.cliente_final_telefone)} />}
                  {order.cliente_final_email?.trim() && <ReadOnlyField label="E-mail" value={text(order.cliente_final_email)} />}
                  {order.cliente_final_endereco?.trim() && <ReadOnlyField label="Endereço" value={text(order.cliente_final_endereco)} />}
                </>}
                <ReadOnlyField label="Representante" value={recordName(representatives, order.representante_id, 'Representante')} />
                <ReadOnlyField label="Perfil comercial" value={order.perfil_comercial === 'VAREJO' ? 'Varejo' : text(order.perfil_comercial)} />
              </div>
            </BudgetSection>
            <BudgetSection icon={<PackagePlus size={17}/>} title="Produtos" subtitle="Itens da venda, somente leitura." count={`${products.length} itens`}>
              {products.length ? <SaleItems items={products} /> : <div className="api-message">Nenhum produto nesta venda.</div>}
            </BudgetSection>
            <BudgetSection icon={<ReceiptText size={17}/>} title="Serviços" subtitle="Itens do tipo serviço, somente leitura." count={`${services.length} itens`}>
              {services.length ? <SaleItems items={services} services /> : <div className="api-message">Nenhum serviço nesta venda.</div>}
            </BudgetSection>
            <BudgetSection icon={<Truck size={17}/>} title="Transporte" subtitle="Informações de transporte da venda.">
              <div className="form-grid relationship-grid">
                <ReadOnlyField label="Frete" value={moneyLabel(0)} />
                <ReadOnlyField label="Transportadora" value="—" />
              </div>
            </BudgetSection>
            <BudgetSection icon={<WalletCards size={17}/>} title="Pagamento" subtitle="Informações de pagamento da venda.">
              <div className="api-message">Forma de pagamento não definida.</div>
            </BudgetSection>
            <BudgetSection icon={<FileText size={17}/>} title="Observações" subtitle="Informações para o cliente e anotações internas da equipe.">
              <div className="budget-observations-grid">
                <Field label="Observações para o cliente"><textarea readOnly value={text(order.observacao)} /></Field>
                <Field label="Observações internas"><textarea readOnly value={text(order.observacao_interna)} /></Field>
              </div>
            </BudgetSection>
          </div>
          <aside className={`budget-summary panel ${isSummaryCollapsed ? 'collapsed' : ''}`}>
            <div className="summary-heading">
              <div><span className="eyebrow">RESUMO DA VENDA</span><h2>Conferência</h2></div>
              <button type="button" className="summary-toggle" onClick={() => setIsSummaryCollapsed(value => !value)} aria-label={isSummaryCollapsed ? 'Mostrar resumo' : 'Recolher resumo'}><ChevronRight size={16}/></button>
            </div>
            <div className="summary-lines">
              <div><span>Produtos</span><strong>{moneyLabel(productsSubtotal)}</strong></div>
              <div><span>Serviços</span><strong>{moneyLabel(servicesSubtotal)}</strong></div>
              <div><span>Frete</span><strong>{moneyLabel(0)}</strong></div>
              <div><span>Subtotal</span><strong>{moneyLabel(order.total)}</strong></div>
              <div><span>Desconto</span><strong>{moneyLabel(order.desconto)}</strong></div>
            </div>
            <div className="summary-total"><span>Total final</span><strong>{moneyLabel(order.total_final)}</strong></div>
            <button type="button" className="secondary-button summary-action" onClick={onBack}><ArrowLeft size={14}/> Voltar para vendas</button>
          </aside>
        </div>
        {isSummaryCollapsed && <button type="button" className="summary-reopen-tab" onClick={() => setIsSummaryCollapsed(false)} aria-label="Mostrar resumo da venda" title="Mostrar resumo da venda"><ChevronLeft size={16}/><span>Mostrar resumo</span></button>}
      </>}
  </div>
}
