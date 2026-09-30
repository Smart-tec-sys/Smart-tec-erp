import { useEffect } from 'react'
import { simulateDoubleVision } from '../services/api'
import { formatCurrency, parseDecimal, type BudgetProduct, type CommercialType } from '../types/budget'
import { doubleVisionKind, doubleVisionKey, type DoubleVisionState } from '../types/double_vision'

type Props = { product: BudgetProduct; profile: CommercialType; onResult: (id: number, state: DoubleVisionState) => void }

export function DoubleVisionSimulation({ product, profile, onResult }: Props) {
  const key = doubleVisionKey(product, profile), id = product.id, kind = product.doubleVisionKind
  useEffect(() => {
    if (kind === 'MANUAL') {
      let cancelled = false
      const [produto_id, width, height, quantidade, desconto, commercial] = JSON.parse(key) as [number, string, string, number, number, CommercialType]
      const timer = setTimeout(() => {
        void simulateDoubleVision({ produto_id, largura: parseDecimal(width), altura: parseDecimal(height), quantidade, desconto, perfil_comercial: profile === 'Decorador' ? 'DECORADOR' : profile === 'Varejo' ? 'VAREJO' : 'CONSUMIDOR_FINAL', com_bando: false, tem_validacao_tecido_fornecedor: false })
          .then(result => { if (!cancelled) onResult(id, { key, result }) })
          .catch(error => { if (!cancelled) onResult(id, { key, error: error instanceof Error ? error.message : String(error) }) })
      }, 350)
      return () => { cancelled = true; clearTimeout(timer) }
    }
  }, [key, id, kind, onResult, profile])

  if (!kind) return null

  if (kind === 'MOTORIZADA') {
    return (
      <div className="api-message error" role="alert">
        Double Vision motorizada: cálculo técnico indisponível. Salvamento bloqueado; nenhum motor genérico será utilizado.
      </div>
    )
  }

  const state = product.doubleVision, current = state?.key === key, r = current && !state?.error ? state?.result : undefined
  const show = (obj: Record<string, unknown>, field: string) => {
    const value = obj?.[field]
    return value === null || value === undefined ? 'Pendente' : typeof value === 'number' ? value.toLocaleString('pt-BR', { maximumFractionDigits: 4 }) : Array.isArray(value) ? value.map(v => typeof v === 'number' ? v.toLocaleString('pt-BR', { maximumFractionDigits: 4 }) : JSON.stringify(v)).join(' · ') : String(value)
  }
  const showNested = (obj: Record<string, unknown>, path: string) => {
    const parts = path.split('.')
    let current: unknown = obj
    for (const part of parts) {
      if (current && typeof current === 'object' && part in current) {
        current = (current as Record<string, unknown>)[part]
      } else {
        return 'Pendente'
      }
    }
    return current === null || current === undefined ? 'Pendente' : typeof current === 'number' ? current.toLocaleString('pt-BR', { maximumFractionDigits: 4 }) : String(current)
  }

  return (
    <section className="api-message" aria-live="polite">
      <strong>Double Vision — simulação técnica</strong>
      <p>Custo técnico: indisponível nesta fase. Resultado recalculado; não é histórico de fabricação.</p>
      {!current && <p>Calculando… Totais ainda não confirmados; aguarde antes de salvar.</p>}
      {current && state?.error && (
        <p role="alert">Não foi possível simular. Revise as medidas ou a conexão. Dados preservados; salvamento bloqueado. {state.error}</p>
      )}
      {r && (
        <>
          <p>{r.quantidade_pecas} peça(s) · Área total: {Number(r.area_total).toLocaleString('pt-BR')} m²</p>
          <p>Bitola selecionada: <strong>{r.bitola_tecnica}</strong> · Estado: {r.estado_validacao}{r.requer_validacao_tecido_fornecedor ? ' ⚠ Requer validação tecido/fornecedor' : ''}</p>
          <p>Custo cadastrado do produto: {r.custo_cadastrado === null ? 'indisponível' : formatCurrency(Number(r.custo_cadastrado))}. Preço comercial unitário: {r.preco_disponivel ? formatCurrency(Number(r.preco_unitario)) : 'indisponível'} · Subtotal: {formatCurrency(Number(r.subtotal))}</p>
          <p>Origem do preço: {r.origem_preco}. {r.aviso}</p>
          <dl>
            <dt>Componentes técnicos</dt>
            <dd>
              Tubo: {showNested(r.componentes_tecnicos, 'tubo.codigo')} ({showNested(r.componentes_tecnicos, 'tubo.diametro')}) · {showNested(r.componentes_tecnicos, 'tubo.quantidade_ml')} ml<br/>
              Tecido: {showNested(r.componentes_tecnicos, 'tecido.quantidade_m2')} m² ({showNested(r.componentes_tecnicos, 'tecido.regra')}) · Camada dupla: {showNested(r.componentes_tecnicos, 'tecido.consumo_camada_dupla') ? 'Sim' : 'Não'}<br/>
              Barra niveladora: {showNested(r.componentes_tecnicos, 'barra_niveladora.aplicavel') ? showNested(r.componentes_tecnicos, 'barra_niveladora.quantidade_ml') + ' ml' : 'Não aplicável (com bandô)'}<br/>
              Bandô: {r.componentes_tecnicos && 'bando' in r.componentes_tecnicos && r.componentes_tecnicos.bando ? (r.componentes_tecnicos.bando as Record<string, unknown>)['aplicavel'] === true ? showNested(r.componentes_tecnicos, 'bando.quantidade_ml') + ' ml' : 'Pendente' : 'não selecionado'}<br/>
              Corrente: {showNested(r.componentes_tecnicos, 'corrente.quantidade_ml')} ml ({showNested(r.componentes_tecnicos, 'corrente.regra')})<br/>
              Emenda corrente: {showNested(r.componentes_tecnicos, 'emenda_corrente.quantidade_un')} un<br/>
              Pêndulo: {showNested(r.componentes_tecnicos, 'pendulo.quantidade_un')} un<br/>
              Eixo base: {showNested(r.componentes_tecnicos, 'eixo_base.quantidade_ml')} ml<br/>
              Base cunha: {showNested(r.componentes_tecnicos, 'base_cunha.quantidade_ml')} ml<br/>
              Tampa eixo: {showNested(r.componentes_tecnicos, 'tampa_eixo.quantidade_un')} un<br/>
              Tampa base: {showNested(r.componentes_tecnicos, 'tampa_base.quantidade_un')} un<br/>
              Clips/Suportes: {show(r.componentes_tecnicos.clips, 'quantidade_un')} un ({showNested(r.componentes_tecnicos, 'clips.regra')})<br/>
              Espaguete: {showNested(r.componentes_tecnicos, 'espaguete.quantidade_ml')} ml<br/>
              Fita plástica: {showNested(r.componentes_tecnicos, 'fita_plastica.quantidade_ml')} ml<br/>
              Tampa bandô: {r.componentes_tecnicos && 'tampa_bando' in r.componentes_tecnicos && r.componentes_tecnicos.tampa_bando ? showNested(r.componentes_tecnicos, 'tampa_bando.quantidade_un') + ' un' : 'não selecionado'}
            </dd>
          </dl>
          <p>Limites: padrão ≤ {r.largura_maxima_padrao_m}m · excepcional ≤ {r.largura_maxima_excepcional_m}m (requer validação tecido/fornecedor)</p>
          {r.alertas.map((alert, index) => <p key={index} role="status">Aviso: {alert}</p>)}
          <details>
            <summary>Resultado completo do motor (por peça)</summary>
            <pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{JSON.stringify(r.fabricacao_por_peca, null, 2)}</pre>
          </details>
        </>
      )}
    </section>
  )
}