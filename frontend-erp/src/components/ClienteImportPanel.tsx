import { useRef, useState } from 'react'
import { Download, Upload, X } from 'lucide-react'
import {
  confirmClientImport, inspectClientImport, previewClientImport,
  type ImportConfig, type ImportPreview, type ImportReport, type ImportRow, type ImportTable, type ImportSourceConfig, type ImportRelatedFiles,
} from '../services/clienteImport'
import { getEmpresaId } from '../services/auth'
import { commercialDisplayText } from '../utils/commercialDisplay'
import { gestaoClickMapping } from '../utils/gestaoClickMapping'
import './clienteImport.css'

const campos = [
  ['nome', 'Nome *'], ['tipo', 'Tipo (Física / Jurídica)'], ['documento', 'CPF / CNPJ'], ['cpf', 'CPF separado'], ['cnpj', 'CNPJ separado'],
  ['email', 'E-mail'], ['telefone_comercial', 'Telefone comercial'], ['telefone_celular', 'Telefone celular'],
  ['cep', 'CEP'], ['logradouro', 'Logradouro'], ['numero', 'Número'], ['complemento', 'Complemento'],
  ['bairro', 'Bairro'], ['cidade', 'Cidade'], ['estado', 'UF'], ['site', 'Site'],
  ['vendedor_responsavel', 'Vendedor / responsável'], ['observacoes', 'Observações'],
] as const

const initialConfig: ImportConfig = {
  codigo_cliente: null, enderecos: null, contatos: null, complementar_vazios: false, ignorar_inconsistencias: false,
  mapeamento: {}, linha_cabecalho: 1, aba: null, separador: 'auto', encoding: 'auto', tipo_padrao: 'Física',
}

const statusNames: Record<ImportRow['status'], string> = {
  complementar: 'Complementar campos vazios', complementado: 'Complementado', revisar: 'Revisão necessária',
  inserir: 'Será inserido', ignorado: 'Ignorado', erro: 'Erro', inserido: 'Inserido', nao_importado: 'Não importado',
}

export function ClienteImportPanel({ onComplete, onClose, onBusyChange }: { onComplete: () => Promise<void>; onClose: () => void; onBusyChange?: (busy: boolean) => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [config, setConfig] = useState<ImportConfig>(initialConfig)
  const [table, setTable] = useState<ImportTable | null>(null)
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [report, setReport] = useState<ImportReport | null>(null)
  const [accepted, setAccepted] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [page, setPage] = useState(0)
  const [related, setRelated] = useState<ImportRelatedFiles>({})
  const [relatedTables, setRelatedTables] = useState<Partial<Record<'enderecos' | 'contatos', ImportTable>>>({})
  const busyRef = useRef(false)
  // Descarta resultado e bloqueia confirmação caso a empresa ativa tenha mudado.
  const company = useRef(getEmpresaId())
  const generation = useRef(0)

  function invalidate() {
    generation.current += 1
    setPreview(null)
    setReport(null)
    setAccepted(false)
    setError('')
    setPage(0)
  }

  function changeConfig(next: ImportConfig, tableChanged = false) {
    invalidate()
    setConfig(next)
    if (tableChanged) setTable(null)
  }

  function currentCompany() {
    if (getEmpresaId() !== company.current) {
      invalidate()
      throw new Error('A empresa ativa mudou. Feche e reabra a importação para gerar uma nova prévia.')
    }
  }

  async function run(action: 'inspect' | 'preview' | 'confirm') {
    if (!file || busyRef.current) return
    setError('')
    try {
      currentCompany()
      if (action !== 'inspect') {
        for (const source of ['enderecos', 'contatos'] as const) {
          if (related[source] && (config.codigo_cliente == null || config[source]?.codigo_cliente == null)) {
            throw new Error('Mapeie o código do cliente no arquivo principal e em cada arquivo relacionado.')
          }
        }
      }
      const version = generation.current
      busyRef.current = true
      setBusy(true)
      onBusyChange?.(true)
      if (action === 'inspect') {
        const result = await inspectClientImport(file, config)
        currentCompany()
        if (version !== generation.current) return
        setTable(result)
        setPreview(null)
        setReport(null)
        setAccepted(false)
      } else if (action === 'preview') {
        const result = await previewClientImport(file, config, related)
        currentCompany()
        if (version !== generation.current) return
        setPreview(result)
        setTable(result)
        setReport(null)
        setAccepted(false)
        setPage(0)
      } else if (preview && accepted && (config.ignorar_inconsistencias || (preview.erros === 0 && (preview.inconsistencias ?? 0) === 0))) {
        const result = await confirmClientImport(file, config, preview.previa_hash, related)
        currentCompany()
        if (version !== generation.current) return
        setReport(result)
        setPreview(null)
        setAccepted(false)
        setPage(0)
        if (result.concluido) await onComplete()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível processar a importação.')
    } finally {
      busyRef.current = false
      setBusy(false)
      onBusyChange?.(false)
    }
  }

  async function inspectRelated(source: 'enderecos' | 'contatos') {
    const sourceFile = related[source], options = config[source]
    if (!sourceFile || !options || busyRef.current) return
    const version = generation.current
    try {
      currentCompany(); busyRef.current = true; setBusy(true); onBusyChange?.(true); setError('')
      const result = await inspectClientImport(sourceFile, { ...initialConfig, ...options, mapeamento: {}, codigo_cliente: null })
      currentCompany()
      if (version === generation.current) setRelatedTables(current => ({ ...current, [source]: result }))
    } catch (err) { setError(err instanceof Error ? err.message : 'Não foi possível ler o arquivo relacionado.') }
    finally { busyRef.current = false; setBusy(false); onBusyChange?.(false) }
  }

  function downloadReport() {
    const result = report ?? preview
    if (!result) return
    const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: 'application/json;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = report ? 'relatorio-importacao-clientes.json' : 'previa-importacao-clientes.json'
    link.click()
    URL.revokeObjectURL(url)
  }

  const rows = report?.linhas ?? preview?.linhas ?? []
  const pageCount = Math.max(1, Math.ceil(rows.length / 50))
  const actionCount = (preview?.inserir ?? 0) + (preview?.complementar ?? 0)
  const previewBlocked = Boolean(preview && !config.ignorar_inconsistencias && (preview.erros > 0 || (preview.inconsistencias ?? 0) > 0))
  return <section className="cliente-import" aria-labelledby="cliente-import-title" aria-busy={busy}>
    <div className="cliente-import-heading"><div><h2 className="commercial-title" id="cliente-import-title">Importar clientes do GestãoClick</h2>
      <p>Selecione CSV ou XLSX e associe as colunas do seu arquivo. Limite: 5 MB e 2.000 clientes por lote.</p></div>
      <button type="button" className="cad-secondary" aria-label="Fechar importação" onClick={onClose} disabled={busy}><X size={18} /></button></div>
    <p>Importação como clientes, sem classificação comercial obrigatória. As planilhas são relacionadas pelo código do cliente do backup, que não substitui o ID do ERP.
      Correspondências seguras usam documento ou nome exato e contato. Nomes semelhantes nunca autorizam uma alteração. Cadastros de teste são preservados.</p>
    <fieldset disabled={busy} className="cliente-import-options">
      <legend>1. Arquivo e leitura</legend>
      <label className="cliente-import-file">Arquivo CSV / XLSX<input type="file" accept=".csv,.xlsx" onChange={event => {
        invalidate(); setTable(null); setConfig(initialConfig); setRelated({}); setRelatedTables({})
        const selected = event.target.files?.[0] ?? null
        setFile(selected)
        if (selected && selected.size > 5 * 1024 * 1024) { setError('O arquivo deve ter até 5 MB.'); setFile(null) }
      }} /></label>
      <label>Linha do cabeçalho<input type="number" min={1} max={100} value={config.linha_cabecalho}
        onChange={event => changeConfig({ ...config, linha_cabecalho: Number(event.target.value), mapeamento: {} }, true)} /></label>
      <label>Separador CSV<select value={config.separador} onChange={event => changeConfig({ ...config, separador: event.target.value as ImportConfig['separador'], mapeamento: {} }, true)}>
        <option value="auto">Detectar</option><option value=";">Ponto e vírgula</option><option value=",">Vírgula</option><option value={'\t'}>Tabulação</option><option value="|">Barra vertical</option></select></label>
      <label>Codificação CSV<select value={config.encoding} onChange={event => changeConfig({ ...config, encoding: event.target.value as ImportConfig['encoding'], mapeamento: {} }, true)}>
        <option value="auto">Detectar</option><option value="utf-8-sig">UTF-8</option><option value="cp1252">Windows-1252</option></select></label>
      {(table?.abas.length ?? 0) > 0 && <label>Aba XLSX<select value={config.aba ?? table?.aba ?? ''} onChange={event => {
        // Mantém a lista de abas disponível até a próxima inspeção.
        invalidate(); setConfig({ ...config, aba: event.target.value, mapeamento: {} }); setTable(current => current ? { ...current, colunas: [], amostra: [] } : null)
      }}>{table?.abas.map(name => <option key={name} value={name}>{name}</option>)}</select></label>}
      <button type="button" className="cad-secondary" disabled={!file} onClick={() => void run('inspect')}>Ler colunas</button>
    </fieldset>
    {table && table.colunas.length > 0 && <>
      <p>{table.total} linha(s) encontrada(s). Confira a amostra antes de mapear. Nenhuma coluna é tratada como definitiva.</p>
      <div className="cliente-import-scroll"><table className="cad-table"><caption>Amostra original do arquivo</caption><thead><tr>{table.colunas.map((name, index) => <th key={index}>{index + 1}. {name}</th>)}</tr></thead>
        <tbody>{table.amostra.map((row, index) => <tr key={index}>{table.colunas.map((_, column) => <td key={column}>{row[column] || '—'}</td>)}</tr>)}</tbody></table></div>
      <fieldset disabled={busy} className="cliente-import-options"><legend>2. Mapeamento de colunas</legend>
        <label>Código do cliente no backup<select value={config.codigo_cliente ?? ''} onChange={event => changeConfig({ ...config, codigo_cliente: event.target.value === '' ? null : Number(event.target.value) })}>
          <option value="">Sem vínculo entre planilhas</option>{table.colunas.map((name, index) => <option key={index} value={index}>{index + 1}. {name}</option>)}</select></label>
        {campos.map(([key, label]) => <label key={key}>{label}<select value={config.mapeamento[key] ?? ''} onChange={event => {
          const mapping = { ...config.mapeamento }
          if (event.target.value === '') delete mapping[key]; else mapping[key] = Number(event.target.value)
          changeConfig({ ...config, mapeamento: mapping })
        }}><option value="">Não importar</option>{table.colunas.map((name, index) => <option key={index} value={index}
          disabled={Object.entries(config.mapeamento).some(([field, mapped]) => field !== key && mapped === index)}>{index + 1}. {name}</option>)}</select></label>)}
        <label>Tipo quando não houver documento ou coluna Tipo<select value={config.tipo_padrao} onChange={event => changeConfig({ ...config, tipo_padrao: event.target.value as ImportConfig['tipo_padrao'] })}>
          <option>Física</option><option>Jurídica</option></select></label>
        <p>Com documento e sem coluna Tipo, CPF define Física e CNPJ define Jurídica. Endereço e contato ausentes geram avisos; valores inválidos geram erros.</p>
      </fieldset>
      {(['enderecos', 'contatos'] as const).map(source => <RelatedSource key={source} source={source} file={related[source] ?? null} config={config[source] ?? null} table={relatedTables[source] ?? null} busy={busy}
        onFile={selected => {
          invalidate(); setRelated(current => ({ ...current, [source]: selected })); setRelatedTables(current => ({ ...current, [source]: undefined }))
          setConfig(current => ({ ...current, [source]: selected ? { ...initialSourceConfig } : null }))
        }} onConfig={(next, changed) => { invalidate(); setConfig(current => ({ ...current, [source]: next })); if (changed) setRelatedTables(current => current[source] ? { ...current, [source]: { ...current[source]!, colunas: [], amostra: [] } } : current) }}
        onInspect={() => void inspectRelated(source)} />)}
      <button type="button" className="cad-secondary" disabled={busy || !relatedTables.enderecos || !relatedTables.contatos}
        onClick={() => {
          try {
            if (!relatedTables.enderecos || !relatedTables.contatos) return
            changeConfig(gestaoClickMapping(config, table, relatedTables.enderecos, relatedTables.contatos))
          } catch (err) { setError(err instanceof Error ? err.message : 'Não foi possível aplicar o mapeamento.') }
        }}>Aplicar mapeamento do backup GestãoClick</button>
      <p>Leia as três planilhas antes de aplicar o mapeamento. O código relaciona somente as fontes; não é o ID do ERP.
        CPF/CNPJ, CEP e telefones incompletos ficam pendentes, sem completar dígitos automaticamente.</p>
      <fieldset disabled={busy} className="cliente-import-summary"><legend>Proteção dos cadastros existentes</legend>
        <label className="cliente-import-accept"><input type="checkbox" checked={Boolean(config.complementar_vazios)} onChange={event => changeConfig({ ...config, complementar_vazios: event.target.checked })} />
          Permitir complementar somente campos vazios em correspondências seguras. O ID e os vínculos com orçamentos serão mantidos; campos preenchidos nunca serão substituídos.</label>
        <label className="cliente-import-accept"><input type="checkbox" checked={Boolean(config.ignorar_inconsistencias)} onChange={event => changeConfig({ ...config, ignorar_inconsistencias: event.target.checked })} />
          Processar somente as linhas validadas e manter inconsistências pendentes no relatório. Sem esta opção, uma inconsistência bloqueia o lote inteiro.</label>
      </fieldset>
      <button type="button" className="cad-secondary" disabled={busy || config.mapeamento.nome == null} onClick={() => void run('preview')}>Gerar prévia sem gravar</button>
    </>}
    {preview && <div className="cliente-import-summary"><h3 className="commercial-title">3. Confira a prévia</h3><p>{preview.inserir} para inserir · {preview.complementar ?? 0} para complementar · {preview.ignorados} duplicidade(s) ignorada(s) · {preview.inconsistencias ?? 0} inconsistência(s) · {preview.erros} com erro.</p>
      {previewBlocked && <p role="alert">Revise as inconsistências e gere outra prévia. Nenhum cadastro será gravado enquanto o lote estiver bloqueado.</p>}
      {config.ignorar_inconsistencias && ((preview.erros + (preview.inconsistencias ?? 0)) > 0) && <p role="status">As linhas inconsistentes serão ignoradas por sua escolha e continuarão identificadas no relatório.</p>}
      <button type="button" className="cad-secondary" onClick={downloadReport}><Download size={16} /> Baixar prévia sem gravar</button>
      <label className="cliente-import-accept"><input type="checkbox" checked={accepted} disabled={busy || previewBlocked || actionCount === 0} onChange={event => setAccepted(event.target.checked)} />
        Conferi a prévia e autorizo {preview.inserir} inserção(ões) e {preview.complementar ?? 0} complementação(ões) na empresa ativa, com IDs preservados. Duplicados e linhas pendentes não serão substituídos.</label>
      <button type="button" className="primary-button" disabled={busy || !accepted || previewBlocked || actionCount === 0} onClick={() => void run('confirm')}><Upload size={16} /> {busy ? 'Processando…' : `Confirmar ${actionCount} cliente(s)`}</button></div>}
    {report && <div className="cliente-import-summary" role={report.concluido ? 'status' : 'alert'}><h3 className="commercial-title">Relatório do lote</h3><p>{report.mensagem}</p>
      <p>{report.inseridos} inserido(s) · {report.complementados ?? 0} complementado(s) · {report.ignorados} ignorado(s) · {report.inconsistencias ?? 0} inconsistência(s) · {report.erros} com erro · {report.nao_importados} não importado(s).</p>
      <button type="button" className="cad-secondary" onClick={downloadReport}><Download size={16} /> Baixar relatório</button></div>}
    {(report ?? preview) && <div className="cliente-import-summary">
      <h3 className="commercial-title">Vínculos das fontes</h3>
      {Object.entries((report ?? preview)?.fontes ?? {}).map(([name, source]) =>
        <p key={name}>{name}: {source.total} linha(s){name !== 'clientes' && ` · ${source.vinculados ?? 0} vinculada(s) · ${source.sem_vinculo ?? 0} sem vínculo`}</p>)}
      {((report ?? preview)?.ocorrencias ?? []).map((message, index) => <p key={index} role="alert">{message}</p>)}
    </div>}
    {rows.length > 0 && <><div className="cliente-import-scroll"><table className="cad-table"><caption>{report ? 'Resultado por linha' : 'Prévia por linha'}</caption>
      <thead><tr><th>Linha / código</th><th>Nome</th><th>CPF / CNPJ</th><th>Contato</th><th>Endereço</th><th>Situação / ID preservado</th><th>Complementos / motivos / avisos</th></tr></thead>
      <tbody>{rows.slice(page * 50, (page + 1) * 50).map(row => <tr key={row.linha}><td>{row.linha}{row.codigo_cliente && <small>Código: {row.codigo_cliente}</small>}</td><td>{commercialDisplayText(row.dados.nome ?? '') || '—'}</td><td>{row.dados.documento || '—'}</td>
        <td>{[row.dados.email, row.dados.telefone_comercial, row.dados.telefone_celular].filter(Boolean).join(' · ') || '—'}</td>
        <td>{[row.dados.logradouro, row.dados.numero, row.dados.complemento, row.dados.bairro, row.dados.cidade, row.dados.estado, row.dados.cep].filter(Boolean).map(value => commercialDisplayText(value ?? '')).join(', ') || '—'}</td>
        <td>{statusNames[row.status]}{row.cliente_existente_id != null && <small>ID ERP: {row.cliente_existente_id}</small>}</td><td>{Object.entries(row.campos_complementar ?? {}).map(([field, value]) => <div key={field}><strong>{campos.find(([key]) => key === field)?.[1] ?? field}:</strong> {['nome','logradouro','numero','complemento','bairro','cidade','estado'].includes(field) ? commercialDisplayText(value ?? '') : value}</div>)}{[...(row.conflitos ?? []), ...row.motivos, ...row.avisos].join(' ') || 'Validado'}</td></tr>)}</tbody></table></div>
      <div className="cliente-import-pagination"><button type="button" className="cad-secondary" disabled={page === 0} onClick={() => setPage(current => current - 1)}>Anterior</button>
        <span>Página {page + 1} de {pageCount}</span><button type="button" className="cad-secondary" disabled={page + 1 >= pageCount} onClick={() => setPage(current => current + 1)}>Próxima</button></div></>}
    {busy && <p role="status">Processando arquivo. Aguarde a confirmação da API.</p>}
    {error && <div className="cad-error" role="alert">{error}</div>}
  </section>
}


type RelatedSourceName = 'enderecos' | 'contatos'
const initialSourceConfig: ImportSourceConfig = { codigo_cliente:null, mapeamento:{}, linha_cabecalho:1, aba:null, separador:'auto', encoding:'auto' }
const relatedFields: Record<RelatedSourceName, readonly (readonly [string,string])[]> = {
  enderecos: [['cep','CEP'],['logradouro','Logradouro'],['numero','Número'],['complemento','Complemento'],['bairro','Bairro'],['cidade','Cidade'],['estado','UF'],['tipo_endereco','Tipo de endereço']],
  contatos: [['contato','Contato (e-mail ou telefone)'],['nome_contato','Nome do contato'],['tipo_contato','Tipo do contato'],['cargo','Cargo'],['email','E-mail'],['telefone_comercial','Telefone comercial'],['telefone_celular','Telefone celular'],['observacao_contato','Observações do contato']],
}
function RelatedSource({ source, file, config, table, busy, onFile, onConfig, onInspect }: {
  source:RelatedSourceName; file:File|null; config:ImportSourceConfig|null; table:ImportTable|null; busy:boolean;
  onFile:(file:File|null)=>void; onConfig:(config:ImportSourceConfig, changed?:boolean)=>void; onInspect:()=>void;
}) {
  const label = source === 'enderecos' ? 'Endereços' : 'Contatos adicionais'
  const options = config ?? initialSourceConfig
  return <fieldset disabled={busy} className="cliente-import-options"><legend>{label} — arquivo relacionado opcional</legend>
    <label className="cliente-import-file">Arquivo CSV / XLSX de {label.toLocaleLowerCase('pt-BR')}<input type="file" accept=".csv,.xlsx" onChange={event => onFile(event.target.files?.[0] ?? null)} /></label>
    {file && <>
      <label>Linha do cabeçalho<input type="number" min={1} max={100} value={options.linha_cabecalho} onChange={event => onConfig({ ...options, linha_cabecalho:Number(event.target.value), mapeamento:{}, codigo_cliente:null },true)} /></label>
      <label>Separador CSV<select value={options.separador} onChange={event => onConfig({ ...options, separador:event.target.value as ImportSourceConfig['separador'], mapeamento:{}, codigo_cliente:null },true)}><option value="auto">Detectar</option><option value=";">Ponto e vírgula</option><option value=",">Vírgula</option><option value={'\t'}>Tabulação</option><option value="|">Barra vertical</option></select></label>
      <label>Codificação CSV<select value={options.encoding} onChange={event => onConfig({ ...options, encoding:event.target.value as ImportSourceConfig['encoding'] },true)}><option value="auto">Detectar</option><option value="utf-8-sig">UTF-8</option><option value="cp1252">Windows-1252</option></select></label>
      {(table?.abas.length ?? 0) > 0 && <label>Aba XLSX<select value={options.aba ?? table?.aba ?? ''} onChange={event => onConfig({ ...options, aba:event.target.value, mapeamento:{}, codigo_cliente:null },true)}>{table?.abas.map(name => <option key={name} value={name}>{name}</option>)}</select></label>}
      <button type="button" className="cad-secondary" onClick={onInspect}>Ler colunas de {label.toLocaleLowerCase('pt-BR')}</button>
      <button type="button" className="cad-secondary" onClick={() => onFile(null)}>Remover arquivo relacionado</button>
      {table && table.colunas.length > 0 && <>
        <p>{table.total} linha(s). O vínculo usa somente o código do cliente do arquivo principal.</p>
        <label>Código do cliente *<select value={options.codigo_cliente ?? ''} onChange={event => onConfig({ ...options, codigo_cliente:event.target.value === '' ? null : Number(event.target.value) })}><option value="">Selecione a coluna</option>{table.colunas.map((name,index) => <option key={index} value={index}>{index + 1}. {name}</option>)}</select></label>
        {relatedFields[source].map(([field,title]) => <label key={field}>{title}<select value={options.mapeamento[field] ?? ''} onChange={event => {
          const mapping = { ...options.mapeamento }; if(event.target.value === '')delete mapping[field]; else mapping[field]=Number(event.target.value)
          onConfig({ ...options, mapeamento:mapping })
        }}><option value="">Não importar</option>{table.colunas.map((name,index) => <option key={index} value={index} disabled={index === options.codigo_cliente || Object.entries(options.mapeamento).some(([key,value]) => key !== field && value === index)}>{index + 1}. {name}</option>)}</select></label>)}
        <div className="cliente-import-scroll cliente-import-original"><table className="cad-table"><caption>Amostra original: {label}</caption><thead><tr>{table.colunas.map((name,index)=><th key={index}>{name}</th>)}</tr></thead><tbody>{table.amostra.map((row,index)=><tr key={index}>{row.map((value,column)=><td key={column}>{value || '—'}</td>)}</tr>)}</tbody></table></div>
      </>}
    </>}
  </fieldset>
}
