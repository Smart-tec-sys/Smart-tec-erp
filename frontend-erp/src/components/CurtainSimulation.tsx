import { CurtainComponents } from './CurtainComponents'
import { curtainComponentLines } from '../utils/curtainComponents'
import { DEFAULT_CURTAIN, canonicalFabricSupplier, getFabricSupplier, getFabricCollection, getFabricVariant, getFabricDisplayName, normalizeCurtainFabric, getFabricColorLabel, curtainFabricCatalog, fabricVariants, fabricState } from '../utils/curtainFabricCatalog'
import { technicalSimulationError } from '../utils/technicalSimulation'
import { useEffect, useRef } from 'react'
import { simulateCurtain } from '../services/api'
import type { ApiProduct, BudgetProduct, CurtainState } from '../types/budget'
import { normalizeSearch, parseDecimal, curtainKey, formatCurrency } from '../types/budget'

type Props = {
  profile: 'Decorador' | 'Varejo' | 'Consumidor final'
  product: BudgetProduct
  catalog: ApiProduct[]
  onResult: (id: number, state: CurtainState) => void
}

function isCurtain(product: BudgetProduct) {
  const model = normalizeSearch(product.modelTechnical ?? '')
  const group = normalizeSearch(product.groupTechnical ?? '')

  return model === 'CORTINA' && group === 'TECIDOS_CORTINA'
}

export function CurtainSimulation({ product, catalog, profile, onResult }: Props) {
  const applicable = isCurtain(product)
  const state = product.curtain

  useEffect(() => {
    if (!applicable || state) return
    onResult(product.id, { ...DEFAULT_CURTAIN })
  }, [applicable, state, product.id, onResult])

  const current = state ?? DEFAULT_CURTAIN

  const fabricQuery = normalizeSearch(current.tecido)

  const fabricOptions = catalog
    .filter((p) => {
      const text = normalizeSearch([
        p.nome,
        p.grupo_produto,
        p.grupo_tecnico,
        p.material_tecido,
        p.descricao,
      ].filter(Boolean).join(' '))

      return (
        text.includes('TECIDO') ||
        text.includes('VOIL') ||
        text.includes('GAZE') ||
        text.includes('LINHO')
      )
    })
    .filter((p) => {
      if (!fabricQuery) return true

      return normalizeSearch([
        p.nome,
        p.material_tecido,
        p.descricao,
      ].filter(Boolean).join(' ')).includes(fabricQuery)
    })
    .slice(0, 12)

  


  const resolvedProductId = current.tecidoProdutoId ?? null
  const latest = useRef(current)
  latest.current = current

  const parseMeasure = (value: unknown) => {
    const parsed = parseDecimal(String(value ?? ''))
    if (parsed > 0) return parsed

    const fallback = Number(
      String(value ?? '')
        .trim()
        .replace(',', '.')
    )

    return Number.isFinite(fallback) ? fallback : 0
  }

  const width = parseMeasure(product.width)
  const height = parseMeasure(product.height)
  const quantity = Math.max(1, product.quantity || 1)

  useEffect(() => {
    if (!applicable || !state || state.componentes !== undefined) return
    // Carry explicit legacy selections once. Subsequent model/measure changes never replace user quantities.
    onResult(product.id, { ...state, componentes: curtainComponentLines(state, width), simulationKey: undefined, result: undefined, error: undefined })
  }, [applicable, state, product.id, width, onResult])

  const commercialProfile =
    profile === 'Decorador'
      ? 'DECORADOR'
      : profile === 'Consumidor final'
        ? 'CONSUMIDOR_FINAL'
        : 'VAREJO'

  const simulationKey = curtainKey({ ...product, curtain: current }, profile)

  useEffect(() => {
    if (
      !applicable ||
      !resolvedProductId ||
      width <= 0 ||
      height <= 0
    ) {
      return
    }

    let cancelled = false

    const timer = window.setTimeout(() => {
      void simulateCurtain({
        tecido_produto_id: resolvedProductId!,
        componentes: curtainComponentLines(current, width).filter(l => l.produto_id).map(l => ({ produto_id: l.produto_id!, quantidade: l.quantidade })),
        forro_produto_id: current.possuiForro ? current.forroProdutoId : undefined,
        largura_forro: current.possuiForro ? current.larguraForro : undefined,
        trilho_produto_id: current.trilhoProdutoId,
        rodizio_produto_id: current.rodizioProdutoId,
        gancho_produto_id: current.ganchoProdutoId,
        botao_produto_id: current.botaoProdutoId,
        entretela_produto_id: current.entretelaProdutoId,
        largura: width,
        altura: height,
        quantidade: quantity,
        perfil_comercial: commercialProfile,
        desconto: product.discount,
        fator: current.fator,
        largura_tecido: current.larguraTecido,
        modelo_prega: current.modeloPrega,
        possui_forro: current.possuiForro,
        tipo_forro: current.tipoForro || undefined,
        trilho_linha: current.trilhoLinha,
        trilho_modelo: current.trilhoModelo || undefined,
        rodizio_tipo:
          current.modeloPrega === 'WAVE' &&
          current.sistemaWave === 'BOTAO'
            ? 'BOTAO'
            : current.rodizioTipo,
        cabeca_cm: current.cabecaCm,
        barra_cm: current.barraCm,
        barra_dupla: current.barraDupla,
        usa_entretela: current.usaEntretela,
        tipo_entretela: current.tipoEntretela,
        fixacao_cortina: current.fixacaoCortina,
        trilho_com_cordas: current.trilhoComCordas,
        sistema_wave: current.sistemaWave,
        espacamento_botao_cm: current.espacamentoBotaoCm,
        abertura_cortina: current.aberturaCortina,
      } as any)
        .then((result) => {
          if (cancelled) return

          onResult(product.id, {
            ...latest.current,
            simulationKey,
            result,
            error: undefined,
          })
        })
        .catch((error) => {
          if (cancelled) return

          onResult(product.id, {
            ...latest.current,
            simulationKey,
            result: undefined,
            error: technicalSimulationError(error),
          })
        })
    }, 350)

    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [
    simulationKey,
    applicable,
    product.id,
    product.productId,
    resolvedProductId,
    onResult,
  ])

  const update = <K extends keyof CurtainState>(
    key: K,
    value: CurtainState[K]
  ) => {
    onResult(product.id, {
      ...current,
      [key]: value,
      simulationKey: undefined,
      result: undefined,
      error: undefined,
    })
  }

  const simulationCurrent =
    state?.simulationKey === simulationKey

  const result =
    simulationCurrent && !state?.error
      ? state?.result
      : undefined

  const simulationError =
    simulationCurrent
      ? state?.error
      : undefined

  const waiting =
    applicable &&
    Boolean(resolvedProductId) &&
    width > 0 &&
    height > 0 &&
    !result &&
    !simulationError


const fabrics = curtainFabricCatalog(catalog)

  const selectedFabric =
    fabrics.find(
      (fabric) => fabric.id === current.tecidoProdutoId
    ) ?? null

  const normalizedSelection = selectedFabric ? normalizeCurtainFabric(selectedFabric) : null

  const selectedSupplier =
    canonicalFabricSupplier(current.fornecedorTecido) ||
    (normalizedSelection?.supplier ?? '') ||
    ''

  const selectedCollection =
    current.colecaoTecido ||
    (normalizedSelection?.collection ?? '')

  const fabricSuppliers = Array.from(
    new Set(
      fabrics
        .map((fabric) => getFabricSupplier(fabric))
        .filter(Boolean)
    )
  ).sort((a, b) => a.localeCompare(b, 'pt-BR'))

  const fabricCollections = Array.from(
    new Set(
      fabrics
        .filter(
          (fabric) =>
            getFabricSupplier(fabric) === selectedSupplier
        )
        .map((fabric) => getFabricCollection(fabric.nome, getFabricSupplier(fabric)))
        .filter(Boolean)
    )
  ).sort((a, b) => a.localeCompare(b, 'pt-BR'))

  const selectedFabricName = normalizedSelection?.fabricName ?? current.tecidoNome ?? ''

  const collectionFabrics = fabrics.filter((fabric) =>
    getFabricSupplier(fabric) === selectedSupplier &&
    getFabricCollection(fabric.nome, getFabricSupplier(fabric)) === selectedCollection
  )
  const fabricNames = Array.from(new Set(
    collectionFabrics.map((fabric) => getFabricVariant(fabric).name).filter(Boolean)
  )).sort((a, b) => a.localeCompare(b, 'pt-BR'))

  const clearFabricSelection = (
    fornecedorTecido: string,
    colecaoTecido: string,
    tecidoNome = ''
  ) => {
    const variants = fabricVariants(catalog, { ...current, fornecedorTecido, colecaoTecido, tecidoNome, tecidoProdutoId: undefined })
    const compatible = variants.filter(fabric => normalizeSearch(getFabricColorLabel(fabric)) === normalizeSearch(current.cor))
    // A reference needs a real fabric ID even before the optional color is chosen.
    const selected = compatible.length === 1 && current.cor
      ? compatible[0]
      : variants.find(fabric => fabric.id === current.tecidoProdutoId) ?? variants[0]
    if (tecidoNome && selected) {
      onResult(product.id, {
        ...fabricState(current, selected),
        cor: compatible.length === 1 && current.cor ? current.cor : '',
      })
      return
    }
    onResult(product.id, {
      ...current,
      fornecedorTecido,
      colecaoTecido,
      cor: '',
      tecido: '',
      tecidoNome,
      tecidoProdutoId: undefined,
      simulationKey: undefined,
      result: undefined,
      error: undefined,
    })
  }

  if (!applicable) return null

  return (
    <section className="curtain-simulation">
      <h4>Cortina — configuração técnica</h4>
      <p className="simulation-note">
        Defina os dados t?cnicos da cortina. O c?lculo de consumo e componentes ser? atualizado automaticamente.
      </p>

      <div className="curtain-simulation-grid">
        <label className="field">
        <span>Fornecedor</span>
        <select
          value={selectedSupplier}
          onChange={(e) =>
            clearFabricSelection(e.target.value, '')
          }
        >
          <option value="">Selecione o fornecedor</option>

          {fabricSuppliers.map((supplier) => (
            <option key={supplier} value={supplier}>
              {supplier}
            </option>
          ))}
        </select>
      </label>

      <label className="field">
        <span>Coleção de tecido</span>
        <select
          value={selectedCollection}
          disabled={!selectedSupplier}
          onChange={(e) =>
            clearFabricSelection(
              selectedSupplier,
              e.target.value
            )
          }
        >
          <option value="">
            {selectedSupplier
              ? 'Selecione a coleção'
              : 'Escolha primeiro o fornecedor'}
          </option>

          {fabricCollections.map((collection) => (
            <option key={collection} value={collection}>
              {collection}
            </option>
          ))}
        </select>
      </label>

      <label className="field">
        <span>Tecido</span>
        <select
          value={selectedFabricName}
          disabled={!selectedSupplier || !selectedCollection}
          onChange={(e) => clearFabricSelection(selectedSupplier, selectedCollection, e.target.value)}
        >
          <option value="">{selectedCollection ? 'Selecione o tecido' : 'Escolha primeiro a coleção'}</option>
          {fabricNames.map((name) => {
            const fabric = collectionFabrics.find(item => getFabricVariant(item).name === name)
            return <option key={name} value={name}>{fabric ? getFabricDisplayName(fabric) : name}</option>
          })}
        </select>
      </label>

        <label className="field">
          <span>Largura do tecido</span>
          <select
            value={current.larguraTecido}
            onChange={(e) =>
              update('larguraTecido', Number(e.target.value) as CurtainState['larguraTecido'])
            }
          >
            <option value={1.4}>1,40 m</option>
            <option value={1.5}>1,50 m</option>
            <option value={2.8}>2,80 m</option>
            <option value={3}>3,00 m</option>
          </select>
        </label>

        <label className="field">
          <span>Modelo / prega</span>
          <select
            value={current.modeloPrega}
            onChange={(e) => update('modeloPrega', e.target.value)}
          >
            <option value="WAVE">Wave</option>
            <option value="FRANZIDO">Franzido</option>
            <option value="PREGA_MACHO">Prega macho</option>
            <option value="PREGA_FEMEA">Prega f?mea</option>
          </select>
        </label>

        <label className="field">
          <span>Fator</span>
          <input
            type="number"
            min="1"
            step="0.1"
            value={current.fator}
            onChange={(e) => update('fator', Number(e.target.value))}
          />
        </label>

        <label className="field">
          <span>Cabeça</span>
          <div className="curtain-measure-input">
            <input
              type="number"
              min="0"
              step="1"
              value={current.cabecaCm === 0 ? '' : current.cabecaCm}
              onChange={(e) => update('cabecaCm', Number(e.target.value))}
            />
            <span>cm</span>
          </div>
        </label>

        <label className="field">
          <span>Barra</span>
          <select
            value={current.barraCm}
            onChange={(e) =>
              update(
                'barraCm',
                Number(e.target.value) as CurtainState['barraCm']
              )
            }
          >
            <option value={0}>Morrendo / barra de len?o</option>
            <option value={5}>5 cm</option>
            <option value={10}>10 cm</option>
            <option value={15}>15 cm</option>
            <option value={20}>20 cm</option>
            <option value={25}>25 cm</option>
            <option value={30}>30 cm</option>
            <option value={35}>35 cm</option>
            <option value={40}>40 cm</option>
            <option value={45}>45 cm</option>
            <option value={50}>50 cm</option>
          </select>
        </label>

        <label className="field">
          <span>Barra dupla</span>
          <select
            value={current.barraDupla ? 'SIM' : 'NAO'}
            disabled={current.barraCm === 0}
            onChange={(e) => update('barraDupla', e.target.value === 'SIM')}
          >
            <option value="SIM">Sim</option>
            <option value="NAO">N?o</option>
          </select>
        </label>

        <label className="field">
          <span>Forro</span>
          <select
            value={current.possuiForro ? 'SIM' : 'NAO'}
            onChange={(e) => update('possuiForro', e.target.value === 'SIM')}
          >
            <option value="NAO">Sem forro</option>
            <option value="SIM">Com forro</option>
          </select>
        </label>

        {current.possuiForro && (
          <label className="field">
            <span>Tipo de forro</span>
            <select value={current.forroProdutoId ?? ''} onChange={e => {
              const forro=catalog.find(p=>p.id===Number(e.target.value))
              onResult(product.id,{...current,forroProdutoId:forro?.id,tipoForro:forro?.nome,
                larguraForro:Number(forro?.largura)||undefined,simulationKey:undefined,result:undefined,error:undefined})
            }}>
              <option value="">Selecione o produto de forro</option>
              {catalog.filter(p=>normalizeSearch(p.modelo_tecnico ?? '') !== 'CORTINA' && /FORRO|TERGAL/.test(normalizeSearch(p.nome))).map(p=><option key={p.id} value={p.id}>{p.nome}</option>)}
            </select>
            {current.forroProdutoId && !Number(catalog.find(p=>p.id===current.forroProdutoId)?.largura) && <input
              type="number" min="0.01" step="0.01" aria-label="Largura do forro em metros"
              placeholder="Largura real do forro (m)" value={current.larguraForro ?? ''}
              onChange={e=>update('larguraForro',Number(e.target.value)||undefined)} />}

          </label>
        )}

        {current.modeloPrega === 'WAVE' && (
          <>
            <label className="field">
              <span>Sistema Wave</span>
              <select
                value={current.sistemaWave}
                onChange={(e) =>
                  update(
                    'sistemaWave',
                    e.target.value as CurtainState['sistemaWave']
                  )
                }
              >
                <option value="PREGA_PRONTA">Prega pronta</option>
                <option value="BOTAO">Fita de bot?o</option>
              </select>
            </label>

            {current.sistemaWave === 'BOTAO' && (
              <label className="field">
                <span>Espa?amento da fita</span>
                <select
                  value={current.espacamentoBotaoCm}
                  onChange={(e) =>
                    update(
                      'espacamentoBotaoCm',
                      Number(e.target.value) as 7 | 10
                    )
                  }
                >
                  <option value={7}>7 cm</option>
                  <option value={10}>10 cm</option>
                </select>
              </label>
            )}

            <label className="field">
              <span>Abertura</span>
              <select
                value={current.aberturaCortina}
                onChange={(e) =>
                  update(
                    'aberturaCortina',
                    e.target.value as CurtainState['aberturaCortina']
                  )
                }
              >
                <option value="LATERAL_ESQUERDA">Lateral esquerda</option>
                <option value="LATERAL_DIREITA">Lateral direita</option>
                <option value="CENTRAL">Central</option>
                <option value="DUAS_LATERAIS">Duas laterais</option>
              </select>
            </label>
          </>
        )}

        <label className="field">
          <span>Entretela</span>
          <select
            value={current.usaEntretela ? 'SIM' : 'NAO'}
            onChange={(e) => update('usaEntretela', e.target.value === 'SIM')}
          >
            <option value="SIM">TNT</option>
            <option value="NAO">Sem entretela</option>
          </select>
        </label>

        <label className="field">
          <span>Fixação da cortina</span>
          <select
            value={current.fixacaoCortina}
            onChange={(e) =>
              update(
                'fixacaoCortina',
                e.target.value as CurtainState['fixacaoCortina']
              )
            }
          >
            <option value="RODIZIO">Rodízio</option>
            <option value="GANCHO">Gancho</option>
          </select>
        </label>

        {current.fixacaoCortina === 'GANCHO' && (
          <label className="field">
            <span>Trilho com cordas</span>
            <select
              value={current.trilhoComCordas ? 'SIM' : 'NAO'}
              onChange={(e) =>
                update('trilhoComCordas', e.target.value === 'SIM')
              }
            >
              <option value="NAO">N?o</option>
              <option value="SIM">Sim</option>
            </select>
          </label>
        )}

        <label className="field">
          <span>Observação do trilho (opcional)</span>
          <input
            value={current.trilhoModelo ?? ''}
            onChange={(e) => update('trilhoModelo', e.target.value)}
            placeholder="Ex.: Simples, duplo, com curva"
          />
        </label>
      </div>

      <CurtainComponents catalog={catalog} lines={curtainComponentLines(current, width)} onChange={lines => update('componentes', lines)} />

      {(!resolvedProductId || width <= 0 || height <= 0) && (
        <div className="api-message" role="status">
          Selecione o tecido real e informe largura e altura para calcular a cortina.
        </div>
      )}

      {waiting && (
        <div className="api-message" role="status" aria-live="polite">
          Calculando a simulação técnica da cortina...
        </div>
      )}

      {simulationError && (
        <div className="api-message error" role="alert">
          Não foi possível simular a Cortina. Dados preservados;
          salvamento bloqueado. {simulationError}
        </div>
      )}

      {result && (
        <section className="api-message curtain-result" aria-live="polite">
          <strong>Cortina — simulação técnica</strong>
          <p>Custo por peça: {formatCurrency(result.custo_total ?? 0)} · Valor unitário: {formatCurrency(result.preco_unitario ?? 0)}</p>
          {result.avisos?.map((aviso,index)=><p key={index} role="status">{aviso}</p>)}

          <p>
            Desenvolvimento:{' '}
            <strong>
              {result.desenvolvimento_m.toLocaleString('pt-BR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })} m
            </strong>
            {' · '}
            Alturas:{' '}
            <strong>{result.quantidade_alturas}</strong>
          </p>

          <p>
            Tecido:{' '}
            <strong>
              {result.tecido.consumo_total_ml.toLocaleString('pt-BR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })} m
            </strong>
            {' · '}
            Consumo por altura:{' '}
            {result.tecido.consumo_por_altura_m.toLocaleString('pt-BR', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })} m
          </p>

          <p>
            Entretela:{' '}
            <strong>
              {result.entretela.usa
                ? `${result.entretela.tipo} — ${result.entretela.quantidade_ml.toLocaleString(
                    'pt-BR',
                    {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    }
                  )} m`
                : 'Sem entretela'}
            </strong>
          </p>

          <p>
            Mão de obra:{' '}
            <strong>
              {result.mao_de_obra.quantidade_alturas} altura(s)
              {' · '}
              {result.mao_de_obra.total.toLocaleString('pt-BR', {
                style: 'currency',
                currency: 'BRL',
              })}
            </strong>
          </p>

          <p>
            Trilho:{' '}
            <strong>
              {result.trilho.quantidade_ml.toLocaleString('pt-BR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })} m
            </strong>
          </p>

          {result.wave.aplicavel && (
            <>
              <p>
                Wave:{' '}
                <strong>
                  {result.wave.sistema === 'BOTAO'
                    ? 'Fita de botão'
                    : 'Prega pronta'}
                </strong>
                {' · '}
                Abertura: {result.wave.abertura}
                {' · '}
                Folhas: {result.wave.quantidade_folhas}
              </p>

              <p>
                Pontos por folha:{' '}
                <strong>{result.wave.pontos_por_folha}</strong>
                {' · '}
                Total de pontos:{' '}
                <strong>{result.wave.quantidade_pontos_total}</strong>

                {result.wave.quantidade_botoes > 0 && (
                  <>
                    {' · '}
                    Botões:{' '}
                    <strong>{result.wave.quantidade_botoes}</strong>
                  </>
                )}
              </p>
            </>
          )}

          <p>
            Rodízios na cortina:{' '}
            <strong>{result.rodizios.quantidade_cortina_un}</strong>
            {' · '}
            Rodízios no trilho:{' '}
            <strong>{result.rodizios.quantidade_trilho_un}</strong>
            {' · '}
            Ganchos:{' '}
            <strong>{result.ganchos.quantidade_cortina_un}</strong>
          </p>
        </section>
      )}
    </section>
  )
}
