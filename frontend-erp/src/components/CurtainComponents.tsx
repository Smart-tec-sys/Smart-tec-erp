import { useState } from 'react'
import type { ApiProduct, CurtainComponent } from '../types/budget'
import { formatCurrency, productCost } from '../types/budget'
import { curtainComponentSubtotal, curtainComponentUnitCost, curtainComponentUnit, isCurtainComponent, searchCurtainComponents } from '../utils/curtainComponents'
import './curtainComponents.css'

type Props = { catalog: ApiProduct[]; lines: CurtainComponent[]; onChange: (lines: CurtainComponent[]) => void; allowPackageConversion?: boolean }

function ComponentLine({ line, catalog, onChange, onRemove, allowPackageConversion }: { line: CurtainComponent; catalog: ApiProduct[]; onChange: (line: CurtainComponent) => void; onRemove: () => void; allowPackageConversion?: boolean }) {
  const product = catalog.find(product => product.id === line.produto_id)
  const [query, setQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [quantityText, setQuantityText] = useState<string | null>(null)
  const units = line.unidades_por_embalagem ?? 1
  const validPackage = Number.isInteger(units) && units >= 1
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
          onMouseDown={event => event.preventDefault()} onClick={() => { onChange(match.id === line.produto_id ? line : { produto_id: match.id, quantidade: line.quantidade }); setSearching(false) }}>
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
    <div><small>Unidade</small><div>{line.unidades_por_embalagem !== undefined ? 'UN (convertida)' : product ? curtainComponentUnit(product) : '—'}</div></div>
    {allowPackageConversion && <label className="field curtain-package-conversion"><span>Unidades por embalagem</span><input aria-label="Unidades por embalagem" type="number" min="1" step="1" value={line.unidades_por_embalagem ?? ''} placeholder="Sem conversao"
      onChange={event => onChange({ ...line, unidades_por_embalagem: event.target.value === '' ? undefined : Number(event.target.value) })} />
      {line.unidades_por_embalagem !== undefined && <small>Custo cadastrado por embalagem: {formatCurrency(product ? productCost(product) : 0)}. Quantidade por peca em unidades individuais.</small>}
      {!validPackage && <small role="alert">Informe um inteiro positivo para unidades por embalagem.</small>}
    </label>}
    <div><small>Custo por unidade</small><div>{validPackage ? formatCurrency(curtainComponentUnitCost(line, product)) : 'Invalido'}</div></div>
    <div><small>Subtotal</small><strong>{validPackage ? formatCurrency(curtainComponentSubtotal(line, product)) : 'Pendente'}</strong></div>
    <button className="curtain-component-remove" type="button" aria-label="Remover componente" onClick={onRemove}>×</button>
  </div>
}

export function CurtainComponents({ catalog, lines, onChange, allowPackageConversion }: Props) {
  return <section className="curtain-components">
    <h4>Componentes da cortina</h4>
    <p>Escolha os produtos e quantidades por peça. Nenhum componente é adicionado pelo modelo da cortina.</p>
    {lines.map((line, index) => <ComponentLine key={index} line={line} catalog={catalog} allowPackageConversion={allowPackageConversion}
      onChange={value => onChange(lines.map((existing, i) => i === index ? value : existing))}
      onRemove={() => onChange(lines.filter((_, i) => i !== index))} />)}
    <button type="button" className="secondary" onClick={() => onChange([...lines, { quantidade: 1 }])}>+ Adicionar componente</button>
  </section>
}
