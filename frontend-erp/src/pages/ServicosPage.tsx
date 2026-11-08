import { useEffect, useState } from 'react'
import { Pencil, Plus, Search } from 'lucide-react'
import { atualizarServico, criarServico, listarServicos, type FaixaAlturaServico, type Servico, type ServicoPayload, type TipoCalculoServico, type UnidadeServico } from '../services/servicos'

type FaixaForm = { altura_max_cm: string; preco_unitario: string }
type Formulario = {
  codigo: string
  descricao: string
  categoria: string
  unidade: UnidadeServico
  tipo_calculo: TipoCalculoServico
  custo: string
  preco_venda: string
  comissao: string
  observacoes: string
  situacao: 'ATIVO' | 'INATIVO'
  faixas_altura: FaixaForm[]
}

const vazio: Formulario = {
  codigo: '', descricao: '', categoria: 'Instalação', unidade: 'UN', tipo_calculo: 'POR_UNIDADE',
  custo: '0', preco_venda: '0', comissao: '', observacoes: '', situacao: 'ATIVO', faixas_altura: [],
}
const unidades: UnidadeServico[] = ['UN', 'ML', 'M2', 'HORA', 'SERVICO']
const categorias = ['Instalação', 'Lavagem', 'Manutenção', 'Assistência técnica', 'Reforma', 'Motorização', 'Visita técnica', 'Mão de obra', 'Outros']
const numero = (value: string) => Number(value.replace(',', '.'))

function formularioDoServico(servico: Servico): Formulario {
  return {
    ...servico,
    custo: String(servico.custo),
    preco_venda: String(servico.preco_venda),
    comissao: servico.comissao == null ? '' : String(servico.comissao),
    observacoes: servico.observacoes || '',
    faixas_altura: (servico.faixas_altura || []).map(faixa => ({
      altura_max_cm: String(faixa.altura_max_cm), preco_unitario: String(faixa.preco_unitario),
    })),
  }
}

export function ServicosPage() {
  const [servicos, setServicos] = useState<Servico[]>([])
  const [busca, setBusca] = useState('')
  const [form, setForm] = useState<Formulario>(vazio)
  const [editando, setEditando] = useState<number | null>(null)
  const [modal, setModal] = useState(false)
  const [carregando, setCarregando] = useState(true)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState('')

  async function carregar(termo = busca) {
    setCarregando(true)
    setErro('')
    try { setServicos(await listarServicos(termo, true)) }
    catch (error) { setErro(error instanceof Error ? error.message : String(error)) }
    finally { setCarregando(false) }
  }

  useEffect(() => { void carregar('') }, [])

  function abrirNovo() {
    setEditando(null); setForm(vazio); setErro(''); setModal(true)
  }

  function abrirEdicao(servico: Servico) {
    setEditando(servico.id); setForm(formularioDoServico(servico)); setErro(''); setModal(true)
  }

  function atualizarCampo<K extends keyof Formulario>(campo: K, valor: Formulario[K]) {
    setForm(atual => {
      const proximo = { ...atual, [campo]: valor }
      if (campo === 'tipo_calculo' && valor === 'FAIXA_ALTURA') proximo.unidade = 'UN'
      if (campo === 'categoria' && valor !== 'Lavagem') {
        proximo.tipo_calculo = 'POR_UNIDADE'
        proximo.faixas_altura = []
      }
      return proximo
    })
  }

  function atualizarFaixa(index: number, campo: keyof FaixaForm, valor: string) {
    setForm(atual => ({
      ...atual,
      faixas_altura: atual.faixas_altura.map((faixa, i) => i === index ? { ...faixa, [campo]: valor } : faixa),
    }))
  }

  async function salvar(event: React.FormEvent) {
    event.preventDefault()
    setErro('')
    const faixas: FaixaAlturaServico[] = form.faixas_altura.map(faixa => ({
      altura_max_cm: numero(faixa.altura_max_cm), preco_unitario: numero(faixa.preco_unitario),
    }))
    const payload: ServicoPayload = {
      codigo: form.codigo.trim(), descricao: form.descricao.trim(), categoria: form.categoria,
      unidade: form.unidade, tipo_calculo: form.tipo_calculo,
      custo: numero(form.custo), preco_venda: numero(form.preco_venda),
      comissao: form.comissao.trim() ? numero(form.comissao) : null,
      observacoes: form.observacoes.trim() || null, situacao: form.situacao,
      faixas_altura: faixas,
    }
    if ([payload.custo, payload.preco_venda, ...(payload.comissao == null ? [] : [payload.comissao])].some(value => !Number.isFinite(value) || value < 0)) {
      setErro('Informe valores numéricos válidos e não negativos.'); return
    }
    if (payload.comissao != null && payload.comissao > 100) {
      setErro('A comissão deve estar entre 0 e 100%.'); return
    }
    if (payload.tipo_calculo === 'FAIXA_ALTURA' && faixas.some(faixa => !Number.isFinite(faixa.altura_max_cm) || !Number.isFinite(faixa.preco_unitario))) {
      setErro('Preencha altura máxima e preço de todas as faixas.'); return
    }
    setSalvando(true)
    try {
      if (editando == null) await criarServico(payload)
      else await atualizarServico(editando, payload)
      setModal(false); await carregar()
    } catch (error) { setErro(error instanceof Error ? error.message : String(error)) }
    finally { setSalvando(false) }
  }

  async function alternarSituacao(servico: Servico) {
    setErro('')
    try {
      await atualizarServico(servico.id, {
        codigo: servico.codigo, descricao: servico.descricao, categoria: servico.categoria,
        unidade: servico.unidade, tipo_calculo: servico.tipo_calculo, custo: servico.custo,
        preco_venda: servico.preco_venda, comissao: servico.comissao, observacoes: servico.observacoes,
        situacao: servico.situacao === 'ATIVO' ? 'INATIVO' : 'ATIVO',
        faixas_altura: servico.faixas_altura,
      })
      await carregar()
    } catch (error) { setErro(error instanceof Error ? error.message : String(error)) }
  }

  return <main className="cad-page" aria-label="Cadastro de serviços">
    <header className="cad-heading">
      <div><p className="cad-eyebrow">CADASTROS</p><h1 className="commercial-title">Serviços</h1><p>Catálogo comercial por empresa; valores dos documentos são preservados como snapshots.</p></div>
      <div className="cad-heading-actions"><button type="button" className="primary-button" onClick={abrirNovo}><Plus size={16}/> Novo serviço</button></div>
    </header>
    <div className="cad-toolbar">
      <div className="cad-search"><Search size={16}/><input aria-label="Buscar serviços" placeholder="Buscar por código, descrição ou categoria..." value={busca} onChange={event => setBusca(event.target.value)} onKeyDown={event => { if (event.key === 'Enter') void carregar() }} /></div>
      <button type="button" className="cad-secondary" onClick={() => void carregar()}>Buscar</button>
    </div>
    {erro && <p className="api-message error" role="alert">{erro}</p>}
    <div className="cad-table-card">
    {carregando ? <p className="cad-empty" role="status">Carregando serviços...</p> : servicos.length === 0 ? <p className="cad-empty">Nenhum serviço encontrado.</p> : <div className="cad-table-wrap">
      <table className="cad-table"><thead><tr><th>Código</th><th>Descrição</th><th>Categoria</th><th>Unidade</th><th>Preço</th><th>Situação</th><th>Ações</th></tr></thead>
        <tbody>{servicos.map(servico => <tr key={servico.id}>
          <td>{servico.codigo}</td><td>{servico.descricao}</td><td>{servico.categoria}</td><td>{servico.unidade === 'M2' ? 'M²' : servico.unidade}</td>
          <td>{Number(servico.preco_venda).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</td>
          <td>{servico.situacao === 'ATIVO' ? 'Ativo' : 'Inativo'}</td>
          <td><button type="button" className="secondary-button" onClick={() => abrirEdicao(servico)} aria-label={`Editar ${servico.descricao}`}><Pencil size={14}/> Editar</button>{' '}
            <button type="button" className="secondary-button" onClick={() => void alternarSituacao(servico)}>{servico.situacao === 'ATIVO' ? 'Inativar' : 'Ativar'}</button></td>
        </tr>)}</tbody>
      </table>
    </div>}
    </div>
    {modal && <div className="modal-overlay" onClick={() => setModal(false)}>
      <div className="modal-container" role="dialog" aria-modal="true" aria-label={editando == null ? 'Novo serviço' : 'Editar serviço'} onClick={event => event.stopPropagation()}>
        <div className="modal-header"><h2>{editando == null ? 'Novo serviço' : 'Editar serviço'}</h2><button type="button" className="modal-close" onClick={() => setModal(false)}>×</button></div>
        <form className="modal-form" onSubmit={event => void salvar(event)}>
          <div className="form-grid">
            <label className="field"><span>Código *</span><input required maxLength={50} value={form.codigo} onChange={event => atualizarCampo('codigo', event.target.value)} /></label>
            <label className="field"><span>Descrição *</span><input required maxLength={500} value={form.descricao} onChange={event => atualizarCampo('descricao', event.target.value)} /></label>
            <label className="field"><span>Categoria *</span><select value={form.categoria} onChange={event => atualizarCampo('categoria', event.target.value)}>{categorias.map(item => <option key={item}>{item}</option>)}</select></label>
            <label className="field"><span>Unidade de cobrança *</span><select value={form.unidade} onChange={event => atualizarCampo('unidade', event.target.value as UnidadeServico)}>{unidades.map(item => <option key={item} value={item}>{item}</option>)}</select></label>
            <label className="field"><span>Tipo de cálculo *</span><select value={form.tipo_calculo} onChange={event => atualizarCampo('tipo_calculo', event.target.value as TipoCalculoServico)}><option value="POR_UNIDADE">Por unidade de cobrança</option>{form.categoria === 'Lavagem' && <option value="FAIXA_ALTURA">Lavagem por faixa de altura</option>}</select></label>
            <label className="field"><span>Custo</span><input type="number" min="0" step="0.0001" value={form.custo} onChange={event => atualizarCampo('custo', event.target.value)} /></label>
            <label className="field"><span>Preço de venda</span><input type="number" min="0" step="0.0001" value={form.preco_venda} onChange={event => atualizarCampo('preco_venda', event.target.value)} /></label>
            <label className="field"><span>Comissão (%)</span><input type="number" min="0" max="100" step="0.0001" value={form.comissao} onChange={event => atualizarCampo('comissao', event.target.value)} /></label>
            <label className="field"><span>Situação</span><select value={form.situacao} onChange={event => atualizarCampo('situacao', event.target.value as Formulario['situacao'])}><option value="ATIVO">Ativo</option><option value="INATIVO">Inativo</option></select></label>
          </div>
          {form.tipo_calculo === 'FAIXA_ALTURA' && <section><h3>Faixas de lavagem</h3><p>Informe os limites em cm e o preço por peça. Não há faixas nem preços predefinidos.</p>
            {form.faixas_altura.map((faixa, index) => <div className="form-grid" key={index}>
              <label className="field"><span>Altura máxima (cm)</span><input type="number" min="0.01" step="0.01" value={faixa.altura_max_cm} onChange={event => atualizarFaixa(index, 'altura_max_cm', event.target.value)} /></label>
              <label className="field"><span>Preço por peça</span><input type="number" min="0" step="0.01" value={faixa.preco_unitario} onChange={event => atualizarFaixa(index, 'preco_unitario', event.target.value)} /></label>
              <button type="button" className="secondary-button" onClick={() => setForm(atual => ({ ...atual, faixas_altura: atual.faixas_altura.filter((_, i) => i !== index) }))}>Remover faixa</button>
            </div>)}
            <button type="button" className="secondary-button" onClick={() => setForm(atual => ({ ...atual, faixas_altura: [...atual.faixas_altura, { altura_max_cm: '', preco_unitario: '' }] }))}><Plus size={14}/> Adicionar faixa</button>
          </section>}
          <label className="field"><span>Observações</span><textarea maxLength={5000} value={form.observacoes} onChange={event => atualizarCampo('observacoes', event.target.value)} /></label>
          {erro && <p className="api-message error" role="alert">{erro}</p>}
          <div className="modal-actions"><button type="button" className="secondary-button" onClick={() => setModal(false)} disabled={salvando}>Cancelar</button><button type="submit" className="primary-button" disabled={salvando}>{salvando ? 'Salvando...' : 'Salvar serviço'}</button></div>
        </form>
      </div>
    </div>}
  </main>
}
