import { useEffect } from 'react'
import { simulateCurtain } from '../services/api'
import type { ApiProduct, BudgetProduct, CurtainState } from '../types/budget'
import { normalizeSearch, parseDecimal } from '../types/budget'

type Props = {
  profile: 'Decorador' | 'Varejo' | 'Consumidor final'
  product: BudgetProduct
  catalog: ApiProduct[]
  onResult: (id: number, state: CurtainState) => void
}

const DEFAULT_CURTAIN: CurtainState = {
  tecido: '',
  cor: '',
  larguraTecido: 1.5,
  possuiForro: false,
  tipoForro: '',
  modeloPrega: 'WAVE',
  fator: 2.5,
  trilhoLinha: 'MINI',
  trilhoModelo: 'SIMPLES',
  rodizioTipo: 'MINI',
  possuiGancho: true,
  cabecaCm: 10,
  barraCm: 15,
  barraDupla: true,
  usaEntretela: true,
  tipoEntretela: 'TNT',
  fixacaoCortina: 'RODIZIO',
  trilhoComCordas: false,
  sistemaWave: 'PREGA_PRONTA',
  espacamentoBotaoCm: 10,
  aberturaCortina: 'LATERAL_ESQUERDA',
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

  

const canonicalFabricSupplier = (value: string | null | undefined) => {
  const raw = String(value ?? '').trim()
  const normalized = normalizeSearch(raw)

  if (!normalized) return ''

  // Aceita A??O, ACAO e tamb?m o legado quebrado A??O.
  if (
    normalized.includes('DISTRIBUIDORA') &&
    (
      normalized.includes('ACAO') ||
      normalized.startsWith('A??O') ||
      normalized.startsWith('A O') ||
      normalized.startsWith('AO ')
    )
  ) {
    return 'AÇÃO DISTRIBUIDORA'
  }

  if (
    normalized.includes('JP PERSIANAS') ||
    normalized === 'JP'
  ) {
    return 'JP PERSIANAS'
  }

  return raw
}

const isAcaoCurtainTableFabric = (fabric: ApiProduct) => {
  const raw = fabric as ApiProduct & { linha?: string | null }
  const line = normalizeSearch(raw.linha ?? '')
  const name = normalizeSearch(fabric.nome ?? '')
    .replace(/^\d+(?:-\d+)*\s*-\s*/, '')

  return line === 'CORTINA' &&
    /^(VOIL\b|LINHO VOIL\b|CAMBURI\b|PARATI\b|TECIDO VELUDO\b)/.test(name)
}

const getFabricSupplier = (fabric: ApiProduct) => {
  const explicit = String(fabric.nome_fornecedor ?? '').trim()

  if (explicit) return canonicalFabricSupplier(explicit)

  if (isAcaoCurtainTableFabric(fabric)) {
    return canonicalFabricSupplier('ACAO DISTRIBUIDORA')
  }

  const raw = fabric as ApiProduct & {
    origem?: string | null
  }

  const origem = normalizeSearch(raw.origem ?? '')
  const nome = normalizeSearch(fabric.nome ?? '')

  if (
    origem.includes('ACAO DISTRIBUIDORA') ||
    origem.includes('TABELA DE CORTINAS') ||
    origem.includes('TABELA CORTINA IMPORTADO')
  ) {
    return 'AÇÃO DISTRIBUIDORA'
  }

  if (
    origem.includes('2 - TECIDO.PDF') ||
    nome.includes(' JP ') ||
    nome.startsWith('JP ') ||
    nome.includes('JP157') ||
    nome.includes('JP159') ||
    nome.includes('RATTAN') ||
    nome.includes('ROLLER') ||
    nome.includes('PANDORA')
  ) {
    return 'JP PERSIANAS'
  }

  return ''
}

const getFabricCollection = (name: string | null | undefined) => {
  let value = String(name ?? '').trim()

  // Remove c?digo inicial
  value = value.replace(/^\d+(?:-\d+)*\s*-\s*/, '')

  // Remove largura final
  value = value.replace(/\s*-\s*\d+[.,]\d+\s*M\s*$/i, '')

  if (/^TECIDO VELUDO\s*-/i.test(value)) {
    return 'VELUDO'
  }

  // Remove cor/c?digo final
  value = value.replace(/\s*-\s*\(\d+\)\s*[^-]+$/i, '')

  const parts = value
    .split(/\s+-\s+/)
    .map((part) => part.trim())
    .filter(Boolean)

  if (parts.length > 1) {
    const first = parts[0]

    if (
      /^(RATTAN|ROLLER|PANDORA)$/i.test(first)
    ) {
      return first
    }

    if (
      /^(VOIL LISO|VOIL TELA|VOIL XADREZ|VOIL RUSTICO|VOIL R?STICO|LINHO VOIL I|LINHO VOIL II|LINHO VOIL III|LINHO VOIL IV)$/i.test(first)
    ) {
      return first
    }
  }

  return value
    .replace(/^TECIDO\s+/i, '')
    .replace(/^CORTINA\s+TECIDO\s+/i, '')
    .trim()
}

const getFabricColorLabel = (fabric: ApiProduct) => {
  const rawFabric = fabric as ApiProduct & {
    cor?: string | null
  }

  const explicit = String(rawFabric.cor ?? '').trim()

  if (explicit) return explicit

  let value = String(fabric.nome ?? '').trim()
  value = value.replace(/^\d+(?:-\d+)*\s*-\s*/, '')

  const parts = value.split(/\s+-\s+/)

  return String(parts[1] ?? '')
    .replace(/^COR\s*/i, '')
    .replace(/[()]/g, '')
    .trim() || 'Sem cor identificada'
}

const selectFabric = (fabric: ApiProduct) => {
    const rawWidth = Number(
      String(fabric.largura ?? '')
        .replace(',', '.')
    )

    let detectedWidth =
      Number.isFinite(rawWidth) && rawWidth > 0
        ? rawWidth
        : undefined

    if (!detectedWidth) {
      const name = normalizeSearch(fabric.nome ?? '')
      const match = name.match(/(?:^|\s)(1[,.]40|1[,.]50|2[,.]80|3[,.]00)(?:M|\s|$)/)

      if (match) {
        detectedWidth = Number(match[1].replace(',', '.'))
      }
    }

    onResult(product.id, {
      ...current,
      tecido: fabric.nome ?? '',
      tecidoNome: fabric.nome ?? '',
      tecidoProdutoId: fabric.id,
      fornecedorTecido: getFabricSupplier(fabric),
      colecaoTecido: getFabricCollection(fabric.nome),
      cor: getFabricColorLabel(fabric),
      larguraTecido:
        detectedWidth === 1.4 ||
        detectedWidth === 1.5 ||
        detectedWidth === 2.8 ||
        detectedWidth === 3
          ? detectedWidth
          : current.larguraTecido,
      simulationKey: undefined,
      result: undefined,
      error: undefined,
    })
  }

  const selectedCatalogProduct =
    catalog.find((p) => p.id === product.productId) ??
    catalog.find(
      (p) =>
        normalizeSearch(p.nome ?? '') ===
        normalizeSearch(product.product ?? '')
    )

  const resolvedProductId =
    product.productId ?? selectedCatalogProduct?.id ?? null

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

  const commercialProfile =
    profile === 'Decorador'
      ? 'DECORADOR'
      : profile === 'Consumidor final'
        ? 'CONSUMIDOR_FINAL'
        : 'VAREJO'

  const simulationKey = JSON.stringify([
    commercialProfile,
    product.discount,
    resolvedProductId,
    width,
    height,
    quantity,
    current.fator,
    current.larguraTecido,
    current.modeloPrega,
    current.possuiForro,
    current.tipoForro ?? '',
    current.trilhoLinha ?? '',
    current.trilhoModelo ?? '',
    current.rodizioTipo ?? '',
    current.cabecaCm,
    current.barraCm,
    current.barraDupla,
    current.usaEntretela,
    current.tipoEntretela,
    current.fixacaoCortina,
    current.trilhoComCordas,
    current.sistemaWave,
    current.espacamentoBotaoCm,
    current.aberturaCortina,
  ])

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
        produto_id: resolvedProductId!,
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
            ...current,
            simulationKey,
            result,
            error: undefined,
          })
        })
        .catch((error) => {
          if (cancelled) return

          onResult(product.id, {
            ...current,
            simulationKey,
            result: undefined,
            error:
              error instanceof Error
                ? error.message
                : String(error),
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


const curtainFabricCatalog = catalog.filter((fabric) => {
  const raw = fabric as ApiProduct & {
    modelo_tecnico?: string | null
    grupo_tecnico?: string | null
    grupo_produto?: string | null
    linha?: string | null
    tipo_produto?: string | null
  }

  const group = normalizeSearch(raw.grupo_tecnico ?? '')
  const productGroup = normalizeSearch(raw.grupo_produto ?? '')
  const name = normalizeSearch(fabric.nome ?? '')

  const isVerticalFabric = [
    name,
    group,
    productGroup,
    normalizeSearch(raw.modelo_tecnico ?? ''),
    normalizeSearch(raw.linha ?? ''),
    normalizeSearch(raw.tipo_produto ?? ''),
  ].some((value) => /(^|[^A-Z])VERTICA(?:L|IS)([^A-Z]|$)/i.test(value))

  if (isVerticalFabric) {
    return false
  }

  if ([name, group, productGroup, normalizeSearch(raw.linha ?? '')]
    .some((value) => value.includes('HOSPITALAR'))) {
    return false
  }

  const isCurtainFabricGroup =
    isAcaoCurtainTableFabric(fabric) ||
    group === 'TECIDOS_CORTINA' ||
    group === 'TECIDOS_CORTINAS' ||
    productGroup.includes('TECIDO CORTINA') ||
    productGroup.includes('TECIDO PARA CORTINA')

  if (!isCurtainFabricGroup) {
    return false
  }

  const isExcluded =
    /FITA|TRILHO|VARAO|RODIZIO|MOTOR|MOTC|PONTEIRA|SUPORTE|CURVA|CORREIA|COMANDO|PERFIL|TAMPA|CLIP|FIO CONTINUO|MANIVELA|HOSPITALAR|CORTINA WAVE|CORTINA MOTORIZADA|APMOTV/.test(
      name
    )

  if (isExcluded) {
    return false
  }

  return true
})

  const selectedFabric =
    curtainFabricCatalog.find(
      (fabric) => fabric.id === current.tecidoProdutoId
    ) ?? null

  const selectedSupplier =
    canonicalFabricSupplier(current.fornecedorTecido) ||
    (selectedFabric ? getFabricSupplier(selectedFabric) : '') ||
    ''

  const selectedCollection =
    current.colecaoTecido ||
    (selectedFabric ? getFabricCollection(selectedFabric.nome) : '')

  const fabricSuppliers = Array.from(
    new Set(
      curtainFabricCatalog
        .map((fabric) => getFabricSupplier(fabric))
        .filter(Boolean)
    )
  ).sort((a, b) => a.localeCompare(b, 'pt-BR'))

  const fabricCollections = Array.from(
    new Set(
      curtainFabricCatalog
        .filter(
          (fabric) =>
            getFabricSupplier(fabric) === selectedSupplier
        )
        .map((fabric) => getFabricCollection(fabric.nome))
        .filter(Boolean)
    )
  ).sort((a, b) => a.localeCompare(b, 'pt-BR'))

  const fabricColors = curtainFabricCatalog
    .filter(
      (fabric) =>
        getFabricSupplier(fabric) === selectedSupplier &&
        getFabricCollection(fabric.nome) === selectedCollection
    )
    .sort((a, b) =>
      getFabricColorLabel(a).localeCompare(
        getFabricColorLabel(b),
        'pt-BR',
        { numeric: true }
      )
    )

  const clearFabricSelection = (
    fornecedorTecido: string,
    colecaoTecido: string
  ) => {
    onResult(product.id, {
      ...current,
      fornecedorTecido,
      colecaoTecido,
      cor: '',
      tecido: '',
      tecidoNome: '',
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
        <span>Cor</span>
        <select
          value={current.tecidoProdutoId ?? ''}
          disabled={!selectedSupplier || !selectedCollection}
          onChange={(e) => {
            const id = Number(e.target.value)

            const fabric = fabricColors.find(
              (item) => item.id === id
            )

            if (fabric) {
              selectFabric(fabric)
            }
          }}
        >
          <option value="">
            {selectedCollection
              ? 'Selecione a cor'
              : 'Escolha primeiro a coleção'}
          </option>

          {fabricColors.map((fabric) => (
            <option key={fabric.id} value={fabric.id}>
              {getFabricColorLabel(fabric)}
            </option>
          ))}
        </select>

        {current.tecidoProdutoId && (
          <small>
            Tecido vinculado ao cadastro #{current.tecidoProdutoId}
          </small>
        )}
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
              value={current.cabecaCm}
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
            <input
              value={current.tipoForro ?? ''}
              onChange={(e) => update('tipoForro', e.target.value)}
              placeholder="Ex.: Tergal"
            />
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
          <span>Linha do trilho</span>
          <select
            value={current.trilhoLinha ?? 'MINI'}
            onChange={(e) =>
              update('trilhoLinha', e.target.value as CurtainState['trilhoLinha'])
            }
          >
            <option value="MINI">Mini</option>
            <option value="MAX">Max</option>
            <option value="MASTER">Master</option>
          </select>
        </label>

        <label className="field">
          <span>Modelo do trilho</span>
          <input
            value={current.trilhoModelo ?? ''}
            onChange={(e) => update('trilhoModelo', e.target.value)}
            placeholder="Ex.: Simples, duplo, com curva"
          />
        </label>
      </div>

      {(!resolvedProductId || width <= 0 || height <= 0) && (
        <div className="api-message" role="status">
          Informe um produto, largura e altura para calcular a cortina.
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
