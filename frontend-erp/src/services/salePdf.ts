import type { ApiOrder } from './api'
import type { ApiBudget, ApiBudgetItem } from '../types/budget'
import { getOrder } from './api'
import {
  budgetPdfCompanyId,
  generateBudgetPdf,
  loadBudgetPdfContext,
  downloadBudgetPdf
} from './budgetPdf'
import { prepareBudgetPdfData } from './budgetPdfData'
import type { BudgetPdfMode } from './budgetPdfData'

function decimal(value: unknown): number {
  if (
    (typeof value !== 'number' && typeof value !== 'string') ||
    String(value).trim() === '' ||
    !Number.isFinite(Number(value))
  ) {
    throw new Error('Valor comercial invalido na venda.')
  }
  return Number(value)
}

const optionalDecimal = (value: unknown) =>
  value == null ? undefined : decimal(value)

export function salePdfSource(order: ApiOrder): ApiBudget {
  const profile = order.perfil_comercial

  if (profile !== 'VAREJO' &&
      profile !== 'DECORADOR' &&
      profile !== 'CONSUMIDOR_FINAL') {
    throw new Error('Perfil comercial invalido.')
  }

  const mode = order.pagamento_modalidade

  if (mode != null && mode !== 'AVISTA' &&
      mode !== 'PARCELADO' && mode !== 'ENTRADA_SALDO') {
    throw new Error('Modalidade de pagamento invalida.')
  }

  return {
    id: order.id,
    numero: order.numero || String(order.id),
    cliente_id: order.cliente_id ?? null,
    cliente_final_nome: order.cliente_final_nome,
    cliente_final_documento: order.cliente_final_documento,
    cliente_final_telefone: order.cliente_final_telefone,
    cliente_final_email: order.cliente_final_email,
    cliente_final_endereco: order.cliente_final_endereco,
    parceiro_id: order.parceiro_id,
    representante_id: order.representante_id,
    vendedor_id: order.vendedor_id,
    perfil_comercial: profile,
    status: order.status || '',
    criado_em: order.data_venda ?? order.criado_em,
    total: decimal(order.total),
    desconto: decimal(order.desconto),
    total_final: decimal(order.total_final),
    total_cliente_final: optionalDecimal(order.total_cliente_final),
    percentual_parceiro: optionalDecimal(order.percentual_parceiro),
    valor_parceiro: optionalDecimal(order.valor_parceiro),
    incluir_rt: order.incluir_rt ?? undefined,
    valor_rt: optionalDecimal(order.valor_rt),
    percentual_rt: optionalDecimal(order.percentual_rt),
    incluir_taxa_bancaria: order.incluir_taxa_bancaria ?? undefined,
    taxa_bancaria_percentual: optionalDecimal(order.taxa_bancaria_percentual),
    valor_taxa_bancaria: optionalDecimal(order.valor_taxa_bancaria),
    observacao: order.observacao,
    observacao_interna: order.observacao_interna,
    pagamento_modalidade: mode,
    pagamento_numero_parcelas: order.pagamento_numero_parcelas,
    pagamento_intervalo_dias: order.pagamento_intervalo_dias,
    pagamento_primeiro_vencimento: order.pagamento_primeiro_vencimento,
    pagamento_parcelas: (order.pagamento_parcelas ?? []).map(p => ({
      ...p, valor: decimal(p.valor)
    })),
    itens: order.itens.map(item => ({
      ...item,
      descricao: item.descricao || '',
      quantidade: decimal(item.quantidade),
      largura: decimal(item.largura),
      altura: decimal(item.altura),
      area: decimal(item.area),
      preco_unitario: decimal(item.preco_unitario),
      desconto: decimal(item.desconto),
      subtotal: decimal(item.subtotal),
      dados_tecnicos: item.dados_tecnicos as ApiBudgetItem['dados_tecnicos']
    }))
  }
}

export async function prepareSavedSalePdf(
  id: number, mode: BudgetPdfMode
) {
  const empresaId = await budgetPdfCompanyId()
  const order = await getOrder(id)

  if (order.empresa_id !== empresaId ||
      await budgetPdfCompanyId() !== empresaId) {
    throw new Error('Empresa ativa diferente da empresa da venda.')
  }

  if (mode === 'direct') {
    if (order.cliente_id == null || order.parceiro_id != null) {
      throw new Error('Confira o cliente e a origem comercial da venda.')
    }

    if (order.incluir_rt || order.incluir_taxa_bancaria ||
        order.representante_id != null ||
        order.cliente_final_nome?.trim()) {
      throw new Error('Venda direta com composicao especial exige tratamento comercial especifico.')
    }

    if (order.total_cliente_final != null &&
        decimal(order.total_cliente_final) !== decimal(order.total_final)) {
      throw new Error('Total comercial divergente do valor interno.')
    }
  }

  const source = salePdfSource(order)
  const projection = prepareBudgetPdfData(source, mode)
  const context = await loadBudgetPdfContext(source, mode)

  if (await budgetPdfCompanyId() !== empresaId) {
    throw new Error('A empresa ativa mudou.')
  }

  const blob = await generateBudgetPdf(source, mode, {
    ...context,
    documentKind: 'sale'
  })

  if (await budgetPdfCompanyId() !== empresaId) {
    throw new Error('A empresa ativa mudou.')
  }

  const suffix = {
    direct: 'Cliente',
    reseller_internal: 'Interno-Smart-tec',
    reseller_commercial: 'Revenda',
    reseller_client: 'Cliente-Final'
  }[mode]

  const number = source.numero.replace(/[^a-zA-Z0-9_-]/g, '-')

  return {
    order,
    blob,
    filename: `Venda-${number}-${suffix}.pdf`,
    warnings: [...(context.warnings ?? []), ...projection.warnings]
  }
}

export async function downloadDirectSalePdf(id: number) {
  const result = await prepareSavedSalePdf(id, 'direct')
  downloadBudgetPdf(result.blob, result.filename)
}
