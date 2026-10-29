import { ColumnManager } from '../components/ColumnManager'
import { useEffect, useMemo, useState } from 'react'
import { Eye, Pencil, Plus, Search, Trash2, X } from 'lucide-react'
import {
  createCommercialPartner,
  createRepresentative,
  getCommercialPartnersCadastro,
  getRepresentativesCadastro,
  createClienteCadastro,
  createFornecedorCadastro,
  createFuncionarioCadastro,
  createTransportadoraCadastro,
  deleteClienteCadastro,
  deleteFornecedorCadastro,
  deleteFuncionarioCadastro,
  deleteTransportadoraCadastro,
  getClientesCadastro,
  getFornecedoresCadastro,
  getFuncionariosCadastro,
  getTransportadorasCadastro,
  updateClienteCadastro,
  updateFornecedorCadastro,
  updateFuncionarioCadastro,
  updateTransportadoraCadastro,
  type CadastroPayload,
  getCommercialPartners,
  getRepresentatives,
  type ApiCommercialPartner,
  type ApiRepresentative,
  type CadastroRecord,
} from '../services/api'
import './cadastrosPage.css'

export type CadastroEntity =
  | 'clientes'
  | 'revendas'
  | 'representantes'
  | 'fornecedores'
  | 'transportadoras'
  | 'funcionarios'

type FieldType = 'text' | 'number' | 'textarea' | 'boolean' | 'select'

type FieldConfig = {
  key: string
  label: string
  type?: FieldType
  required?: boolean
  options?: string[]
  step?: string
}

type EntityConfig = {
  title: string
  singular: string
  fields: FieldConfig[]
  listColumns: string[]
  load: () => Promise<CadastroRecord[]>
  create: (payload: CadastroPayload) => Promise<CadastroRecord>
  update?: (id: number, payload: CadastroPayload) => Promise<CadastroRecord>
  remove?: (id: number) => Promise<unknown>
}

const situacaoField: FieldConfig = {
  key: 'situacao',
  label: 'Situação',
  type: 'select',
  options: ['Ativo', 'Inativo', 'Bloqueado'],
}

const configs: Record<CadastroEntity, EntityConfig> = {
  revendas: {
    title: 'Revendas', singular: 'Revenda',
    load: getCommercialPartnersCadastro, create: createCommercialPartner,
    listColumns: ['nome', 'documento', 'email', 'telefone', 'percentual_padrao'],
    fields: [
      { key: 'nome', label: 'Nome', required: true },
      { key: 'documento', label: 'CPF / CNPJ' },
      { key: 'email', label: 'E-mail' },
      { key: 'telefone', label: 'Telefone' },
      { key: 'percentual_padrao', label: '% revenda padrão', type: 'number', step: '0.0001' },
      { key: 'observacao', label: 'Observações', type: 'textarea' },
    ],
  },
  representantes: {
    title: 'Representantes', singular: 'Representante',
    load: getRepresentativesCadastro, create: createRepresentative,
    listColumns: ['nome', 'documento', 'email', 'telefone', 'tipo_rt_padrao'],
    fields: [
      { key: 'nome', label: 'Nome', required: true },
      { key: 'documento', label: 'CPF / CNPJ' },
      { key: 'email', label: 'E-mail' },
      { key: 'telefone', label: 'Telefone' },
      { key: 'tipo_rt_padrao', label: 'Tipo de RT padrão', type: 'select', options: ['PERCENTUAL', 'VALOR_FIXO'] },
      { key: 'percentual_rt_padrao', label: 'Percentual RT padrão (%)', type: 'number', step: '0.0001' },
      { key: 'valor_rt_padrao', label: 'Valor RT padrão', type: 'number', step: '0.01' },
      { key: 'observacao', label: 'Observações', type: 'textarea' },
    ],
  },
  clientes: {
    title: 'Clientes',
    singular: 'Cliente',
    listColumns: ['nome', 'tipo', 'documento', 'telefone_celular', 'cidade', 'situacao'],
    load: getClientesCadastro,
    create: createClienteCadastro,
    update: updateClienteCadastro,
    remove: deleteClienteCadastro,
    fields: [
      {
        key: 'tipo',
        label: 'Tipo de cliente',
        type: 'select',
        required: true,
        options: ['Selecione', 'Física', 'Jurídica'],
      },
      situacaoField,
      { key: 'nome', label: 'Nome', required: true },
      { key: 'documento', label: 'CPF / CNPJ' },
      { key: 'email', label: 'E-mail' },
      { key: 'telefone_comercial', label: 'Telefone comercial' },
      { key: 'telefone_celular', label: 'Telefone celular' },
      { key: 'site', label: 'Site' },
      { key: 'vendedor_responsavel', label: 'Vendedor / Responsável' },
      { key: 'cep', label: 'CEP' },
      { key: 'logradouro', label: 'Logradouro' },
      { key: 'numero', label: 'Número' },
      { key: 'complemento', label: 'Complemento' },
      { key: 'bairro', label: 'Bairro' },
      { key: 'cidade', label: 'Cidade' },
      { key: 'estado', label: 'UF' },
      { key: 'limite_credito', label: 'Limite de crédito', type: 'number', step: '0.01' },
      { key: 'permitir_exceder', label: 'Permitir exceder limite', type: 'boolean' },
      { key: 'observacoes', label: 'Observações', type: 'textarea' },
    ],
  },

  fornecedores: {
    title: 'Fornecedores',
    singular: 'Fornecedor',
    listColumns: ['nome', 'tipo', 'documento', 'telefone_comercial', 'cidade', 'situacao'],
    load: getFornecedoresCadastro,
    create: createFornecedorCadastro,
    update: updateFornecedorCadastro,
    remove: deleteFornecedorCadastro,
    fields: [
      { key: 'nome', label: 'Nome', required: true },
      {
        key: 'tipo',
        label: 'Tipo de fornecedor',
        type: 'select',
        required: true,
        options: ['Selecione', 'Física', 'Jurídica'],
      },
      {
        key: 'situacao',
        label: 'Situação',
        type: 'select',
        options: ['Ativo', 'Inativo', 'Bloqueado'],
      },
      { key: 'documento', label: 'CPF / CNPJ' },
      { key: 'email', label: 'E-mail' },
      { key: 'site', label: 'Site' },
      { key: 'telefone_comercial', label: 'Telefone comercial' },
      { key: 'telefone_celular', label: 'Telefone celular' },
      { key: 'cep', label: 'CEP' },
      { key: 'logradouro', label: 'Logradouro' },
      { key: 'numero', label: 'Número' },
      { key: 'complemento', label: 'Complemento' },
      { key: 'bairro', label: 'Bairro' },
      { key: 'cidade', label: 'Cidade' },
      { key: 'estado', label: 'UF' },
      { key: 'observacoes', label: 'Observações', type: 'textarea' },
    ],
  },

  transportadoras: {
    title: 'Transportadoras',
    singular: 'Transportadora',
    listColumns: ['nome', 'tipo', 'documento', 'telefone', 'cidade_uf', 'situacao'],
    load: getTransportadorasCadastro,
    create: createTransportadoraCadastro,
    update: updateTransportadoraCadastro,
    remove: deleteTransportadoraCadastro,
    fields: [
      {
        key: 'tipo',
        label: 'Tipo de transportadora',
        type: 'select',
        required: true,
        options: ['Selecione', 'Pessoa Física', 'Pessoa Jurídica'],
      },
      {
        key: 'situacao',
        label: 'Situação',
        type: 'select',
        options: ['Ativo', 'Inativo'],
      },
      { key: 'nome', label: 'Nome', required: true },
      { key: 'documento', label: 'CPF / CNPJ' },
      { key: 'razao_social', label: 'Razão social' },
      { key: 'inscricao_estadual', label: 'Inscrição estadual' },
      { key: 'inscricao_municipal', label: 'Inscrição municipal' },
      { key: 'responsavel', label: 'Responsável' },
      { key: 'email', label: 'E-mail' },
      { key: 'telefone', label: 'Telefone' },
      { key: 'celular', label: 'Celular' },
      { key: 'cep', label: 'CEP' },
      { key: 'logradouro', label: 'Logradouro' },
      { key: 'numero', label: 'Número' },
      { key: 'complemento', label: 'Complemento' },
      { key: 'bairro', label: 'Bairro' },
      { key: 'cidade_uf', label: 'Cidade / UF' },
      { key: 'observacoes', label: 'Observações', type: 'textarea' },
    ],
  },

  funcionarios: {
    title: 'Funcionários',
    singular: 'Funcionário',
    listColumns: ['nome', 'cargo', 'departamento', 'telefone', 'email', 'situacao'],
    load: getFuncionariosCadastro,
    create: createFuncionarioCadastro,
    update: updateFuncionarioCadastro,
    remove: deleteFuncionarioCadastro,
    fields: [
      { key: 'nome', label: 'Nome', required: true },
      { key: 'cpf', label: 'CPF' },
      { key: 'rg', label: 'RG' },
      { key: 'data_nascimento', label: 'Data de nascimento' },
      {
        key: 'sexo',
        label: 'Sexo',
        type: 'select',
        options: ['Selecione', 'Masculino', 'Feminino', 'Outro'],
      },
      { key: 'email', label: 'E-mail' },
      {
        key: 'comissao',
        label: 'Comissão (%)',
        type: 'number',
        step: '0.5',
      },
      situacaoField,
      {
        key: 'permite_acesso',
        label: 'Permitir acesso ao sistema',
        type: 'boolean',
      },
      { key: 'cargo', label: 'Cargo' },
      { key: 'departamento', label: 'Departamento' },
      { key: 'salario', label: 'Salário', type: 'number', step: '0.01' },
      { key: 'telefone', label: 'Telefone' },
      { key: 'celular1', label: 'Celular 1' },
      { key: 'celular2', label: 'Celular 2' },
      { key: 'cep', label: 'CEP' },
      { key: 'logradouro', label: 'Logradouro' },
      { key: 'numero', label: 'Número' },
      { key: 'complemento', label: 'Complemento' },
      { key: 'bairro', label: 'Bairro' },
      { key: 'cidade', label: 'Cidade' },
      { key: 'estado', label: 'UF' },
      { key: 'observacoes', label: 'Observações', type: 'textarea' },
    ],
  },
}

function emptyPayload(config: EntityConfig): CadastroPayload {
  const payload: CadastroPayload = {}

  for (const field of config.fields) {
    if (field.key === 'tipo_rt_padrao') payload[field.key] = 'PERCENTUAL'
    else if (field.key === 'situacao') payload[field.key] = 'Ativo'
    else if (field.key === 'permitir_exceder') payload[field.key] = false
    else if (field.key === 'permite_acesso') payload[field.key] = 'Não'
    else if (field.type === 'number') payload[field.key] = 0
    else payload[field.key] = ''
  }

  return payload
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '?'
  if (typeof value === 'boolean') return value ? 'Sim' : 'Não'
  return String(value)
}

function labelFor(config: EntityConfig, key: string) {
  return config.fields.find((field) => field.key === key)?.label ?? key
}

export function CadastrosPage({ entity }: { entity: CadastroEntity }) {
  const config = configs[entity]

  const [items, setItems] = useState<CadastroRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [mode, setMode] = useState<'create' | 'edit' | 'view' | null>(null)
  const [selected, setSelected] = useState<CadastroRecord | null>(null)
  const [form, setForm] = useState<CadastroPayload>(() => emptyPayload(config))
  const [saving, setSaving] = useState(false)

  const [commercialPartners,setCommercialPartners]=
    useState<ApiCommercialPartner[]>([])

  const [commercialRepresentatives,setCommercialRepresentatives]=
    useState<ApiRepresentative[]>([])

  const [clientLinkType,setClientLinkType]=useState<
    'DIRETO'|'PARCEIRO'|'REPRESENTANTE'
  >('DIRETO')
  const reload = async () => {
    setLoading(true)
    setError('')

    try {
      setItems(await config.load())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar cadastro.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setMode(null)
    setSelected(null)
    setForm(emptyPayload(config))
    void reload()
  }, [entity])
  useEffect(()=>{
    if(entity!=='clientes'){
      setCommercialPartners([])
      setCommercialRepresentatives([])
      return
    }

    let cancelled=false

    void Promise.all([
      getCommercialPartners(),
      getRepresentatives(),
    ])
      .then(([partnerRows,representativeRows])=>{
        if(cancelled)return

        setCommercialPartners(partnerRows)
        setCommercialRepresentatives(representativeRows)
      })
      .catch(err=>{
        if(cancelled)return

        console.error(
          'Falha ao carregar vínculos comerciais',
          err,
        )
      })

    return ()=>{
      cancelled=true
    }
  },[entity])

  const filtered = useMemo(() => {
    const term = search.trim().toLocaleLowerCase('pt-BR')
    if (!term) return items

    return items.filter((item) =>
      Object.values(item).some((value) =>
        displayValue(value).toLocaleLowerCase('pt-BR').includes(term),
      ),
    )
  }, [items, search])

  const openCreate = () => {
    setSelected(null)
    setForm(emptyPayload(config))

    if(entity==='clientes'){
      setClientLinkType('DIRETO')
    }

    setMode('create')
  }

  const openRecord = (item: CadastroRecord, nextMode: 'edit' | 'view') => {
    setSelected(item)

    const payload = emptyPayload(config)
    for (const field of config.fields) {
      const value = item[field.key]
      if (value !== undefined && value !== null) {
        payload[field.key] = value as never
      }
    }

    if(entity==='clientes'){
      payload.parceiro_id =
        item.parceiro_id == null
          ? null
          : Number(item.parceiro_id)

      payload.representante_id =
        item.representante_id == null
          ? null
          : Number(item.representante_id)

      setClientLinkType('DIRETO')
    }

    setForm(payload)
    setMode(nextMode)
  }

  const closeForm = () => {
    setMode(null)
    setSelected(null)
  }

  const save = async () => {
    const missing = config.fields.find(
      (field) =>
        field.required &&
        String(form[field.key] ?? '').trim().length === 0,
    )

    if (missing) {
      setError(`O campo ${missing.label} ? obrigat?rio.`)
      return
    }

    if (entity === 'clientes' && form.tipo === 'Selecione') {
      setError('Selecione o tipo de cliente.')
      return
    }

    if (entity === 'fornecedores' && form.tipo === 'Selecione') {
      setError('Selecione o tipo de fornecedor.')
      return
    }

    if (entity === 'transportadoras' && form.tipo === 'Selecione') {
      setError('Selecione o tipo de transportadora.')
      return
    }

    if(

      entity==='clientes' &&

      clientLinkType==='PARCEIRO' &&

      !Number(form.parceiro_id)

    ){

      setError('Selecione a revenda.')

      return

    }


    if(

      entity==='clientes' &&

      clientLinkType==='REPRESENTANTE' &&

      !Number(form.representante_id)

    ){

      setError('Selecione o representante.')

      return

    }


    const payloadToSave: CadastroPayload =
      entity==='clientes'
        ? {
            ...form,
            parceiro_id:null,
            representante_id:null,
          }
        : form

    setSaving(true)

    setError('')

    try {
      if (mode === 'edit' && selected) {
        if (!config.update) return
        await config.update(selected.id, payloadToSave)
      } else {
        await config.create(payloadToSave)
      }

      closeForm()
      await reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao salvar cadastro.')
    } finally {
      setSaving(false)
    }
  }

  const remove = async (item: CadastroRecord) => {
    if (!config.remove) return
    if (!window.confirm(`Excluir ${config.singular.toLowerCase()} "${displayValue(item.nome)}"?`)) {
      return
    }

    setError('')

    try {
      await config.remove(item.id)
      await reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao excluir cadastro.')
    }
  }

  return (
    <section className="cad-page">
      <div className="cad-heading">
        <div>
          <p className="cad-eyebrow">CADASTROS</p>
          <h1>{config.title}</h1>
          <p>Gerencie os dados de {config.title.toLowerCase()} da empresa.</p>
        </div>

        <button className="primary-button" onClick={openCreate}>
          <Plus size={18} />
          {config.singular === 'Revenda' ? 'Nova' : 'Novo'} {config.singular.toLowerCase()}
        </button>
      </div>

      <div className="cad-toolbar">
        <div className="cad-search">
          <Search size={17} />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={`Buscar em ${config.title.toLowerCase()}...`}
          />
          {search && (
            <button onClick={() => setSearch('')} aria-label="Limpar busca">
              <X size={16} />
            </button>
          )}
        </div>

        <span>{filtered.length} registro(s)</span>
      </div>

      {!config.update && <p className="cad-empty">Listagem e inclusão disponíveis. Edição e exclusão aguardam suporte no backend.</p>}

      {error && <div className="cad-error">{error}</div>}

      <div className="cad-table-card">
        {loading ? (
          <div className="cad-empty">Carregando...</div>
        ) : filtered.length === 0 ? (
          <div className="cad-empty">Nenhum registro encontrado.</div>
        ) : (
          <div className="cad-table-wrap">
            <ColumnManager key={entity} storageKey={`smarttec:columns:${{ clientes: 'clients', revendas: 'resellers', representantes: 'representatives', fornecedores: 'suppliers', transportadoras: 'carriers', funcionarios: 'employees' }[entity]}`} lockedColumns={['nome', 'actions']} columns={[...config.listColumns.map(id => ({ id, label: labelFor(config, id), defaultVisible: true })), { id: 'actions', label: 'Ações', defaultVisible: true }]}><table className="cad-table">
              <thead>
                <tr>
                  {config.listColumns.map((column) => (
                    <th key={column}>{labelFor(config, column)}</th>
                  ))}
                  <th className="cad-actions-col">Ações</th>
                </tr>
              </thead>

              <tbody>
                {filtered.map((item) => (
                  <tr key={item.id}>
                    {config.listColumns.map((column) => (
                      <td key={column}>
                        {column === 'nome' ? (
                          <strong>{displayValue(item[column])}</strong>
                        ) : (
                          displayValue(item[column])
                        )}
                      </td>
                    ))}

                    <td>
                      <div className="cad-actions">
                        <button
                          title="Visualizar"
                          onClick={() => openRecord(item, 'view')}
                        >
                          <Eye size={16} />
                        </button>

                        <button
                          title={config.update ? 'Editar' : 'Edição indisponível: endpoint não implementado'}
                          disabled={!config.update}
                          onClick={() => openRecord(item, 'edit')}
                        >
                          <Pencil size={16} />
                        </button>

                        <button
                          title={config.remove ? 'Excluir' : 'Exclusão indisponível: endpoint não implementado'}
                          disabled={!config.remove}
                          className="danger"
                          onClick={() => void remove(item)}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table></ColumnManager>
          </div>
        )}
      </div>

      {mode && (
        <div className="cad-modal-backdrop" onMouseDown={closeForm}>
          <div
            className="cad-modal"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="cad-modal-header">
              <div>
                <span>
                  {mode === 'create'
                    ? 'NOVO CADASTRO'
                    : mode === 'edit'
                      ? 'EDITAR CADASTRO'
                      : 'VISUALIZAR CADASTRO'}
                </span>
                <h2>
                  {mode === 'create'
                    ? `${config.singular === 'Revenda' ? 'Nova' : 'Novo'} ${config.singular.toLowerCase()}`
                    : displayValue(selected?.nome)}
                </h2>
              </div>

              <button onClick={closeForm} aria-label="Fechar">
                <X size={19} />
              </button>
            </div>

            <div className="cad-form-grid">

              {config.fields.map((field) => {
                const value = form[field.key]

                if (field.type === 'textarea') {
                  return (
                    <label className="cad-field cad-field-full" key={field.key}>
                      <span>
                        {field.label}
                        {field.required && ' *'}
                      </span>
                      <textarea
                        disabled={mode === 'view'}
                        value={String(value ?? '')}
                        onChange={(event) =>
                          setForm((current) => ({
                            ...current,
                            [field.key]: event.target.value,
                          }))
                        }
                      />
                    </label>
                  )
                }

                if (field.type === 'boolean') {
                  return (
                    <label className="cad-checkbox" key={field.key}>
                      <input
                        type="checkbox"
                        disabled={mode === 'view'}
                        checked={
                          field.key === 'permite_acesso'
                            ? String(value ?? '').toLowerCase() === 'sim'
                            : Boolean(value)
                        }
                        onChange={(event) =>
                          setForm((current) => ({
                            ...current,
                            [field.key]:
                              field.key === 'permite_acesso'
                                ? event.target.checked
                                  ? 'Sim'
                                  : 'Não'
                                : event.target.checked,
                          }))
                        }
                      />
                      <span>{field.label}</span>
                    </label>
                  )
                }

                if (field.type === 'select') {
                  return (
                    <label className="cad-field" key={field.key}>
                      <span>
                        {field.label}
                        {field.required && ' *'}
                      </span>
                      <select
                        disabled={mode === 'view'}
                        value={String(value ?? '')}
                        onChange={(event) =>
                          setForm((current) => ({
                            ...current,
                            [field.key]: event.target.value,
                          }))
                        }
                      >
                        {(field.options ?? []).map((option) => (
                          <option value={option} key={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </label>
                  )
                }

                return (
                  <label className="cad-field" key={field.key}>
                    <span>
                      {field.label}
                      {field.required && ' *'}
                    </span>
                    <input
                      disabled={mode === 'view'}
                      type={field.type === 'number' ? 'number' : 'text'}
                      step={field.step}
                      value={String(value ?? '')}
                      onChange={(event) =>
                        setForm((current) => ({
                          ...current,
                          [field.key]:
                            field.type === 'number'
                              ? Number(event.target.value || 0)
                              : event.target.value,
                        }))
                      }
                    />
                  </label>
                )
              })}
            </div>

            <div className="cad-modal-footer">
              <button className="cad-secondary" onClick={closeForm}>
                {mode === 'view' ? 'Voltar' : 'Cancelar'}
              </button>

              {mode !== 'view' && (
                <button
                  className="primary-button"
                  disabled={saving}
                  onClick={() => void save()}
                >
                  {saving ? 'Salvando...' : 'Salvar'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
