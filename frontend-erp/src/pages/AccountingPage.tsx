import { ColumnManager } from '../components/ColumnManager'
import {
  BadgeDollarSign,
  BookOpenCheck,
  CheckCircle2,
  CircleDollarSign,
  FileCheck2,
  FilePlus2,
  ReceiptText,
  RefreshCcw,
  WalletCards,
} from 'lucide-react'
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  closeAccountingPeriod,
  createAccountingDocument,
  createAccountingObligation,
  createAccountingPayable,
  getAccountingDocuments,
  getAccountingObligations,
  getAccountingSummary,
  markAccountingObligationPaid,
  type AccountingDocument,
  type AccountingObligation,
  type AccountingSummary,
} from '../services/api'
import { formatCurrency } from '../types/budget'


function currentCompetence() {
  const date = new Date()

  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, '0'),
  ].join('-')
}


function today() {
  const date = new Date()

  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, '0'),
    String(date.getDate()).padStart(2, '0'),
  ].join('-')
}


function money(value: number | string | undefined) {
  return formatCurrency(Number(value || 0))
}


function statusLabel(value: string) {
  const normalized = value.toUpperCase()

  if (normalized === 'RECEBIDO') return 'Recebido'
  if (normalized === 'AGUARDANDO_PAGAMENTO') {
    return 'Aguardando pagamento'
  }
  if (normalized === 'PAGO') return 'Pago'
  if (normalized === 'CANCELADO') return 'Cancelado'
  if (normalized === 'FECHADO') return 'Fechado'
  if (normalized === 'ABERTO') return 'Aberto'

  return value.replaceAll('_', ' ')
}


function documentTypeLabel(value: string) {
  const labels: Record<string, string> = {
    NF_SAIDA_PRODUTO: 'NF saída - produtos',
    NF_SAIDA_SERVICO: 'NF saída - serviços',
    NF_ENTRADA_PRODUTO: 'NF entrada - produtos',
    NF_ENTRADA_SERVICO: 'NF entrada - serviços',
    OUTRO: 'Outro',
  }

  return labels[value] || value
}


function obligationTypeLabel(value: string) {
  const labels: Record<string, string> = {
    DAS: 'DAS',
    DARF: 'DARF',
    FGTS: 'FGTS',
    INSS: 'INSS',
    IMPOSTO: 'Imposto',
    HONORARIOS_CONTABEIS: 'Honorários contábeis',
    TAXA: 'Taxa',
    OUTRO: 'Outro',
  }

  return labels[value] || value
}


export function AccountingPage() {
  const [competence, setCompetence] = useState(
    currentCompetence(),
  )

  const [summary, setSummary] =
    useState<AccountingSummary | null>(null)

  const [documents, setDocuments] =
    useState<AccountingDocument[]>([])

  const [obligations, setObligations] =
    useState<AccountingObligation[]>([])

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const [documentSaving, setDocumentSaving] =
    useState(false)

  const [obligationSaving, setObligationSaving] =
    useState(false)

  const [actionId, setActionId] =
    useState<number | null>(null)

  const [documentForm, setDocumentForm] = useState({
    tipo_documento: 'NF_SAIDA_PRODUTO',
    numero: '',
    data_emissao: today(),
    valor: '',
    observacao: '',
  })

  const [obligationForm, setObligationForm] = useState({
    tipo_obrigacao: 'DAS',
    descricao: '',
    valor: '',
    vencimento: today(),
    observacao: '',
  })


  const load = useCallback(async () => {
    setLoading(true)
    setError('')

    try {
      const [
        summaryData,
        documentData,
        obligationData,
      ] = await Promise.all([
        getAccountingSummary(competence),
        getAccountingDocuments(competence),
        getAccountingObligations(competence),
      ])

      setSummary(summaryData)
      setDocuments(documentData)
      setObligations(obligationData)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : String(err),
      )
    } finally {
      setLoading(false)
    }
  }, [competence])


  useEffect(() => {
    void load()
  }, [load])


  const pendingObligations = useMemo(
    () =>
      obligations.filter(
        (item) =>
          item.status !== 'PAGO' &&
          item.status !== 'CANCELADO',
      ),
    [obligations],
  )


  async function handleCreateDocument() {
    const value = Number(
      documentForm.valor.replace(',', '.'),
    )

    if (
      !documentForm.data_emissao ||
      !Number.isFinite(value) ||
      value < 0
    ) {
      setError(
        'Preencha data e valor válido do documento fiscal.',
      )
      return
    }

    setDocumentSaving(true)
    setError('')
    setMessage('')

    try {
      await createAccountingDocument({
        competencia: competence,
        tipo_documento:
          documentForm.tipo_documento,
        numero:
          documentForm.numero.trim() || null,
        data_emissao:
          documentForm.data_emissao,
        valor: value,
        observacao:
          documentForm.observacao.trim() || null,
      })

      setDocumentForm({
        tipo_documento: 'NF_SAIDA_PRODUTO',
        numero: '',
        data_emissao: today(),
        valor: '',
        observacao: '',
      })

      setMessage(
        'Documento fiscal registrado.',
      )

      await load()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : String(err),
      )
    } finally {
      setDocumentSaving(false)
    }
  }


  async function handleCreateObligation() {
    const value = Number(
      obligationForm.valor.replace(',', '.'),
    )

    if (
      !obligationForm.descricao.trim() ||
      !obligationForm.vencimento ||
      !Number.isFinite(value) ||
      value < 0
    ) {
      setError(
        'Preencha descrição, valor e vencimento da obrigação.',
      )
      return
    }

    setObligationSaving(true)
    setError('')
    setMessage('')

    try {
      await createAccountingObligation({
        competencia: competence,
        tipo_obrigacao:
          obligationForm.tipo_obrigacao,
        descricao:
          obligationForm.descricao.trim(),
        valor: value,
        vencimento:
          obligationForm.vencimento,
        observacao:
          obligationForm.observacao.trim() ||
          null,
      })

      setObligationForm({
        tipo_obrigacao: 'DAS',
        descricao: '',
        valor: '',
        vencimento: today(),
        observacao: '',
      })

      setMessage(
        'Obrigação do contador registrada.',
      )

      await load()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : String(err),
      )
    } finally {
      setObligationSaving(false)
    }
  }


  async function handleGeneratePayable(
    obligation: AccountingObligation,
  ) {
    setActionId(obligation.id)
    setError('')
    setMessage('')

    try {
      await createAccountingPayable(
        obligation.id,
      )

      setMessage(
        'Conta a pagar criada no Financeiro.',
      )

      await load()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : String(err),
      )
    } finally {
      setActionId(null)
    }
  }


  async function handlePaid(
    obligation: AccountingObligation,
  ) {
    const paymentDate = window.prompt(
      'Data do pagamento (AAAA-MM-DD):',
      today(),
    )

    if (!paymentDate) return

    setActionId(obligation.id)
    setError('')
    setMessage('')

    try {
      await markAccountingObligationPaid(
        obligation.id,
        paymentDate,
      )

      setMessage(
        'Obrigação marcada como paga.',
      )

      await load()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : String(err),
      )
    } finally {
      setActionId(null)
    }
  }


  async function handleClosePeriod() {
    if (pendingObligations.length > 0) {
      const proceed = window.confirm(
        `Existem ${pendingObligations.length} obrigação(ões) ainda pendente(s). Fechar a competência mesmo assim?`,
      )

      if (!proceed) return
    }

    const confirmed = window.confirm(
      `Fechar a competência ${competence}?`,
    )

    if (!confirmed) return

    setError('')
    setMessage('')

    try {
      await closeAccountingPeriod(
        competence,
        'Fechamento realizado pelo módulo Contabilidade.',
      )

      setMessage(
        `Competência ${competence} fechada.`,
      )

      await load()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : String(err),
      )
    }
  }


  return (
    <div className="budget-page">
      <section className="budget-page-heading page-heading">
        <div>
          <p className="eyebrow">
            CONTROLE CONTÁBIL
          </p>

          <h1>Contabilidade</h1>

          <p className="heading-subtitle">
            Faturamento fiscal, documentos, guias,
            honorários e fechamento mensal em um só lugar.
          </p>
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'end',
            gap: 10,
            flexWrap: 'wrap',
          }}
        >
          <label className="field">
            <span>Competência</span>

            <input
              type="month"
              value={competence}
              onChange={(event) =>
                setCompetence(event.target.value)
              }
            />
          </label>

          <button
            type="button"
            className="secondary-button"
            onClick={() => void load()}
          >
            <RefreshCcw size={16} />
            Atualizar
          </button>

          <button
            type="button"
            className="primary-button"
            onClick={() => void handleClosePeriod()}
            disabled={
              summary?.fechamento?.status === 'FECHADO'
            }
          >
            <BookOpenCheck size={16} />

            {summary?.fechamento?.status === 'FECHADO'
              ? 'Competência fechada'
              : 'Fechar competência'}
          </button>
        </div>
      </section>

      {error && (
        <div className="api-message error">
          {error}
        </div>
      )}

      {message && (
        <div className="api-message">
          {message}
        </div>
      )}

      {loading ? (
        <div className="panel loading-state">
          Carregando contabilidade...
        </div>
      ) : (
        <>
          <section className="budget-kpi-grid">
            <Kpi
              icon={<FileCheck2 size={18} />}
              label="NF produtos"
              value={money(summary?.nf_produtos)}
              small={`${summary?.qtd_nf_produtos || 0} nota(s)`}
            />

            <Kpi
              icon={<ReceiptText size={18} />}
              label="NF serviços"
              value={money(summary?.nf_servicos)}
              small={`${summary?.qtd_nf_servicos || 0} nota(s)`}
            />

            <Kpi
              icon={<CircleDollarSign size={18} />}
              label="Faturamento fiscal"
              value={money(
                summary?.faturamento_fiscal,
              )}
              small={competence}
            />

            <Kpi
              icon={<WalletCards size={18} />}
              label="Obrigações"
              value={money(
                summary?.total_obrigacoes,
              )}
              small="Guias e honorários"
            />

            <Kpi
              icon={<CheckCircle2 size={18} />}
              label="Pago"
              value={money(summary?.total_pago)}
              small="No período"
            />

            <Kpi
              icon={<BadgeDollarSign size={18} />}
              label="Pendente"
              value={money(summary?.total_pendente)}
              small={`${pendingObligations.length} pendência(s)`}
            />

            <Kpi
              icon={<BookOpenCheck size={18} />}
              label="Honorários"
              value={money(
                summary?.honorarios_contabeis,
              )}
              small="Contabilidade"
            />
          </section>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns:
                'repeat(auto-fit,minmax(360px,1fr))',
              gap: 18,
              marginTop: 18,
            }}
          >
            <section className="panel">
              <div className="section-title">
                <div className="section-icon">
                  <FilePlus2 size={17} />
                </div>

                <div>
                  <h2>Registrar documento fiscal</h2>
                  <p>
                    Cadastro manual enquanto a integração
                    fiscal automática não estiver conectada.
                  </p>
                </div>
              </div>

              <div
                className="form-grid"
                style={{ marginTop: 18 }}
              >
                <label className="field">
                  <span>Tipo</span>

                  <select
                    value={documentForm.tipo_documento}
                    onChange={(event) =>
                      setDocumentForm((current) => ({
                        ...current,
                        tipo_documento:
                          event.target.value,
                      }))
                    }
                  >
                    <option value="NF_SAIDA_PRODUTO">
                      NF saída - produtos
                    </option>
                    <option value="NF_SAIDA_SERVICO">
                      NF saída - serviços
                    </option>
                    <option value="NF_ENTRADA_PRODUTO">
                      NF entrada - produtos
                    </option>
                    <option value="NF_ENTRADA_SERVICO">
                      NF entrada - serviços
                    </option>
                    <option value="OUTRO">
                      Outro
                    </option>
                  </select>
                </label>

                <label className="field">
                  <span>Número</span>

                  <input
                    value={documentForm.numero}
                    onChange={(event) =>
                      setDocumentForm((current) => ({
                        ...current,
                        numero: event.target.value,
                      }))
                    }
                    placeholder="Número da NF"
                  />
                </label>

                <label className="field">
                  <span>Data de emissão</span>

                  <input
                    type="date"
                    value={documentForm.data_emissao}
                    onChange={(event) =>
                      setDocumentForm((current) => ({
                        ...current,
                        data_emissao:
                          event.target.value,
                      }))
                    }
                  />
                </label>

                <label className="field">
                  <span>Valor</span>

                  <input
                    inputMode="decimal"
                    value={documentForm.valor}
                    onChange={(event) =>
                      setDocumentForm((current) => ({
                        ...current,
                        valor: event.target.value,
                      }))
                    }
                    placeholder="0,00"
                  />
                </label>

                <label
                  className="field"
                  style={{ gridColumn: '1 / -1' }}
                >
                  <span>Observação</span>

                  <textarea
                    value={documentForm.observacao}
                    onChange={(event) =>
                      setDocumentForm((current) => ({
                        ...current,
                        observacao:
                          event.target.value,
                      }))
                    }
                  />
                </label>
              </div>

              <button
                type="button"
                className="primary-button"
                onClick={() =>
                  void handleCreateDocument()
                }
                disabled={documentSaving}
              >
                <FilePlus2 size={16} />

                {documentSaving
                  ? 'Salvando...'
                  : 'Registrar documento'}
              </button>
            </section>

            <section className="panel">
              <div className="section-title">
                <div className="section-icon">
                  <ReceiptText size={17} />
                </div>

                <div>
                  <h2>O que o contador enviou</h2>
                  <p>
                    Guias, impostos, honorários e valores
                    recebidos para pagamento.
                  </p>
                </div>
              </div>

              <div
                className="form-grid"
                style={{ marginTop: 18 }}
              >
                <label className="field">
                  <span>Tipo</span>

                  <select
                    value={obligationForm.tipo_obrigacao}
                    onChange={(event) =>
                      setObligationForm((current) => ({
                        ...current,
                        tipo_obrigacao:
                          event.target.value,
                      }))
                    }
                  >
                    <option value="DAS">DAS</option>
                    <option value="DARF">DARF</option>
                    <option value="FGTS">FGTS</option>
                    <option value="INSS">INSS</option>
                    <option value="IMPOSTO">
                      Imposto
                    </option>
                    <option value="HONORARIOS_CONTABEIS">
                      Honorários contábeis
                    </option>
                    <option value="TAXA">
                      Taxa
                    </option>
                    <option value="OUTRO">
                      Outro
                    </option>
                  </select>
                </label>

                <label className="field">
                  <span>Descrição</span>

                  <input
                    value={obligationForm.descricao}
                    onChange={(event) =>
                      setObligationForm((current) => ({
                        ...current,
                        descricao:
                          event.target.value,
                      }))
                    }
                    placeholder="Ex: DAS setembro/2026"
                  />
                </label>

                <label className="field">
                  <span>Valor</span>

                  <input
                    inputMode="decimal"
                    value={obligationForm.valor}
                    onChange={(event) =>
                      setObligationForm((current) => ({
                        ...current,
                        valor: event.target.value,
                      }))
                    }
                    placeholder="0,00"
                  />
                </label>

                <label className="field">
                  <span>Vencimento</span>

                  <input
                    type="date"
                    value={obligationForm.vencimento}
                    onChange={(event) =>
                      setObligationForm((current) => ({
                        ...current,
                        vencimento:
                          event.target.value,
                      }))
                    }
                  />
                </label>

                <label
                  className="field"
                  style={{ gridColumn: '1 / -1' }}
                >
                  <span>Observação</span>

                  <textarea
                    value={obligationForm.observacao}
                    onChange={(event) =>
                      setObligationForm((current) => ({
                        ...current,
                        observacao:
                          event.target.value,
                      }))
                    }
                  />
                </label>
              </div>

              <button
                type="button"
                className="primary-button"
                onClick={() =>
                  void handleCreateObligation()
                }
                disabled={obligationSaving}
              >
                <ReceiptText size={16} />

                {obligationSaving
                  ? 'Salvando...'
                  : 'Registrar obrigação'}
              </button>
            </section>
          </div>

          <section
            className="panel"
            style={{ marginTop: 18 }}
          >
            <div className="section-title">
              <div className="section-icon">
                <FileCheck2 size={17} />
              </div>

              <div>
                <h2>Documentos fiscais do mês</h2>
                <p>
                  Produtos e serviços separados para
                  o fechamento com o contador.
                </p>
              </div>
            </div>

            {documents.length === 0 ? (
              <div className="loading-state">
                Nenhum documento fiscal registrado para
                {` ${competence}`}.
              </div>
            ) : (
              <div className="table-wrap">
                <ColumnManager storageKey="smarttec:columns:accounting-documents" lockedColumns={['number']} columns={[{ id: 'type', label: 'Tipo', defaultVisible: true }, { id: 'number', label: 'Número', defaultVisible: true }, { id: 'issueDate', label: 'Emissão', defaultVisible: true }, { id: 'notes', label: 'Observação', defaultVisible: true }, { id: 'amount', label: 'Valor', defaultVisible: true }]}><table>
                  <thead>
                    <tr>
                      <th>Tipo</th>
                      <th>Número</th>
                      <th>Emissão</th>
                      <th>Observação</th>
                      <th style={{ textAlign: 'right' }}>
                        Valor
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {documents.map((document) => (
                      <tr key={document.id}>
                        <td>
                          {documentTypeLabel(
                            document.tipo_documento,
                          )}
                        </td>
                        <td>
                          {document.numero || '-'}
                        </td>
                        <td>
                          {document.data_emissao}
                        </td>
                        <td>
                          {document.observacao || '-'}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <strong>
                            {money(document.valor)}
                          </strong>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table></ColumnManager>
              </div>
            )}
          </section>

          <section
            className="panel"
            style={{ marginTop: 18 }}
          >
            <div className="section-title">
              <div className="section-icon">
                <WalletCards size={17} />
              </div>

              <div>
                <h2>Obrigações e pagamentos</h2>
                <p>
                  Controle do que o contador enviou,
                  do que foi para o Financeiro e do
                  que já foi pago.
                </p>
              </div>
            </div>

            {obligations.length === 0 ? (
              <div className="loading-state">
                Nenhuma obrigação registrada para
                {` ${competence}`}.
              </div>
            ) : (
              <div className="table-wrap">
                <ColumnManager storageKey="smarttec:columns:accounting-obligations" lockedColumns={['description', 'actions']} columns={[{ id: 'type', label: 'Tipo', defaultVisible: true }, { id: 'description', label: 'Descrição', defaultVisible: true }, { id: 'dueDate', label: 'Vencimento', defaultVisible: true }, { id: 'status', label: 'Status', defaultVisible: true }, { id: 'financial', label: 'Financeiro', defaultVisible: true }, { id: 'amount', label: 'Valor', defaultVisible: true }, { id: 'actions', label: 'Ações', defaultVisible: true }]}><table>
                  <thead>
                    <tr>
                      <th>Tipo</th>
                      <th>Descrição</th>
                      <th>Vencimento</th>
                      <th>Status</th>
                      <th>Financeiro</th>
                      <th style={{ textAlign: 'right' }}>
                        Valor
                      </th>
                      <th>Ações</th>
                    </tr>
                  </thead>

                  <tbody>
                    {obligations.map((obligation) => (
                      <tr key={obligation.id}>
                        <td>
                          {obligationTypeLabel(
                            obligation.tipo_obrigacao,
                          )}
                        </td>

                        <td>
                          <strong>
                            {obligation.descricao}
                          </strong>
                        </td>

                        <td>
                          {obligation.vencimento}
                        </td>

                        <td>
                          <span className="draft-badge">
                            {statusLabel(
                              obligation.status,
                            )}
                          </span>
                        </td>

                        <td>
                          {obligation.financeiro_id
                            ? `#${obligation.financeiro_id}`
                            : '-'}
                        </td>

                        <td style={{ textAlign: 'right' }}>
                          <strong>
                            {money(obligation.valor)}
                          </strong>
                        </td>

                        <td>
                          <div
                            style={{
                              display: 'flex',
                              gap: 8,
                              flexWrap: 'wrap',
                            }}
                          >
                            {!obligation.financeiro_id &&
                              obligation.status !== 'PAGO' &&
                              obligation.status !==
                                'CANCELADO' && (
                                <button
                                  type="button"
                                  className="secondary-button"
                                  disabled={
                                    actionId ===
                                    obligation.id
                                  }
                                  onClick={() =>
                                    void handleGeneratePayable(
                                      obligation,
                                    )
                                  }
                                >
                                  Gerar conta a pagar
                                </button>
                              )}

                            {Boolean(obligation.financeiro_id) &&
                              obligation.status !== 'PAGO' &&
                              obligation.status !==
                                'CANCELADO' && (
                                <button
                                  type="button"
                                  className="primary-button"
                                  disabled={
                                    actionId ===
                                    obligation.id
                                  }
                                  onClick={() =>
                                    void handlePaid(
                                      obligation,
                                    )
                                  }
                                >
                                  Marcar pago
                                </button>
                              )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table></ColumnManager>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}


function Kpi({
  icon,
  label,
  value,
  small,
}: {
  icon: React.ReactNode
  label: string
  value: string
  small: string
}) {
  return (
    <article className="budget-kpi dark">
      <div className="budget-kpi-icon">
        {icon}
      </div>

      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{small}</small>
      </div>
    </article>
  )
}