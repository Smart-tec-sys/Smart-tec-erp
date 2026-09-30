import { Search, Filter, ChevronLeft, ChevronRight, X, Package, Eye, ChevronDown, ChevronUp } from 'lucide-react'
import { useEffect, useState, useMemo } from 'react'
import { getAllProducts } from '../services/api'
import { ProductCommercialForm } from '../components/ProductCommercialForm'
import { productSortLabels, sortProducts, type ProductSort } from './productSorting'
import './productsLayout.css'
import type { ApiProduct } from '../types/budget'
import { formatCurrency, productColor, productCost } from '../types/budget'
import { emptyProductFilters, indexProduct, normalizeProductSearch, productFilterKeys, productFilterLabels, productFilterOptions } from './productFilters'

export function ProductsPage() {
    const [products, setProducts] = useState<ApiProduct[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [search, setSearch] = useState('')
    const [filter, setFilter] = useState<'all' | 'ativos' | 'inativos'>('all')
    const [criteria, setCriteria] = useState({ ...emptyProductFilters })
    const [sortOrder, setSortOrder] = useState<ProductSort>('newest')
    const [page, setPage] = useState(1)
    const [selectedProduct, setSelectedProduct] = useState<ApiProduct | null>(null)
    const [detailOpen, setDetailOpen] = useState(false)
    const [editing, setEditing] = useState(false)
    const [savingProduct, setSavingProduct] = useState(false)
    const [savedMessage, setSavedMessage] = useState('')
    const [creating, setCreating] = useState(false)
    const closeCreate = () => { if (!savingProduct) setCreating(false) }

    const PAGE_SIZE = 50

    useEffect(() => {
        let cancelled = false
        setLoading(true)
        setError('')
        getAllProducts()
            .then((data) => {
                if (!cancelled) {
                    setProducts(data)
                    setPage(1)
                }
            })
            .catch((e) => {
                if (!cancelled) setError(e instanceof Error ? e.message : String(e))
            })
            .finally(() => {
                if (!cancelled) setLoading(false)
            })
        return () => { cancelled = true }
    }, [])

    const indexedProducts = useMemo(() => products.map(indexProduct), [products])
    const filterOptions = useMemo(() => productFilterOptions(products), [products])
    const filteredProducts = useMemo(() => {
        const terms = normalizeProductSearch(search).split(' ').filter(Boolean)
        return indexedProducts.filter(({ product, text, values }) => {
            const inactive = (product.situacao || '').toLowerCase() === 'inativo'
            return (filter === 'all' || (filter === 'inativos' ? inactive : !inactive))
                && terms.every(term => text.includes(term))
                && productFilterKeys.every(key => !criteria[key] || values[key].includes(criteria[key]))
        }).map(item => item.product)
    }, [indexedProducts, search, filter, criteria])
    const hasFilters = Boolean(search.trim()) || filter !== 'all' || Object.values(criteria).some(Boolean)
    const clearFilters = () => { setSearch(''); setFilter('all'); setCriteria({ ...emptyProductFilters }); setPage(1) }

    const totalPages = Math.max(1, Math.ceil(filteredProducts.length / PAGE_SIZE))
    const sortedProducts = useMemo(() => sortProducts(filteredProducts, sortOrder), [filteredProducts, sortOrder])
    useEffect(() => { setPage(current => Math.min(current, totalPages)) }, [totalPages])
    const currentPageProducts = useMemo(() => {
        const start = (page - 1) * PAGE_SIZE
        return sortedProducts.slice(start, start + PAGE_SIZE)
    }, [sortedProducts, page])

    const openDetail = (product: ApiProduct) => {
        setEditing(false)
        setSavedMessage('')
        setSelectedProduct(product)
        setDetailOpen(true)
    }

    const closeDetail = () => {
        if (savingProduct) return
        setEditing(false)
        setDetailOpen(false)
        setSelectedProduct(null)
    }

    const statusLabel = (situacao: string | null | undefined) => {
        const s = (situacao || '').toLowerCase()
        return s === 'inativo' ? 'Inativo' : 'Ativo'
    }

    const statusTone = (situacao: string | null | undefined) => {
        const s = (situacao || '').toLowerCase()
        return s === 'inativo' ? 'cancelled' : 'approved'
    }

    return (
        <div className="products-page">
            <section className="budget-page-heading page-heading">
                <div>
                    <p className="eyebrow">CADASTROS</p>
                    <h1>Produtos</h1>
                    <p className="heading-subtitle">Dados carregados diretamente do FastAPI.</p>
                </div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <button className="primary-button" disabled={loading || Boolean(error)} onClick={() => setCreating(true)}>Novo produto</button>
                    <span className="budget-number">
                        <span>Total carregado</span>
                        <strong>{products.length}</strong>
                    </span>
                </div>
            </section>

            <section className="budget-kpi-grid">
                <div className="budget-kpi dark">
                    <div className="budget-kpi-icon"><Package size={18} /></div>
                    <div>
                        <span>Total</span>
                        <strong>{products.length}</strong>
                        <small>API real</small>
                    </div>
                </div>
                <div className="budget-kpi green">
                    <div className="budget-kpi-icon"><CheckCircle2 size={18} /></div>
                    <div>
                        <span>Ativos</span>
                        <strong>{products.filter(p => (p.situacao || '').toLowerCase() !== 'inativo').length}</strong>
                        <small>Situação ativa</small>
                    </div>
                </div>
                <div className="budget-kpi gold">
                    <div className="budget-kpi-icon"><AlertCircle size={18} /></div>
                    <div>
                        <span>Inativos</span>
                        <strong>{products.filter(p => (p.situacao || '').toLowerCase() === 'inativo').length}</strong>
                        <small>Situação inativa</small>
                    </div>
                </div>
            </section>

            {loading ? (
                <div className="panel loading-state">Carregando produtos...</div>
            ) : error ? (
                <div className="api-message error">{error}</div>
            ) : (
                <>
                    <div className="budget-table-panel">
                        <div className="budget-toolbar products-toolbar">
                            <div className="budget-search product-search-box">
                                <Search size={16} />
                                <input
                                    type="text"
                                    placeholder="Nome, código, família, cor, fornecedor..."
                                    aria-label="Buscar produtos por múltiplos termos"
                                    value={search}
                                    onChange={(e) => { setSearch(e.target.value); setPage(1) }}
                                />
                                <kbd>⌘ K</kbd>
                            </div>
                            <label className="products-sort">Ordenar por
                                <select value={sortOrder} onChange={e => { setSortOrder(e.target.value as ProductSort); setPage(1) }}>
                                    {(Object.keys(productSortLabels) as ProductSort[]).map(key => <option key={key} value={key}>{productSortLabels[key]}</option>)}
                                </select>
                            </label>
                            <div className="budget-filters products-filters">
                                <select value={filter} onChange={(e) => { setFilter(e.target.value as typeof filter); setPage(1) }} aria-label="Filtrar por situação">
                                    <option value="all">Todas as situações</option>
                                    <option value="ativos">Ativos</option>
                                    <option value="inativos">Inativos</option>
                                </select>
                                {productFilterKeys.map(key => <select key={key} aria-label={productFilterLabels[key]} value={criteria[key]}
                                    title={productFilterLabels[key]} onChange={e => { setCriteria(current => ({ ...current, [key]: e.target.value })); setPage(1) }}>
                                    <option value="">{productFilterLabels[key]}: todos</option>
                                    {criteria[key] && !filterOptions[key].some(option => option.value === criteria[key]) && <option value={criteria[key]}>{criteria[key]}</option>}
                                    {filterOptions[key].map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
                                </select>)}
                                {hasFilters && <button type="button" className="secondary-button" onClick={clearFilters}>Limpar filtros</button>}
                            </div>
                            <span role="status" style={{ fontSize: 13 }}>{filteredProducts.length} {filteredProducts.length === 1 ? 'produto encontrado' : 'produtos encontrados'}</span>
                        </div>
                        <div className="budget-table-wrap products-table-scroll" tabIndex={0} role="region" aria-label="Tabela de produtos com rolagem horizontal">
                            <table className="budget-table">
                                <thead>
                                    <tr>
                                        <th style={{ width: '60px' }}>ID</th>
<th style={{ minWidth: '220px' }}>Nome</th>
                                         <th>Grupo Comercial</th>
                                         <th>Unidade</th>
                                         <th>Cor/Variação</th>
                                         <th>Família</th>
                                         <th style={{ textAlign: 'right' }}>Custo</th>
                                         <th style={{ textAlign: 'right' }}>Custo Final</th>
                                         <th style={{ textAlign: 'right' }}>Venda</th>
                                         <th style={{ width: '100px' }}>Situação</th>
                                         <th style={{ width: '40px' }}></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {currentPageProducts.length === 0 ? (
                                        <tr>
                                            <td colSpan={11} style={{ textAlign: 'center', padding: '32px', color: 'var(--color-muted)' }}>
                                                Nenhum produto encontrado
                                            </td>
                                        </tr>
                                    ) : (
                                        currentPageProducts.map((product) => (
                                            <tr key={product.id} onClick={() => openDetail(product)} style={{ cursor: 'pointer' }}>
                                                <td><strong>{product.id}</strong></td>
                                                <td>
                                                    <strong className="products-name" title={product.nome}>{product.nome}</strong>
                                                    {product.codigo_interno && <small>Cód: {product.codigo_interno}</small>}
                                                </td>
                                                <td>{product.grupo_produto || product.grupo_tecnico || '-'}</td>
                                                <td>{product.unidade_venda || product.unidade || '-'}</td>
                                                <td>{productColor(product) || '-'}</td>
                                                <td>{product.familia_tecnica || '-'}</td>
                                                <td style={{ textAlign: 'right' }}>{formatCurrency(Number(product.valor_custo || 0))}</td>
                                                <td style={{ textAlign: 'right' }}>{formatCurrency(productCost(product))}</td>
                                                <td style={{ textAlign: 'right' }}>{formatCurrency(Number(product.valor_venda || 0))}</td>
                                                <td>
                                                    <span className={`budget-status budget-status-${statusTone(product.situacao)}`}>
                                                        <span />
                                                        {statusLabel(product.situacao)}
                                                    </span>
                                                </td>
                                                <td style={{ textAlign: 'center' }}>
                                                    <button className="table-action" onClick={(e) => { e.stopPropagation(); openDetail(product) }} aria-label="Ver detalhes">
                                                        <Eye size={16} />
                                                    </button>
                                                </td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        </div>
                        <div className="budget-table-footer">
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span>Página {page} de {totalPages}</span>
                                <span style={{ color: 'var(--color-muted)', fontSize: '10px' }}>(Mostrando {currentPageProducts.length} de {filteredProducts.length})</span>
                            </div>
                            <div style={{ display: 'flex', gap: '6px' }}>
                                <button
                                    className="filter-button"
                                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                                    disabled={page === 1}
                                    aria-label="Página anterior"
                                >
                                    <ChevronLeft size={16} />
                                </button>
                                <button
                                    className="filter-button"
                                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                                    disabled={page === totalPages}
                                    aria-label="Próxima página"
                                >
                                    <ChevronRight size={16} />
                                </button>
                            </div>
                        </div>
                    </div>
                </>
            )}

            {creating && <div className="modal-overlay" onClick={closeCreate} role="dialog" aria-modal="true" aria-labelledby="product-create-title">
                <div className="modal-container" style={{ maxWidth: '900px', maxHeight: '90vh', overflow: 'auto' }} onClick={e => e.stopPropagation()}>
                    <div className="modal-header"><h3 id="product-create-title">Novo produto</h3><button className="modal-close" disabled={savingProduct} onClick={closeCreate} aria-label="Fechar"><X size={18} /></button></div>
                    <div className="modal-form" style={{ padding: '24px' }}><ProductCommercialForm catalog={products} onBusy={setSavingProduct} onCancel={closeCreate} onSaved={created => {
                        setProducts(rows => [created, ...rows.filter(row => row.id !== created.id)].sort((a, b) => b.id - a.id))
                        setCreating(false)
                        openDetail(created)
                        setSavedMessage('Produto criado com sucesso.')
                    }} /></div>
                </div>
            </div>}
            {detailOpen && selectedProduct && (
                <div className="modal-overlay" onClick={closeDetail} role="dialog" aria-modal="true" aria-labelledby="product-detail-title">
                    <div className="modal-container" style={{ maxWidth: '900px', maxHeight: '90vh', overflow: 'auto' }} onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3 id="product-detail-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <Package size={18} />
                                Detalhes do Produto
                            </h3>
                            {!editing && <button className="secondary-button" onClick={() => { setSavedMessage(''); setEditing(true) }}>Editar</button>}
                            <button className="modal-close" disabled={savingProduct} onClick={closeDetail} aria-label="Fechar">
                                <X size={18} />
                            </button>
                        </div>
                        <div className="modal-form" style={{ padding: '24px' }}>
                            {savedMessage && <p role="status">{savedMessage}</p>}
                            {editing ? <ProductCommercialForm product={selectedProduct} catalog={products} onBusy={setSavingProduct} onCancel={() => setEditing(false)} onSaved={updated => {
                                setProducts(rows => rows.map(row => row.id === updated.id ? updated : row))
                                setSelectedProduct(updated)
                                setEditing(false)
                                setSavedMessage('Alterações salvas.')
                            }} /> : <>
                            <div style={{ display: 'grid', gap: '20px' }}>
                                <section style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '16px' }}>
                                    <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: 'var(--color-primary)' }}>
                                        <Package size={16} />
                                        COMERCIAL
                                    </h4>
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                                        <div className="modal-field">
                                            <label>Grupo Produto</label>
                                            <input value={selectedProduct.grupo_produto || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Unidade de Venda</label>
                                            <input value={selectedProduct.unidade_venda || selectedProduct.unidade || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Status Comercial</label>
                                            <input value={selectedProduct.status_comercial || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Situação</label>
                                            <input value={statusLabel(selectedProduct.situacao)} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Ativo</label>
                                            <input value={(selectedProduct.situacao || '').toLowerCase() !== 'inativo' ? 'Sim' : 'Não'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Valor de Custo</label>
                                            <input value={formatCurrency(Number(selectedProduct.valor_custo || 0))} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Despesas Acessórias</label>
                                            <input value={formatCurrency(Number(selectedProduct.despesas_acessorias || 0))} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Outras Despesas</label>
                                            <input value={formatCurrency(Number(selectedProduct.outras_despesas || 0))} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Custo Final</label>
                                            <input value={formatCurrency(productCost(selectedProduct))} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Margem de Lucro</label>
                                            <input value={selectedProduct.margem_lucro !== null && selectedProduct.margem_lucro !== undefined ? `${Number(selectedProduct.margem_lucro).toFixed(2)}%` : '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Valor de Venda</label>
                                            <input value={formatCurrency(Number(selectedProduct.valor_venda || 0))} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Tipo Produto</label>
                                            <input value={selectedProduct.tipo_produto || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Movimenta Estoque</label>
                                            <input value={selectedProduct.movimenta_estoque || '-'} readOnly />
                                        </div>
                                    </div>
                                </section>

                                <section style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '16px' }}>
                                    <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: 'var(--color-primary)' }}>
                                        <Package size={16} />
                                        IDENTIFICAÇÃO
                                    </h4>
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                                        <div className="modal-field">
                                            <label>ID</label>
                                            <input value={String(selectedProduct.id)} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Nome</label>
                                            <input value={selectedProduct.nome} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Código Interno</label>
                                            <input value={selectedProduct.codigo_interno || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Código de Barras</label>
                                            <input value={selectedProduct.codigo_barras || selectedProduct.codigo || '-'} readOnly />
                                        </div>
                                        <div className="modal-field" style={{ gridColumn: 'span 3' }}>
                                            <label>Descrição</label>
                                            <textarea readOnly style={{ minHeight: '60px', resize: 'vertical' }}>{selectedProduct.descricao || '-'}</textarea>
                                        </div>
                                        <div className="modal-field" style={{ gridColumn: 'span 3' }}>
                                            <label>Observações</label>
                                            <textarea readOnly style={{ minHeight: '60px', resize: 'vertical' }}>{selectedProduct.observacoes || '-'}</textarea>
                                        </div>
                                    </div>
                                </section>

                                <section style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '16px' }}>
                                    <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: 'var(--color-primary)' }}>
                                        <Package size={16} />
                                        TÉCNICO
                                    </h4>
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                                        <div className="modal-field">
                                            <label>Grupo Técnico</label>
                                            <input value={selectedProduct.grupo_tecnico || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Modelo Técnico</label>
                                            <input value={selectedProduct.modelo_tecnico || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Família Técnica</label>
                                            <input value={selectedProduct.familia_tecnica || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Produto Base</label>
                                            <input value={selectedProduct.produto_base || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Linha</label>
                                            <input value={selectedProduct.linha || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Modelo</label>
                                            <input value={selectedProduct.modelo || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Tipo Cortina/Persiana</label>
                                            <input value={selectedProduct.tipo_cortina_persiana || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Material/Tecido</label>
                                            <input value={selectedProduct.material_tecido || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Cor/Componente</label>
                                            <input value={selectedProduct.cor_componente || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Cor</label>
                                            <input value={selectedProduct.cor || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Variação de Cor</label>
                                            <input value={selectedProduct.variacao_cor || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Variação de Lado</label>
                                            <input value={selectedProduct.variacao_lado || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Variação de Tamanho</label>
                                            <input value={selectedProduct.variacao_tamanho || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Varia Cor?</label>
                                            <input value={selectedProduct.varia_cor ? 'Sim' : 'Não'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Possui Variações</label>
                                            <input value={selectedProduct.possui_variacoes || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Possui Composição</label>
                                            <input value={selectedProduct.possui_composicao || '-'} readOnly />
                                        </div>
                                    </div>
                                </section>

                                <section style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '16px' }}>
                                    <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: 'var(--color-primary)' }}>
                                        <Package size={16} />
                                        DIMENSÕES E PESO
                                    </h4>
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                                        <div className="modal-field">
                                            <label>Largura</label>
                                            <input value={selectedProduct.largura !== null && selectedProduct.largura !== undefined ? Number(selectedProduct.largura).toFixed(2) : '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Altura</label>
                                            <input value={selectedProduct.altura !== null && selectedProduct.altura !== undefined ? Number(selectedProduct.altura).toFixed(2) : '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Comprimento</label>
                                            <input value={selectedProduct.comprimento !== null && selectedProduct.comprimento !== undefined ? Number(selectedProduct.comprimento).toFixed(2) : '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Peso</label>
                                            <input value={selectedProduct.peso !== null && selectedProduct.peso !== undefined ? Number(selectedProduct.peso).toFixed(2) : '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Comprimento Compra</label>
                                            <input value={selectedProduct.comprimento_compra !== null && selectedProduct.comprimento_compra !== undefined ? Number(selectedProduct.comprimento_compra).toFixed(2) : '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Saldo Metros</label>
                                            <input value={selectedProduct.saldo_metros !== null && selectedProduct.saldo_metros !== undefined ? Number(selectedProduct.saldo_metros).toFixed(2) : '-'} readOnly />
                                        </div>
                                    </div>
                                </section>

                                <section style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '16px' }}>
                                    <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: 'var(--color-primary)' }}>
                                        <Package size={16} />
                                        UNIDADES DE MEDIDA
                                    </h4>
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                                        <div className="modal-field">
                                            <label>Unidade Venda</label>
                                            <input value={selectedProduct.unidade_venda || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Unidade Compra</label>
                                            <input value={selectedProduct.unidade_compra || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Unidade Controle</label>
                                            <input value={selectedProduct.unidade_controle || '-'} readOnly />
                                        </div>
                                    </div>
                                </section>

                                <section style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '16px' }}>
                                    <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: 'var(--color-primary)' }}>
                                        <Package size={16} />
                                        ESTOQUE
                                    </h4>
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                                        <div className="modal-field">
                                            <label>Estoque Mínimo</label>
                                            <input value={selectedProduct.estoque_minimo !== null && selectedProduct.estoque_minimo !== undefined ? Number(selectedProduct.estoque_minimo).toFixed(2) : '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Estoque Máximo</label>
                                            <input value={selectedProduct.estoque_maximo !== null && selectedProduct.estoque_maximo !== undefined ? Number(selectedProduct.estoque_maximo).toFixed(2) : '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Estoque Atual</label>
                                            <input value={selectedProduct.estoque_atual !== null && selectedProduct.estoque_atual !== undefined ? Number(selectedProduct.estoque_atual).toFixed(2) : '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Habilita Nota Fiscal</label>
                                            <input value={selectedProduct.habilitar_nota_fiscal || '-'} readOnly />
                                        </div>
                                    </div>
                                </section>

                                <section style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '16px' }}>
                                    <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: 'var(--color-primary)' }}>
                                        <Package size={16} />
                                        FORNECEDOR
                                    </h4>
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                                        <div className="modal-field">
                                            <label>Nome Fornecedor</label>
                                            <input value={selectedProduct.nome_fornecedor || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Código Fornecedor</label>
                                            <input value={selectedProduct.codigo_fornecedor || '-'} readOnly />
                                        </div>
                                        <div className="modal-field" style={{ gridColumn: 'span 3' }}>
                                            <label>Fornecedores</label>
                                            <textarea readOnly style={{ minHeight: '60px', resize: 'vertical' }}>{selectedProduct.fornecedores || '-'}</textarea>
                                        </div>
                                    </div>
                                </section>

                                <section>
                                    <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: 'var(--color-primary)' }}>
                                        <Package size={16} />
                                        FISCAL
                                    </h4>
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                                        <div className="modal-field">
                                            <label>NCM</label>
                                            <input value={selectedProduct.ncm || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>CEST</label>
                                            <input value={selectedProduct.cest || '-'} readOnly />
                                        </div>
                                        <div className="modal-field">
                                            <label>Origem</label>
                                            <input value={selectedProduct.origem || '-'} readOnly />
                                        </div>
                                    </div>
                                </section>
                            </div>
                            </>}
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

function CheckCircle2({ size }: { size?: number }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
        </svg>
    )
}

function AlertCircle({ size }: { size?: number }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
    )
}
