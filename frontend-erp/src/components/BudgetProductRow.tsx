import { commercialDisplayText } from '../utils/commercialDisplay'
import { FloatingProductSuggestions } from './FloatingProductSuggestions'
import { CurtainColorField } from './CurtainColorField'
import { DEFAULT_CURTAIN, curtainSuggestions, applyCurtainSuggestion, type CurtainSuggestion } from '../utils/curtainFabricCatalog'
import { ZeroNumberInput, zeroInputValue } from './ZeroNumberInput'
import { fabricDisplay } from '../utils/fabricDisplay'
import { rankProductSuggestions } from '../utils/productSuggestionRank'
import { selectZeroOnFocus } from '../utils/selectZeroOnFocus'
import { Minus, Plus, Trash2, PackagePlus } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { ApiProduct, BudgetProduct, CommercialType } from '../types/budget'
import { commercialPrice, formatCurrency, normalizeSearch, parseDecimal, productColor, productLineSubtotal, negotiateProductPrice, restoreSuggestedProductPrice, suggestedProductPrice } from '../types/budget'
const CREATE_PRODUCT_VALUE = '__CREATE_PRODUCT__'
import { RomanaSimulation } from './RomanaSimulation'
import { RomanaTetoSimulation } from './RomanaTetoSimulation'
import { RoloSimulation } from './RoloSimulation'
import { RoloMotorSelector } from './RoloMotorSelector'
import { MotorHelp } from './MotorHelp'
import { DoubleVisionSimulation } from './DoubleVisionSimulation'
import { CurtainSimulation } from './CurtainSimulation'
import type { CurtainState } from '../types/budget'
import { romanaKind, type RomanaState } from '../types/romana'
import { romanaTetoKind, type RomanaTetoState } from '../types/romana_teto'
import { roloKey, roloKind, normalizeRoloDrive, type RoloState } from '../types/rolo'
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

const isBkCatalogItem = (p: ApiProduct) => /\bBK\b/.test(normalizeSearch(p.nome || ''))
const normalizeBkModel = (value: string) => normalizeSearch(value)
  .replace(/\bBK\s*\.\s*/g, 'BK ').replace(/\bBRISCK\b/g, 'BRISK')
  .replace(/\s+/g, ' ').trim()

// Cores legadas escritas no nome: «MODELO (COR) 38MM» e «MODELO – COR».
// A bitola é mantida como variante técnica, nunca presumida equivalente.
const legacyVariant = (p: ApiProduct) => {
  const name = String(p.nome || '').trim()
  const explicitColor = productColor(p).trim()
  const diameter = /\s+(\d{2,3})\s*MM\s*$/i
  const normalizeBitola = (value: string) => value.replace(/\s+/g, '').toUpperCase()
  const fortalezaColor = name.match(/^(.*?)\s*\((WHITE|BEGE)\s*\/\s*2[,.]50\)$/i)
  if (
    normalizeSearch(p.familia_tecnica || '').replaceAll('_', ' ') === 'ROLO FORTALEZA 2 50M'
    && fortalezaColor
  ) {
    return { model: fortalezaColor[1].trim(), color: fortalezaColor[2].toUpperCase(), bitola: '' }
  }
  // BK: cor e bitola podem estar em qualquer uma das duas ordens no legado.
  if (isBkCatalogItem(p)) {
    const bitola = normalizeBitola(name.match(/\b\d{2,3}\s*MM\b/i)?.[0] || '')
    let model = name.replace(/\s+\d{2,3}\s*MM\b/i, '').trim()
    const paren = model.match(/^(.*?)\s*\(([^()]+)\)$/)
    if (paren && (/^[\p{L}\s-]+$/u.test(paren[2]) || (explicitColor && normalizeSearch(paren[2]) === normalizeSearch(explicitColor)))) {
      return { model: paren[1].trim(), color: explicitColor || paren[2].trim().toUpperCase(), bitola }
    }
    if (explicitColor && normalizeSearch(model).endsWith(` ${normalizeSearch(explicitColor)}`)) {
      model = model.slice(0, -explicitColor.length).replace(/\s+[–—-]\s*$/, '').trim()
      return { model, color: explicitColor, bitola }
    }
    const suffix = model.match(/^(.*?)\s+(?:[–—-]\s*)?(OFF WHITE|LIGHT GREY|LIGTH GREY|AZUL ROYAL|AM[ÊE]NDOA|ALPINO|BEGE|BRANC[OA]|CINZA|CREME|MARROM|IVORY|GELO|PRET[OA]|WHITE|BLACK|MARFIM|AREIA|PEACH|NAVY|GREY)$/i)
    return { model: suffix ? suffix[1].trim() : model, color: explicitColor || suffix?.[2].toUpperCase() || '', bitola }
  }
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
  return base && normalizeSearch(base).split(/\s+/).length >= 3
    ? isBkCatalogItem(p) ? legacyVariant({ ...p, nome: base }).model : base
    : legacy
}
const catalogColor = (p: ApiProduct) => legacyVariant(p).color
const importedScreen3Colors = ['BEGE', 'BRANCO', 'CINZA', 'PRETO'] as const
const isImportedScreen3 = (p: ApiProduct) =>
  /SCREEN\s*3\s*%/.test(normalizeSearch(p.nome || '')) &&
  /IMPORTAD/.test(normalizeSearch(p.nome || '')) &&
  !/STANDARD|STANDART/.test(normalizeSearch(p.nome || ''))
const isStandardScreen3 = (p: ApiProduct) =>
  /SCREEN\s*3\s*%/.test(normalizeSearch(p.nome || '')) &&
  /STANDARD|STANDART/.test(normalizeSearch(p.nome || ''))
const isStandardLegacyVariant = (p: ApiProduct) => p.id === 523
const isStandardBase = (p: ApiProduct) => p.id === 503
const standardScreen3Colors = ['BRANCO', 'CINZA'] as const
const normalizedRoloLabel = (p: ApiProduct, label: string) =>
  isStandardBase(p) ? 'ROLÔ SCREEN 3% STANDARD' : label
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
  if (isFinishedProduct(p)) {
    if (/\bSCREEN\b/.test(normalizeSearch(p.nome || ''))) return `ROL\u00d4 ${screenCollectionLabel(p).toUpperCase()}`
    const model = normalizedRoloLabel(p, catalogModelName(p))
    const bitola = catalogBitola(p) || legacyVariant({ ...p, nome: p.produto_base || '' }).bitola
    return isBkCatalogItem(p) && bitola ? `${model} ${bitola}` : model
  }
  if (isFabricCatalogItem(p)) {
    const name = fabricDisplay(p).name || p.nome
    const candidate = catalogModelName({ ...p, nome: name })
    return candidate || name
  }
  return fabricDisplay(p).name
}

const screenCollectionLabel = (p: ApiProduct) => {
  const name = normalizeSearch(p.nome || '')
  const opening = name.match(/\b(\d+)\s*%/)
  const collection = opening ? `Screen ${opening[1]}%` : 'Screen'
  const variant = /\bONE\b/.test(name) ? ' ONE'
    : /\bECO\b/.test(name) ? ' ECO'
    : /STANDARD|STANDART/.test(name) ? ' Standard'
    : /IMPORTAD/.test(name) ? ' Importado'
    : ''
  return `${collection}${variant}`
}

const catalogGroupKey = (p: ApiProduct) => {
  if (isFinishedProduct(p) && /\bSCREEN\b/.test(normalizeSearch(p.nome || ''))) {
    return `ACABADO|SCREEN|${screenCollectionLabel(p)}`
  }
  if (!isFinishedProduct(p) && !isFabricCatalogItem(p)) return `id:${p.id}`
  const extra = p as CatalogWithSupplier
  // Código de fornecedor pode ser SKU individual; não serve como identidade do fornecedor.
  const supplier = extra.fornecedor_id != null
    ? `id:${extra.fornecedor_id}`
    : extra.nome_fornecedor?.trim()
      ? `nome:${normalizeSearch(extra.nome_fornecedor)}`
      : 'fornecedor:nao-identificado'
  const bk = isBkCatalogItem(p)
  const modelOriginal = normalizeSearch(bk ? catalogModelName(p) : displayModel(p))
  const model = bk ? normalizeBkModel(modelOriginal) : modelOriginal
  const collection = (bk ? normalizeBkModel : normalizeSearch)(String(extra.colecao || extra.linha || '').trim())
  // Evita dividir a mesma coleção quando a informação já está no nome principal.
  const distinctCollection = collection && !model.includes(collection) ? collection : ''
  const kind = isFinishedProduct(p) ? 'ACABADO' : 'TECIDO'
  const key = `${kind}|${supplier}|${model}|${distinctCollection}`
  return bk ? `${key}|${catalogBitola(p) || legacyVariant({ ...p, nome: p.produto_base || '' }).bitola}|${roloKind(p) || ''}` : key
}

// Bases consolidadas perderam as variantes ativas; estas são as cores comerciais
// já confirmadas dessas famílias, não todas as cores dos tecidos de mesmo nome.
const consolidatedBkColors: Record<string, readonly string[]> = {
  'ROLO BK NAPOLES': ['BEGE', 'BRANCO', 'CINZA', 'CREME'],
  'ROLO BK DENVER': ['BEGE', 'BRANCO', 'CINZA'],
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
  compactMotorHelp?: boolean
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
  compactMotorHelp = false,
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
    : selected ? commercialDisplayText(selected.nome, [selected.codigo_interno || '', selected.codigo || '', selected.codigo_barras || '']) : fabricDisplay({ id: product.productId ?? 0, nome: product.product }).name
  const [query, setQuery] = useState(selectedDisplay)
  const update = <K extends keyof BudgetProduct>(key: K, value: BudgetProduct[K]) => onChange({ ...product, [key]: value })
  const matches = useMemo(() => {
    const terms = normalizeSearch(query).split(/\s+/).filter(Boolean)
    if (!terms.length) return []
    return catalog
      .filter(active)
      .filter(p => p.rolo_liberado_comercial !== false)
      .filter((p) => {
        const buscaRolo = /\bROLO\b/.test(normalizeSearch(query))
        if (!buscaRolo) return true
        return Boolean(roloKind(p)) && !isFabricCatalogItem(p)
      })
      .filter((p) => !(isStandardLegacyVariant(p) && catalog.some(item => isStandardBase(item) && active(item))))
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
    const screen84 = ranked.find(p => p.id === 84 && isImportedScreen3(p))
    if (screen84) {
      const screenKey = catalogGroupKey(screen84)
      for (let i = ranked.length - 1; i >= 0; i--) {
        if (ranked[i].id === 7 && catalogGroupKey(ranked[i]) === screenKey) ranked.splice(i, 1)
      }
    }
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

  const consolidatedColorOptions = selected && isBkCatalogItem(selected) && roloKind(selected) &&
    selected.varia_cor && !catalogColor(selected) && !colors.length
    ? consolidatedBkColors[normalizeBkModel((selected.familia_tecnica || '').replace(/_/g, ' '))] || []
    : []

  // Cores da coleção importada: não trocar o produto acabado por um registro de tecido.
  // A receita técnica continua responsável por resolver a referência e custo do tecido.
  const linkedRoloColors = selected?.rolo_cores_disponiveis || []
  const importedFinishedScreen3 = Boolean(selected && isFinishedProduct(selected) && isImportedScreen3(selected))
  const standardFinishedScreen3 = Boolean(selected && isStandardBase(selected) && isFinishedProduct(selected) && isStandardScreen3(selected))
  const importedColorOptions = useMemo(() => {
    if (!importedFinishedScreen3) return [] as string[]
    const values = new Set<string>()
    for (const item of catalog) {
      if (!active(item) || isFinishedProduct(item) || !isImportedScreen3(item)) continue
      const c = normalizeSearch(catalogColor(item) || productColor(item))
      if (importedScreen3Colors.some(color => normalizeSearch(color) === c)) values.add(c)
    }
    return importedScreen3Colors.filter(c => values.has(normalizeSearch(c)))
  }, [catalog, importedFinishedScreen3])
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
      roloKind: undefined, rolo: undefined, motorProdutoId: undefined, kitProdutoId: undefined, doubleVisionKind: undefined, doubleVision: undefined,
      acessorioRolo: false,
      acao_acionamento: undefined, lado_comando: undefined, comprimento_bastao: undefined,
      comprimento_corrente_sem_fim: undefined, acionamento: undefined,
    })
  }

  const choose = (p: ApiProduct, preserveRoloDrive = false) => {
    if (!confirmPriceReset()) return
    const rKind = romanaKind(p)
    const rtKind = romanaTetoKind(p)
    const rlKind = roloKind(p)
    const dvKind = doubleVisionKind(p)
    setQuery(commercialDisplayText(p.nome, [p.codigo_interno || '', p.codigo || '', p.codigo_barras || '']))
    const color = p.id === product.productId && product.color
      ? product.color
      : isFinishedProduct(p) ? catalogColor(p) : productColor(p)
    onChange({
      ...product,
      productId: p.id,
      product: p.nome,
      code: p.codigo_interno || p.codigo || '',
      family: p.familia_tecnica || '',
      groupTechnical: p.grupo_tecnico || '',
      modelTechnical: p.modelo_tecnico || '',
      unit: p.unidade_venda || p.unidade || '',
      color,
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
      motorProdutoId: preserveRoloDrive && p.id === product.productId ? product.motorProdutoId : undefined,
      kitProdutoId: preserveRoloDrive && p.id === product.productId ? product.kitProdutoId : undefined,
      acessorioRolo: false,
      doubleVisionKind: dvKind,
      doubleVision: undefined,
      acionamento: normalizeRoloDrive(preserveRoloDrive && rlKind && rlKind === product.roloKind
        ? product.acionamento ?? (rlKind === 'MOTORIZADA' ? 'motorizado' : 'manual')
        : rlKind === 'MOTORIZADA' ? 'motorizado' : 'manual'),
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
  const needsMeasures = Boolean(isCurtain || product.romanaKind || product.romanaTetoKind || product.roloKind || product.doubleVisionKind)
  const widthInvalid = compactMotorHelp && needsMeasures && (parseDecimal(product.width) < 0 || (validationAttempted && parseDecimal(product.width) <= 0))
  const heightInvalid = compactMotorHelp && needsMeasures && (parseDecimal(product.height) < 0 || (validationAttempted && parseDecimal(product.height) <= 0))
  const measureHelpId = `product-measures-${product.id}`

  const subtotal = productLineSubtotal(product, commercialType)
  const suggestedPrice = suggestedProductPrice(product,commercialType)

  const measureFields = <>
        <label className={`field product-field-measure${widthInvalid ? ' field-invalid' : ''}`}>
          <span>Largura</span>
          <input inputMode="decimal" placeholder="0,00" aria-invalid={widthInvalid || undefined} aria-describedby={compactMotorHelp && (product.roloKind || widthInvalid || heightInvalid) ? measureHelpId : undefined} value={zeroInputValue(product.width)} onChange={(e) => update('width', e.target.value)} />
        </label>
        <label className={`field product-field-measure${heightInvalid ? ' field-invalid' : ''}`}>
          <span>Altura</span>
          <input inputMode="decimal" placeholder="0,00" aria-invalid={heightInvalid || undefined} aria-describedby={compactMotorHelp && (product.roloKind || widthInvalid || heightInvalid) ? measureHelpId : undefined} value={zeroInputValue(product.height)} onChange={(e) => update('height', e.target.value)} />
        </label>
  </>

  return (
    <article className={`budget-product-row${product.acessorioRolo ? " product-accessory-row" : ""}`} onFocusCapture={selectZeroOnFocus}>
      <div className="product-row-head">
        <span className="product-row-index">{String(product.id).padStart(2, '0')}</span>
        <strong>{product.acessorioRolo ? "Acessorio - UN" : "Produto"}</strong>
        <button type="button" className="row-remove" aria-label={`Remover ${product.product}`} onClick={onRemove}>
          <Trash2 size={15} />
        </button>
      </div>
      {product.historico && !product.recalcular && <div>
        <span>Item salvo: preço, desconto e subtotal preservados.</span>
        <button type="button" className="secondary-button" onClick={() => {
          const technical = product.romanaKind || product.romanaTetoKind || product.roloKind || product.doubleVisionKind || product.curtain
          const price = selected && !technical ? commercialPrice(selected, commercialType) : undefined
          onChange({ ...product, recalcular:true, priceManual:false,
            ...(price === undefined ? {} : {price, suggestedPrice:price}) })
        }}>Recalcular este item</button>
      </div>}
      <fieldset disabled={Boolean(product.historico && !product.recalcular)} style={{ border:0, padding:0, margin:0, minWidth:0 }}>
      <div className="product-fields" role="region" aria-label={`Campos de ${product.product || 'produto'}`} tabIndex={0}>
        <label className="field product-field-wide product-search-box product-field-name">
          <span>Produto</span>
          <input className={commercialDisplayText(query, [product.code]) === query.toLocaleUpperCase('pt-BR') ? 'commercial-name' : undefined} value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ex.: rolo bk denver" autoComplete="off" />
          {query !== selectedDisplay && (
            <FloatingProductSuggestions enabled={compactMotorHelp} onClose={() => setQuery(selectedDisplay)}>
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
                    {!match.suggestion && match.product && isFinishedProduct(match.product) &&
                      /\bSCREEN\b/.test(normalizeSearch(match.product.nome || '')) &&
                      <small>{screenCollectionLabel(match.product)}</small>}
                    {!match.suggestion && match.product && !isFabricCatalogItem(match.product) && fabricDisplay(match.product).width && <small>Largura de fornecimento: {fabricDisplay(match.product).width}</small>}
                  </button>
                ))
              )}
            </div>
            </FloatingProductSuggestions>
          )}
        </label>
        <label className="field product-field-color">
          <span>Cor</span>
          {isCurtain ? (
            <CurtainColorField product={product} catalog={catalog} onChange={onChange} />
          ) : importedFinishedScreen3 ? (
            <select value={importedColorOptions.find(c => normalizeSearch(c) === normalizeSearch(product.color || '')) || ''}
              disabled={!importedColorOptions.length}
              onChange={e => onChange({ ...product, color: e.target.value, rolo: undefined })}>
              <option value="">Selecione a cor</option>
              {importedColorOptions.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          ) : linkedRoloColors.length ? (
              <select
                value={linkedRoloColors.find(c => normalizeSearch(c) === normalizeSearch(product.color || '')) || ''}
                onChange={e => onChange({ ...product, color: e.target.value, rolo: undefined })}
              >
                <option value="">Selecione a cor</option>
                {linkedRoloColors.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            ) : standardFinishedScreen3 ? (
            <select value={standardScreen3Colors.find(c => normalizeSearch(c) === normalizeSearch(product.color || '')) || ''}
              onChange={e => onChange({ ...product, color: e.target.value, rolo: undefined })}>
              <option value="">Selecione a cor</option>
              {standardScreen3Colors.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          ) : consolidatedColorOptions.length ? (
            <select value={consolidatedColorOptions.find(c => normalizeSearch(c) === normalizeSearch(product.color || '')) || ''}
              onChange={e => onChange({ ...product, color: e.target.value, rolo: undefined })}>
              <option value="">Selecione a cor</option>
              {consolidatedColorOptions.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          ) : (
            <select value={selected && colors.some(([, items]) => items.some(p => p.id === selected.id)) ? String(selected.id) : ''}
              disabled={!colors.length}
              onChange={(e) => {
                const variant = variants.find(p => p.id === Number(e.target.value))
                if (variant) choose(variant, true)
              }}>
              <option value="">Selecione a cor</option>
              {colors.flatMap(([c, items]) => items.map(p => (
                <option key={p.id} value={p.id}>
                  {c}</option>
              )))}
            </select>
          )}
        </label>
        {product.roloKind && (
          <div className="field product-field-drive">
          <label className="field">
            <span>Acionamento</span>
            <select aria-label={`Motor? de ${product.product || 'Rolô'}`}
              value={normalizeRoloDrive(product.acionamento ?? (product.roloKind === 'MOTORIZADA' ? 'motorizado' : 'manual'))}
              onChange={e => onChange({ ...product, acionamento: normalizeRoloDrive(e.target.value), motorProdutoId: undefined, kitProdutoId: undefined, rolo: undefined, suggestedPrice: undefined })}>
              <option value="manual">Manual</option>
              <option value="motorizado">Motorizado</option>
            </select>
          </label>
          {compactMotorHelp && normalizeRoloDrive(product.acionamento ?? (product.roloKind === 'MOTORIZADA' ? 'motorizado' : 'manual')) === 'motorizado'
            && product.rolo?.key === roloKey(product, commercialType) && product.rolo.error && (
              <MotorHelp label="Detalhes do bloqueio técnico" message={`Não foi possível simular. Revise as medidas ou a conexão. Dados preservados; salvamento bloqueado. ${product.rolo.error}`} />
            )}
          </div>
        )}
        {(!product.historico || product.recalcular) && product.roloKind
          && normalizeRoloDrive(product.acionamento ?? (product.roloKind === 'MOTORIZADA' ? 'motorizado' : 'manual')) === 'motorizado'
          && <div className="product-field-motor">
          <RoloMotorSelector product={product} catalog={catalog} onChange={onChange} />
        </div>}
        <label className="field product-field-wide product-field-details">
          <span>Detalhe</span>
          <input value={product.details} onChange={(e) => update('details', e.target.value)} placeholder="Ex.: Sala Ã‚Â· comando ÃƒÂ  direita" />
        </label>
        <label className="field product-field-environment">
          <span>Ambiente</span>
          <input maxLength={200} value={product.environment} onChange={(e) => update('environment', e.target.value)} placeholder="Ex.: Sala" />
        </label>
        <label className={`field product-field-quantity${validationAttempted && quantityInvalid ? ' field-invalid' : ''}`}>
          <span>{product.acessorioRolo ? "Quantidade (UN)" : "Quant. *"}</span>
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
        <label className={`field product-field-profile${validationAttempted && profileInvalid ? ' field-invalid' : ''}`}>
          <span>Perfil *</span>
          <input value={commercialType} readOnly />
        </label>
        {compactMotorHelp ? <div className="product-field-measures">
          {measureFields}
          {(product.roloKind || widthInvalid || heightInvalid) && <div className="product-measures-help" id={measureHelpId}>
          {(widthInvalid || heightInvalid) && <small role="alert" className="product-measure-error">{widthInvalid && heightInvalid ? 'Informe largura e altura maiores que zero.' : widthInvalid ? 'Informe largura maior que zero.' : 'Informe altura maior que zero.'}</small>}

        </div>}
        </div> : measureFields}
        <label className={`field product-field-price${validationAttempted && valueInvalid ? ' field-invalid' : ''}`}>
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
      </fieldset>
      {!product.acessorioRolo && (!product.historico || product.recalcular) && <>
      <details className="product-technical-details">
        <summary>Simulação técnica</summary>
      <RomanaSimulation product={product} profile={commercialType} onResult={onRomana} />
      <RomanaTetoSimulation product={product} profile={commercialType} onResult={onRomanaTeto} onChange={onChange} />
      <RoloSimulation product={product} profile={commercialType} onResult={onRolo} compactMotorHelp={compactMotorHelp} />
      <DoubleVisionSimulation product={product} profile={commercialType} onResult={onDoubleVision} />
      <CurtainSimulation product={product} catalog={catalog} profile={commercialType} onResult={onCurtain} allowPackageConversion={allowPackageConversion} />
      </details>
      </>}
    </article>
  )
}
