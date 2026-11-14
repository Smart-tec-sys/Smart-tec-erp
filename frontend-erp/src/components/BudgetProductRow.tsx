import { commercialDisplayText } from '../utils/commercialDisplay'
import { CurtainColorField } from './CurtainColorField'
import { DEFAULT_CURTAIN, curtainSuggestions, applyCurtainSuggestion, type CurtainSuggestion } from '../utils/curtainFabricCatalog'
import { ZeroNumberInput, zeroInputValue } from './ZeroNumberInput'
import { commercialVariantKey, fabricColor, fabricDisplay, fabricVariantKey, groupFabricCollections } from '../utils/fabricDisplay'
import { rankProductSuggestions } from '../utils/productSuggestionRank'
import { selectZeroOnFocus } from '../utils/selectZeroOnFocus'
import { Minus, Plus, Trash2, PackagePlus } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { ApiProduct, BudgetProduct, CommercialType } from '../types/budget'
import { commercialPrice, formatCurrency, normalizeSearch, productColor, productLineSubtotal, negotiateProductPrice, restoreSuggestedProductPrice, suggestedProductPrice } from '../types/budget'
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
  allowPackageConversion?: boolean
  allowManualPrice?: boolean
}

const active = (p: ApiProduct) => !['INATIVO', 'INATIVA'].includes(normalizeSearch(p.status_comercial || p.situacao || 'ATIVO'))

const isFinishedProduct = (p: ApiProduct) =>
  Boolean(romanaKind(p) || romanaTetoKind(p) || roloKind(p) || doubleVisionKind(p))

const isCurtainCatalogItem = (p: ApiProduct) =>
  normalizeSearch(p.modelo_tecnico ?? '') === 'CORTINA' ||
  [p.grupo_tecnico, p.grupo_produto].some((group) =>
    /^TECIDOS? CORTINAS?$/.test(normalizeSearch(group ?? '').replace(/_/g, ' ')))

export function BudgetProductRow({
  product,
  catalog,
  allowPackageConversion,
  allowManualPrice = false,
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
          `${fabricDisplay(p).name} ${p.nome} ${p.produto_base || ''} ${p.codigo_interno || ''} ${p.codigo || ''} ${p.codigo_barras || ''} ${p.grupo_produto || ''} ${p.grupo_tecnico || ''} ${p.familia_tecnica || ''} ${p.modelo_tecnico || ''} ${p.modelo || ''} ${productColor(p)} ${fabricColor(p)}`
        )
        return terms.every((t) => hay.includes(t))
      })

  }, [catalog, query])
  useEffect(() => { setQuery(selectedDisplay) }, [selectedDisplay])
  const variants = useMemo(() => {
    if (!selected) return []
    const commercialKey = isFinishedProduct(selected) ? commercialVariantKey(selected) : null
    if (commercialKey) return catalog.filter(p => active(p) && isFinishedProduct(p) && commercialVariantKey(p) === commercialKey)
    if (fabricDisplay(selected).fabric) {
      if (!(fabricColor(selected) || selected.produto_base?.trim())) return [selected]
      return catalog.filter(p => active(p) && fabricDisplay(p).fabric && fabricVariantKey(p) === fabricVariantKey(selected))
    }
    return selected.familia_tecnica ? catalog.filter(p => active(p) && p.familia_tecnica === selected.familia_tecnica) : [selected]
  }, [catalog, selected])
  const curtainVirtualMatches = useMemo(() => curtainSuggestions(catalog, query), [catalog, query])
  const rankedMatches = useMemo(() => {
    const q = normalizeSearch(query.trim())
    if (q.includes('CORTINA')) return []
    const collections = groupFabricCollections(matches.filter((p) => !isCurtainCatalogItem(p)))
    const byRepresentative = new Map(collections.map(group => [group.representative.id, group]))
    return rankProductSuggestions(collections.map(group => group.representative), query, isFinishedProduct)
      .slice(0, 12)
      .map(p => ({ product: p, collection: byRepresentative.get(p.id) }))
  }, [matches, query])

  const dropdownMatches = [
    ...rankedMatches.map(({ product: p, collection }) => ({
      key: collection?.key ?? String(p.id), product: p, collection,
      suggestion: undefined as CurtainSuggestion | undefined,
    })),
    ...curtainVirtualMatches.map(suggestion => ({ key: suggestion.key, product: undefined, collection: undefined, suggestion })),
  ]

  const colorOptions = useMemo(() => {
    const items = variants.filter((p) => !isCurtainCatalogItem(p) && (fabricDisplay(p).fabric ? fabricColor(p) : productColor(p)))
    const counts = new Map<string, number>()
    items.forEach(p => {
      const color = fabricDisplay(p).fabric ? fabricColor(p) : productColor(p)
      const key = normalizeSearch(color)
      counts.set(key, (counts.get(key) ?? 0) + 1)
    })
    return items.map(p => {
      const color = fabricDisplay(p).fabric ? fabricColor(p) : productColor(p)
      const duplicate = (counts.get(normalizeSearch(color)) ?? 0) > 1
      return { product: p, label: duplicate ? color + ' (' + (p.codigo_interno || p.codigo || 'ID ' + p.id) + ')' : color }
    })
  }, [variants])

  const fixedFamilyColors =
    selected?.familia_tecnica && !isCurtainCatalogItem(selected)
      ? FAMILY_COLOR_OPTIONS[selected.familia_tecnica] || []
      : []

  const confirmPriceReset = () => !allowManualPrice || !product.priceManual || window.confirm('Trocar o produto restaura o preço sugerido para este item. Deseja continuar?')
  const chooseCurtain = (suggestion: CurtainSuggestion) => {
    if (!confirmPriceReset()) return
    const curtain = applyCurtainSuggestion(isCurtain ? product.curtain ?? DEFAULT_CURTAIN : DEFAULT_CURTAIN, suggestion)
    setQuery('Cortina de tecido')
    onChange({
      ...product,
      productId: null, product: 'Cortina de tecido', code: '', family: '',
      groupTechnical: 'TECIDOS_CORTINA', modelTechnical: 'CORTINA', unit: 'M²',
      color: curtain.cor, curtain, price: 0, priceManual:false, suggestedPrice:undefined,
      romanaKind: undefined, romana: undefined, romanaTetoKind: undefined, romanaTeto: undefined,
      roloKind: undefined, rolo: undefined, doubleVisionKind: undefined, doubleVision: undefined,
      acao_acionamento: undefined, lado_comando: undefined, comprimento_bastao: undefined,
      comprimento_corrente_sem_fim: undefined, acionamento: undefined,
    })
  }

  const choose = (p: ApiProduct) => {
    if (!confirmPriceReset()) return
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
      color: fabricDisplay(p).fabric ? fabricColor(p) : productColor(p),
      price: rKind ? 0 : rlKind ? 0 : dvKind ? 0 : rtKind ? 0 : commercialPrice(p, commercialType),
      priceManual:false,
      suggestedPrice:rKind || rlKind || dvKind || rtKind ? undefined : commercialPrice(p,commercialType),
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
  const suggestedPrice = suggestedProductPrice(product,commercialType)

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
          <input className={commercialDisplayText(query, [product.code]) === query.toLocaleUpperCase('pt-BR') ? 'commercial-name' : undefined} value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ex.: rolo bk denver" autoComplete="off" />
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
                    <strong>{commercialDisplayText(match.suggestion?.label ?? fabricDisplay(match.product!).name, [match.product?.codigo_interno || '', match.product?.codigo || '', match.product?.codigo_barras || ''])}</strong>
                    {!match.suggestion && match.collection && match.collection.colors.filter(c => c.color).length > 1 && <small>{match.collection.colors.filter(c => c.color).length} cores cadastradas</small>}
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
          ) : colorOptions.length > 0 ? (
            <select value={colorOptions.some(option => option.product.id === product.productId) ? String(product.productId) : ''}
              onChange={(e) => {
                const selectedVariant = colorOptions.find(option => String(option.product.id) === e.target.value)?.product
                if (selectedVariant) choose(selectedVariant)
              }}>
              <option value="">Selecione a cor</option>
              {colorOptions.map(({ product: variant, label }) => (
                <option key={variant.id} value={String(variant.id)}>{label}</option>
              ))}
            </select>
          ) : fixedFamilyColors.length > 0 ? (
            <select value={product.color} onChange={(e) => handleColorChange(e.target.value)}>
              <option value="">Selecione a cor</option>
              {fixedFamilyColors.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          ) : (
            <select value="" disabled><option value="">Sem variação cadastrada</option></select>
          )}
        </label>
        <label className="field product-field-wide">
          <span>Detalhe</span>
          <input value={product.details} onChange={(e) => update('details', e.target.value)} placeholder="Ex.: Sala Ã‚Â· comando ÃƒÂ  direita" />
        </label>
        <label className="field">
          <span>Ambiente</span>
          <input maxLength={200} value={product.environment} onChange={(e) => update('environment', e.target.value)} placeholder="Ex.: Sala" />
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
          <span>Valor unitário *</span>
          <ZeroNumberInput min="0" step="0.01" aria-label={`Valor unitário de ${product.product || 'produto'}`} value={product.price} readOnly={!allowManualPrice && Boolean(product.romanaKind || product.romanaTetoKind || product.roloKind || product.doubleVisionKind || product.curtain)} onValueChange={value => allowManualPrice ? onChange(negotiateProductPrice(product,value)) : update('price',value)} />
          {allowManualPrice && <small>{product.priceManual ? 'Preço negociado neste orçamento.' : 'Preço sugerido.'} {suggestedPrice !== undefined && `Sugestão: ${formatCurrency(suggestedPrice)}`}</small>}
          {allowManualPrice && product.priceManual && <button type="button" className="secondary-button" disabled={suggestedPrice === undefined} onClick={() => onChange(restoreSuggestedProductPrice(product,commercialType))}>Restaurar preço sugerido</button>}
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
      <CurtainSimulation product={product} catalog={catalog} profile={commercialType} onResult={onCurtain} allowPackageConversion={allowPackageConversion} />
    </article>
  )
}
