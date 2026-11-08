import { useEffect, useState } from 'react'
import {
  adicionarComponentePeca, avancarPeca, aprovarProducao, carregarDocumentoProducao, carregarEtiquetasLoteProducao,
  conferirPeca,
  criarProducao, liberarPedidoProducao, liberarProducao, listarProducao, obterAutorizacaoProducao,
  listarCatalogoComponentes, removerComponentePeca, salvarPeca, atualizarComponentePeca,
  statusProducao, type AtualizacaoPeca, type ComponentePecaProducao,
  type DadosComponenteProducao, type OrdemProducao, type PecaProducao,
  type ProdutoComponenteProducao,
  type AutorizacaoProducao,
} from '../services/producao'
import './producaoPanel.css'
import { producaoV1Enabled } from '../services/producaoFlag'

type Props = { pedidoId: number; statusVenda: string }

export function ProducaoPanel({ pedidoId, statusVenda }: Props) {
  return producaoV1Enabled ? <ProducaoPanelHabilitado pedidoId={pedidoId} statusVenda={statusVenda} /> : null
}

function ProducaoPanelHabilitado({ pedidoId, statusVenda }: Props) {
  const [ordem, setOrdem] = useState<OrdemProducao | null>(null)
  const [autorizacao, setAutorizacao] = useState<AutorizacaoProducao | null>(null)
  const [carregando, setCarregando] = useState(true)
  const [tentativa, setTentativa] = useState(0)
  const [ocupado, setOcupado] = useState(false)
  const [erro, setErro] = useState('')
  const [confirmado, setConfirmado] = useState(false)
  const [documento, setDocumento] = useState<string | null>(null)
  const permitida = ['ABERTO', 'FATURADO', 'CONCLUIDO'].includes(statusVenda)
  const autorizada = permitida && Boolean(autorizacao?.aprovado_em && autorizacao.liberado_em)
  useEffect(() => {
    let cancelado = false
    setCarregando(true); setErro('')
    Promise.all([listarProducao(pedidoId), obterAutorizacaoProducao(pedidoId)]).then(([ordens, estado]) => {
      if (!cancelado) { setOrdem(ordens[0] ?? null); setAutorizacao(estado) }
    }).catch(err => {
      if (!cancelado) setErro(err instanceof Error ? err.message : String(err))
    }).finally(() => { if (!cancelado) setCarregando(false) })
    return () => { cancelado = true }
  }, [pedidoId, tentativa])

  async function executar(acao: () => Promise<OrdemProducao>) {
    setOcupado(true); setErro('')
    try { setOrdem(await acao()); setDocumento(null) }
    catch (err) { setErro(err instanceof Error ? err.message : String(err)) }
    finally { setOcupado(false) }
  }
  async function executarAutorizacao(acao: () => Promise<AutorizacaoProducao>) {
    setOcupado(true); setErro('')
    try { setAutorizacao(await acao()) }
    catch (err) { setErro(err instanceof Error ? err.message : String(err)) }
    finally { setOcupado(false) }
  }
  async function visualizar(pecaId?: number) {
    if (!ordem) return
    setOcupado(true); setErro('')
    try { setDocumento(await carregarDocumentoProducao(ordem.id, pecaId)) }
    catch (err) { setErro(err instanceof Error ? err.message : String(err)) }
    finally { setOcupado(false) }
  }
  async function visualizarLote() {
    if (!ordem) return
    setOcupado(true); setErro('')
    try { setDocumento(await carregarEtiquetasLoteProducao(ordem.id)) }
    catch (err) { setErro(err instanceof Error ? err.message : String(err)) }
    finally { setOcupado(false) }
  }
  return <section className="panel producao-panel" aria-label="Produção V1">
    <h2>Produção V1</h2>
    <p>Fabricação independente do faturamento. Não reserva nem baixa estoque.</p>
    <button type="button" className="secondary-button" disabled={ocupado || carregando}
      onClick={() => setTentativa(value => value + 1)}>Recarregar produção</button>
    {erro && <p className="api-message error" role="alert">{erro}</p>}
    {carregando ? <p role="status">Carregando produção...</p> : <>
      <div className="producao-autorizacao">
        <h3>Autorização de fabricação</h3>
        <p>Faturamento ou conclusão não autorizam fabricação automaticamente.</p>
        <p>{autorizacao?.aprovado_em
          ? `Aprovada por ${autorizacao.aprovado_por} em ${new Date(autorizacao.aprovado_em).toLocaleString('pt-BR')}`
          : 'Pedido ainda não aprovado para fabricação.'}</p>
        {!autorizacao?.aprovado_em && <button type="button" className="secondary-button"
          disabled={!permitida || ocupado || Boolean(erro)}
          onClick={() => window.confirm('Aprovar este pedido para fabricação? Usuário e horário serão registrados.')
            && void executarAutorizacao(() => aprovarProducao(pedidoId))}>Aprovar pedido para fabricação</button>}
        <p>{autorizacao?.liberado_em
          ? `Liberado por ${autorizacao.liberado_por} em ${new Date(autorizacao.liberado_em).toLocaleString('pt-BR')}`
          : 'Pedido ainda não liberado para fabricação.'}</p>
        {autorizacao?.aprovado_em && !autorizacao.liberado_em && <button type="button" className="secondary-button"
          disabled={!permitida || ocupado || Boolean(erro)}
          onClick={() => window.confirm('Liberar este pedido para fabricação? Esta ação é separada da aprovação.')
            && void executarAutorizacao(() => liberarPedidoProducao(pedidoId))}>Liberar pedido para fabricação</button>}
        {!!autorizacao?.historico.length && <details><summary>Histórico de autorização</summary>
          <ul>{autorizacao.historico.map((evento, index) => <li key={`${evento.em}-${index}`}>
            {evento.acao} · {evento.usuario || 'usuário não identificado'} · {new Date(evento.em).toLocaleString('pt-BR')}
          </li>)}</ul></details>}
      </div>
      {!ordem && <>
        <label><input type="checkbox" checked={confirmado} onChange={e => setConfirmado(e.target.checked)} />
          Confirmo a criação da OP após aprovação e liberação explícitas.</label>
        <button type="button" className="primary-button"
          disabled={!confirmado || !permitida || !autorizacao?.aprovado_em || !autorizacao?.liberado_em || ocupado || Boolean(erro)}
          onClick={() => void executar(() => criarProducao(pedidoId))}>Criar ordem de produção</button>
      </>}
      {ordem && <>
        <h3>OP-{String(ordem.id).padStart(6, '0')} · {ordem.status}</h3>
        <p>OP criada por {ordem.confirmado_por} em {new Date(ordem.confirmado_em).toLocaleString('pt-BR')}</p>
        <p>{ordem.liberado_em ? `OP tecnicamente liberada por ${ordem.liberado_por} em ${new Date(ordem.liberado_em).toLocaleString('pt-BR')}` : 'OP ainda não liberada após conferência técnica'}</p>
        <button type="button" className="secondary-button" disabled={ocupado} onClick={() => void visualizar()}>Visualizar / imprimir ficha</button>
        {ordem.liberado_em && autorizada && <button type="button" className="secondary-button" disabled={ocupado}
          onClick={() => void visualizarLote()}>Imprimir etiquetas do lote</button>}
        {ordem.liberado_em && !autorizada && <p role="alert">Autorização de fabricação invalidada. Consulte o histórico antes de continuar.</p>}
        {ordem.pendencias.length > 0 && <div role="status"><h4>Liberação bloqueada</h4>
          <ul>{ordem.pendencias.map((p, i) => <li key={i}>{p}</li>)}</ul></div>}
        {!ordem.liberado_em && <button type="button" className="primary-button"
          disabled={ocupado || !permitida || ordem.pendencias.length > 0 || !autorizacao?.liberado_em}
          onClick={() => {
            if (window.confirm('Confirma a liberação técnica desta OP? Sua identidade e horário serão registrados.'))
              void executar(() => liberarProducao(ordem.id))
          }}>Liberar OP para fabricação</button>}
        {ordem.pecas.map(peca => <FichaPeca key={`${peca.id}-${peca.versao_ficha}`}
          peca={peca} liberada={Boolean(ordem.liberado_em)} autorizado={autorizada} ocupado={ocupado} permitida={permitida}
          onSave={dados => void executar(() => salvarPeca(ordem.id, peca.id, dados))}
          onAddComponent={dados => void executar(() => adicionarComponentePeca(ordem.id, peca.id, dados))}
          onUpdateComponent={(componenteId, dados) => void executar(
            () => atualizarComponentePeca(ordem.id, peca.id, componenteId, dados),
          )}
          onRemoveComponent={(componenteId, justificativa) => void executar(
            () => removerComponentePeca(ordem.id, peca.id, componenteId, justificativa),
          )}
          onReview={justificativa => void executar(() => conferirPeca(ordem.id, peca.id, justificativa))}
          onAdvance={() => void executar(() => avancarPeca(ordem.id, peca))}
          onLabel={() => void visualizar(peca.id)} />)}
      </>}
    </>}
    {!permitida && <p role="alert">Venda cancelada ou com situação não suportada. Fabricação bloqueada.</p>}
    {documento && <div className="producao-documento">
      <button type="button" className="secondary-button" onClick={() => setDocumento(null)}>Fechar documento</button>
      <iframe title="Documento de fabricação" srcDoc={documento} sandbox="allow-scripts allow-modals" />
    </div>}
  </section>
}

function FichaPeca({ peca, liberada, autorizado, ocupado, permitida, onSave, onAddComponent,
  onUpdateComponent, onRemoveComponent, onReview, onAdvance, onLabel }: {
  peca: PecaProducao; liberada: boolean; autorizado: boolean; ocupado: boolean; permitida: boolean
  onSave: (dados: AtualizacaoPeca) => void
  onAddComponent: (dados: DadosComponenteProducao) => void
  onUpdateComponent: (componenteId: number, dados: DadosComponenteProducao) => void
  onRemoveComponent: (componenteId: number, justificativa: string) => void
  onReview: (justificativa: string) => void
  onAdvance: () => void; onLabel: () => void
}) {
  const [ambiente, setAmbiente] = useState(peca.ambiente)
  const [largura, setLargura] = useState(String(peca.largura))
  const [altura, setAltura] = useState(String(peca.altura))
  const [quantidade, setQuantidade] = useState(String(peca.quantidade))
  const [observacoes, setObservacoes] = useState(peca.observacoes)
  const [modo, setModo] = useState(peca.modo_fabricacao)
  const [especificacoes, setEspecificacoes] = useState(
    JSON.stringify(peca.especificacoes_fabricacao ?? {}, null, 2),
  )
  const [justificativa, setJustificativa] = useState('')
  const [erroLocal, setErroLocal] = useState('')
  const [mostrarComposicao, setMostrarComposicao] = useState(false)
  const [busca, setBusca] = useState('')
  const [catalogo, setCatalogo] = useState<ProdutoComponenteProducao[]>([])
  const [componenteEditando, setComponenteEditando] = useState<number | null>(null)
  const [produtoId, setProdutoId] = useState('')
  const [componenteQuantidade, setComponenteQuantidade] = useState('1')
  const [unidade, setUnidade] = useState('')
  const [comprimentoCorte, setComprimentoCorte] = useState('')
  const [custoUnitario, setCustoUnitario] = useState('')
  const [observacoesComponente, setObservacoesComponente] = useState('')
  const [justificativaComponente, setJustificativaComponente] = useState('')
  const proxima = statusProducao[statusProducao.indexOf(peca.status) + 1]
  const manual = modo === 'MANUAL_SUPERVISIONADA'
  const podeEditar = !liberada && !ocupado && permitida && autorizado

  function dadosEspecificacoes(): Record<string, string> {
    const parsed: unknown = JSON.parse(especificacoes)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)
      || Object.values(parsed).some(value => typeof value !== 'string')) {
      throw new Error('Especificações devem ser um objeto JSON de textos.')
    }
    return parsed as Record<string, string>
  }

  function salvarFicha() {
    setErroLocal('')
    try {
      onSave({
        ambiente, largura: Number(largura), altura: Number(altura),
        quantidade: Number(quantidade), observacoes,
        modo_fabricacao: modo, especificacoes_fabricacao: dadosEspecificacoes(),
        justificativa,
      })
      setJustificativa('')
    } catch (error) {
      setErroLocal(error instanceof Error ? error.message : String(error))
    }
  }

  async function carregarCatalogo() {
    setErroLocal('')
    try { setCatalogo(await listarCatalogoComponentes(busca)) }
    catch (error) { setErroLocal(error instanceof Error ? error.message : String(error)) }
  }

  function selecionarProduto(id: string) {
    setProdutoId(id)
    const produto = catalogo.find(item => String(item.id) === id)
    if (!produto) return
    if (produto.unidade) setUnidade(produto.unidade)
  }

  function editarComponente(componente?: ComponentePecaProducao) {
    setComponenteEditando(componente?.id ?? null)
    setProdutoId(componente ? String(componente.produto_id) : '')
    setComponenteQuantidade(componente ? String(componente.quantidade) : '1')
    setUnidade(componente?.unidade ?? '')
    setComprimentoCorte(componente?.comprimento_corte == null ? '' : String(componente.comprimento_corte))
    setCustoUnitario(
      componente?.origem_custo === 'INFORMADO' ? String(componente.custo_unitario) : '',
    )
    setObservacoesComponente(componente?.observacoes ?? '')
    setJustificativaComponente('')
    setMostrarComposicao(true)
    void carregarCatalogo()
  }

  function salvarComponente() {
    setErroLocal('')
    const dados: DadosComponenteProducao = {
      produto_id: Number(produtoId),
      quantidade: Number(componenteQuantidade),
      unidade,
      comprimento_corte: comprimentoCorte === '' ? null : Number(comprimentoCorte),
      custo_unitario: custoUnitario === '' ? null : Number(custoUnitario),
      observacoes: observacoesComponente,
      justificativa: justificativaComponente,
    }
    if (componenteEditando == null) onAddComponent(dados)
    else onUpdateComponent(componenteEditando, dados)
    setComponenteEditando(null)
    setJustificativaComponente('')
  }

  return <article className="producao-peca">
    <h4>{peca.codigo} · {peca.status} · ficha v{peca.versao_ficha}</h4>
    <p>{peca.modelo || 'Modelo ausente'} · {peca.tecido || 'Tecido ausente'} · {peca.cor || 'Cor ausente'}</p>
    <p>{peca.largura} m × {peca.altura} m · quantidade {peca.quantidade} · {peca.acionamento || 'Acionamento ausente'}</p>
    <p>{manual ? 'Modo manual supervisionado — composição não homologada.' : 'Modo automático — cálculos não homologados permanecem bloqueados.'}</p>
    {peca.conferido_em && <p>Conferida por {peca.conferido_por} em {new Date(peca.conferido_em).toLocaleString('pt-BR')}</p>}
    <label>Modo de fabricação<select value={modo} disabled={!podeEditar}
      onChange={event => setModo(event.target.value as typeof modo)}>
      {modo === 'AUTOMATICA' && <option value="AUTOMATICA">Automática existente</option>}
      <option value="MANUAL_SUPERVISIONADA">Manual supervisionada</option>
    </select></label>
    <label>Ambiente<input maxLength={200} value={ambiente} disabled={!podeEditar} onChange={e => setAmbiente(e.target.value)} /></label>
    <label>Largura (m)<input type="number" min="0.001" step="0.001" value={largura} disabled={!podeEditar || !manual}
      onChange={e => setLargura(e.target.value)} /></label>
    <label>Altura (m)<input type="number" min="0.001" step="0.001" value={altura} disabled={!podeEditar || !manual}
      onChange={e => setAltura(e.target.value)} /></label>
    <label>Quantidade<input type="number" min="0.001" step="0.001" value={quantidade} disabled={!podeEditar || !manual}
      onChange={e => setQuantidade(e.target.value)} /></label>
    <label>Especificações de fabricação (JSON)<textarea value={especificacoes}
      disabled={!podeEditar || !manual} onChange={e => setEspecificacoes(e.target.value)} /></label>
    <label>Observações<textarea maxLength={5000} value={observacoes} disabled={!podeEditar} onChange={e => setObservacoes(e.target.value)} /></label>
    {manual && <p>Dados e componentes são técnicos e não alteram orçamento nem pedido. A composição não constitui BOM industrial validada.</p>}
    {podeEditar && <label>Justificativa da alteração<input maxLength={1000} value={justificativa}
      onChange={e => setJustificativa(e.target.value)} /></label>}
    {erroLocal && <p className="api-message error" role="alert">{erroLocal}</p>}
    {!liberada && <button type="button" className="secondary-button"
      disabled={!podeEditar || justificativa.trim().length < 5}
      onClick={salvarFicha}>Salvar ficha / nova versão</button>}
    {!liberada && manual && <button type="button" className="secondary-button"
      disabled={!podeEditar || peca.conferido_em != null || justificativa.trim().length < 5}
      onClick={() => { onReview(justificativa); setJustificativa('') }}>
      Conferir tecnicamente esta peça</button>}
    {manual && <section className="producao-composicao">
      <h5>Composição manual supervisionada — não homologada</h5>
      {peca.componentes.map(componente => <div className="producao-componente" key={componente.id}>
        <span>{componente.descricao} · {componente.quantidade} {componente.unidade}
          {componente.comprimento_corte != null ? ` · corte ${componente.comprimento_corte}` : ''}
          {` · custo ${componente.custo_unitario} (${componente.origem_custo})`}</span>
        {!liberada && <button type="button" className="secondary-button" disabled={!podeEditar}
          onClick={() => editarComponente(componente)}>Substituir / editar</button>}
        {!liberada && <button type="button" className="secondary-button" disabled={!podeEditar}
          onClick={() => {
            const motivo = window.prompt('Justificativa para remover o componente (mínimo 5 caracteres):')
            if (motivo) onRemoveComponent(componente.id, motivo)
          }}>Remover</button>}
      </div>)}
      {!liberada && <button type="button" className="secondary-button" disabled={!podeEditar}
        onClick={() => editarComponente()}>Adicionar componente</button>}
      {mostrarComposicao && !liberada && <div>
        <label>Buscar no catálogo da empresa
          <input value={busca} onChange={event => setBusca(event.target.value)} />
        </label>
        <button type="button" className="secondary-button" disabled={ocupado} onClick={() => void carregarCatalogo()}>
          Buscar produtos ativos</button>
        <label>Produto<select value={produtoId} onChange={event => selecionarProduto(event.target.value)}>
          <option value="">Selecione</option>
          {catalogo.map(produto => <option value={produto.id} key={produto.id}>
            {produto.codigo_interno ? `${produto.codigo_interno} · ` : ''}{produto.descricao} (#{produto.id})
          </option>)}
        </select></label>
        {catalogo.find(item => String(item.id) === produtoId)?.custo_unitario != null
          && <p>Custo atual do catálogo: {catalogo.find(item => String(item.id) === produtoId)?.custo_unitario}</p>}
        <label>Quantidade<input type="number" min="0.001" step="0.001" value={componenteQuantidade}
          onChange={event => setComponenteQuantidade(event.target.value)} /></label>
        <label>Unidade<input maxLength={50} value={unidade} onChange={event => setUnidade(event.target.value)} /></label>
        <label>Comprimento de corte (opcional)<input type="number" min="0.001" step="0.001"
          value={comprimentoCorte} onChange={event => setComprimentoCorte(event.target.value)} /></label>
        <label>Custo unitário (vazio usa custo cadastrado)<input type="number" min="0" step="0.0001"
          value={custoUnitario} onChange={event => setCustoUnitario(event.target.value)} /></label>
        <label>Observações do componente<textarea value={observacoesComponente}
          onChange={event => setObservacoesComponente(event.target.value)} /></label>
        <label>Justificativa<input maxLength={1000} value={justificativaComponente}
          onChange={event => setJustificativaComponente(event.target.value)} /></label>
        <button type="button" className="primary-button"
          disabled={!podeEditar || !produtoId || !unidade.trim() || justificativaComponente.trim().length < 5}
          onClick={salvarComponente}>{componenteEditando == null ? 'Incluir componente' : 'Salvar substituição'}</button>
        <button type="button" className="secondary-button"
          onClick={() => { setMostrarComposicao(false); setComponenteEditando(null) }}>Cancelar</button>
      </div>}
    </section>}
    {!!peca.revisoes.length && <details><summary>Histórico de versões da ficha</summary>
      <ol>{peca.revisoes.map(revisao => <li key={revisao.versao}>
        v{revisao.versao} · {revisao.usuario} · {new Date(revisao.criado_em).toLocaleString('pt-BR')}
        {' · '}{revisao.justificativa}
        <details><summary>Ver dados antes e depois</summary>
          <pre>{JSON.stringify({ antes: revisao.antes, depois: revisao.depois }, null, 2)}</pre>
        </details>
      </li>)}</ol></details>}
    {liberada && <>
      <button type="button" className="secondary-button" disabled={ocupado || !autorizado} onClick={onLabel}>Imprimir etiqueta</button>
      {proxima && <button type="button" className="primary-button" disabled={ocupado || !permitida || !autorizado} onClick={onAdvance}>Avançar para {proxima}</button>}
    </>}
    {peca.historico.length > 0 && <ul>{peca.historico.map((h, i) =>
      <li key={i}>{h.de} → {h.para} · {h.usuario} · {new Date(h.em).toLocaleString('pt-BR')}</li>)}</ul>}
  </article>
}
