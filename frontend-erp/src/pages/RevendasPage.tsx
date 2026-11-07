import { commercialDisplayText } from '../utils/commercialDisplay'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Eye, Pencil, Plus, Search } from 'lucide-react'
import { ColumnManager } from '../components/ColumnManager'
import { RevendaForm } from '../components/RevendaForm'
import { listarRevendas, obterRevenda, type Revenda } from '../services/revendas'
import './cadastrosPage.css'
import './revendasPage.css'

export function RevendasPage() {
  const [rows, setRows] = useState<Revenda[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [opening, setOpening] = useState(false)
  const [error, setError] = useState('')
  const [modal, setModal] = useState<{ mode: 'create' | 'edit' | 'view'; revenda?: Revenda } | null>(null)
  const mounted = useRef(true)
  const selection = useRef(0)
  useEffect(() => {
    mounted.current = true
    void listarRevendas().then(result => { if (mounted.current) setRows(result) })
      .catch(err => { if (mounted.current) setError(err instanceof Error ? err.message : 'Não foi possível carregar revendas.') })
      .finally(() => { if (mounted.current) setLoading(false) })
    return () => { mounted.current = false; selection.current++ }
  }, [])
  const filtered = useMemo(() => {
    const term = search.trim().toLocaleLowerCase('pt-BR')
    return rows.filter(row => [row.nome, row.nome_fantasia, row.razao_social, row.documento, row.email, row.telefone, row.cidade]
      .some(value => typeof value === 'string' && value.toLocaleLowerCase('pt-BR').includes(term)))
  }, [rows, search])
  async function open(row: Revenda, mode: 'edit' | 'view') {
    const requestId = ++selection.current
    setOpening(true); setError('')
    try {
      const revenda = await obterRevenda(row.id)
      if (mounted.current && requestId === selection.current) setModal({ mode, revenda })
    } catch (err) {
      if (mounted.current && requestId === selection.current) setError(err instanceof Error ? err.message : 'Não foi possível abrir a revenda.')
    } finally { if (mounted.current && requestId === selection.current) setOpening(false) }
  }
  const columns = [
    { id: 'nome', label: 'Nome', defaultVisible: true }, { id: 'documento', label: 'CPF / CNPJ', defaultVisible: true },
    { id: 'email', label: 'E-mail', defaultVisible: true }, { id: 'telefone', label: 'Telefone comercial', defaultVisible: true },
    { id: 'percentual_padrao', label: '% revenda padrão', defaultVisible: true }, { id: 'ativo', label: 'Situação', defaultVisible: true },
    { id: 'actions', label: 'Ações', defaultVisible: true },
  ]
  return <section className="cad-page">
    <div className="cad-heading"><div><p className="cad-eyebrow">CADASTROS</p><h1 className="commercial-title">Revendas</h1><p>Cadastro rápido com preenchimento assistido por CNPJ e CEP.</p></div>
      <button className="primary-button" disabled={opening} onClick={() => setModal({ mode: 'create' })}><Plus size={18} /> Nova revenda</button></div>
    <div className="cad-toolbar"><div className="cad-search"><Search size={17} /><input aria-label="Buscar revendas" value={search}
      onChange={event => setSearch(event.target.value)} placeholder="Buscar revendas..." /></div><span>{filtered.length} registro(s)</span></div>
    {error && <div className="cad-error" role="alert">{error}</div>}
    {opening && <p role="status">Carregando cadastro...</p>}
    <div className="cad-table-card">{loading ? <div className="cad-empty">Carregando...</div> : !filtered.length ? <div className="cad-empty">Nenhuma revenda encontrada.</div>
      : <div className="cad-table-wrap"><ColumnManager storageKey="smarttec:columns:resellers" lockedColumns={['nome', 'actions']} columns={columns}>
        <table className="cad-table"><thead><tr>{columns.map(column => <th key={column.id}>{column.label}</th>)}</tr></thead><tbody>
          {filtered.map(row => <tr key={row.id}><td><strong>{commercialDisplayText(row.nome)}</strong></td><td>{row.documento || '—'}</td><td>{row.email || '—'}</td>
            <td>{row.telefone || '—'}</td><td>{row.percentual_padrao ?? 0}%</td><td>{row.ativo ? 'Ativo' : 'Inativo'}</td>
            <td><div className="cad-actions"><button disabled={opening} title="Visualizar" aria-label={`Visualizar ${row.nome}`} onClick={() => void open(row, 'view')}><Eye size={16} /></button>
              <button disabled={opening} title="Editar" aria-label={`Editar ${row.nome}`} onClick={() => void open(row, 'edit')}><Pencil size={16} /></button></div></td></tr>)}
        </tbody></table></ColumnManager></div>}</div>
    {modal && <RevendaForm key={`${modal.mode}-${modal.revenda?.id ?? 'new'}`} revenda={modal.revenda} somenteLeitura={modal.mode === 'view'}
      onClose={() => setModal(null)} onSaved={record => {
        setRows(previous => [record, ...previous.filter(row => row.id !== record.id)].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')))
        setModal(null)
      }} />}
  </section>
}
