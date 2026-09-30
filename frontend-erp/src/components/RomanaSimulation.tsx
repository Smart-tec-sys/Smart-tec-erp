import { useEffect } from 'react'
import { simulateRomana } from '../services/api'
import { formatCurrency, parseDecimal, type BudgetProduct, type CommercialType, type CommercialProfile } from '../types/budget'
import { romanaKey, type RomanaState } from '../types/romana'

type Props = { product: BudgetProduct; profile: CommercialType; onResult: (id: number, state: RomanaState) => void }
const profiles: Record<CommercialType, CommercialProfile> = { Decorador: 'DECORADOR', Varejo: 'VAREJO', 'Consumidor final': 'CONSUMIDOR_FINAL' }

export function RomanaSimulation({ product, profile, onResult }: Props) {
  const key = romanaKey(product, profile), id = product.id, kind = product.romanaKind
  useEffect(() => {
    if (kind !== 'MANUAL') return
    let cancelled = false
    const [produto_id, width, height, quantidade, desconto, commercial] = JSON.parse(key) as [number, string, string, number, number, CommercialType]
    const timer = setTimeout(() => {
      void simulateRomana({ produto_id, largura: parseDecimal(width), altura: parseDecimal(height), quantidade, desconto, perfil_comercial: profiles[commercial] })
        .then(result => { if (!cancelled) onResult(id, { key, result }) })
        .catch(error => { if (!cancelled) onResult(id, { key, error: error instanceof Error ? error.message : String(error) }) })
    }, 350)
    return () => { cancelled = true; clearTimeout(timer) }
  }, [key, id, kind, onResult])
  if (!kind) return null
  if (kind === 'MOTORIZADA') return <div className="api-message error" role="alert">Romana motorizada: cálculo técnico indisponível. Salvamento bloqueado; nenhum motor genérico será utilizado.</div>
  const state = product.romana, current = state?.key === key, r = current && !state?.error ? state?.result : undefined
  const f = r?.fabricacao_por_peca
  const show = (name: string) => {
    const value = f?.[name]
    return value === null || value === undefined ? 'Pendente' : typeof value === 'number' ? value.toLocaleString('pt-BR', { maximumFractionDigits: 4 }) : Array.isArray(value) ? value.map(v => typeof v === 'number' ? v.toLocaleString('pt-BR', { maximumFractionDigits: 4 }) : JSON.stringify(v)).join(' · ') : String(value)
  }
  return <section className="api-message" aria-live="polite">
    <strong>Romana manual — simulação técnica</strong>
    <p>Custo técnico: indisponível nesta fase. Resultado recalculado; não é histórico de fabricação.</p>
    {!current && <p>Calculando… Totais ainda não confirmados; aguarde antes de salvar.</p>}
    {current && state?.error && <p role="alert">Não foi possível simular. Revise as medidas ou a conexão. Dados preservados; salvamento bloqueado. {state.error}</p>}
    {r && <>
      <p>{r.quantidade_pecas} peça(s) · Área total: {Number(r.area_total).toLocaleString('pt-BR')} m²</p>
      <p>Custo cadastrado do produto: {r.custo_cadastrado === null ? 'indisponível' : formatCurrency(Number(r.custo_cadastrado))}. Preço comercial unitário: {r.preco_disponivel ? formatCurrency(Number(r.preco_unitario)) : 'indisponível'} · Subtotal: {formatCurrency(Number(r.subtotal))}</p>
      <p>Defaults do motor: {r.defaults_utilizados.tipo_corrente} / {r.defaults_utilizados.tipo_comando}. Fabricação abaixo: <strong>por peça</strong>, sem multiplicação local.</p>
      <dl>
        <dt>Geometria e distribuição</dt><dd>{show('quantidade_gomos')} gomos; primeiro {show('primeiro_gomo_pronto_cm')} cm; intermediários {show('gomos_intermediarios_prontos_cm')} cm; último {show('ultimo_gomo_pronto_cm')} cm.</dd>
        <dt>Varetas</dt><dd>{show('quantidade_varetas')} · largura {show('largura_vareta_cm')} cm · posições {show('posicoes_varetas')}</dd>
        <dt>Cortes e tecido</dt><dd>Primeiro {show('primeiro_gomo_corte_cm')} cm; intermediários {show('intermediarios_corte_cm')} cm; último {show('ultimo_gomo_corte_cm')} cm. Comprimento total: {show('comprimento_total_tecido_cm')} cm.</dd>
        <dt>Passadores, guias e cavaletes</dt><dd>{show('quantidade_total_passadores')} passadores · {show('quantidade_guias_corda')} guias · {show('quantidade_cavaletes')} cavaletes.</dd>
        <dt>Corda</dt><dd>{show('corda_total_m')} m · referência comercial {show('produto_comercial_corda_romana_1mm')}.</dd>
        <dt>Espaguetes</dt><dd>2,5 mm: {show('espaguete_romana_2_5_total_m')} m; base 3 mm: {show('espaguete_base_romana_3mm_total_m')} m.</dd>
        <dt>Corrente e comando</dt><dd>{show('quantidade_correntes')} corrente de {show('medida_corrente_selecionada_m')} m ({show('corrente_pronta_referencia_status')}); {show('quantidade_comando')} comando {show('tipo_comando')}, referência #{show('id_comercial_comando_selecionado')}.</dd>
      </dl>
      {r.alertas.map((alert, index) => <p key={index} role="status">Aviso: {alert}</p>)}
      <details><summary>Resultado completo do motor (por peça)</summary><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{JSON.stringify(f, null, 2)}</pre></details>
    </>}
  </section>
}
