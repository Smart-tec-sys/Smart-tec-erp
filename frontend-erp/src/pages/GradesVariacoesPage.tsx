import { useEffect, useState, type FormEvent } from 'react'
import { ColumnManager } from '../components/ColumnManager'
import * as api from '../services/gradesVariacoes'
import './gradesVariacoes.css'

const columns = [
  { id: 'nome', label: 'Nome / valor', defaultVisible: true },
  { id: 'ativo', label: 'Situação', defaultVisible: true },
  { id: 'ordem', label: 'Ordem', defaultVisible: true },
  { id: 'acoes', label: 'Ações', defaultVisible: true },
]
type Editor = { id?: number; text: string; descricao: string; ativo: boolean; ordem: number }
export function GradesVariacoesPage({ onBack }: { onBack: () => void }) {
  const [grades, setGrades] = useState<api.Grade[]>([])
  const [selected, setSelected] = useState<api.Grade | null>(null)
  const [values, setValues] = useState<api.GradeValue[]>([])
  const [editor, setEditor] = useState<Editor | null>(null)
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const visible = columns.map(c => c.id)
  async function reload(grade = selected) {
    const nextGrades = await api.listGrades()
    setGrades(nextGrades)
    if (grade) {
      const updated = nextGrades.find(g => g.id === grade.id)
      if (updated) { setSelected(updated); setValues(await api.listGradeValues(grade.id)) }
      else { setSelected(null); setValues([]) }
    }
  }
  useEffect(() => {
    let active = true
    api.listGrades().then(data => { if (active) setGrades(data) })
      .catch(err => { if (active) setError(err instanceof Error ? err.message : 'Erro ao carregar grades.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])
  async function run(action: () => Promise<unknown>, success: string, closeEditor = false) {
    setBusy(true); setError(''); setMessage('')
    try {
      await action()
      if (closeEditor) setEditor(null)
      setMessage(success)
      await reload()
    } catch (err) { setError(err instanceof Error ? err.message : 'Não foi possível concluir a operação.') }
    finally { setBusy(false) }
  }
  async function open(grade: api.Grade) {
    setLoading(true); setError(''); setMessage('')
    try { const data = await api.listGradeValues(grade.id); setValues(data); setSelected(grade); setEditor(null) }
    catch (err) { setError(err instanceof Error ? err.message : 'Erro ao carregar valores.') }
    finally { setLoading(false) }
  }
  function save(event: FormEvent) {
    event.preventDefault()
    if (!editor) return
    const common = { ativo: editor.ativo, ordem: editor.ordem }
    if (selected) {
      const data = { ...common, valor: editor.text.trim() }
      void run(() => editor.id ? api.updateGradeValue(selected.id, editor.id, data) : api.createGradeValue(selected.id, data), 'Valor salvo.', true)
    } else {
      const data = { ...common, nome: editor.text.trim(), descricao: editor.descricao.trim() || null }
      void run(() => editor.id ? api.updateGrade(editor.id, data) : api.createGrade(data), 'Grade salva.', true)
    }
  }
  const rows = selected ? values : grades
  const isVisible = (id: string) => visible.includes(id)
  return <section className="grades-page">
    <button className="profile-secondary-button" disabled={busy || loading} onClick={() => {
      if (selected) { setSelected(null); setValues([]); setEditor(null); setError(''); setMessage('') }
      else onBack()
    }}>← {selected ? 'Voltar para grades' : 'Voltar para Configurações'}</button>
    <div className="page-heading"><div><p className="eyebrow">CONFIGURAÇÕES / OPÇÕES AUXILIARES</p>
      <h1>{selected ? `Valores — ${selected.nome}` : 'Grades/Variações'}</h1>
      <p className="heading-subtitle">Opções auxiliares reutilizáveis para todos os produtos.</p>
    </div></div>
    {error && <div role="alert" className="settings-error">{error}</div>}
    {message && <div role="status" className="settings-message">{message}</div>}
    <div className="grades-toolbar">
      <button className="profile-secondary-button" disabled={busy || loading || !!editor} onClick={() => setEditor({ text: '', descricao: '', ativo: true, ordem: rows.length ? Math.max(...rows.map(r => r.ordem)) + 1 : 0 })}>+ {selected ? 'Novo valor' : 'Nova grade'}</button>
      <button className="profile-secondary-button" disabled={busy || loading} onClick={() => void run(() => Promise.resolve(), 'Lista atualizada.')}>Atualizar</button>
    </div>
    {editor && <form className="grades-editor" onSubmit={save}>
      <h2>{editor.id ? 'Editar' : 'Cadastrar'} {selected ? 'valor' : 'grade'}</h2>
      <label>{selected ? 'Valor' : 'Nome'}<input autoFocus required maxLength={selected ? 150 : 120} value={editor.text} disabled={busy} onChange={e => setEditor({ ...editor, text: e.target.value })} /></label>
      {!selected && <label>Descrição<textarea value={editor.descricao} disabled={busy} onChange={e => setEditor({ ...editor, descricao: e.target.value })} /></label>}
      <label>Ordem<input type="number" required min={0} step={1} value={editor.ordem} disabled={busy} onChange={e => setEditor({ ...editor, ordem: Number(e.target.value) })} /></label>
      <label className="grades-checkbox"><input type="checkbox" checked={editor.ativo} disabled={busy} onChange={e => setEditor({ ...editor, ativo: e.target.checked })} />Ativo</label>
      <p className="grades-help">A listagem segue a ordem informada. Para reordenar, altere este número.</p>
      <div className="grades-actions"><button className="profile-secondary-button" disabled={busy || !editor.text.trim()} type="submit">{busy ? 'Salvando...' : 'Salvar'}</button><button className="profile-secondary-button" disabled={busy} type="button" onClick={() => setEditor(null)}>Cancelar</button></div>
    </form>}
    {loading ? <p role="status">Carregando...</p> : <div className="grades-table-wrap"><ColumnManager key={selected ? 'valores' : 'lista'} columns={columns} storageKey={`smarttec-grades-${selected ? 'valores' : 'lista'}`} lockedColumns={['nome', 'acoes']}><table>
      <thead><tr>{isVisible('nome') && <th>{selected ? 'Valor' : 'Grade'}</th>}{isVisible('ativo') && <th>Situação</th>}{isVisible('ordem') && <th>Ordem</th>}{isVisible('acoes') && <th>Ações</th>}</tr></thead>
      <tbody>{rows.map(row => {
        const name = 'nome' in row ? row.nome : row.valor
        return <tr key={row.id}>
          {isVisible('nome') && <td>{selected ? <strong>{name}</strong> : <button className="grades-link" disabled={busy || !!editor} onClick={() => void open(row as api.Grade)}>{name}</button>}
            {'descricao' in row && row.descricao && <small>{row.descricao}</small>}
            {'quantidade_valores' in row && <small>{row.quantidade_valores} valores</small>}</td>}
          {isVisible('ativo') && <td>{row.ativo ? 'Ativo' : 'Inativo'}</td>}
          {isVisible('ordem') && <td>{row.ordem}</td>}
          {isVisible('acoes') && <td><div className="grades-actions">
            <button className="profile-secondary-button" disabled={busy || !!editor} onClick={() => setEditor({ id: row.id, text: name, descricao: 'descricao' in row ? row.descricao || '' : '', ativo: row.ativo, ordem: row.ordem })}>Editar</button>
            <button className="profile-secondary-button" disabled={busy || !!editor} onClick={() => void run(() => selected ? api.updateGradeValue(selected.id, row.id, { ativo: !row.ativo }) : api.updateGrade(row.id, { ativo: !row.ativo }), 'Situação atualizada.')}>{row.ativo ? 'Inativar' : 'Ativar'}</button>
            <button className="profile-danger-button" disabled={busy || !!editor} onClick={() => {
              if (window.confirm(`Excluir "${name}"? Esta ação não pode ser desfeita.`)) void run(() => selected ? api.deleteGradeValue(selected.id, row.id) : api.deleteGrade(row.id), 'Cadastro excluído.')
            }}>Excluir</button>
          </div></td>}
        </tr>
      })}{!rows.length && <tr><td colSpan={visible.length}>{error ? 'Listagem indisponível.' : selected ? 'Nenhum valor cadastrado.' : 'Nenhuma grade cadastrada.'}</td></tr>}</tbody>
    </table></ColumnManager></div>}
  </section>
}
