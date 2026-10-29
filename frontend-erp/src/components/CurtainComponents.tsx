import { useState } from 'react'
import type { ApiProduct, CurtainComponent } from '../types/budget'
import { formatCurrency, productCost } from '../types/budget'
import { curtainComponentSubtotal, curtainComponentUnit, isCurtainComponent, searchCurtainComponents } from '../utils/curtainComponents'
import './curtainComponents.css'

type Props = { catalog: ApiProduct[]; lines: CurtainComponent[]; onChange: (lines: CurtainComponent[]) => void }

function ComponentLine({ line, catalog, onChange, onRemove }: { line: CurtainComponent; catalog: ApiProduct[]; onChange: (line: CurtainComponent) => void; onRemove: () => void }) {
  const product = catalog.find(product => product.id === line.produto_id)
  const [query, setQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [quantityText, setQuantityText] = useState<string | null>(null)
  const matches = searchCurtainComponents(catalog, query)
  const unit = product ? curtainComponentUnit(product).trim().toUpperCase().replace(/\./g, '').replace(/\s+/g, ' ') : ''
  const linearMeters = ['M', 'ML', 'METRO', 'METROS', 'METRO LINEAR', 'METROS LINEARES', 'M LINEAR', 'M LINEARES'].includes(unit)
  const displayedQuantity = linearMeters
    ? line.quantidade.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2, useGrouping: false })
    : String(line.quantidade)
  return <div className="curtain-component-line">
    <div className="curtain-component-search" onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setSearching(false) }}>
      <label className="field"><span>Componente</span><input aria-label="Buscar componente" value={searching ? query : product?.nome ?? ''} placeholder="Buscar componente..."
        onFocus={() => { setQuery(''); setSearching(true) }} onChange={event => { setQuery(event.target.value); setSearching(true) }}
        onKeyDown={event => { if (event.key === 'ArrowDown') { event.preventDefault(); event.currentTarget.closest('.curtain-component-search')?.querySelector<HTMLButtonElement>('[role=option]')?.focus() } if (event.key === 'Escape') { setSearching(false); event.currentTarget.blur() } }} /></label>
      {searching && <div className="curtain-component-options" role="listbox" aria-label="Componentes de cortina">
        {matches.map(match => <button type="button" role="option" aria-selected={line.produto_id === match.id} key={match.id}
          onMouseDown={event => event.preventDefault()} onClick={() => { onChange({ ...line, produto_id: match.id }); setSearching(false) }}>
          <strong>{match.nome}</strong><small>{match.nome_fornecedor || match.fornecedores || '—'} · {curtainComponentUnit(match)} · {formatCurrency(productCost(match))}</small>
        </button>)}
        {!matches.length && <span>Nenhum componente de cortina encontrado.</span>}
      </div>}
      {product && !isCurtainComponent(product) && <small role="alert">Produto indisponível no catálogo de componentes de cortina. Selecione outro ou remova.</small>}
      {line.produto_id && !product && <small role="alert">Produto #{line.produto_id} indisponível. Selecione outro ou remova.</small>}
    </div>
    <label className="field"><span>Quantidade por peça</span><input aria-label="Quantidade do componente" inputMode="decimal" value={quantityText ?? displayedQuantity}
      onFocus={event => { if (line.quantidade === 0) event.currentTarget.select() }} onBlur={() => setQuantityText(null)}
      onChange={event => {
        const text = event.target.value
        setQuantityText(text)
        const quantity = Number(text.trim().replace(',', '.'))
        // Text-only edits must not clear a valid simulation whose numeric key is unchanged.
        if (Number.isFinite(quantity) && quantity >= 0 && quantity !== line.quantidade) {
          onChange({ ...line, quantidade: quantity })
        }
      }} /></label>
    <div><small>Unidade</small><div>{product ? curtainComponentUnit(product) : '—'}</div></div>
    <div><small>Custo</small><div>{formatCurrency(product ? productCost(product) : 0)}</div></div>
    <div><small>Subtotal</small><strong>{formatCurrency(curtainComponentSubtotal(line, product))}</strong></div>
    <button className="curtain-component-remove" type="button" aria-label="Remover componente" onClick={onRemove}>×</button>
  </div>
}

export function CurtainComponents({ catalog, lines, onChange }: Props) {
  return <section className="curtain-components">
    <h4>Componentes da cortina</h4>
    <p>Escolha os produtos e quantidades por peça. Nenhum componente é adicionado pelo modelo da cortina.</p>
    {lines.map((line, index) => <ComponentLine key={index} line={line} catalog={catalog}
      onChange={value => onChange(lines.map((existing, i) => i === index ? value : existing))}
      onRemove={() => onChange(lines.filter((_, i) => i !== index))} />)}
    <button type="button" className="secondary" onClick={() => onChange([...lines, { quantidade: 1 }])}>+ Adicionar componente</button>
  </section>
}
