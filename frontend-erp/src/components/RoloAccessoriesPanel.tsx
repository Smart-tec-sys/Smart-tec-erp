import { useEffect, useState } from 'react'
import { getRoloAccessories, type RoloAccessory, type RoloRequest } from '../services/api'
import { parseDecimal, type BudgetProduct, type CommercialProfile } from '../types/budget'
import { normalizeRoloDrive } from '../types/rolo'
import { technicalSimulationError } from '../utils/technicalSimulation'

type Group = { ambiente: string; entradas: RoloRequest[]; incompleto: boolean }
type Result = { ambiente: string; acessorios: RoloAccessory[]; error?: string }
type Props = {
  products: BudgetProduct[]
  profile: CommercialProfile
  onAdd: (acessorio: RoloAccessory, ambiente: string) => void
}

export function RoloAccessoriesPanel({ products, profile, onAdd }: Props) {
  const groups = new Map<string, Group>()
  for (const product of products) {
    if (!product.roloKind || normalizeRoloDrive(product.acionamento ?? (product.roloKind === 'MOTORIZADA' ? 'motorizado' : 'manual')) !== 'motorizado') continue
    const ambiente = product.environment.trim()
    const name = ambiente.toLowerCase()
    const group = groups.get(name) ?? { ambiente, entradas: [], incompleto: false }
    if (!ambiente || !product.productId || !product.motorProdutoId || parseDecimal(product.width) <= 0 ||
        parseDecimal(product.height) <= 0 || !Number.isInteger(product.quantity) || product.quantity <= 0) {
      group.incompleto = true
    } else {
      group.entradas.push({ produto_id: product.productId, largura: parseDecimal(product.width),
        altura: parseDecimal(product.height), quantidade: product.quantity, perfil_comercial: profile,
        desconto: product.discount, cor: product.color || undefined, acionamento: 'motorizado',
        motor_produto_id: product.motorProdutoId, kit_produto_id: product.kitProdutoId,
        incluir_kit_instalacao: product.incluirKitInstalacao ?? false })
    }
    groups.set(name, group)
  }
  const key = JSON.stringify([...groups.values()])
  const [state, setState] = useState<{ key: string; results: Result[] }>({ key: '', results: [] })
  useEffect(() => {
    let cancelled = false
    const parsed = JSON.parse(key) as Group[]
    void Promise.all(parsed.map(async group => {
      if (group.incompleto) return { ambiente: group.ambiente, acessorios: [], error: 'Informe ambiente, medidas, motor em todas as persianas motorizadas.' }
      try {
        return { ambiente: group.ambiente, acessorios: await getRoloAccessories(group.entradas) }
      } catch (error) {
        return { ambiente: group.ambiente, acessorios: [], error: technicalSimulationError(error) }
      }
    })).then(results => { if (!cancelled) setState({ key, results }) })
    return () => { cancelled = true }
  }, [key])

  if (!groups.size) return null
  return <section className="rolo-accessories-panel">
    <strong>Controles e interruptores opcionais</strong>
    <p>Adicione por unidade. Cada acessório atende todas as Rolôs motorizadas do ambiente; nenhum é incluído automaticamente.</p>
    {state.key !== key ? <p>Consultando compatibilidade…</p> : state.results.map(group =>
      <div key={group.ambiente.toLowerCase()}>
        <strong>{group.ambiente || 'Ambiente não informado'}</strong>
        {group.error ? <p role="status">{group.error}</p> : !group.acessorios.length
          ? <p>Nenhum acessório compatível configurado para todas as persianas deste ambiente.</p>
          : <label className="field"><span>Adicionar acessório</span>
            <select aria-label={`Adicionar acessório em ${group.ambiente}`} value="" onChange={event => {
              const acessorio = group.acessorios.find(item => item.produto_id === Number(event.target.value))
              if (acessorio) onAdd(acessorio, group.ambiente)
            }}>
              <option value="">Selecione</option>
              {group.acessorios.map(item => <option key={item.produto_id} value={item.produto_id}>
                {item.nome}
              </option>)}
            </select></label>}
      </div>)}
  </section>
}
