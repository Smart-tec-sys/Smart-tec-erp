import { useEffect, useState } from 'react'
import {
  avancarPeca, carregarDocumentoProducao, criarProducao, liberarProducao, listarProducao,
  salvarPeca, statusProducao, type OrdemProducao, type PecaProducao,
} from '../services/producao'
import './producaoPanel.css'
import { producaoV1Enabled } from '../services/producaoFlag'

type Props = { pedidoId: number; statusVenda: string }

export function ProducaoPanel({ pedidoId, statusVenda }: Props) {
  return producaoV1Enabled ? <ProducaoPanelHabilitado pedidoId={pedidoId} statusVenda={statusVenda} /> : null
}

function ProducaoPanelHabilitado({ pedidoId, statusVenda }: Props) {
  const [ordem, setOrdem] = useState<OrdemProducao | null>(null)
  const [carregando, setCarregando] = useState(true)
  const [tentativa, setTentativa] = useState(0)
  const [ocupado, setOcupado] = useState(false)
  const [erro, setErro] = useState('')
  const [confirmado, setConfirmado] = useState(false)
  const [documento, setDocumento] = useState<string | null>(null)
  const permitida = ['ABERTO', 'FATURADO', 'CONCLUIDO'].includes(statusVenda)
  useEffect(() => {
    let cancelado = false
    setCarregando(true); setErro('')
    listarProducao(pedidoId).then(ordens => {
      if (!cancelado) setOrdem(ordens[0] ?? null)
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
  async function visualizar(pecaId?: number) {
    if (!ordem) return
    setOcupado(true); setErro('')
    try { setDocumento(await carregarDocumentoProducao(ordem.id, pecaId)) }
    catch (err) { setErro(err instanceof Error ? err.message : String(err)) }
    finally { setOcupado(false) }
  }
  return <section className="panel producao-panel" aria-label="Produção V1">
    <h2>Produção V1</h2>
    <p>Fabricação independente do faturamento. Não reserva nem baixa estoque.</p>
    <button type="button" className="secondary-button" disabled={ocupado || carregando}
      onClick={() => setTentativa(value => value + 1)}>Recarregar produção</button>
    {erro && <p className="api-message error" role="alert">{erro}</p>}
    {carregando ? <p role="status">Carregando produção...</p> : !ordem ? <>
      <label><input type="checkbox" checked={confirmado} onChange={e => setConfirmado(e.target.checked)} />
        Confirmo explicitamente a fabricação desta venda. Meu usuário, data e hora serão registrados.</label>
      <button type="button" className="primary-button" disabled={!confirmado || !permitida || ocupado || Boolean(erro)}
        onClick={() => void executar(() => criarProducao(pedidoId))}>Criar ordem de produção</button>
    </> : <>
      <h3>OP-{String(ordem.id).padStart(6, '0')} · {ordem.status}</h3>
      <p>Confirmada por {ordem.confirmado_por} em {new Date(ordem.confirmado_em).toLocaleString('pt-BR')}</p>
      <p>{ordem.liberado_em ? `Liberada por ${ordem.liberado_por} em ${new Date(ordem.liberado_em).toLocaleString('pt-BR')}` : 'Não liberada para fabricação'}</p>
      <button type="button" className="secondary-button" disabled={ocupado} onClick={() => void visualizar()}>Visualizar / imprimir ficha</button>
      {ordem.pendencias.length > 0 && <div role="status"><h4>Liberação bloqueada</h4>
        <ul>{ordem.pendencias.map((p, i) => <li key={i}>{p}</li>)}</ul></div>}
      {!ordem.liberado_em && <button type="button" className="primary-button"
        disabled={ocupado || !permitida || ordem.pendencias.length > 0}
        onClick={() => {
          if (window.confirm('Confirma a liberação das peças e dos cálculos para fabricação? Sua identidade e horário serão registrados.'))
            void executar(() => liberarProducao(ordem.id))
        }}>Liberar fabricação</button>}
      {ordem.pecas.map(peca => <FichaPeca key={`${peca.id}-${peca.ambiente}-${peca.observacoes}`}
        peca={peca} liberada={Boolean(ordem.liberado_em)} ocupado={ocupado} permitida={permitida}
        onSave={(ambiente, observacoes) => void executar(() => salvarPeca(ordem.id, peca.id, ambiente, observacoes))}
        onAdvance={() => void executar(() => avancarPeca(ordem.id, peca))}
        onLabel={() => void visualizar(peca.id)} />)}
    </>}
    {!permitida && <p role="alert">Venda cancelada ou com situação não suportada. Fabricação bloqueada.</p>}
    {documento && <div className="producao-documento">
      <button type="button" className="secondary-button" onClick={() => setDocumento(null)}>Fechar documento</button>
      <iframe title="Documento de fabricação" srcDoc={documento} sandbox="allow-scripts allow-modals" />
    </div>}
  </section>
}

function FichaPeca({ peca, liberada, ocupado, permitida, onSave, onAdvance, onLabel }: {
  peca: PecaProducao; liberada: boolean; ocupado: boolean; permitida: boolean
  onSave: (ambiente: string, observacoes: string) => void; onAdvance: () => void; onLabel: () => void
}) {
  const [ambiente, setAmbiente] = useState(peca.ambiente)
  const [observacoes, setObservacoes] = useState(peca.observacoes)
  const proxima = statusProducao[statusProducao.indexOf(peca.status) + 1]
  return <article className="producao-peca">
    <h4>{peca.codigo} · {peca.status}</h4>
    <p>{peca.modelo || 'Modelo ausente'} · {peca.tecido || 'Tecido ausente'} · {peca.cor || 'Cor ausente'}</p>
    <p>{peca.largura} m × {peca.altura} m · {peca.acionamento || 'Acionamento ausente'}</p>
    <label>Ambiente<input maxLength={200} value={ambiente} disabled={liberada || ocupado || !permitida} onChange={e => setAmbiente(e.target.value)} /></label>
    <label>Observações<textarea maxLength={5000} value={observacoes} disabled={liberada || ocupado || !permitida} onChange={e => setObservacoes(e.target.value)} /></label>
    {!liberada && <button type="button" className="secondary-button" disabled={ocupado || !permitida}
      onClick={() => onSave(ambiente, observacoes)}>Salvar ficha da peça</button>}
    {liberada && <>
      <button type="button" className="secondary-button" disabled={ocupado} onClick={onLabel}>Etiqueta existente</button>
      {proxima && <button type="button" className="primary-button" disabled={ocupado || !permitida} onClick={onAdvance}>Avançar para {proxima}</button>}
    </>}
    {peca.historico.length > 0 && <ul>{peca.historico.map((h, i) =>
      <li key={i}>{h.de} → {h.para} · {h.usuario} · {new Date(h.em).toLocaleString('pt-BR')}</li>)}</ul>}
  </article>
}
