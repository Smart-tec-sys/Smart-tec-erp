import { ArrowLeft, Check, ChevronLeft, ChevronRight, FileClock } from 'lucide-react'
import { formatCurrency } from '../types/budget'

type Props = { products: number; services: number; freight: number; discount: number; onDiscount: (value: number) => void; onCancel: () => void; onSave: () => void; saving?: boolean; isCollapsed?: boolean; onToggle?: () => void }

export function BudgetSummary({ products, services, freight, discount, onDiscount, onCancel, onSave, saving, isCollapsed, onToggle }: Props) {
  const subtotal = products + services + freight
  const total = Math.max(0, subtotal - discount)
  return <aside className={`budget-summary panel ${isCollapsed ? 'collapsed' : ''}`}><div className="summary-heading"><div><span className="eyebrow">RESUMO COMERCIAL</span><h2>Conferência</h2></div><button type="button" className="summary-toggle" onClick={onToggle} aria-label={isCollapsed ? 'Mostrar resumo' : 'Recolher resumo'}><ChevronRight size={16} /></button></div>{!isCollapsed && (<div><div className="summary-lines"><div><span>Produtos</span><strong>{formatCurrency(products)}</strong></div><div><span>Serviços</span><strong>{formatCurrency(services)}</strong></div><div><span>Frete</span><strong>{formatCurrency(freight)}</strong></div><div><span>Subtotal</span><strong>{formatCurrency(subtotal)}</strong></div></div><label className="field summary-discount-field"><span>Desconto geral</span><input type="number" min="0" step="0.01" value={discount} onChange={(e) => onDiscount(Number(e.target.value))} /></label><div className="summary-total"><span>Total</span><strong>{formatCurrency(total)}</strong></div><div className="summary-note">Produtos, serviços, desconto e totais serão persistidos. Frete e pagamento ainda não possuem campo próprio no contrato.</div><button type="button" className="primary-button summary-action" onClick={onSave} disabled={saving}><Check size={17} /> {saving?'Salvando...':'Salvar orçamento'}</button><button type="button" className="back-button" onClick={onCancel}><ArrowLeft size={15} /> Cancelar e voltar</button></div>)}
</aside>
}
