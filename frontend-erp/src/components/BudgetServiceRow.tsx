import { Trash2, Plus } from 'lucide-react'
import type { BudgetService } from '../types/budget'
import { formatCurrency } from '../types/budget'

type Props = {
  service: BudgetService;
  onChange: (next: BudgetService) => void;
  onRemove: () => void;
  onCreateService?: (serviceId: number) => void;
  createServiceValue?: string;
  serviceOptions?: string[];
}

export function BudgetServiceRow({ service, onChange, onRemove, onCreateService, createServiceValue = '__CREATE_SERVICE__', serviceOptions = [] }: Props) {
  const update = <K extends keyof BudgetService>(key: K, value: BudgetService[K]) => onChange({ ...service, [key]: value })
  const subtotal = Math.max(0, service.quantity * service.value - service.discount)

  const handleServiceChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value
    if (value === createServiceValue && onCreateService) {
      onCreateService(service.id)
      return
    }
    update('service', value)
  }

  return <article className="budget-service-row"><div className="service-row-title"><span>{String(service.id).padStart(2, '0')}</span><strong>{service.service}</strong><button type="button" className="row-remove" aria-label={`Remover ${service.service}`} onClick={onRemove}><Trash2 size={15} /></button></div><div className="service-fields"><label className="field"><span>Serviço</span><select value={service.service} onChange={handleServiceChange}>{serviceOptions.map((opt, idx) => <option key={idx} value={opt}>{opt}</option>)}<option value={createServiceValue}><Plus size={14} className="inline-icon"/> + Cadastrar novo serviço</option></select></label><label className="field service-details"><span>Detalhes</span><input value={service.details} onChange={(e) => update('details', e.target.value)} /></label><label className="field"><span>Quantidade</span><input type="number" min="1" value={service.quantity} onChange={(e) => update('quantity', Math.max(1, Number(e.target.value)))} /></label><label className="field"><span>Valor</span><input type="number" min="0" step="0.01" value={service.value} onChange={(e) => update('value', Number(e.target.value))} /></label><label className="field"><span>Desconto</span><input type="number" min="0" step="0.01" value={service.discount} onChange={(e) => update('discount', Number(e.target.value))} /></label><div className="service-subtotal"><span>Subtotal</span><strong>{formatCurrency(subtotal)}</strong></div></div></article>
}
