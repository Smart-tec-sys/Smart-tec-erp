import { commercialDisplayText } from '../utils/commercialDisplay'
import { ZeroNumberInput } from './ZeroNumberInput'
import { selectZeroOnFocus } from '../utils/selectZeroOnFocus'
import { Trash2 } from 'lucide-react'
import type { BudgetService } from '../types/budget'
import { formatCurrency } from '../types/budget'
import { precoServicoParaAltura, type Servico, type UnidadeServico } from '../services/servicos'

type Props = {
  service: BudgetService;
  onChange: (next: BudgetService) => void;
  onRemove: () => void;
  catalogServices?: Servico[];
}

const unidades: UnidadeServico[] = ['UN', 'ML', 'M2', 'HORA', 'SERVICO']

export function BudgetServiceRow({ service, onChange, onRemove, catalogServices = [] }: Props) {
  const update = <K extends keyof BudgetService>(key: K, value: BudgetService[K]) => onChange({ ...service, [key]: value })
  const subtotal = Math.max(0, service.quantity * service.value - service.discount)
  const linkedService = catalogServices.find(item => item.id === service.serviceId)
  const updateHeight = (heightCm: number) => {
    let value = service.value
    if (linkedService?.tipo_calculo === 'FAIXA_ALTURA' && !service.priceManual) {
      try { value = precoServicoParaAltura(linkedService, heightCm) } catch { value = 0 }
    }
    onChange({ ...service, heightCm, value })
  }
  const selectCatalogService = (selectedId: string) => {
    const selected = catalogServices.find(item => item.id === Number(selectedId))
    if (!selected) {
      onChange({ ...service, serviceId: null, priceManual: true })
      return
    }
    let preco = selected.preco_venda
    if (selected.tipo_calculo === 'FAIXA_ALTURA' && service.heightCm) {
      try { preco = precoServicoParaAltura(selected, service.heightCm) } catch { preco = 0 }
    }
    onChange({
      ...service, serviceId: selected.id, service: selected.descricao, unit: selected.unidade,
      value: preco, priceManual: false,
    })
  }

  return <article className="budget-service-row" onFocusCapture={selectZeroOnFocus}>
    <div className="service-row-title"><span>{String(service.id).padStart(2, '0')}</span><strong>{commercialDisplayText(service.service)}</strong><button type="button" className="row-remove" aria-label={`Remover ${service.service}`} onClick={onRemove}><Trash2 size={15} /></button></div>
    <div className="service-fields">
      {catalogServices.length > 0 && <label className="field"><span>Catálogo</span><select value={service.serviceId ?? ''} onChange={e => selectCatalogService(e.target.value)}><option value="">Serviço livre</option>{service.serviceId && !linkedService && <option value={service.serviceId}>Serviço inativo ou indisponível · {commercialDisplayText(service.service)}</option>}{catalogServices.map(item => <option key={item.id} value={item.id}>{item.codigo} · {commercialDisplayText(item.descricao)}</option>)}</select></label>}
      <label className="field"><span>Serviço</span><input className={commercialDisplayText(service.service) === service.service.toLocaleUpperCase('pt-BR') ? 'commercial-name' : undefined} value={service.service} onChange={e => update('service', e.target.value)} placeholder="Descrição do serviço" /></label>
      <label className="field service-details"><span>Detalhes</span><input value={service.details} onChange={(e) => update('details', e.target.value)} /></label>
      <label className="field"><span>Unidade</span><select value={service.unit || 'UN'} disabled={Boolean(linkedService)} onChange={e => update('unit', e.target.value)}>{unidades.map(unit => <option key={unit} value={unit}>{unit === 'M2' ? 'M²' : unit}</option>)}</select></label>
      <label className="field"><span>Quantidade ({service.unit === 'M2' ? 'M²' : service.unit || 'UN'})</span><ZeroNumberInput min="0.0001" step="0.01" value={service.quantity} onValueChange={value => update('quantity', Math.max(0.0001, value))} /></label>
      {linkedService?.tipo_calculo === 'FAIXA_ALTURA' && <label className="field"><span>Altura (cm)</span><ZeroNumberInput min="0" step="0.1" value={service.heightCm || ''} onValueChange={updateHeight} /></label>}
      <label className="field"><span>Preço unitário</span><ZeroNumberInput min="0" step="0.01" value={service.value === 0 ? '' : service.value} onValueChange={value => onChange({ ...service, value, priceManual: true })} /></label>
      <label className="field"><span>Desconto</span><ZeroNumberInput min="0" step="0.01" value={service.discount === 0 ? '' : service.discount} onValueChange={value => update('discount', value)} /></label>
      <div className="service-subtotal"><span>Subtotal</span><strong>{formatCurrency(subtotal)}</strong></div>
    </div>
  </article>
}
