import { useEffect, useState } from 'react'
import { getAllProducts } from '../services/api'
import type { ApiProduct } from '../types/budget'
import { useAuthSession } from '../components/AuthGate'
import { getFiscalEmpresa, getFiscalProduto, patchFiscalEmpresa, patchFiscalProduto } from '../services/fiscal'
import type { FiscalEmpresaDados, FiscalProdutoDados } from '../services/fiscal'
import './FiscalPage.css'
import { NfeGestaoClickPreview } from './NfeGestaoClickPreview'

type Field = { id:string; label:string; placeholder?:string }
const companyFields:Field[] = [
  {id:'inscricao_estadual',label:'Inscrição Estadual (IE)'},
  {id:'inscricao_municipal',label:'Inscrição Municipal (IM)'},
  {id:'cnae_principal',label:'CNAE principal (7 dígitos)'},
  {id:'regime_especial_tributacao',label:'Regime especial de tributação'},
  {id:'crt',label:'CRT (1 a 4)'},
  {id:'uf',label:'UF',placeholder:'SP'},
  {id:'municipio_codigo_ibge',label:'Código IBGE do município',placeholder:'3550308'},
  {id:'cidade',label:'Cidade'},
  {id:'cep',label:'CEP (8 dígitos)'},
  {id:'logradouro',label:'Logradouro'},
  {id:'numero',label:'Número'},
  {id:'bairro',label:'Bairro'},
  {id:'complemento',label:'Complemento'},
]
const productFields:Field[] = [
  {id:'ncm',label:'NCM (8 dígitos)'},{id:'cfop_padrao_saida',label:'CFOP de saída (4 dígitos)'},
  {id:'cest',label:'CEST (7 dígitos)'},{id:'origem_mercadoria',label:'Origem (0 a 8)'},
  {id:'cst_icms',label:'CST ICMS'},{id:'csosn',label:'CSOSN'},
  {id:'cst_pis',label:'CST PIS'},{id:'cst_cofins',label:'CST COFINS'},
  {id:'cst_ibs_cbs',label:'CST IBS/CBS'},{id:'cclass_trib_ibs_cbs',label:'cClassTrib IBS/CBS'},
]
const emptyCompany: FiscalEmpresaDados = {
  inscricao_estadual:null,inscricao_municipal:null,cnae_principal:null,regime_especial_tributacao:null,
  informacoes_complementares:null,crt:null,uf:null,municipio_codigo_ibge:null,cidade:null,
  cep:null,logradouro:null,numero:null,bairro:null,complemento:null,serie_nfe:null,ambiente:'HOMOLOGACAO',
}
const emptyProduct: FiscalProdutoDados = {
  ncm:null,cfop_padrao_saida:null,cest:null,origem_mercadoria:null,cst_icms:null,csosn:null,
  cst_pis:null,cst_cofins:null,cst_ibs_cbs:null,cclass_trib_ibs_cbs:null,
}

export function FiscalPage({ modoHomologacao = false }: { modoHomologacao?: boolean } = {}) {
  const session = useAuthSession()
  const canEdit = modoHomologacao || session?.empresa.papel === 'OWNER' || session?.empresa.papel === 'ADMIN'
  const companyId=modoHomologacao ? 999 : session?.empresa.id
  const [tab,setTab]=useState<'empresa'|'produto'|'nfe'|'certificado'|'configuracoes'|'confirmacao'>('empresa')
  const [company,setCompany]=useState<FiscalEmpresaDados>(emptyCompany)
  const [emitente,setEmitente]=useState({razao_social:'',nome_fantasia:'',documento:''})
  const [product,setProduct]=useState<FiscalProdutoDados>(emptyProduct)
  const [selectedId,setSelectedId]=useState<number|null>(null)
  const [catalog,setCatalog]=useState<ApiProduct[]>([])
  const [query,setQuery]=useState('')
  const [loading,setLoading]=useState(false)
  const [saving,setSaving]=useState(false)
  const [error,setError]=useState('')
  const [message,setMessage]=useState('')
  const [demoProductsSaved,setDemoProductsSaved]=useState<Record<number,FiscalProdutoDados>>({})

  useEffect(()=>{
    let active=true
    setCompany(emptyCompany)
    setEmitente({razao_social:'',nome_fantasia:'',documento:''})
    setProduct(emptyProduct)
    setSelectedId(null)
    setCatalog([])
    setLoading(true)
    setError('')
    if (modoHomologacao) {
      setEmitente({razao_social:'Empresa de Demonstração Ltda.',nome_fantasia:'Smart-tec — Exemplo',documento:'11.222.333/0001-81'})
      setCompany({...emptyCompany,uf:'SP',cidade:'Cidade Fictícia',logradouro:'Rua Demonstração',numero:'10',bairro:'Centro',cep:'01001000',municipio_codigo_ibge:'3550308',serie_nfe:1})
      setLoading(false)
      return () => {active=false}
    }
    getFiscalEmpresa().then(r=>{if(active){setCompany(r.dados);setEmitente({razao_social:r.razao_social||'',nome_fantasia:r.nome_fantasia||'',documento:r.documento||''})}}).catch(e=>{if(active)setError(String(e.message||e))}).finally(()=>{if(active)setLoading(false)})
    return()=>{active=false}
  },[companyId,modoHomologacao])

  useEffect(()=>{
    if(tab!=='produto'||catalog.length)return
    if(modoHomologacao){
      setCatalog([
        {id:101,nome:'Persiana Rolô de demonstração',codigo_interno:'DEMO-RL-101'},
        {id:202,nome:'Cortina Wave de demonstração',codigo_interno:'DEMO-CW-202'},
        {id:303,nome:'Persiana Romana de demonstração',codigo_interno:'DEMO-RM-303'},
      ] as ApiProduct[])
      return
    }
    let active=true
    getAllProducts().then(p=>{if(active)setCatalog(p)})
      .catch(e=>{if(active)setError(String(e.message||e))})
    return()=>{active=false}
  },[tab,companyId,catalog.length,modoHomologacao])

  async function selectProduct(id:number){
    setError('');setMessage('');setSelectedId(id);setLoading(true)
    if(modoHomologacao){setProduct(demoProductsSaved[id]??emptyProduct);setLoading(false);return}
    try{const result=await getFiscalProduto(id);setProduct(result.dados)}
    catch(e){setSelectedId(null);setError(e instanceof Error?e.message:'Falha ao carregar produto.')}
    finally{setLoading(false)}
  }
  async function saveCompany(){
    if(!canEdit)return
    setSaving(true);setError('');setMessage('')
    if(modoHomologacao){setMessage('Prévia: preenchimento simulado somente nesta tela. Nada foi enviado a um banco.');setSaving(false);return}
    try{const result=await patchFiscalEmpresa(company);setCompany(result.dados);setEmitente({razao_social:result.razao_social||'',nome_fantasia:result.nome_fantasia||'',documento:result.documento||''});setMessage('Cadastro fiscal da empresa salvo. Emissão continua desabilitada.')}
    catch(e){setError(e instanceof Error?e.message:'Erro ao salvar.')}
    finally{setSaving(false)}
  }
  async function saveProduct(){
    if(!canEdit||selectedId===null)return
    setSaving(true);setError('');setMessage('')
    if(modoHomologacao){setDemoProductsSaved(v=>({...v,[selectedId]:{...product}}));setMessage('Prévia: produto simulado apenas na memória desta página, sem banco.');setSaving(false);return}
    try{const result=await patchFiscalProduto(selectedId,product);setProduct(result.dados);setMessage('Classificação fiscal do produto salva. Emissão continua desabilitada.')}
    catch(e){setError(e instanceof Error?e.message:'Erro ao salvar.')}
    finally{setSaving(false)}
  }
  const matches = query.trim().length>=2 ? catalog.filter(p=>
    (p.nome+' '+(p.codigo_interno||'')+' '+p.id).toLocaleLowerCase('pt-BR').includes(query.toLocaleLowerCase('pt-BR'))
  ).slice(0,20) : []

  return <main className="fiscal-v1">
    <header className="fiscal-v1-head">
      <h1>Fiscal · Cadastros V1</h1>
      <p>Preparação de NF-e sem emissão ou transmissão. Confira todos os códigos com a contabilidade.</p>
    </header>
    <div className="fiscal-v1-warning" role="status">{modoHomologacao ? 'PRÉVIA VISUAL — dados fictícios e não persistidos. Sem API, sem banco, sem SEFAZ.' : 'Ambiente: homologação de cadastro · NF-e e SEFAZ desabilitadas'}</div>
    <section className="fiscal-v1-setup" aria-label="Etapas da configuração de NF-e">
      <h2>Configurar emissão de NF-e</h2>
      <p>Fluxo de preparação inspirado na referência enviada. Nenhuma etapa habilita emissão nesta versão.</p>
      <nav className="fiscal-v1-steps" aria-label="Etapas da NF-e">
        {([
          ['empresa','1','Dados da empresa'],
          ['certificado','2','Certificado digital'],
          ['configuracoes','3','Configurações'],
          ['confirmacao','4','Confirmação'],
        ] as const).map(([value,n,label])=>
          <button key={value} type="button" aria-current={tab===value?'step':undefined}
            onClick={()=>{setTab(value);setError('');setMessage('')}}>
            <span className="fiscal-v1-step-num">{n}</span><span>{label}</span>
          </button>
        )}
      </nav>
    </section>
    <div className="fiscal-v1-tabs">
      <button type="button" aria-pressed={tab==='empresa'} onClick={()=>{setTab('empresa');setError('');setMessage('')}}>Dados da empresa</button>
      <button type="button" aria-pressed={tab==='produto'} onClick={()=>{setTab('produto');setError('');setMessage('')}}>Tributação dos produtos</button>
      <button type="button" aria-pressed={tab==='nfe'} onClick={()=>{setTab('nfe');setError('');setMessage('')}}>NF-e · Referência GestãoClick</button>
    </div>
    {error&&<p className="fiscal-v1-error" role="alert">{error}</p>}
    {message&&<p className="fiscal-v1-success" role="status">{message}</p>}
    {!canEdit&&<p className="fiscal-v1-muted">Apenas proprietários e administradores podem alterar estes cadastros.</p>}
    {tab==='nfe' ? <NfeGestaoClickPreview />
      : tab==='certificado' ? <section className="fiscal-v1-panel">
        <h2>Certificado digital</h2>
        <p>O GestãoClick apresenta certificados A1 e A3. Nesta primeira versão da Smart-tec, estamos preparando a integração segura do <strong>A1 (arquivo PFX/P12)</strong>.</p>
        <div className="fiscal-v1-cert-types">
          <article><strong>Certificado A1</strong><p>Arquivo e senha serão tratados em fluxo protegido, com autorização por empresa. Ainda não disponível nesta prévia.</p></article>
          <article><strong>Certificado A3</strong><p>Compatibilidade futura, condicionada a integração com dispositivo ou provedor de assinatura.</p></article>
        </div>
        <p className="fiscal-v1-warning">Não envie certificados ou senhas nesta tela. Importação e assinatura ainda desativadas.</p>
        <button className="fiscal-v1-add" type="button" onClick={()=>setTab('configuracoes')}>Ver configurações de homologação</button>
      </section>
      : tab==='configuracoes' ? <section className="fiscal-v1-panel">
        <h2>Configurações de NF-e</h2>
        <p>Separe as opções da NF-e de produtos da NFC-e, NFS-e e notas de entrada.</p>
        <div className="fiscal-v1-grid">
          <label><span>Ambiente</span><input readOnly value="Homologação (sem valor fiscal)" /></label>
          <label><span>Série de NF-e — homologação</span><input
            type="number" min={1} max={899} disabled={loading||saving||!canEdit}
            value={company.serie_nfe??''} placeholder="1"
            onChange={e=>setCompany(v=>({...v,serie_nfe:e.target.value?Number(e.target.value):null}))}/></label>
          <label><span>Última NF-e autorizada</span><input readOnly value="" placeholder="Indisponível até integrar a SEFAZ"/></label>
        </div>
        <label className="fiscal-v1-multiline"><span>Informações complementares padrão da NF-e</span>
          <textarea rows={4} maxLength={2000} disabled={loading||saving||!canEdit}
            value={company.informacoes_complementares??''}
            onChange={e=>setCompany(v=>({...v,informacoes_complementares:e.target.value||null}))}
            placeholder="Texto padrão, sujeito à revisão fiscal"/></label>
        <p className="fiscal-v1-muted">Dados salvos apenas como cadastro preparatório. Não reservam número nem calculam tributos.</p>
        <button type="button" className="fiscal-v1-save" disabled={loading||saving||!canEdit} onClick={saveCompany}>{saving?'Salvando...':'Salvar configurações'}</button>
      </section>
      : tab==='confirmacao' ? <section className="fiscal-v1-panel">
        <h2>Confirmação e pendências</h2>
        <p>Conferência cadastral inicial. A emissão permanece indisponível mesmo quando os campos estão preenchidos.</p>
        <ul className="fiscal-v1-review">
          <li>{emitente.documento?'✓':'○'} CNPJ do emitente</li>
          <li>{emitente.razao_social?'✓':'○'} Razão social</li>
          <li>{company.inscricao_estadual?'✓':'○'} Inscrição Estadual ou situação a confirmar</li>
          <li>{company.cnae_principal?'✓':'○'} CNAE principal</li>
          <li>{company.crt?'✓':'○'} CRT confirmado pela contabilidade</li>
          <li>{company.cep&&company.logradouro&&company.numero&&company.bairro&&company.cidade&&company.uf?'✓':'○'} Endereço completo</li>
          <li>{company.serie_nfe?'✓':'○'} Série de homologação</li>
          <li>○ Certificado A1 ainda não integrado</li>
          <li>○ XML, regras tributárias e autorização SEFAZ ainda pendentes</li>
        </ul>
        <button type="button" className="fiscal-v1-add" onClick={()=>setTab('empresa')}>Revisar dados da empresa</button>
      </section>
      : tab==='empresa'?<section className="fiscal-v1-panel">
      <h2>Emitente</h2><p>Os dados são específicos da empresa ativa, sem alterar outras empresas.</p>
      <div className="fiscal-v1-grid fiscal-v1-company-identification">
        <label><span>CNPJ do emitente</span><input readOnly value={emitente.documento} placeholder="CNPJ do cadastro da empresa"/><small>Vinculado ao cadastro central da empresa.</small></label>
        <label><span>Razão social</span><input readOnly value={emitente.razao_social} placeholder="Razão social cadastrada"/><small>Edite no cadastro da empresa, não na NF-e.</small></label>
        <label><span>Nome fantasia</span><input readOnly value={emitente.nome_fantasia} placeholder="Nome fantasia cadastrado"/></label>
      </div>
      <div className="fiscal-v1-grid">{companyFields.map(field=><label key={field.id}>
        <span>{field.label}</span>
        <input disabled={loading||saving||!canEdit} placeholder={field.placeholder||''}
          inputMode={field.id==='serie_nfe'?'numeric':undefined}
          value={String(company[field.id as keyof FiscalEmpresaDados]??'')}
          onChange={e=>setCompany(v=>({...v,[field.id]:field.id==='serie_nfe'?(e.target.value?Number(e.target.value):null):(e.target.value||null)}))}/>
      </label>)}</div>
      <button type="button" className="fiscal-v1-save" disabled={loading||saving||!canEdit} onClick={saveCompany}>{saving?'Salvando...':'Salvar dados fiscais'}</button>
    </section>:<section className="fiscal-v1-panel">
      <h2>Classificação fiscal por produto</h2>
      {modoHomologacao && <div className="fiscal-v1-sample-products"><strong>Produtos de exemplo — clique para conferir a tributação</strong><div className="fiscal-v1-matches">{catalog.map(p=><button type="button" key={p.id} onClick={()=>{void selectProduct(p.id);setQuery(p.nome)}}>{p.nome} · #{p.id}</button>)}</div></div>}
      <label className="fiscal-v1-product-search"><span>Buscar pelo nome ou código</span>
        <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Ex.: Rolô BK Nápoles" />
      </label>
      {matches.length>0&&<div className="fiscal-v1-matches">{matches.map(p=><button type="button" key={p.id}
        onClick={()=>{void selectProduct(p.id);setQuery(p.nome)}}>{p.nome} · #{p.id}</button>)}</div>}
      {selectedId!==null&&<><p className="fiscal-v1-muted">Produto selecionado: #{selectedId}</p>
        <div className="fiscal-v1-grid">{productFields.map(field=><label key={field.id}>
          <span>{field.label}</span><input disabled={loading||saving||!canEdit} value={product[field.id as keyof FiscalProdutoDados]||''}
            onChange={e=>setProduct(v=>({...v,[field.id]:e.target.value||null}))}/>
        </label>)}</div>
        <button type="button" className="fiscal-v1-save" disabled={loading||saving||!canEdit} onClick={saveProduct}>{saving?'Salvando...':'Salvar classificação fiscal'}</button>
      </>}
    </section>}
  </main>
}
