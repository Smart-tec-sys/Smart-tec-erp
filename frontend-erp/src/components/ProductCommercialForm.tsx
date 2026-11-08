import { commercialDisplayText } from '../utils/commercialDisplay'
import { useEffect, useRef, useState } from 'react'
import {
    createProduct,
    getProductGroups,
    getProductTechnicalClassifications,
    getProductUnits,
    updateProductCommercial,
    type ProductCommercialUpdate,
    type ProductTechnicalClassifications,
} from '../services/api'
import { formatCurrency, type ApiProduct } from '../types/budget'

const textFields = [
    'grupo_produto', 'grupo_tecnico', 'familia_tecnica', 'modelo_tecnico',
    'unidade', 'unidade_venda', 'unidade_compra', 'unidade_controle',
    'nome_fornecedor', 'codigo_fornecedor', 'fornecedores',
    'cor', 'cor_componente', 'variacao_cor', 'situacao', 'status_comercial',
] as const
const labels: Record<typeof textFields[number], string> = {
    grupo_produto: 'Grupo do produto',
    grupo_tecnico: 'Grupo técnico',
    familia_tecnica: 'Família técnica',
    modelo_tecnico: 'Modelo técnico',
    unidade: 'Unidade',
    unidade_venda: 'Unidade de venda',
    unidade_compra: 'Unidade de compra',
    unidade_controle: 'Unidade de controle',
    nome_fornecedor: 'Fornecedor principal (texto)',
    codigo_fornecedor: 'Código no fornecedor',
    fornecedores: 'Fornecedores (texto)',
    cor: 'Cor',
    cor_componente: 'Cor do componente',
    variacao_cor: 'Variação de cor',
    situacao: 'Situação',
    status_comercial: 'Status comercial',
}
const optionsWithCurrent = (options: string[], current: string) => [...new Set([current, ...options].filter(Boolean))]
const moneyInput = (value: unknown) => String(value ?? '').replace('.', ',')
const decimalInput = (value: number) => String(Math.round((value + Number.EPSILON) * 100) / 100).replace('.', ',')

export function parseCommercialValue(raw: string): number {
    const value = raw.trim()
    if (!/^(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d+)?$/.test(value)) {
        throw new Error('Informe um valor válido, por exemplo 1.234,56, sem sinal negativo.')
    }
    const parsed = Number(value.replace(/\./g, '').replace(',', '.'))
    if (!Number.isFinite(parsed)) throw new Error('Valor fora do limite permitido.')
    return parsed
}

export function ProductCommercialForm({ product, catalog, onCancel, onSaved, onBusy }: {
    product?: ApiProduct; catalog: ApiProduct[]; onCancel: () => void;
    onSaved: (product: ApiProduct) => void; onBusy: (busy: boolean) => void
}) {
    const creating = !product
    const original: Partial<ApiProduct> = product ?? { nome: '', situacao: 'Ativo', status_comercial: 'Ativo', varia_cor: false }
    const [draft, setDraft] = useState(() => ({
        nome: original.nome ?? '', descricao: original.descricao ?? '',
        grupo_produto: original.grupo_produto ?? '', grupo_tecnico: original.grupo_tecnico ?? '',
        familia_tecnica: original.familia_tecnica ?? '', modelo_tecnico: original.modelo_tecnico ?? '',
        unidade: original.unidade ?? '', unidade_venda: original.unidade_venda ?? '',
        unidade_compra: original.unidade_compra ?? '', unidade_controle: original.unidade_controle ?? '',
        nome_fornecedor: original.nome_fornecedor ?? '', codigo_fornecedor: original.codigo_fornecedor ?? '',
        fornecedores: original.fornecedores ?? '',
        cor: original.cor ?? '', cor_componente: original.cor_componente ?? '', variacao_cor: original.variacao_cor ?? '',
        situacao: original.situacao ?? '', status_comercial: original.status_comercial ?? '', varia_cor: Boolean(original.varia_cor),
        valor_custo: moneyInput(original.valor_custo), margem_lucro: moneyInput(original.margem_lucro),
        valor_venda: moneyInput(original.valor_venda),
    }))
    const [groups, setGroups] = useState<string[]>([])
    const [units, setUnits] = useState<string[]>([])
    const [technicalClassifications, setTechnicalClassifications] =
        useState<ProductTechnicalClassifications>({
            grupo_tecnico: [], familia_tecnica: [], modelo_tecnico: [],
        })
    const [loading, setLoading] = useState(true)
    const [optionError, setOptionError] = useState('')
    const [error, setError] = useState('')
    const [saving, setSaving] = useState(false)
    const inFlight = useRef(false)
    const classificationOptions = (field: 'grupo_tecnico' | 'familia_tecnica' | 'modelo_tecnico') =>
        technicalClassifications[field]
    const catalogUnitOptions = (field: 'unidade' | 'unidade_compra' | 'unidade_controle') =>
        [...new Set(catalog.map(item => item[field]?.trim()).filter((value): value is string => Boolean(value)))]
            .sort((a, b) => a.localeCompare(b, 'pt-BR'))
    useEffect(() => {
        let cancelled = false
        Promise.all([
            getProductGroups(),
            getProductUnits(),
            getProductTechnicalClassifications(),
        ]).then(([g, u, technical]) => {
            if (cancelled) return
            setGroups(g)
            setUnits(u.length ? u : [...new Set(catalog.map(p => p.unidade_venda?.trim() || p.unidade?.trim() || '').filter(Boolean))].sort((a, b) => a.localeCompare(b, 'pt-BR')))
            setTechnicalClassifications(technical)
        }).catch(() => { if (!cancelled) setOptionError('Não foi possível carregar grupos, unidades e classificações técnicas. Reabra o formulário para tentar novamente.') })
            .finally(() => { if (!cancelled) setLoading(false) })
        return () => { cancelled = true }
    }, [catalog])

    const save = async () => {
        if (inFlight.current) return
        setError('')
        try {
            if (!draft.nome.trim()) throw new Error('O nome do produto é obrigatório.')
            if (creating && (!draft.grupo_produto.trim() || !draft.unidade_venda.trim() || !draft.valor_custo.trim())) {
                throw new Error('Nome, grupo, unidade de venda e valor de custo são obrigatórios.')
            }
            const payload: ProductCommercialUpdate = { nome: draft.nome.trim() }
            let changed = creating || payload.nome !== original.nome
            for (const field of textFields) {
                if (draft[field] !== (original[field] ?? '')) {
                    if (!creating || draft[field].trim()) payload[field] = draft[field].trim() || null
                    changed = true
                }
            }
            if (draft.descricao !== (original.descricao ?? '')) {
                payload.descricao = draft.descricao.trim() || null
                changed = true
            }
            if (draft.varia_cor !== Boolean(original.varia_cor)) { payload.varia_cor = draft.varia_cor; changed = true }
            for (const field of ['valor_custo', 'margem_lucro', 'valor_venda'] as const) {
                if (draft[field] !== moneyInput(original[field])) { payload[field] = parseCommercialValue(draft[field]); changed = true }
            }
            if (!changed) { onCancel(); return }
            inFlight.current = true
            setSaving(true)
            onBusy(true)
            const updated = product ? await updateProductCommercial(product.id, payload) : await createProduct({
                ...payload, grupo_produto: draft.grupo_produto.trim(), unidade_venda: draft.unidade_venda.trim(),
                valor_custo: parseCommercialValue(draft.valor_custo),
            })
            onSaved(updated)
        } catch (e) {
            const message = e instanceof Error ? e.message : String(e)
            setError(/409|unique|duplic/i.test(message)
                ? 'Já existe um cadastro com um identificador igual. Revise os dados; as alterações não foram salvas.'
                : /404/.test(message) ? 'Este produto não foi encontrado. Feche o modal e atualize a lista.'
                : /Failed to fetch|NetworkError/i.test(message) ? 'Não foi possível confirmar o salvamento. Verifique a conexão e consulte o produto antes de tentar novamente.' : message)
        } finally { inFlight.current = false; setSaving(false); onBusy(false) }
    }

    const recalculateSalePrice = () => {
        try {
            setError('')
            const finalCost = parseCommercialValue(draft.valor_custo)
                + Number(original.despesas_acessorias || 0)
                + Number(original.outras_despesas || 0)
            const margin = parseCommercialValue(draft.margem_lucro || '0')
            setDraft({ ...draft, valor_venda: decimalInput(finalCost * (1 + margin / 100)) })
        } catch (e) {
            setError(e instanceof Error ? e.message : String(e))
        }
    }
    return <form onSubmit={e => { e.preventDefault(); void save() }} aria-busy={saving}>
        <fieldset disabled={saving} style={{ border: 0, padding: 0, margin: 0 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
                <label className="modal-field">Nome<input className={commercialDisplayText(draft.nome, [original.codigo_interno || '', original.codigo || '', original.codigo_barras || '']) === draft.nome.toLocaleUpperCase('pt-BR') ? 'commercial-name' : undefined} autoFocus required value={draft.nome} onChange={e => setDraft({ ...draft, nome: e.target.value })} /></label>
                <label className="modal-field" style={{ gridColumn: '1 / -1' }}>Descrição
                    <textarea maxLength={5000} value={draft.descricao}
                        onChange={e => setDraft({ ...draft, descricao: e.target.value })} />
                </label>
                {textFields.map(field => <label className="modal-field" key={field}>{labels[field]}
                    {field === 'grupo_produto' || field === 'unidade_venda' ? <select
                        required={creating || field === 'unidade_venda'}
                        disabled={loading || Boolean(optionError)}
                        value={draft[field]}
                        onChange={e => setDraft({ ...draft, [field]: e.target.value })}>
                        <option value="">Não informado</option>{optionsWithCurrent(
                            field === 'grupo_produto' ? groups : units, draft[field],
                        ).map(value => <option key={value}>{value}</option>)}
                    </select>
                    : field === 'grupo_tecnico' || field === 'familia_tecnica' || field === 'modelo_tecnico'
                        ? <select disabled={loading || Boolean(optionError)} value={draft[field]} onChange={e => setDraft({ ...draft, [field]: e.target.value })}>
                            <option value="">Não informado</option>
                            {optionsWithCurrent(classificationOptions(field), draft[field]).map(value =>
                                <option key={value}>{value}</option>)}
                        </select>
                    : field === 'unidade' || field === 'unidade_compra' || field === 'unidade_controle'
                        ? <select value={draft[field]} onChange={e => setDraft({ ...draft, [field]: e.target.value })}>
                            <option value="">Não informado</option>
                            {optionsWithCurrent(catalogUnitOptions(field), draft[field]).map(value =>
                                <option key={value}>{value}</option>)}
                        </select>
                    : field === 'fornecedores'
                        ? <textarea maxLength={5000} value={draft[field]} onChange={e => setDraft({ ...draft, [field]: e.target.value })} />
                        : <input maxLength={field === 'situacao' ? 20 : 255} value={draft[field]}
                            onChange={e => setDraft({ ...draft, [field]: e.target.value })} />}
                </label>)}
                <label className="modal-field">Varia cor<select value={String(draft.varia_cor)} onChange={e => setDraft({ ...draft, varia_cor: e.target.value === 'true' })}><option value="true">Sim</option><option value="false">Não</option></select></label>
                <label className="modal-field">Valor de custo (R$)<input required={creating} inputMode="decimal" value={draft.valor_custo} onChange={e => setDraft({ ...draft, valor_custo: e.target.value })} placeholder="1.234,56" /></label>
                <label className="modal-field">Margem de lucro (%)<input inputMode="decimal" value={draft.margem_lucro} onChange={e => setDraft({ ...draft, margem_lucro: e.target.value })} placeholder="150,00" /></label>
                <label className="modal-field">Valor de venda (R$)<input inputMode="decimal" value={draft.valor_venda} onChange={e => setDraft({ ...draft, valor_venda: e.target.value })} placeholder="1.234,56" /></label>
                <div className="modal-field"><span>Recalcular preço</span><button type="button" className="secondary-button" onClick={recalculateSalePrice}>Usar custo final + margem</button></div>
                {product && <label className="modal-field">Custo final atual<input readOnly value={formatCurrency(Number(product.custo_final || 0))} /></label>}
            </div>
            <p>Ao salvar, o sistema recalcula o custo final: custo + despesas acessórias + outras despesas. O valor de venda manual é preservado; use “Usar custo final + margem” quando desejar recalculá-lo.</p>
            <p>Classificações técnicas usam a lista canônica da empresa. Os campos de fornecedor seguem o formato textual legado e não alteram equivalências técnicas.</p>
            {loading && <p role="status">Carregando grupos, unidades e classificações técnicas...</p>}
            {optionError && <p role="alert">{optionError}</p>}
            {error && <div className="modal-error" role="alert">{error}</div>}
            {creating && <p>Nome, grupo, unidade de venda e custo são obrigatórios. Os demais campos são opcionais.</p>}
            <div className="modal-actions"><button type="button" className="secondary-button" onClick={onCancel}>Cancelar</button><button className="primary-button" type="submit" disabled={loading || Boolean(optionError)}>{saving ? 'Salvando...' : creating ? 'Salvar produto' : 'Salvar alterações'}</button></div>
        </fieldset>
    </form>
}
