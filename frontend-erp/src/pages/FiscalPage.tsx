import { useEffect, useState } from 'react'
import { getAllProducts } from '../services/api'
import type { ApiProduct } from '../types/budget'
import { useAuthSession } from '../components/AuthGate'
import { getFiscalEmpresa, getFiscalProduto, patchFiscalEmpresa, patchFiscalProduto } from '../services/fiscal'
import type { FiscalEmpresaDados, FiscalProdutoDados } from '../services/fiscal'
import './FiscalPage.css'

type Field = { id:string; label:string; placeholder?:string }
const companyFields:Field[] = [
  {id:'inscricao_estadual',label:'Inscrição estadual'},
  {id:'crt',label:'CRT (1 a 4)'},
  {id:'uf',label:'UF',placeholder:'SP'},
  {id:'municipio_codigo_ibge',label:'Código IBGE do município',placeholder:'3550308'},
  {id:'cidade',label:'Cidade'},
  {id:'cep',label:'CEP (8 dígitos)'},
  {id:'logradouro',label:'Logradouro'},
  {id:'numero',label:'Número'},
  {id:'bairro',label:'Bairro'},
  {id:'complemento',label:'Complemento'},
  {id:'serie_nfe',label:'Série de homologação',placeholder:'1'},
]
const productFields:Field[] = [
  {id:'ncm',label:'NCM (8 dígitos)'},{id:'cfop_padrao_saida',label:'CFOP de saída (4 dígitos)'},
  {id:'cest',label:'CEST (7 dígitos)'},{id:'origem_mercadoria',label:'Origem (0 a 8)'},
  {id:'cst_icms',label:'CST ICMS'},{id:'csosn',label:'CSOSN'},
  {id:'cst_pis',label:'CST PIS'},{id:'cst_cofins',label:'CST COFINS'},
  {id:'cst_ibs_cbs',label:'CST IBS/CBS'},{id:'cclass_trib_ibs_cbs',label:'cClassTrib IBS/CBS'},
]
const emptyCompany: FiscalEmpresaDados = {
  inscricao_estadual:null,crt:null,uf:null,municipio_codigo_ibge:null,cidade:null,
  cep:null,logradouro:null,numero:null,bairro:null,complemento:null,serie_nfe:null,ambiente:'HOMOLOGACAO',
}
const emptyProduct: FiscalProdutoDados = {
  ncm:null,cfop_padrao_saida:null,cest:null,origem_mercadoria:null,cst_icms:null,csosn:null,
  cst_pis:null,cst_cofins:null,cst_ibs_cbs:null,cclass_trib_ibs_cbs:null,
}

export function FiscalPage() {
  const session = useAuthSession()
  const canEdit = session?.empresa.papel === 'OWNER' || session?.empresa.papel === 'ADMIN'
  const companyId=session?.empresa.id
  const [tab,setTab]=useState<'empresa'|'produto'>('empresa')
  const [company,setCompany]=useState<FiscalEmpresaDados>(emptyCompany)
  const [product,setProduct]=useState<FiscalProdutoDados>(emptyProduct)
  const [selectedId,setSelectedId]=useState<number|null>(null)
  const [catalog,setCatalog]=useState<ApiProduct[]>([])
  const [query,setQuery]=useState('')
  const [loading,setLoading]=useState(false)
  const [saving,setSaving]=useState(false)
  const [error,setError]=useState('')
  const [message,setMessage]=useState('')

  useEffect(()=>{
    let active=true
    setCompany(emptyCompany)
    setProduct(emptyProduct)
    setSelectedId(null)
    setCatalog([])
    setLoading(true)
    setError('')
    getFiscalEmpresa().then(r=>{if(active)setCompany(r.dados)}).catch(e=>{if(active)setError(String(e.message||e))}).finally(()=>{if(active)setLoading(false)})
    return()=>{active=false}
  },[companyId])

  useEffect(()=>{
    if(tab!=='produto'||catalog.length)return
    let active=true
    getAllProducts().then(p=>{if(active)setCatalog(p)})
      .catch(e=>{if(active)setError(String(e.message||e))})
    return()=>{active=false}
  },[tab,companyId,catalog.length])

  async function selectProduct(id:number){
    setError('');setMessage('');setSelectedId(id);setLoading(true)
    try{const result=await getFiscalProduto(id);setProduct(result.dados)}
    catch(e){setSelectedId(null);setError(e instanceof Error?e.message:'Falha ao carregar produto.')}
    finally{setLoading(false)}
  }
  async function saveCompany(){
    if(!canEdit)return
    setSaving(true);setError('');setMessage('')
    try{const result=await patchFiscalEmpresa(company);setCompany(result.dados);setMessage('Cadastro fiscal da empresa salvo. Emissão continua desabilitada.')}
    catch(e){setError(e instanceof Error?e.message:'Erro ao salvar.')}
    finally{setSaving(false)}
  }
  async function saveProduct(){
    if(!canEdit||selectedId===null)return
    setSaving(true);setError('');setMessage('')
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
    <div className="fiscal-v1-warning" role="status">Ambiente: homologação de cadastro · NF-e e SEFAZ desabilitadas</div>
    <div className="fiscal-v1-tabs">
      <button type="button" aria-pressed={tab==='empresa'} onClick={()=>{setTab('empresa');setError('');setMessage('')}}>Dados da empresa</button>
      <button type="button" aria-pressed={tab==='produto'} onClick={()=>{setTab('produto');setError('');setMessage('')}}>Tributação dos produtos</button>
    </div>
    {error&&<p className="fiscal-v1-error" role="alert">{error}</p>}
    {message&&<p className="fiscal-v1-success" role="status">{message}</p>}
    {!canEdit&&<p className="fiscal-v1-muted">Apenas proprietários e administradores podem alterar estes cadastros.</p>}
    {tab==='empresa'?<section className="fiscal-v1-panel">
      <h2>Emitente</h2><p>Os dados são específicos da empresa ativa, sem alterar outras empresas.</p>
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
