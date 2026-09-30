import { useEffect, useState } from 'react'
import { simulateRomanaTeto } from '../services/api'
import { formatCurrency, parseDecimal, type BudgetProduct, type CommercialType } from '../types/budget'
import { romanaTetoKey, type RomanaTetoState } from '../types/romana_teto'

const ACIONAMENTO_OPCOES = [
  { value: 'MANUAL_BASTAO', label: 'Bastão' },
  { value: 'MANUAL_CORRENTE', label: 'Corrente' },
  { value: 'MOTORIZADA', label: 'Motorizada' },
] as const

const BASTAO_OPCOES = [1.00, 1.25, 1.50, 1.75, 2.00, 2.25]
const CORRENTE_SEM_FIM_OPCOES = [0.75, 1.00, 1.25, 1.50, 1.75, 2.00, 2.50, 3.00, 4.00]
const LADO_COMANDO_OPCOES = ['ESQUERDA', 'DIREITA'] as const

type Props = { product: BudgetProduct; profile: CommercialType; onResult: (id: number, state: RomanaTetoState) => void }

export function RomanaTetoSimulation({ product, profile, onResult }: Props) {
  const key = romanaTetoKey(product, profile)
  const id = product.id
  const kind = product.romanaTetoKind
  const [acionamento, setAcionamento] = useState<'MANUAL_BASTAO' | 'MANUAL_CORRENTE' | 'MOTORIZADA'>('MANUAL_BASTAO')
  const [ladoComando, setLadoComando] = useState<'ESQUERDA' | 'DIREITA'>('ESQUERDA')
  const [comprimentoBastao, setComprimentoBastao] = useState<string>('1.50')
  const [comprimentoCorrenteSemFim, setComprimentoCorrenteSemFim] = useState<string>('1.50')

  useEffect(() => {
    if (kind !== 'MANUAL_BASTAO' && kind !== 'MANUAL_CORRENTE' && kind !== 'MOTORIZADA') return
    let cancelled = false
    const [produto_id, width, height, quantidade, desconto, commercial, acionamentoStr, ladoComandoStr, bastaoStr, correnteStr, corStr] = JSON.parse(key) as [number, string, string, number, number, CommercialType, string, string, string, string, string]
    if (acionamentoStr) setAcionamento(acionamentoStr as 'MANUAL_BASTAO' | 'MANUAL_CORRENTE' | 'MOTORIZADA')
    if (ladoComandoStr) setLadoComando(ladoComandoStr as 'ESQUERDA' | 'DIREITA')
    if (bastaoStr) setComprimentoBastao(bastaoStr)
    if (correnteStr) setComprimentoCorrenteSemFim(correnteStr)

    const timer = setTimeout(() => {
      void simulateRomanaTeto({
        produto_id,
        largura_modulo_m: parseDecimal(width),
        comprimento_avanco_m: parseDecimal(height),
        quantidade_modulos: quantidade,
        desconto,
        perfil_comercial: profile === 'Decorador' ? 'DECORADOR' : profile === 'Varejo' ? 'VAREJO' : 'CONSUMIDOR_FINAL',
        acionamento,
        lado_comando: acionamento === 'MANUAL_CORRENTE' ? ladoComando : undefined,
        comprimento_bastao_m: acionamento === 'MANUAL_BASTAO' ? parseDecimal(comprimentoBastao) : undefined,
        comprimento_corrente_sem_fim_m: acionamento === 'MANUAL_CORRENTE' ? parseDecimal(comprimentoCorrenteSemFim) : undefined,
        cor: corStr || undefined,
      })
        .then(result => { if (!cancelled) onResult(id, { key, result }) })
        .catch(error => { if (!cancelled) onResult(id, { key, error: error instanceof Error ? error.message : String(error) }) })
    }, 350)
    return () => { cancelled = true; clearTimeout(timer) }
  }, [key, id, kind, onResult, profile, acionamento, ladoComando, comprimentoBastao, comprimentoCorrenteSemFim])

  if (!kind) return null

  if (kind === 'MOTORIZADA') {
    return (
      <div className="api-message error" role="alert">
        Romana de teto motorizada: cálculo técnico indisponível. Salvamento bloqueado; nenhum motor genérico será utilizado.
      </div>
    )
  }

  const state = product.romanaTeto
  const current = state?.key === key
  const r = current && !state?.error ? state?.result : undefined

  const show = (obj: Record<string, unknown>, field: string) => {
    const value = obj?.[field]
    return value === null || value === undefined ? 'Pendente' : typeof value === 'number' ? value.toLocaleString('pt-BR', { maximumFractionDigits: 4 }) : Array.isArray(value) ? value.map(v => typeof v === 'number' ? v.toLocaleString('pt-BR', { maximumFractionDigits: 4 }) : JSON.stringify(v)).join(' · ') : String(value)
  }

  const fab = r?.fabricacao_por_modulo as Record<string, unknown> | undefined

  return (
    <section className="api-message" aria-live="polite">
      <div className="form-grid" style={{ marginBottom: '1rem' }}>
        <label className="field">
          <span>Acionamento</span>
          <select
            value={acionamento}
            onChange={e => setAcionamento(e.target.value as 'MANUAL_BASTAO' | 'MANUAL_CORRENTE' | 'MOTORIZADA')}
            disabled={current}
          >
            {ACIONAMENTO_OPCOES.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
          </select>
        </label>

        {acionamento === 'MANUAL_BASTAO' && (
          <label className="field">
            <span>Comprimento do bastão (m)</span>
            <select value={comprimentoBastao} onChange={e => setComprimentoBastao(e.target.value)} disabled={current}>
              {BASTAO_OPCOES.map(v => <option key={v} value={v.toFixed(2)}>{v.toFixed(2)}</option>)}
            </select>
          </label>
        )}

        {acionamento === 'MANUAL_CORRENTE' && (
          <>
            <label className="field">
              <span>Lado de comando</span>
              <select value={ladoComando} onChange={e => setLadoComando(e.target.value as 'ESQUERDA' | 'DIREITA')} disabled={current}>
                {LADO_COMANDO_OPCOES.map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </label>
            <label className="field">
              <span>Comprimento da corrente sem fim (m)</span>
              <select value={comprimentoCorrenteSemFim} onChange={e => setComprimentoCorrenteSemFim(e.target.value)} disabled={current}>
                {CORRENTE_SEM_FIM_OPCOES.map(v => <option key={v} value={v.toFixed(2)}>{v.toFixed(2)}</option>)}
              </select>
            </label>
          </>
        )}

        {acionamento === 'MOTORIZADA' && (
          <p className="api-message" style={{ margin: 0 }}>Motorizada: sem lado de comando, bastão ou corrente sem fim.</p>
        )}
      </div>

      <strong>Romana de teto — simulação técnica</strong>
      <p>Custo técnico: indisponível nesta fase. Resultado recalculado; não é histórico de fabricação.</p>
      {!current && <p>Calculando… Totais ainda não confirmados; aguarde antes de salvar.</p>}
      {current && state?.error && (
        <p role="alert">Não foi possível simular. Revise as medidas ou a conexão. Dados preservados; salvamento bloqueado. {state.error}</p>
      )}
      {r && (
        <>
          <p>{r.quantidade_modulos} módulo(s) · Área real: {Number(r.area_real_m2).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} m² · Área faturável: {Number(r.area_faturavel_m2).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} m² · Mínimo faturável aplicado: {r.minimo_faturavel_aplicado ? 'Sim' : 'Não'}</p>
          <p>Custo cadastrado do produto: {r.custo_cadastrado === null ? 'indisponível' : formatCurrency(Number(r.custo_cadastrado))}. Preço comercial unitário: {r.preco_disponivel ? formatCurrency(Number(r.preco_unitario)) : 'indisponível'} · Subtotal: {formatCurrency(Number(r.subtotal))}</p>
          <p>Origem do preço: {r.origem_preco}. {r.aviso}</p>

          <dl>
            <dt>Geometria e distribuição</dt>
            <dd>{show(fab || {}, 'quantidade_gomos')} gomos · passo {show(fab || {}, 'passo_gomo_cm')} cm</dd>
            <dt>Varetas</dt>
            <dd>{show(fab || {}, 'quantidade_varetas')} · largura {show(fab || {}, 'comprimento_vareta_m')} m</dd>
            <dt>Tecido</dt>
            <dd>Largura {show(fab || {}, 'largura_tecido_m')} m · Comprimento {show(fab || {}, 'comprimento_tecido_m')} m · Área técnica {show(fab || {}, 'area_tecido_m2')} m²</dd>
            <dt>Deslizantes</dt>
            <dd>{show(fab || {}, 'quantidade_deslizantes')}</dd>
            <dt>Trilhos</dt>
            <dd>{show(fab || {}, 'tipo_trilho')} · Base: {show(fab || {}, 'quantidade_trilhos_base')} · Comprimento: {show(fab || {}, 'comprimento_trilho_m')} m</dd>
            <dt>Bases cônicas</dt>
            <dd>{show(fab || {}, 'quantidade_bases_conicas')} · Comprimento: {show(fab || {}, 'comprimento_base_conica_m')} m</dd>
            <dt>Tampas de base</dt>
            <dd>{show(fab || {}, 'quantidade_tampas_base')}</dd>
            <dt>Guias de corda</dt>
            <dd>{show(fab || {}, 'quantidade_guias_corda')}</dd>
            <dt>Argolas</dt>
            <dd>{show(fab || {}, 'quantidade_argolas')}</dd>
            <dt>Espaguete 2,5</dt>
            <dd>{show(fab || {}, 'quantidade_espaguete_2_5')} un · {show(fab || {}, 'metragem_total_espaguete_2_5')} m</dd>
            <dt>Espaguete 3,0</dt>
            <dd>{show(fab || {}, 'quantidade_espaguete_3')} un · {show(fab || {}, 'metragem_total_espaguete_3')} m</dd>
            <dt>Tampas de vareta</dt>
            <dd>{show(fab || {}, 'quantidade_tampas_vareta')}</dd>
            <dt>Puxadores</dt>
            <dd>{show(fab || {}, 'quantidade_puxadores')}</dd>

            {acionamento === 'MANUAL_BASTAO' && (
              <>
                <dt>Bastão</dt>
                <dd>{show(fab || {}, 'quantidade_bastoes')} · Comprimento: {show(fab || {}, 'comprimento_bastao_m')} m</dd>
                <dt>Mecanismo manual</dt>
                <dd>{show(fab || {}, 'tipo_acionamento_manual')} · Ref: {show(fab || {}, 'referencia_mecanismo_manual')}</dd>
              </>
            )}

            {acionamento === 'MANUAL_CORRENTE' && (
              <>
                <dt>Lado de comando</dt>
                <dd>{show(fab || {}, 'lado_comando')} · Trilho: {show(fab || {}, 'trilho_comando')}</dd>
                <dt>Carrinhos Master</dt>
                <dd>{show(fab || {}, 'quantidade_carrinho_master')}</dd>
                <dt>Tampas de cabeceira</dt>
                <dd>{show(fab || {}, 'quantidade_tampas_cabeceira_teto')}</dd>
                <dt>Corrente de tração</dt>
                <dd>{show(fab || {}, 'metragem_corrente_tracao_m')} m</dd>
                <dt>Corrente sem fim Bola 10</dt>
                <dd>{show(fab || {}, 'quantidade_correntes_sem_fim')} · Comprimento: {show(fab || {}, 'comprimento_corrente_sem_fim_m')} m</dd>
                <dt>Pêndulo</dt>
                <dd>{show(fab || {}, 'quantidade_pendulos')}</dd>
                <dt>Comando teto</dt>
                <dd>{show(fab || {}, 'referencia_comando_teto')}</dd>
              </>
            )}

            {acionamento === 'MOTORIZADA' && (
              <>
                <dt>Motores</dt>
                <dd>{show(fab || {}, 'quantidade_motores')} · Modelo: {show(fab || {}, 'motor_modelo')} · Torque: {show(fab || {}, 'motor_torque_nm')} · Tensão: {show(fab || {}, 'motor_tensao')}</dd>
                <dt>Status do motor</dt>
                <dd>{show(fab || {}, 'status_motor')}</dd>
              </>
            )}

            <dt>Avaliação trilho central</dt>
            <dd>{fab && 'avaliacao_trilho_central' in fab ? (fab.avaliacao_trilho_central ? 'Sim' : 'Não') : 'Pendente'}</dd>
            <dt>Terceiro trilho confirmado</dt>
            <dd>{fab && 'terceiro_trilho_confirmado' in fab ? (fab.terceiro_trilho_confirmado === true ? 'Sim' : fab.terceiro_trilho_confirmado === false ? 'Não' : 'Pendente') : 'Pendente'}</dd>
          </dl>

          {r.alertas.map((alert, index) => <p key={index} role="status">Aviso: {alert}</p>)}
          <details>
            <summary>Resultado completo do motor (por módulo)</summary>
            <pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{JSON.stringify(fab, null, 2)}</pre>
          </details>
        </>
      )}
    </section>
  )
}