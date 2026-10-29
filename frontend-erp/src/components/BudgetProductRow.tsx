import { CurtainColorField } from './CurtainColorField'
import { DEFAULT_CURTAIN, curtainSuggestions, applyCurtainSuggestion, type CurtainSuggestion } from '../utils/curtainFabricCatalog'
import { ZeroNumberInput, zeroInputValue } from './ZeroNumberInput'
import { fabricDisplay, fabricVariantKey, groupFabricSuggestions } from '../utils/fabricDisplay'
import { selectZeroOnFocus } from '../utils/selectZeroOnFocus'
import { Minus, Plus, Trash2, PackagePlus } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { ApiProduct, BudgetProduct, CommercialType } from '../types/budget'
import { commercialPrice, formatCurrency, normalizeSearch, productColor, productLineSubtotal } from '../types/budget'
const CREATE_PRODUCT_VALUE = '__CREATE_PRODUCT__'
import { RomanaSimulation } from './RomanaSimulation'
import { RomanaTetoSimulation } from './RomanaTetoSimulation'
import { RoloSimulation } from './RoloSimulation'
import { DoubleVisionSimulation } from './DoubleVisionSimulation'
import { CurtainSimulation } from './CurtainSimulation'
import type { CurtainState } from '../types/budget'
import { romanaKind, type RomanaState } from '../types/romana'
import { romanaTetoKind, type RomanaTetoState } from '../types/romana_teto'
import { roloKind, normalizeRoloDrive, type RoloState } from '../types/rolo'
import { doubleVisionKind, type DoubleVisionState } from '../types/double_vision'

const FAMILY_COLOR_OPTIONS: Record<string, readonly string[]> = {
  ROLO_BK_NAPOLES: ['BEGE', 'BRANCO', 'CINZA', 'CREME'] as const,
  ROLO_BK_DENVER: ['BEGE', 'BRANCO', 'CINZA'] as const,
  ROMANA_TETO_BLACKOUT_PIMPOINT: ['BEGE', 'BRANCO', 'CINZA'] as const,
  ROMANA_TETO_BLACKOUT_NAPOLES: ['BEGE', 'BRANCO', 'CINZA', 'CREME', 'MARROM'] as const,
  ROMANA_TETO_BLACKOUT_ROMA: ['BRANCO', 'LINHO', 'TINTO BEGE', 'TINTO PALHA', 'TINTO PRATA'] as const,
  ROMANA_TETO_SCREEN_1_ECO_IMPORTADA: ['BEGE', 'BRANCO', 'CINZA'] as const,
  ROMANA_TETO_SCREEN_1_ONE: ['51', '52', '53', '73', '75', 'BEGE', 'BRANCO', 'CINZA'] as const,
  ROMANA_TETO_SCREEN_3_JP_IMPORTADA: ['BEGE', 'BRANCO', 'CINZA', 'PRETO'] as const,
}

type Props = {
  product: BudgetProduct
  catalog: ApiProduct[]
  commercialType: CommercialType
  onChange: (next: BudgetProduct) => void
  onRemove: () => void
  onCreateProduct?: (productId: number) => void
  onRomana: (id: number, state: RomanaState) => void
  onRomanaTeto: (id: number, state: RomanaTetoState) => void
  onRolo: (id: number, state: RoloState) => void
  onDoubleVision: (id: number, state: DoubleVisionState) => void
  onCurtain: (id: number, state: CurtainState) => void
  validationAttempted?: boolean
}

const active = (p: ApiProduct) => !['INATIVO', 'INATIVA'].includes(normalizeSearch(p.status_comercial || p.situacao || 'ATIVO'))

const isCurtainCatalogItem = (p: ApiProduct) =>
  normalizeSearch(p.modelo_tecnico ?? '') === 'CORTINA' ||
  [p.grupo_tecnico, p.grupo_produto].some((group) =>
    /^TECIDOS? CORTINAS?$/.test(normalizeSearch(group ?? '').replace(/_/g, ' ')))

export function BudgetProductRow({
  product,
  catalog,
  commercialType,
  onChange,
  onRemove,
  onCreateProduct,
  onRomana,
  onRomanaTeto,
  onRolo,
  onDoubleVision,
  onCurtain,
  validationAttempted = false,
}: Props) {
  const isCurtain = product.modelTechnical === 'CORTINA' && product.groupTechnical === 'TECIDOS_CORTINA'
  const selected = catalog.find((p) => p.id === product.productId)
  const selectedDisplay = isCurtain
    ? 'Cortina de tecido'
    : fabricDisplay(selected ?? { id: product.productId ?? 0, nome: product.product }).name
  const [query, setQuery] = useState(fabricDisplay({ id: product.productId ?? 0, nome: product.product }).name)
  const update = <K extends keyof BudgetProduct>(key: K, value: BudgetProduct[K]) => onChange({ ...product, [key]: value })
  const matches = useMemo(() => {
    const terms = normalizeSearch(query).split(/\s+/).filter(Boolean)
    if (!terms.length) return []
    return catalog
      .filter(active)
      .filter((p) => {
        const hay = normalizeSearch(
          `${fabricDisplay(p).name} ${p.nome} ${p.produto_base || ''} ${p.codigo_interno || ''} ${p.codigo || ''} ${p.codigo_barras || ''} ${p.grupo_produto || ''} ${p.grupo_tecnico || ''} ${p.familia_tecnica || ''} ${p.modelo_tecnico || ''} ${p.modelo || ''} ${productColor(p)}`
        )
        return terms.every((t) => hay.includes(t))
      })

  }, [catalog, query])
  useEffect(() => { setQuery(selectedDisplay) }, [selectedDisplay])
  const variants = useMemo(
    () => (selected && fabricDisplay(selected).fabric && productColor(selected) ? catalog.filter(p => active(p) && fabricVariantKey(p) === fabricVariantKey(selected)) : selected?.familia_tecnica ? catalog.filter((p) => active(p) && p.familia_tecnica === selected.familia_tecnica) : selected ? [selected] : []),
    [catalog, selected]
  )
  const curtainVirtualMatches = useMemo(() => curtainSuggestions(catalog, query), [catalog, query])
  const rankedMatches = useMemo(() => {
    const q = normalizeSearch(query.trim())
    if (q.includes('CORTINA')) {
      return []
    }
    return groupFabricSuggestions(matches.filter((p) => !isCurtainCatalogItem(p)))
      .slice(0, 12)
  }, [matches, query])

  // Both sources reach exactly the same rendered dropdown array.
  const dropdownMatches = [
    ...rankedMatches.map(p => ({ key: String(p.id), product: p, suggestion: undefined as CurtainSuggestion | undefined })),
    ...curtainVirtualMatches.map(suggestion => ({ key: suggestion.key, product: undefined, suggestion })),
  ]

  const colors = useMemo(() => {
    const grouped = new Map<string, ApiProduct[]>()
    variants.filter((p) => !isCurtainCatalogItem(p)).forEach((p) => {
      const c = productColor(p)
      if (c) grouped.set(c, [...(grouped.get(c) || []), p])
    })
    return [...grouped.entries()]
  }, [variants])

  const fixedFamilyColors =
    selected?.familia_tecnica && !isCurtainCatalogItem(selected)
      ? FAMILY_COLOR_OPTIONS[selected.familia_tecnica] || []
      : []

  const chooseCurtain = (suggestion: CurtainSuggestion) => {
    const curtain = applyCurtainSuggestion(isCurtain ? product.curtain ?? DEFAULT_CURTAIN : DEFAULT_CURTAIN, suggestion)
    setQuery('Cortina de tecido')
    onChange({
      ...product,
      productId: null, product: 'Cortina de tecido', code: '', family: '',
      groupTechnical: 'TECIDOS_CORTINA', modelTechnical: 'CORTINA', unit: 'M²',
      color: curtain.cor, curtain, price: isCurtain ? product.price : 0,
      romanaKind: undefined, romana: undefined, romanaTetoKind: undefined, romanaTeto: undefined,
      roloKind: undefined, rolo: undefined, doubleVisionKind: undefined, doubleVision: undefined,
      acao_acionamento: undefined, lado_comando: undefined, comprimento_bastao: undefined,
      comprimento_corrente_sem_fim: undefined, acionamento: undefined,
    })
  }

  const choose = (p: ApiProduct) => {
    const rKind = romanaKind(p)
    const rtKind = romanaTetoKind(p)
    const rlKind = roloKind(p)
    const dvKind = doubleVisionKind(p)
    setQuery(fabricDisplay(p).name)
    onChange({
      ...product,
      productId: p.id,
      product: p.nome,
      code: p.codigo_interno || p.codigo || '',
      family: p.familia_tecnica || '',
      groupTechnical: p.grupo_tecnico || '',
      modelTechnical: p.modelo_tecnico || '',
      unit: p.unidade_venda || p.unidade || '',
      color: productColor(p),
      price: rKind ? 0 : rlKind ? 0 : dvKind ? 0 : rtKind ? 0 : commercialPrice(p, commercialType),
      romanaKind: rKind,
      romanaTetoKind: rtKind,
      romanaTeto: undefined,
      acao_acionamento: undefined,
      lado_comando: undefined,
      comprimento_bastao: undefined,
      comprimento_corrente_sem_fim: undefined,
      curtain: undefined,
      romana: undefined,
      roloKind: rlKind,
      rolo: undefined,
      doubleVisionKind: dvKind,
      doubleVision: undefined,
      acionamento: normalizeRoloDrive(rlKind === 'MOTORIZADA' ? 'motorizado' : 'manual'),
    })
  }

  const handleCreateProductClick = () => {
    onCreateProduct?.(product.id)
  }

  const handleColorChange = (cor: string) => {
    onChange({ ...product, color: cor })
  }

  const hasSelectedProduct = isCurtain || Boolean(product.productId)
  const quantityInvalid =
    hasSelectedProduct &&
    (!Number.isFinite(Number(product.quantity)) || Number(product.quantity) <= 0)
  const profileInvalid =
    hasSelectedProduct && !commercialType
  const valueInvalid =
    hasSelectedProduct &&
    (!Number.isFinite(Number(product.price)) || Number(product.price) <= 0)

  const subtotal = productLineSubtotal(product, commercialType)

  return (
    <article className="budget-product-row" onFocusCapture={selectZeroOnFocus}>
      <div className="product-row-head">
        <span className="product-row-index">{String(product.id).padStart(2, '0')}</span>
        <strong>Produto</strong>
        <button type="button" className="row-remove" aria-label={`Remover ${product.product}`} onClick={onRemove}>
          <Trash2 size={15} />
        </button>
      </div>
      <div className="product-fields">
        <label className="field product-field-wide product-search-box">
          <span>Produto</span>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ex.: rolo bk denver" autoComplete="off" />
          {query !== selectedDisplay && (
            <div className="product-suggestions">
              {onCreateProduct && <button type="button" key={CREATE_PRODUCT_VALUE} onClick={handleCreateProductClick} className="create-product-option">
                <PackagePlus size={14} /> + Cadastrar novo produto
              </button>}
              {dropdownMatches.length === 0 ? (
                <span className="no-matches">Nenhum produto encontrado</span>
              ) : (
                dropdownMatches.map(match => (
                  <button type="button" key={match.key}
                    onClick={() => { if (match.suggestion) chooseCurtain(match.suggestion); else if (match.product) choose(match.product) }}>
                    <strong>{match.suggestion?.label ?? fabricDisplay(match.product!).name}</strong>
                    {!match.suggestion && match.product && fabricDisplay(match.product).width && <small>Largura de fornecimento: {fabricDisplay(match.product).width}</small>}
                  </button>
                ))
              )}
            </div>
          )}
        </label>
        <label className="field">
          <span>Cor</span>
          {isCurtain ? (
            <CurtainColorField product={product} catalog={catalog} onChange={onChange} />
          ) : fixedFamilyColors.length > 0 ? (
            <select value={product.color} onChange={(e) => handleColorChange(e.target.value)} disabled={fixedFamilyColors.length === 0}>
              <option value="">Selecione a cor</option>
              {fixedFamilyColors.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          ) : (
            <select value={product.color} disabled={!colors.length} onChange={(e) => {
              const options = colors.find(([c]) => c === e.target.value)?.[1] || []
              if (options.length === 1) choose(options[0])
            }}>
              <option value="">Sem variaÃƒÂ§ÃƒÂ£o</option>
              {colors.map(([c, items]) => (
                <option key={c} value={c} disabled={items.length !== 1}>
                  {c}{items.length !== 1 ? ' (ambÃƒÂ­gua)' : ''}
                </option>
              ))}
            </select>
          )}
        </label>
        <label className="field product-field-wide">
          <span>Detalhe</span>
          <input value={product.details} onChange={(e) => update('details', e.target.value)} placeholder="Ex.: Sala Ã‚Â· comando ÃƒÂ  direita" />
        </label>
        <label className={`field${validationAttempted && quantityInvalid ? ' field-invalid' : ''}`}>
          <span>Quant. *</span>
          <div className="stepper">
            <button type="button" onClick={() => update('quantity', Math.max(1, product.quantity - 1))}>
              <Minus size={13} />
            </button>
            <input value={product.quantity} onChange={(e) => update('quantity', Math.max(1, Number(e.target.value) || 1))} />
            <button type="button" onClick={() => update('quantity', product.quantity + 1)}>
              <Plus size={13} />
            </button>
          </div>
        </label>
        <label className={`field${validationAttempted && profileInvalid ? ' field-invalid' : ''}`}>
          <span>Perfil *</span>
          <input value={commercialType} readOnly />
        </label>
        <label className="field">
          <span>Largura</span>
          <input inputMode="decimal" placeholder="0,00" value={zeroInputValue(product.width)} onChange={(e) => update('width', e.target.value)} />
        </label>
        <label className="field">
          <span>Altura</span>
          <input inputMode="decimal" placeholder="0,00" value={zeroInputValue(product.height)} onChange={(e) => update('height', e.target.value)} />
        </label>
        <label className={`field${validationAttempted && valueInvalid ? ' field-invalid' : ''}`}>
          <span>Valor *</span>
          <ZeroNumberInput min="0" step="0.01" value={product.price} readOnly={Boolean(product.romanaKind || product.romanaTetoKind || product.roloKind || product.doubleVisionKind || product.curtain)} onValueChange={value => update('price', value)} />
        </label>
        <div className="product-subtotal">
          <span>Subtotal estimado</span>
          <strong>{formatCurrency(subtotal)}</strong>
        </div>
      </div>
      <RomanaSimulation product={product} profile={commercialType} onResult={onRomana} />
      <RomanaTetoSimulation product={product} profile={commercialType} onResult={onRomanaTeto} onChange={onChange} />
      <RoloSimulation product={product} profile={commercialType} onResult={onRolo} />
      <DoubleVisionSimulation product={product} profile={commercialType} onResult={onDoubleVision} />
      <CurtainSimulation product={product} catalog={catalog} profile={commercialType} onResult={onCurtain} />
    </article>
  )
}
