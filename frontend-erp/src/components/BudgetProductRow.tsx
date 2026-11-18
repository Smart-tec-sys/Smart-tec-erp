import { commercialDisplayText } from '../utils/commercialDisplay'
import { CurtainColorField } from './CurtainColorField'
import { DEFAULT_CURTAIN, curtainSuggestions, applyCurtainSuggestion, type CurtainSuggestion } from '../utils/curtainFabricCatalog'
import { ZeroNumberInput, zeroInputValue } from './ZeroNumberInput'
import { fabricDisplay } from '../utils/fabricDisplay'
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

// Cada cor continua com ID, referência e custo próprios; o agrupamento é apenas visual.
// NUNCA combinar registros de fornecedores diferentes.
type CatalogWithSupplier = ApiProduct & {
  nome_fornecedor?: string | null
  fornecedor_id?: number | null
  codigo_fornecedor?: string | null
  linha?: string | null
  colecao?: string | null
}

// Cores legadas escritas no nome: «MODELO (COR) 38MM» e «MODELO – COR».
// A bitola é mantida como variante técnica, nunca presumida equivalente.
const legacyVariant = (p: ApiProduct) => {
  const name = String(p.nome || '').trim()
  const explicitColor = productColor(p).trim()
  const diameter = /\s+(\d{2,3})\s*MM\s*$/i
  const normalizeBitola = (value: string) => value.replace(/\s+/g, '').toUpperCase()
  const paren = name.match(/^(.*?)\s*\(([^()]+)\)\s*(\d{2,3}\s*MM)?$/i)
  if (paren && !/\d/.test(paren[2]) && /^[\p{L}\s-]+$/u.test(paren[2])) {
    return { model: paren[1].trim(), color: explicitColor || paren[2].trim(),
      bitola: normalizeBitola(paren[3] || '') }
  }
  const suffix = name.match(/^(.*?)\s+[–—-]\s+(.+)$/)
  if (suffix && explicitColor && normalizeSearch(suffix[2]) === normalizeSearch(explicitColor)) {
    return { model: suffix[1].trim(), color: explicitColor, bitola: '' }
  }
  // Retira cor/bitola do nome de apresentação, mas mantém a referência real intacta.
  const bitolaMatch = name.match(diameter)
  const bitola = normalizeBitola(bitolaMatch?.[1] ? `${bitolaMatch[1]}MM` : '')
  let model = bitolaMatch ? name.slice(0, bitolaMatch.index).trim() : name
  if (explicitColor) {
    const normalizedName = normalizeSearch(model)
    const normalizedColor = normalizeSearch(explicitColor)
    if (normalizedName.endsWith(` ${normalizedColor}`)) {
      model = model.slice(0, model.length - explicitColor.length).trim()
    }
  }
  const trailingColor = model.match(/^(.*?)\s*\(([^()]+)\)$/)
  if (trailingColor && !/\d/.test(trailingColor[2])) {
    return { model: trailingColor[1].trim(), color: explicitColor || trailingColor[2].trim(), bitola }
  }
  return { model, color: explicitColor, bitola }
}

const catalogModelName = (p: ApiProduct) => {
  const base = String(p.produto_base || '').trim()
  const legacy = legacyVariant(p).model
  // "ROLÔ" genérico não substitui o nome completo da coleção.
  return base && normalizeSearch(base).split(/\s+/).length >= 3 ? base : legacy
}
const catalogColor = (p: ApiProduct) => legacyVariant(p).color
const catalogBitola = (p: ApiProduct) => legacyVariant(p).bitola

const isFabricCatalogItem = (p: ApiProduct) => {
  if (isFinishedProduct(p) || isCurtainCatalogItem(p)) return false
  const technical = normalizeSearch(
    [p.grupo_tecnico, p.grupo_produto, p.familia_tecnica].filter(Boolean).join(' ')
  )
  return Boolean(fabricDisplay(p).fabric) ||
    /(?:^|\\s)TECIDOS?(?:\\s|$)/.test(technical)
}

const displayModel = (p: ApiProduct) => {
  if (isFinishedProduct(p)) return catalogModelName(p)
  if (isFabricCatalogItem(p)) {
    const name = fabricDisplay(p).name || p.nome
    const candidate = catalogModelName({ ...p, nome: name })
    return candidate || name
  }
  return fabricDisplay(p).name
}

const catalogGroupKey = (p: ApiProduct) => {
  if (!isFinishedProduct(p) && !isFabricCatalogItem(p)) return `id:${p.id}`
  const extra = p as CatalogWithSupplier
  // Código de fornecedor pode ser SKU individual; não serve como identidade do fornecedor.
  const supplier = extra.fornecedor_id != null
    ? `id:${extra.fornecedor_id}`
    : extra.nome_fornecedor?.trim()
      ? `nome:${normalizeSearch(extra.nome_fornecedor)}`
      : 'fornecedor:nao-identificado'
  const model = normalizeSearch(displayModel(p))
  const collection = normalizeSearch(String(extra.colecao || extra.linha || '').trim())
  // Evita dividir a mesma coleção quando a informação já está no nome principal.
  const distinctCollection = collection && !model.includes(collection) ? collection : ''
  const kind = isFinishedProduct(p) ? 'ACABADO' : 'TECIDO'
  return `${kind}|${supplier}|${model}|${distinctCollection}`
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

const isFinishedProduct = (p: ApiProduct) => {
  if (romanaKind(p) || romanaTetoKind(p) || roloKind(p) || doubleVisionKind(p)) return true
  const classification = normalizeSearch(
    [p.modelo_tecnico, p.familia_tecnica, p.grupo_tecnico, p.grupo_produto].filter(Boolean).join(' ')
  )
  return /(?:^|\s)(?:PAINEL|SHANGRILA|SHANGRILA|SHANGRI LA)(?:$|\s)/.test(classification)
}

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
    : selected ? displayModel(selected) : fabricDisplay({ id: product.productId ?? 0, nome: product.product }).name
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
  const variants = useMemo(() => {
    if (!selected) return []
    if (isFinishedProduct(selected) || isFabricCatalogItem(selected)) {
      const key = catalogGroupKey(selected)
      return catalog.filter(p => active(p) && catalogGroupKey(p) === key)
    }
    return [selected]
  }, [catalog, selected])
  const curtainVirtualMatches = useMemo(() => curtainSuggestions(catalog, query), [catalog, query])
  const rankedMatches = useMemo(() => {
    const q = normalizeSearch(query.trim())
    if (q.includes('CORTINA')) return []
    const ranked = rankProductSuggestions(matches.filter((p) => !isCurtainCatalogItem(p)), query, isFinishedProduct)
    const seen = new Set<string>()
    return ranked.filter(p => {
      const key = catalogGroupKey(p)
      if (seen.has(key)) return false
      seen.add(key)
      return true
    }).slice(0, 12)
  }, [matches, query])

  // Both sources reach exactly the same rendered dropdown array.
  const dropdownMatches = [
    ...rankedMatches.map(p => ({ key: String(p.id), product: p, suggestion: undefined as CurtainSuggestion | undefined })),
    ...curtainVirtualMatches.map(suggestion => ({ key: suggestion.key, product: undefined, suggestion })),
  ]

  const colors = useMemo(() => {
    const grouped = new Map<string, ApiProduct[]>()
    variants.filter((p) => !isCurtainCatalogItem(p)).forEach((p) => {
      const c = catalogColor(p) || productColor(p)
      if (c) grouped.set(c, [...(grouped.get(c) || []), p])
    })
    return [...grouped.entries()]
  }, [variants])

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
    setQuery(displayModel(p))
    onChange({
      ...product,
      productId: p.id,
      product: p.nome,
      code: p.codigo_interno || p.codigo || '',
      family: p.familia_tecnica || '',
      groupTechnical: p.grupo_tecnico || '',
      modelTechnical: p.modelo_tecnico || '',
      unit: p.unidade_venda || p.unidade || '',
      color: isFinishedProduct(p) ? catalogColor(p) : productColor(p),
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
                    <strong>{commercialDisplayText(match.suggestion?.label ?? displayModel(match.product!), [match.product?.codigo_interno || '', match.product?.codigo || '', match.product?.codigo_barras || ''])}</strong>
                    {!match.suggestion && match.product && !isFabricCatalogItem(match.product) && fabricDisplay(match.product).width && <small>Largura de fornecimento: {fabricDisplay(match.product).width}</small>}
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
          ) : (
            <select value={selected && colors.some(([, items]) => items.some(p => p.id === selected.id)) ? String(selected.id) : ''}
              disabled={!colors.length}
              onChange={(e) => {
                const variant = variants.find(p => p.id === Number(e.target.value))
                if (variant) choose(variant)
              }}>
              <option value="">Selecione a cor</option>
              {colors.flatMap(([c, items]) => items.map(p => (
                <option key={p.id} value={p.id}>
                  {items.length === 1 ? c :
                    `${c} · ${[catalogBitola(p), fabricDisplay(p).width ? `Largura ${fabricDisplay(p).width}` : '', p.codigo_interno || p.codigo || `ID ${p.id}`].filter(Boolean).join(' · ')}`}
                </option>
              )))}
            </select>
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
