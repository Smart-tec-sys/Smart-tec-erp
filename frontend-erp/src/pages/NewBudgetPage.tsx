import { ArrowLeft, ChevronLeft, ChevronRight, FileText, PackagePlus, Plus, ReceiptText, Truck, WalletCards, X, Loader2, UserPlus, LayoutDashboard } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { romanaKind, romanaKey, type RomanaState } from '../types/romana'
import { romanaTetoKind, romanaTetoKey, type RomanaTetoState } from '../types/romana_teto'
import { roloKind, roloKey, type RoloState } from '../types/rolo'
import { doubleVisionKind, doubleVisionKey, type DoubleVisionState } from '../types/double_vision'
import { BudgetProductRow } from '../components/BudgetProductRow'
import { BudgetServiceRow } from '../components/BudgetServiceRow'
import { BudgetSummary } from '../components/BudgetSummary'
import { createBudget, getAllProducts, getBudget, getClients, updateBudget, createClient, createProduct, getProductGroups, getProductUnits } from '../services/api'
import { commercialPrice, emptyProduct, parseDecimal, productLineSubtotal, profileLabel, formatClientCompletenessMessage, getClientCompleteness, formatProductCompletenessMessage, getProductCompleteness, type ApiBudget, type ApiClient, type ApiProduct, type BudgetPayload, type BudgetProduct, type BudgetService, type CommercialProfile } from '../types/budget'
import type { CurtainState } from '../types/budget'

type Props={onBack:()=>void; budgetId?:number|null; onSaved:(id:number,mode:'created'|'updated')=>void}
const today=new Date().toISOString().slice(0,10)
const CREATE_CLIENT_VALUE = '__CREATE_CLIENT__'
const CREATE_SERVICE_VALUE = '__CREATE_SERVICE__'
const CREATE_PRODUCT_VALUE = '__CREATE_PRODUCT__'

export function NewBudgetPage({onBack,budgetId,onSaved}:Props){
  const [catalog,setCatalog]=useState<ApiProduct[]>([]),[clients,setClients]=useState<ApiClient[]>([])
  const [productGroups,setProductGroups]=useState<string[]>([]),[productUnits,setProductUnits]=useState<string[]>([])

  const effectiveProductUnits = useMemo(() => {
    if (productUnits.length > 0) return productUnits
    const units = catalog
      .map(p => p.unidade_venda?.trim() || p.unidade?.trim() || '')
      .filter(u => u.length > 0)
      .filter((u, i, arr) => arr.indexOf(u) === i)
      .sort((a, b) => a.localeCompare(b, 'pt-BR'))
    return units
  }, [productUnits, catalog])
  const [clientId,setClientId]=useState(0),[profile,setProfile]=useState<CommercialProfile>('VAREJO'),[status,setStatus]=useState('EM_ABERTO'),[validity,setValidity]=useState(today),[observation,setObservation]=useState(''),[internalObservation,setInternalObservation]=useState('')
  const [products,setProducts]=useState<BudgetProduct[]>([emptyProduct(1)]),[services,setServices]=useState<BudgetService[]>([]),[discount,setDiscount]=useState(0),[freight]=useState(0)
  const [loading,setLoading]=useState(true),[saving,setSaving]=useState(false),[error,setError]=useState(''),[saved,setSaved]=useState<ApiBudget|null>(null)
  const [showClientModal,setShowClientModal]=useState(false)
  const [clientForm,setClientForm]=useState({tipo:'',nome:''})
  const [clientModalError,setClientModalError]=useState('')
  const [clientModalSaving,setClientModalSaving]=useState(false)
  const [showServiceModal,setShowServiceModal]=useState(false)
  const [serviceForm,setServiceForm]=useState({nome:''})
  const [serviceModalError,setServiceModalError]=useState('')
  const [serviceModalSaving,setServiceModalSaving]=useState(false)
  const [editingServiceId,setEditingServiceId]=useState<number|null>(null)
  const [showProductModal,setShowProductModal]=useState(false)
  const [editingProductId,setEditingProductId]=useState<number|null>(null)
  const [productForm,setProductForm]=useState({nome:'',grupo_produto:'',unidade_venda:'',valor_custo:''})
  const [productModalError,setProductModalError]=useState('')
  const [productModalSaving,setProductModalSaving]=useState(false)
  const [isSummaryCollapsed,setIsSummaryCollapsed]=useState(false)
  const [validationAttempted,setValidationAttempted]=useState(false)

  const selectedClient = clients.find(c => c.id === clientId)
  const completeness = selectedClient ? getClientCompleteness(selectedClient) : null
 useEffect(()=>{void(async()=>{try{const [p,c,b,g,u]=await Promise.all([getAllProducts(),getClients(),budgetId?getBudget(budgetId):Promise.resolve(null),getProductGroups(),getProductUnits()]);setCatalog(p);setClients(c);setProductGroups(g);setProductUnits(u);setInternalObservation(b?.observacao_interna??'');if(!budgetId&&c.length)setClientId(c[0].id);if(b){setClientId(b.cliente_id);setStatus(b.status);setValidity(b.validade||today);setObservation(b.observacao||'');setDiscount(Number(b.desconto));const pp=b.itens.filter(i=>i.tipo_item==='PRODUTO').map((i,index)=>{const found=p.find(x=>x.id===i.produto_id);return{...emptyProduct(index+1),productId:i.produto_id||null,product:found?.nome||i.descricao,code:i.codigo_interno||'',family:found?.familia_tecnica||'',groupTechnical:i.grupo_tecnico||'',modelTechnical:i.modelo_tecnico||'',unit:i.unidade||'',color:i.cor||'',details:i.observacao_item||'',quantity:Number(i.quantidade),width:String(i.largura).replace('.',','),height:String(i.altura).replace('.',','),price:Number(i.preco_unitario),discount:Number(i.desconto),curtain:i.dados_tecnicos?.cortina ? {...i.dados_tecnicos.cortina,simulationKey:undefined,result:undefined,error:undefined} : undefined}});setProducts(pp.length?pp:[emptyProduct(1)]);setServices(b.itens.filter(i=>i.tipo_item==='SERVICO').map((i,index)=>({id:index+1,service:i.descricao,details:i.observacao_item||'',quantity:Number(i.quantidade),value:Number(i.preco_unitario),discount:Number(i.desconto)})));setSaved(b)}}catch(e){setError(e instanceof Error?e.message:String(e))}finally{setLoading(false)}})()},[budgetId])
useEffect(()=>{if(budgetId)getBudget(budgetId).then(b=>setProfile(b.perfil_comercial||'VAREJO')).catch(()=>undefined)},[budgetId])
  useEffect(()=>{setProducts(rows=>rows.map(row=>{const found=catalog.find(p=>p.id===row.productId);return found?{...row,romanaKind:romanaKind(found),romanaTetoKind:romanaTetoKind(found),roloKind:roloKind(found),doubleVisionKind:doubleVisionKind(found),price:(romanaKind(found)||romanaTetoKind(found)||roloKind(found)||doubleVisionKind(found))?0:commercialPrice(found,profileLabel[profile])}:row}))},[profile,catalog])
  const onRomana = useCallback((id:number, state:RomanaState) => {
    setProducts(rows => rows.map(row => row.id === id ? {...row, romana:{...state,result:state.result || row.romana?.result}, price:state.result ? Number(state.result.preco_unitario) : row.price} : row))
  }, [])
  const onRomanaTeto = useCallback((id:number, state:RomanaTetoState) => {
    setProducts(rows => rows.map(row => row.id === id ? {...row, romanaTeto:{...state,result:state.result || row.romanaTeto?.result}, price:state.result ? Number(state.result.preco_unitario) : row.price} : row))
  }, [])
  const onRolo = useCallback((id:number, state:RoloState) => {
    setProducts(rows => rows.map(row => row.id === id ? {...row, rolo:{...state,result:state.result || row.rolo?.result}, price:state.result ? Number(state.result.preco_unitario) : row.price} : row))
  }, [])
  const onDoubleVision = useCallback((id:number, state:DoubleVisionState) => {
    setProducts(rows => rows.map(row => row.id === id ? {...row, doubleVision:{...state,result:state.result || row.doubleVision?.result}, price:state.result ? Number(state.result.preco_unitario) : row.price} : row))
  }, [])

  const onCurtain = useCallback((id: number, state: CurtainState) => {
    setProducts(rows =>
      rows.map(row =>
        row.id === id
          ? {
              ...row,
              curtain: {
                ...state,
                result: state.result || row.curtain?.result,
              },
              price:
                state.result?.preco_disponivel
                  ? Number(state.result.preco_unitario)
                  : row.price,
            }
          : row
      )
    )
  }, [])

  const handleOpenClientModal=()=>{
    setClientForm({tipo:'',nome:''})
    setClientModalError('')
    setShowClientModal(true)
  }

  const handleClientSelectChange=(value:string)=>{
    if(value===CREATE_CLIENT_VALUE){
      handleOpenClientModal()
      return
    }
    setClientId(Number(value))
  }

  const handleCloseClientModal=()=>{
    setShowClientModal(false)
    setClientForm({tipo:'',nome:''})
    setClientModalError('')
  }

  const handleClientFormChange=(field:string,value:string)=>{
    setClientForm(prev=>({...prev,[field]:value}))
    if(clientModalError)setClientModalError('')
  }

  const handleCreateClient=async()=>{
    if(!clientForm.tipo.trim()||!clientForm.nome.trim()){
      setClientModalError('Tipo e Nome são obrigatórios')
      return
    }
    setClientModalSaving(true)
    setClientModalError('')
    try{
      const newClient=await createClient({tipo:clientForm.tipo.trim(),nome:clientForm.nome.trim()})
      setClients(prev=>[newClient,...prev])
      setClientId(newClient.id)
      handleCloseClientModal()
    }catch(e){
      const msg=e instanceof Error?e.message:String(e)
      if(msg.includes('409')||msg.toLowerCase().includes('duplic')||msg.toLowerCase().includes('unique')){
        setClientModalError('Cliente já cadastrado com estes dados')
      }else{
        setClientModalError(msg)
      }
    }finally{
      setClientModalSaving(false)
    }
  }

  const handleOpenServiceModal=(serviceId:number)=>{
    setEditingServiceId(serviceId)
    setServiceForm({nome:''})
    setServiceModalError('')
    setShowServiceModal(true)
  }

  const handleCloseServiceModal=()=>{
    setShowServiceModal(false)
    setServiceForm({nome:''})
    setServiceModalError('')
    setEditingServiceId(null)
  }

  const handleServiceFormChange=(field:string,value:string)=>{
    setServiceForm(prev=>({...prev,[field]:value}))
    if(serviceModalError)setServiceModalError('')
  }

  const handleCreateService=async()=>{
    if(!serviceForm.nome.trim()){
      setServiceModalError('Nome do serviço é obrigatório')
      return
    }
    if(editingServiceId===null){
      setServiceModalError('Erro interno: serviço não identificado')
      return
    }
    setServiceModalSaving(true)
    setServiceModalError('')
    try{
      // No backend service catalog endpoint exists - service is just a description in orcamento item
      // Update the specific service row with the new service name
      setServices(rows=>rows.map(r=>r.id===editingServiceId?{...r,service:serviceForm.nome.trim()}:r))
      handleCloseServiceModal()
    }catch(e){
      const msg=e instanceof Error?e.message:String(e)
      setServiceModalError(msg)
    }finally{
      setServiceModalSaving(false)
    }
  }

  const handleOpenProductModal=(productId:number)=>{
    setEditingProductId(productId)
    setProductForm({nome:'',grupo_produto:'',unidade_venda:'',valor_custo:''})
    setProductModalError('')
    setShowProductModal(true)
  }

  const handleCloseProductModal=()=>{
    setShowProductModal(false)
    setProductForm({nome:'',grupo_produto:'',unidade_venda:'',valor_custo:''})
    setProductModalError('')
    setEditingProductId(null)
  }

  const handleProductFormChange=(field:string,value:string)=>{
    setProductForm(prev=>({...prev,[field]:value}))
    if(productModalError)setProductModalError('')
  }

  const handleCreateProduct=async()=>{
    if(!productForm.nome.trim()||!productForm.grupo_produto.trim()||!productForm.unidade_venda.trim()||!productForm.valor_custo.trim()){
      setProductModalError('Nome, Grupo do produto, Unidade de venda e Valor de custo são obrigatórios')
      return
    }
    const custo = parseDecimal(productForm.valor_custo)
    if(custo <= 0){
      setProductModalError('Valor de custo deve ser maior que zero')
      return
    }
    setProductModalSaving(true)
    setProductModalError('')
    try{
      const newProduct=await createProduct({
        nome:productForm.nome.trim(),
        grupo_produto:productForm.grupo_produto.trim(),
        unidade_venda:productForm.unidade_venda.trim(),
        valor_custo:custo
      })
      setCatalog(prev=>[newProduct,...prev])
      setProducts(rows=>rows.map(r=>r.id===editingProductId?{...r,productId:newProduct.id,product:newProduct.nome,code:newProduct.codigo_interno||newProduct.codigo||'',family:newProduct.familia_tecnica||'',groupTechnical:newProduct.grupo_tecnico||'',modelTechnical:newProduct.modelo_tecnico||'',unit:newProduct.unidade_venda||newProduct.unidade||'',color:newProduct.cor_componente||newProduct.cor||newProduct.variacao_cor||'',romanaKind:romanaKind(newProduct),romanaTetoKind:romanaTetoKind(newProduct),roloKind:roloKind(newProduct),doubleVisionKind:doubleVisionKind(newProduct),romana:undefined,romanaTeto:undefined,rolo:undefined,doubleVision:undefined,price:(romanaKind(newProduct)||romanaTetoKind(newProduct)||roloKind(newProduct)||doubleVisionKind(newProduct))?0:commercialPrice(newProduct,profileLabel[profile])}:r))
      handleCloseProductModal()
    }catch(e){
      const msg=e instanceof Error?e.message:String(e)
      if(msg.includes('409')||msg.toLowerCase().includes('duplic')||msg.toLowerCase().includes('unique')){
        setProductModalError('Produto já cadastrado com este nome')
      }else{
        setProductModalError(msg)
      }
    }finally{
      setProductModalSaving(false)
    }
  }

const productTotal=products.reduce((s,i)=>s+productLineSubtotal(i),0),serviceTotal=services.reduce((s,i)=>s+Math.max(0,i.quantity*i.value-i.discount),0),total=Math.max(0,productTotal+serviceTotal+freight-discount)
const makeItem = (p:BudgetProduct) => ({
  tipo_item:'PRODUTO' as const,
  produto_id:p.productId,
  descricao:p.product,
  codigo_interno:p.code||null,
  grupo_tecnico:p.groupTechnical||null,
  modelo_tecnico:p.modelTechnical||null,
  unidade:p.unit||null,
  quantidade:p.quantity,
  largura:parseDecimal(p.width),
  altura:parseDecimal(p.height),
  area:(p.romanaKind||p.romanaTetoKind||p.roloKind||p.doubleVisionKind)?Number(p.romana?.result?.area_total||p.romanaTeto?.result?.area_real_m2||p.rolo?.result?.area_faturavel_m2||p.doubleVision?.result?.area_total||0):parseDecimal(p.width)*parseDecimal(p.height)*p.quantity,
  preco_unitario:p.price,
  desconto:p.discount,
  subtotal:productLineSubtotal(p),
  dados_tecnicos:
    p.curtain &&
    String(p.modelTechnical).trim().toUpperCase() === 'CORTINA' &&
    String(p.groupTechnical).trim().toUpperCase() === 'TECIDOS_CORTINA'
      ? {
          cortina: {
            ...p.curtain,
            simulationKey: undefined,
            result: undefined,
            error: undefined,
          },
        }
      : null,
  observacao_item:p.details||null,
  cor:p.color||null,
  acionamento:p.acao_acionamento||undefined,
  lado_comando:p.lado_comando||null,
  comprimento_bastao:p.comprimento_bastao||null,
  comprimento_corrente_sem_fim:p.comprimento_corrente_sem_fim||null,
})
const payload=useMemo<BudgetPayload>(()=>({cliente_id:clientId,status,validade:validity||null,observacao:observation,observacao_interna:internalObservation,desconto:discount,total:productTotal+serviceTotal,total_final:total,itens:[...products.filter(p=>p.productId).map(makeItem),...services.map(s=>({tipo_item:'SERVICO' as const,produto_id:null,descricao:s.service,quantidade:s.quantity,largura:0,altura:0,area:0,preco_unitario:s.value,desconto:s.discount,subtotal:Math.max(0,s.quantity*s.value-s.discount),observacao_item:s.details||null,cor:null}))]}),[clientId,status,validity,observation,internalObservation,discount,total,productTotal,serviceTotal,products,services])
const serverPayload={...payload,perfil_comercial:profile}
const romanaPending = products.some(p => p.romanaKind && (p.romanaKind === 'MOTORIZADA' || p.romana?.key !== romanaKey(p,profileLabel[profile]) || p.romana?.error || !p.romana?.result?.preco_disponivel))
const romanaTetoPending = products.some(p => p.romanaTetoKind && (p.romanaTetoKind === 'MOTORIZADA' || p.romanaTeto?.key !== romanaTetoKey(p,profileLabel[profile]) || p.romanaTeto?.error || !p.romanaTeto?.result?.preco_disponivel))
const roloPending = products.some(p => p.roloKind && (p.roloKind === 'MOTORIZADA' || p.rolo?.key !== roloKey(p,profileLabel[profile]) || p.rolo?.error || !p.rolo?.result?.preco_disponivel))
const doubleVisionPending = products.some(p => p.doubleVisionKind && (p.doubleVisionKind === 'MOTORIZADA' || p.doubleVision?.key !== doubleVisionKey(p,profileLabel[profile]) || p.doubleVision?.error || !p.doubleVision?.result?.preco_disponivel || p.doubleVision?.result?.estado_validacao === 'requer_validacao' || p.doubleVision?.result?.estado_validacao === 'bloqueado'))

  const curtainPending = products.some((p) => {
    const isFinalCurtain =
      String(p.modelTechnical ?? '').trim().toUpperCase() === 'CORTINA' &&
      String(p.groupTechnical ?? '').trim().toUpperCase() === 'TECIDOS_CORTINA'

    if (!isFinalCurtain) return false

    const c = p.curtain
    if (!c) return true

    const width = parseDecimal(p.width)
    const height = parseDecimal(p.height)

    const currentKey = JSON.stringify([
      p.productId,
      width,
      height,
      Math.max(1, p.quantity || 1),
      c.fator,
      c.larguraTecido,
      c.modeloPrega,
      c.possuiForro,
      c.tipoForro ?? '',
      c.trilhoLinha ?? '',
      c.trilhoModelo ?? '',
      c.rodizioTipo ?? '',
      c.cabecaCm,
      c.barraCm,
      c.barraDupla,
      c.usaEntretela,
      c.tipoEntretela,
      c.fixacaoCortina,
      c.trilhoComCordas,
      c.sistemaWave,
      c.espacamentoBotaoCm,
      c.aberturaCortina,
    ])

    return (
      !p.productId ||
      width <= 0 ||
      height <= 0 ||
      c.simulationKey !== currentKey ||
      Boolean(c.error) ||
      !c.result
    )
  })


  useEffect(() => {
    const technicalPending =
      romanaPending ||
      romanaTetoPending ||
      roloPending ||
      doubleVisionPending ||
      curtainPending

    const isStaleTechnicalError =
      error.startsWith('Romana:') ||
      error.startsWith('Romana de teto:') ||
      error.startsWith('Rol?:') ||
      error.startsWith('Double Vision:') ||
      error.startsWith('Cortina:')

    if (!technicalPending && isStaleTechnicalError) {
      setError('')
    }
  }, [
    romanaPending,
    romanaTetoPending,
    roloPending,
    doubleVisionPending,
    error
  ])
const save=async()=>{
  setValidationAttempted(true)

  const invalidRequiredProduct = serverPayload.itens.some(item =>
    item.tipo_item === 'PRODUTO' &&
    (
      !Number.isFinite(Number(item.quantidade)) ||
      Number(item.quantidade) <= 0 ||
      !Number.isFinite(Number(item.preco_unitario)) ||
      Number(item.preco_unitario) <= 0
    )
  )

  if (!profile || invalidRequiredProduct) {
    setError('Preencha os campos obrigat?rios destacados.')
    return
  }

  if(romanaPending){setError('Romana: resolva os avisos técnicos ou aguarde a simulação antes de salvar. Totais não confirmados.');return}if(romanaTetoPending){setError('Romana de teto: resolva os avisos técnicos ou aguarde a simulação antes de salvar. Totais não confirmados.');return}if(roloPending){setError('Rolô: resolva os avisos técnicos ou aguarde a simulação antes de salvar. Totais não confirmados.');return}if(doubleVisionPending){setError('Double Vision: resolva os avisos técnicos ou aguarde a simulação antes de salvar. Totais não confirmados.');return}if(!clientId||serverPayload.itens.length===0){setError('Selecione um cliente e ao menos um item.');return}setSaving(true);setError('');try{const editing=budgetId!=null;const result=editing?await updateBudget(budgetId,serverPayload):await createBudget(serverPayload);setSaved(result);onSaved(result.id,editing?'updated':'created')}catch(e){setError(e instanceof Error?e.message:String(e))}finally{setSaving(false)}}
 const nextId=(items:{id:number}[])=>Math.max(0,...items.map(i=>i.id))+1
  const serviceOptions = useMemo(() => [...new Set(services.map(s => s.service).filter(Boolean))], [services])
if(loading)return <div className="panel loading-state">Carregando catálogo completo, clientes e orçamento...</div>
  return (
    <>
      <div className="new-budget-page"><section className="new-budget-heading page-heading"><div><button type="button" className="back-button page-back" onClick={onBack}><ArrowLeft size={15}/> Voltar para orçamentos</button><p className="eyebrow">PROPOSTA COMERCIAL CONECTADA</p><h1>{budgetId?'Editar orçamento':'Novo orçamento'} <span className="draft-badge">API real</span></h1><p className="heading-subtitle">Catálogo, clientes, itens, totais e reabertura conectados ao FastAPI.</p></div><div className="budget-number"><span>NÚMERO</span><strong>{saved?`#${saved.numero}`:'Automático'}</strong></div></section>
      {error&&<div className="api-message error">{error}</div>}
      <div className={`new-budget-layout ${isSummaryCollapsed ? 'summary-collapsed' : ''}`}><div className="new-budget-main">
      <BudgetSection icon={<FileText size={17}/>} title="Perfil comercial" subtitle="Um único perfil para todos os produtos; o backend recalcula os preços."><Field label="Tabela de preço"><select value={profile} onChange={e=>setProfile(e.target.value as CommercialProfile)}><option value="DECORADOR">Decorador</option><option value="VAREJO">Varejo</option><option value="CONSUMIDOR_FINAL">Consumidor final</option></select></Field></BudgetSection>
      <BudgetSection icon={<FileText size={17}/>} title="Dados gerais" subtitle="Campos suportados pelo contrato atual."><div className="form-grid general-grid"><Field label="Cliente"><div className="product-search-box"><select value={clientId} onChange={e=>handleClientSelectChange(e.target.value)}><option value={0}>Selecione</option>{clients.map(c=><option key={c.id} value={c.id}>{c.nome}</option>)}<option value={CREATE_CLIENT_VALUE}>+ Cadastrar novo cliente</option></select>{selectedClient && completeness && !completeness.isComplete && <small className="client-incomplete-hint">{formatClientCompletenessMessage(selectedClient)}</small>}</div></Field><Field label="Status"><select value={status} onChange={e=>setStatus(e.target.value)}><option value="EM_ABERTO">Em aberto</option><option value="APROVADO">Aprovado</option><option value="CANCELADO">Cancelado</option></select></Field><Field label="Validade"><input type="date" value={validity} onChange={e=>setValidity(e.target.value)}/></Field><Field label="Cliente final"><input disabled placeholder="Disponível em breve"/><small>Não persistido pelo contrato atual</small></Field><Field label="Representante"><input disabled placeholder="Não persistida nesta fase"/><small>Não persistido pelo contrato atual</small></Field></div></BudgetSection>
      <BudgetSection icon={<PackagePlus size={17}/>} title="Produtos" subtitle={`${catalog.length} produtos carregados; somente ativos aparecem na busca.`} count={`${products.length} itens`}>{romanaPending && <div className="api-message error">Romana com simulação pendente, inválida ou indisponível: os totais ainda não estão confirmados e o salvamento está bloqueado.</div>}{romanaTetoPending && <div className="api-message error">Romana de teto com simulação pendente, inválida ou indisponível: os totais ainda não estão confirmados e o salvamento está bloqueado.</div>}{roloPending && <div className="api-message error">Rolô com simulação pendente, inválida ou indisponível: os totais ainda não estão confirmados e o salvamento está bloqueado.</div>}{doubleVisionPending && <div className="api-message error">Double Vision com simulação pendente, inválida ou indisponível: os totais ainda não estão confirmados e o salvamento está bloqueado.</div>}<div className="product-rows">{products.map(p=><BudgetProductRow key={p.id} product={p} catalog={catalog} commercialType={profileLabel[profile]} validationAttempted={validationAttempted} onRomana={onRomana} onRomanaTeto={onRomanaTeto} onRolo={onRolo} onDoubleVision={onDoubleVision} onCurtain={onCurtain} onChange={n=>setProducts(rows=>rows.map(r=>r.id===n.id?n:r))} onRemove={()=>setProducts(rows=>rows.filter(r=>r.id!==p.id))} onCreateProduct={handleOpenProductModal}/>)}</div><button type="button" className="secondary-button add-product" onClick={()=>setProducts(rows=>[...rows,emptyProduct(nextId(rows))])}><Plus size={16}/> Adicionar produto</button></BudgetSection>
      <BudgetSection icon={<ReceiptText size={17}/>} title="Serviços" subtitle="Persistidos como itens do tipo SERVICO." count={`${services.length} itens`}><div className="service-rows">{services.map(s=><BudgetServiceRow key={s.id} service={s} onChange={n=>setServices(rows=>rows.map(r=>r.id===n.id?n:r))} onRemove={()=>setServices(rows=>rows.filter(r=>r.id!==s.id))} onCreateService={handleOpenServiceModal} createServiceValue={CREATE_SERVICE_VALUE} serviceOptions={serviceOptions}/>)}</div><button type="button" className="secondary-button add-product" onClick={()=>setServices(rows=>[...rows,{id:nextId(rows),service:'Instalação',details:'',quantity:1,value:0,discount:0}])}><Plus size={16}/> Adicionar serviço</button></BudgetSection>
      <BudgetSection icon={<Truck size={17}/>} title="Transporte" subtitle="Ainda sem campos próprios no contrato."><div className="form-grid relationship-grid"><Field label="Frete"><input type="number" value={freight} disabled/><small>Não persistido nesta fase</small></Field><Field label="Transportadora"><input disabled placeholder="Não persistida nesta fase"/></Field></div></BudgetSection>
      <BudgetSection icon={<WalletCards size={17}/>} title="Pagamento" subtitle="Não persistido pelo contrato atual."><div className="api-message">Condição, parcelas, vencimento e forma de pagamento permanecem pendentes de modelagem futura.</div></BudgetSection>
      <BudgetSection icon={<FileText size={17}/>} title="Observações" subtitle="Informações para o cliente e anotações internas da equipe."><div className="budget-observations-grid"><Field label="Observações para o cliente"><textarea value={observation} onChange={e=>setObservation(e.target.value)}/></Field><Field label="Observações internas"><textarea value={internalObservation} onChange={e=>setInternalObservation(e.target.value)}/></Field></div></BudgetSection>
<BudgetSection icon={<ReceiptText size={17}/>} title="Payload da API" subtitle="O preço de produto é apenas estimativo; o servidor recalcula o valor definitivo."><pre className="payload-preview">{JSON.stringify(serverPayload,null,2)}</pre></BudgetSection>
      </div><BudgetSummary products={productTotal} services={serviceTotal} freight={freight} discount={discount} onDiscount={setDiscount} onCancel={onBack} onSave={save} saving={saving} isCollapsed={isSummaryCollapsed} onToggle={() => setIsSummaryCollapsed(prev => !prev)} /></div></div>
      {isSummaryCollapsed && (
        <button
          type="button"
          className="summary-reopen-tab"
          onClick={() => setIsSummaryCollapsed(false)}
          aria-label="Mostrar resumo comercial"
          title="Mostrar resumo comercial"
        >
          <ChevronLeft size={16} />
          <span>Mostrar resumo</span>
        </button>
      )}

      {showClientModal&&<div className="modal-overlay" onClick={handleCloseClientModal}><div className="modal-container" onClick={e=>e.stopPropagation()}><div className="modal-header"><h3><UserPlus size={16}/> Cadastrar novo cliente</h3><button type="button" className="modal-close" onClick={handleCloseClientModal}><X size={16}/></button></div><form className="modal-form" onSubmit={e=>{e.preventDefault();handleCreateClient()}}><div className="modal-field"><label>Tipo *</label><select value={clientForm.tipo} onChange={e=>handleClientFormChange('tipo',e.target.value)}><option value="">Selecione</option><option value="Pessoa Física">Pessoa Física</option><option value="Pessoa Jurídica">Pessoa Jurídica</option></select></div><div className="modal-field"><label>Nome *</label><input type="text" value={clientForm.nome} onChange={e=>handleClientFormChange('nome',e.target.value)} placeholder="Nome do cliente" autoFocus/></div>{clientModalError&&<div className="modal-error">{clientModalError}</div>}<div className="modal-actions"><button type="button" className="secondary-button" onClick={handleCloseClientModal} disabled={clientModalSaving}>Cancelar</button><button type="submit" className="primary-button" disabled={clientModalSaving||!clientForm.tipo.trim()||!clientForm.nome.trim()}>{clientModalSaving?<><Loader2 size={14} className="spinning"/> Salvando...</>:<><UserPlus size={14}/> Salvar e selecionar</>}</button></div></form></div></div>}

      {showServiceModal&&<div className="modal-overlay" onClick={handleCloseServiceModal}><div className="modal-container" onClick={e=>e.stopPropagation()}><div className="modal-header"><h3><PackagePlus size={16}/> Cadastrar novo serviço</h3><button type="button" className="modal-close" onClick={handleCloseServiceModal}><X size={16}/></button></div><form className="modal-form" onSubmit={e=>{e.preventDefault();handleCreateService()}}><div className="modal-field"><label>Nome do serviço *</label><input type="text" value={serviceForm.nome} onChange={e=>handleServiceFormChange('nome',e.target.value)} placeholder="Ex: Instalação, Medição, Manutenção" autoFocus/></div>{serviceModalError&&<div className="modal-error">{serviceModalError}</div>}<div className="modal-actions"><button type="button" className="secondary-button" onClick={handleCloseServiceModal} disabled={serviceModalSaving}>Cancelar</button><button type="submit" className="primary-button" disabled={serviceModalSaving||!serviceForm.nome.trim()}>{serviceModalSaving?<><Loader2 size={14} className="spinning"/> Salvando...</>:<><PackagePlus size={14}/> Salvar e usar</>}</button></div></form></div></div>}

      {showProductModal&&<div className="modal-overlay" onClick={handleCloseProductModal}><div className="modal-container" onClick={e=>e.stopPropagation()}><div className="modal-header"><h3><PackagePlus size={16}/> Cadastrar novo produto</h3><button type="button" className="modal-close" onClick={handleCloseProductModal}><X size={16}/></button></div><form className="modal-form" onSubmit={e=>{e.preventDefault();handleCreateProduct()}}><div className="modal-field"><label>Nome *</label><input type="text" value={productForm.nome} onChange={e=>handleProductFormChange('nome',e.target.value)} placeholder="Nome do produto" autoFocus/></div><div className="modal-field"><label>Grupo do produto *</label><select value={productForm.grupo_produto} onChange={e=>handleProductFormChange('grupo_produto',e.target.value)}><option value="">Selecione</option>{productGroups.map(g=><option key={g} value={g}>{g}</option>)}</select></div><div className="modal-field"><label>Unidade de venda *</label><select value={productForm.unidade_venda} onChange={e=>handleProductFormChange('unidade_venda',e.target.value)}><option value="">Selecione</option>{effectiveProductUnits.map(u=><option key={u} value={u}>{u}</option>)}</select></div><div className="modal-field"><label>Valor de custo *</label><input type="text" value={productForm.valor_custo} onChange={e=>handleProductFormChange('valor_custo',e.target.value)} placeholder="Ex: 150,00"/></div>{productModalError&&<div className="modal-error">{productModalError}</div>}<div className="modal-actions"><button type="button" className="secondary-button" onClick={handleCloseProductModal} disabled={productModalSaving}>Cancelar</button><button type="submit" className="primary-button" disabled={productModalSaving||!productForm.nome.trim()||!productForm.grupo_produto.trim()||!productForm.unidade_venda.trim()||!productForm.valor_custo.trim()}>{productModalSaving?<><Loader2 size={14} className="spinning"/> Salvando...</>:<><PackagePlus size={14}/> Salvar e selecionar</>}</button></div></form></div></div>}
    </>
  )
}
function BudgetSection({icon,title,subtitle,count,children}:{icon:React.ReactNode;title:string;subtitle:string;count?:string;children:React.ReactNode}){return <section className="form-section panel"><div className="section-title"><div className="section-icon">{icon}</div><div><h2>{title}</h2><p>{subtitle}</p></div>{count&&<span className="section-count">{count}</span>}</div>{children}</section>}
function Field({label,children}:{label:string;children:React.ReactNode}){return <label className="field"><span>{label}</span>{children}</label>}
