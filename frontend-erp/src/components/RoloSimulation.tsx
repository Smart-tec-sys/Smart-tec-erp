import { useEffect } from 'react'
import { simulateRolo } from '../services/api'
import { formatCurrency, parseDecimal, type BudgetProduct, type CommercialType } from '../types/budget'
import { roloKey, normalizeRoloDrive, type RoloState } from '../types/rolo'

type Props = { product: BudgetProduct; profile: CommercialType; onResult: (id: number, state: RoloState) => void }

export function RoloSimulation({ product, profile, onResult }: Props) {
  const key = roloKey(product, profile), id = product.id, kind = product.roloKind
  useEffect(() => {
    if (kind === 'MOTORIZADA' || kind === 'MANUAL') {
      let cancelled = false
      const [produto_id, width, height, quantidade, desconto, commercial, cor, acionamento] = JSON.parse(key) as [number, string, string, number, number, CommercialType, string, string]
      const timer = setTimeout(() => {
        void simulateRolo({ produto_id, largura: parseDecimal(width), altura: parseDecimal(height), quantidade, desconto, perfil_comercial: profile === 'Decorador' ? 'DECORADOR' : profile === 'Varejo' ? 'VAREJO' : 'CONSUMIDOR_FINAL', cor: cor || undefined, acionamento: normalizeRoloDrive(acionamento) })
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
        Rolô motorizada: cálculo técnico indisponível. Salvamento bloqueado; nenhum motor genérico será utilizado.
      </div>
    )
  }

  const state = product.rolo, current = state?.key === key, r = current && !state?.error ? state?.result : undefined
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
      <strong>Rolô — simulação técnica</strong>
      <p>Custo técnico: indisponível nesta fase. Resultado recalculado; não é histórico de fabricação.</p>
      {!current && <p>Calculando… Totais ainda não confirmados; aguarde antes de salvar.</p>}
      {current && state?.error && (
        <p role="alert">Não foi possível simular. Revise as medidas ou a conexão. Dados preservados; salvamento bloqueado. {state.error}</p>
      )}
      {r && (
        <>
          <p>{r.quantidade_pecas} peça(s) · Área real: {Number(r.area_real_m2).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} m² · Área faturável: {Number(r.area_faturavel_m2).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} m² · Mínimo faturável aplicado: {r.minimo_faturavel_aplicado ? 'Sim' : 'Não'}</p>
          <p>Bitola selecionada: <strong>{r.bitola_tecnica}</strong> · Acionamento: {r.acionamento_permitido}{r.requer_confirmacao_vendedor ? ' ⚠ Requer confirmação do vendedor' : ''}</p>
          <p>Custo cadastrado do produto: {r.custo_cadastrado === null ? 'indisponível' : formatCurrency(Number(r.custo_cadastrado))}. Preço comercial unitário: {r.preco_disponivel ? formatCurrency(Number(r.preco_unitario)) : 'indisponível'} · Subtotal: {formatCurrency(Number(r.subtotal))}</p>
          <p>Origem do preço: {r.origem_preco}. {r.aviso}</p>
          <dl>
            <dt>Componentes técnicos</dt>
            <dd>
              Tubo: {showNested(r.componentes_tecnicos, 'tubo.codigo')} ({showNested(r.componentes_tecnicos, 'tubo.diametro')}) · {showNested(r.componentes_tecnicos, 'tubo.quantidade_ml')} ml<br/>
              Comando: {showNested(r.componentes_tecnicos, 'comando.tipo')} — {showNested(r.componentes_tecnicos, 'comando.observacao')}<br/>
              Tecido: {showNested(r.componentes_tecnicos, 'tecido.quantidade_m2')} m² ({showNested(r.componentes_tecnicos, 'tecido.regra')})<br/>
              Base: {showNested(r.componentes_tecnicos, 'base.quantidade_ml')} ml<br/>
              Corrente: {showNested(r.componentes_tecnicos, 'corrente.quantidade_ml')} ml ({showNested(r.componentes_tecnicos, 'corrente.regra')})<br/>
              Emenda corrente: {showNested(r.componentes_tecnicos, 'emenda_corrente.quantidade_un')} un<br/>
              Tampas: {showNested(r.componentes_tecnicos, 'tampas.quantidade_un')} un<br/>
              Suportes: {showNested(r.componentes_tecnicos, 'suportes.observacao')}<br/>
              Ponteira: {showNested(r.componentes_tecnicos, 'ponteira.observacao')}<br/>
              Bandô/Guias: {showNested(r.componentes_tecnicos, 'bando_guias.aplicavel') ? 'Aplicável' : showNested(r.componentes_tecnicos, 'bando_guias.observacao')}
            </dd>
          </dl>
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