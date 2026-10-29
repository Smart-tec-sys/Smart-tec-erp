import { curtainKey } from "../types/budget"
import { technicalItemData } from '../utils/technicalSimulation'
import { ZeroNumberInput } from '../components/ZeroNumberInput'
import { selectZeroOnFocus } from '../utils/selectZeroOnFocus'
import { CommercialRegistrationDialog, CREATE_COMMERCIAL_VALUE, type CommercialRegistration } from '../components/CommercialRegistrationDialog'
import { ArrowLeft, ChevronLeft, ChevronRight, FileText, PackagePlus, Plus, ReceiptText, Truck, WalletCards, X, Loader2, UserPlus, LayoutDashboard } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { romanaKind, romanaKey, type RomanaState } from '../types/romana'
import { romanaTetoKind, romanaTetoKey, type RomanaTetoState } from '../types/romana_teto'
import { roloKind, roloKey, type RoloState } from '../types/rolo'
import { doubleVisionKind, doubleVisionKey, type DoubleVisionState } from '../types/double_vision'
import { BudgetProductRow } from '../components/BudgetProductRow'
import { BudgetServiceRow } from '../components/BudgetServiceRow'
import { BudgetSummary } from '../components/BudgetSummary'
import { createBudget, getAllProducts, getBudget, getClients, updateBudget, createClient, createProduct, getProductGroups, getProductUnits, convertBudgetToOrder, getCommercialPartners, getRepresentatives, getFuncionariosCadastro, type ApiOrder, type ApiCommercialPartner, type ApiRepresentative, type CadastroRecord } from '../services/api'
import { commercialPrice, emptyProduct, parseDecimal, productLineSubtotal, profileLabel, formatClientCompletenessMessage, getClientCompleteness, formatProductCompletenessMessage, getProductCompleteness, type ApiBudget, type ApiClient, type ApiProduct, type BudgetPayload, type BudgetProduct, type BudgetService, type CommercialProfile } from '../types/budget'
import type { CurtainState } from '../types/budget'

type Props={onBack:()=>void; budgetId?:number|null; onSaved:(id:number,mode:'created'|'updated')=>void; onConverted?:()=>void}
const today=new Date().toISOString().slice(0,10)
const CREATE_CLIENT_VALUE = '__CREATE_CLIENT__'
const CREATE_SERVICE_VALUE = '__CREATE_SERVICE__'
const CREATE_PRODUCT_VALUE = '__CREATE_PRODUCT__'

export function NewBudgetPage({onBack,budgetId,onSaved,onConverted}:Props){
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
  const [converting,setConverting]=useState(false)
  const [convertedOrder,setConvertedOrder]=useState<ApiOrder|null>(null)
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

  const [partners,setPartners]=useState<ApiCommercialPartner[]>([])
  const [commercialRegistration, setCommercialRegistration] = useState<CommercialRegistration | null>(null)
  const [representatives,setRepresentatives]=useState<ApiRepresentative[]>([])
  const [sellers,setSellers]=useState<CadastroRecord[]>([])
  const [sellerId,setSellerId]=useState<number|null>(null)

  const [partnerId,setPartnerId]=useState<number|null>(null)
  const [partnerPercent,setPartnerPercent]=useState(0)

  // FASE 10I.2 - PROTOTIPO VISUAL
  // Estes dados ainda nao sao persistidos.
  const [showPartnerRepresentative,setShowPartnerRepresentative]=useState(false)
  const [partnerFinalClient,setPartnerFinalClient]=useState('')
  const [partnerFinalClientFull,setPartnerFinalClientFull]=useState(false)

  const [partnerFinalDocument,setPartnerFinalDocument]=useState('')
  const [partnerFinalPhone,setPartnerFinalPhone]=useState('')
  const [partnerFinalEmail,setPartnerFinalEmail]=useState('')
  const [partnerFinalAddress,setPartnerFinalAddress]=useState('')

  // Fase 10I.1 - visual para aprovação.
  // Estes campos ainda NÃO são persistidos no backend.
  const [partnerRepresentativeName,setPartnerRepresentativeName]=useState('')
  const [partnerRepresentativeRole,setPartnerRepresentativeRole]=useState('')
  const [partnerClientFinalName,setPartnerClientFinalName]=useState('')
  const [showPartnerClientFull,setShowPartnerClientFull]=useState(false)
  const [partnerClientDocument,setPartnerClientDocument]=useState('')
  const [partnerClientPhone,setPartnerClientPhone]=useState('')
  const [partnerClientEmail,setPartnerClientEmail]=useState('')
  const [partnerClientAddress,setPartnerClientAddress]=useState('')
  const [saleType,setSaleType]=useState<
    'DIRETA'|'PARCEIRO'
  >('DIRETA')

  const [includeRt,setIncludeRt]=useState(false)
  const [representativeId,setRepresentativeId]=useState<number|null>(null)
  const [showDirectRepresentative,setShowDirectRepresentative]=useState(false)
  const [rtType,setRtType]=useState<'VALOR_FIXO'|'PERCENTUAL'>('VALOR_FIXO')
  const [rtValue,setRtValue]=useState(0)
  const [rtPercent,setRtPercent]=useState(0)

  const [includeBankFee,setIncludeBankFee]=useState(false)
  const [bankFeePercent,setBankFeePercent]=useState(0)

  const selectedClient = clients.find(c => c.id === clientId)
  const completeness = selectedClient ? getClientCompleteness(selectedClient) : null

  useEffect(()=>{
    void (async()=>{
      try{
        const [partnerRows,representativeRows,sellerRows]=await Promise.all([
          getCommercialPartners(),
          getRepresentatives(),
          getFuncionariosCadastro(),
        ])

        setPartners(partnerRows)
        setRepresentatives(representativeRows)
        setSellers(sellerRows)
      }catch(e){
        console.error(
          'Falha ao carregar parceiro/representante',
          e
        )
      }
    })()
  },[])

  useEffect(()=>{
    if(!budgetId)return

    void getBudget(budgetId)
      .then(b=>{
        setPartnerFinalClient(b.cliente_final_nome ?? '')
        setPartnerFinalDocument(b.cliente_final_documento ?? '')
        setPartnerFinalPhone(b.cliente_final_telefone ?? '')
        setPartnerFinalEmail(b.cliente_final_email ?? '')
        setPartnerFinalAddress(b.cliente_final_endereco ?? '')
        setPartnerFinalClientFull(Boolean(b.cliente_final_documento || b.cliente_final_telefone || b.cliente_final_email || b.cliente_final_endereco))

        setPartnerId(
          b.parceiro_id ?? null
        )

        setSaleType(
          b.parceiro_id
            ? 'PARCEIRO'
            : 'DIRETA'
        )

        setPartnerPercent(
          Number(b.percentual_parceiro ?? 0)
        )

        setIncludeRt(
          Boolean(b.incluir_rt)
        )

        setRepresentativeId(b.representante_id ?? null)
        setShowDirectRepresentative(Boolean(b.representante_id && !b.parceiro_id))
        setShowPartnerRepresentative(Boolean(b.representante_id && b.parceiro_id))

        setSellerId(
          b.vendedor_id ?? null
        )

        setRtType(
          b.tipo_rt==='PERCENTUAL'
            ? 'PERCENTUAL'
            : 'VALOR_FIXO'
        )

        setRtValue(
          Number(b.valor_rt ?? 0)
        )

        setRtPercent(
          Number(b.percentual_rt ?? 0)
        )

        setIncludeBankFee(
          Boolean(b.incluir_taxa_bancaria)
        )

        setBankFeePercent(
          Number(b.taxa_bancaria_percentual ?? 0)
        )
      })
      .catch(()=>undefined)
  },[budgetId])
 useEffect(()=>{void(async()=>{try{const [p,c,b,g,u]=await Promise.all([getAllProducts(),getClients(),budgetId?getBudget(budgetId):Promise.resolve(null),getProductGroups(),getProductUnits()]);setCatalog(p);setClients(c);setProductGroups(g);setProductUnits(u);setInternalObservation(b?.observacao_interna??'');if(!budgetId)setClientId(0);if(b){setClientId(b.cliente_id ?? 0);setStatus(b.status);setValidity(b.validade||today);setObservation(b.observacao||'');setDiscount(Number(b.desconto));const pp=b.itens.filter(i=>i.tipo_item==='PRODUTO').map((i,index)=>{const found=p.find(x=>x.id===i.produto_id);return{...emptyProduct(index+1),productId:i.produto_id||null,product:found?.nome||i.descricao,code:i.codigo_interno||'',family:found?.familia_tecnica||'',groupTechnical:i.grupo_tecnico||'',modelTechnical:i.modelo_tecnico||'',unit:i.unidade||'',color:i.cor||'',details:i.observacao_item||'',quantity:Number(i.quantidade),width:String(i.largura).replace('.',','),height:String(i.altura).replace('.',','),price:Number(i.preco_unitario),discount:Number(i.desconto),curtain:i.dados_tecnicos?.cortina ? {...i.dados_tecnicos.cortina,simulationKey:undefined,result:undefined,error:undefined} : undefined}});setProducts(pp.length?pp:[emptyProduct(1)]);setServices(b.itens.filter(i=>i.tipo_item==='SERVICO').map((i,index)=>({id:index+1,service:i.descricao,details:i.observacao_item||'',quantity:Number(i.quantidade),value:Number(i.preco_unitario),discount:Number(i.desconto)})));setSaved(b)}}catch(e){setError(e instanceof Error?e.message:String(e))}finally{setLoading(false)}})()},[budgetId])
useEffect(()=>{if(budgetId)getBudget(budgetId).then(b=>setProfile(b.perfil_comercial||'VAREJO')).catch(()=>undefined)},[budgetId])
  useEffect(()=>{setProducts(rows=>rows.map(row=>{const found=catalog.find(p=>p.id===row.productId);return found?{...row,romanaKind:romanaKind(found),romanaTetoKind:romanaTetoKind(found),roloKind:roloKind(found),doubleVisionKind:doubleVisionKind(found),price:(romanaKind(found)||romanaTetoKind(found)||roloKind(found)||doubleVisionKind(found))?0:commercialPrice(found,profileLabel[profile])}:row}))},[profile,catalog])
  const onRomana = useCallback((id:number, state:RomanaState) => {
    setProducts(rows => rows.map(row => row.id === id ? {...row, romana:state, price:state.result ? Number(state.result.preco_unitario) : row.price} : row))
  }, [])
  const onRomanaTeto = useCallback((id:number, state:RomanaTetoState) => {
    setProducts(rows => rows.map(row => row.id === id ? {...row, romanaTeto:state, price:state.result ? Number(state.result.preco_unitario) : row.price} : row))
  }, [])
  const onRolo = useCallback((id:number, state:RoloState) => {
    setProducts(rows => rows.map(row => row.id === id ? {...row, rolo:state, price:state.result ? Number(state.result.preco_unitario) : row.price} : row))
  }, [])
  const onDoubleVision = useCallback((id:number, state:DoubleVisionState) => {
    setProducts(rows => rows.map(row => row.id === id ? {...row, doubleVision:state, price:state.result ? Number(state.result.preco_unitario) : row.price} : row))
  }, [])

  const onCurtain = useCallback((id: number, state: CurtainState) => {
    setProducts(rows =>
      rows.map(row =>
        row.id === id
          ? {
              ...row,
              color: state.cor,
              curtain: {
                ...state,
                result: state.result,
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

    setClientId(
      Number(value)||0
    )
  }

  const changeRepresentative=(id:number|null)=>{
    setRepresentativeId(id)
    if(id===null){setIncludeRt(false);setRtType('VALOR_FIXO');setRtValue(0);setRtPercent(0)}
  }
  const handleRepresentativeSelect=(value:string)=>{
    if(value===CREATE_COMMERCIAL_VALUE){setCommercialRegistration('representante');return}
    changeRepresentative(value ? Number(value) : null)
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

const productTotal=products.reduce((s,i)=>s+productLineSubtotal(i,profileLabel[profile]),0),serviceTotal=services.reduce((s,i)=>s+Math.max(0,i.quantity*i.value-i.discount),0),total=Math.max(0,productTotal+serviceTotal+freight-discount)
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
  area:(p.romanaKind||p.romanaTetoKind||p.roloKind||p.doubleVisionKind)?Number(p.romana?.result?.area_real_m2||p.romanaTeto?.result?.area_real_m2||p.rolo?.result?.area_real_m2||p.doubleVision?.result?.area_real_m2||0):parseDecimal(p.width)*parseDecimal(p.height)*p.quantity,
  preco_unitario:p.price,
  desconto:p.discount,
  subtotal:productLineSubtotal(p,profileLabel[profile]),
  dados_tecnicos:technicalItemData(p),
  observacao_item:p.details||null,
  cor:p.color||null,
  acionamento:p.acao_acionamento||undefined,
  lado_comando:p.lado_comando||null,
  comprimento_bastao:p.comprimento_bastao||null,
  comprimento_corrente_sem_fim:p.comprimento_corrente_sem_fim||null,
})
const payload=useMemo<BudgetPayload>(()=>({
  cliente_id:saleType==='DIRETA' ? clientId||null : null,
  ...(saleType==='PARCEIRO' ? {
    cliente_final_nome:partnerFinalClient.trim()||null,
    cliente_final_documento:partnerFinalDocument.trim()||null,
    cliente_final_telefone:partnerFinalPhone.trim()||null,
    cliente_final_email:partnerFinalEmail.trim()||null,
    cliente_final_endereco:partnerFinalAddress.trim()||null,
  } : {}),
  status,
  validade:validity||null,
  observacao:observation,
  observacao_interna:internalObservation,
  desconto:discount,
  total:productTotal+serviceTotal,
  total_final:total,

  parceiro_id:
    saleType==='DIRETA'
      ? null
      : partnerId,

  percentual_parceiro:
    saleType==='DIRETA'
      ? 0
      : partnerPercent,

  representante_id:
    representativeId,

  vendedor_id:
    sellerId,

  incluir_rt:
    includeRt,

  tipo_rt:
    includeRt
      ? rtType
      : null,

  percentual_rt:
    saleType==='PARCEIRO'&&
    includeRt&&
    rtType==='PERCENTUAL'
      ? rtPercent
      : 0,

  valor_rt:
    saleType==='PARCEIRO'&&
    includeRt&&
    rtType==='VALOR_FIXO'
      ? rtValue
      : 0,

  incluir_taxa_bancaria:includeBankFee,

  taxa_bancaria_percentual:includeBankFee
    ? bankFeePercent
    : 0,

  itens:[
    ...products
      .filter(p=>p.productId || p.curtain?.tecidoProdutoId)
      .map(makeItem),

    ...services.map(s=>({
      tipo_item:'SERVICO' as const,
      produto_id:null,
      descricao:s.service,
      quantidade:s.quantity,
      largura:0,
      altura:0,
      area:0,
      preco_unitario:s.value,
      desconto:s.discount,
      subtotal:Math.max(
        0,
        s.quantity*s.value-s.discount
      ),
      observacao_item:s.details||null,
      cor:null,
    }))
  ]
}),[
  clientId,
  status,
  validity,
  observation,
  internalObservation,
  discount,
  total,
  productTotal,
  serviceTotal,
  products,
  services,
  partnerId,
  partnerFinalClient,
  partnerFinalDocument,
  partnerFinalPhone,
  partnerFinalEmail,
  partnerFinalAddress,
  partnerPercent,
  saleType,
  includeRt,
  representativeId,
  sellerId,
  rtType,
  rtValue,
  rtPercent,
  includeBankFee,
  bankFeePercent,
])
const internalValuePreview=Math.max(
  0,
  total
)

const partnerValuePreview=partnerId
  ? internalValuePreview*Math.max(
      0,
      partnerPercent
    )/100
  : 0

const rtValuePreview=includeRt
  ? (
      rtType==='PERCENTUAL'
        ? internalValuePreview*Math.max(0,rtPercent)/100
        : Math.max(0,rtValue)
    )
  : 0

const protectedBasePreview=
  internalValuePreview+
  partnerValuePreview+
  rtValuePreview

const feeRatePreview=includeBankFee
  ? Math.max(
      0,
      Math.min(
        99.99,
        bankFeePercent
      )
    )
  : 0

const clientTotalPreview=
  feeRatePreview>0
    ? protectedBasePreview/
      (1-feeRatePreview/100)
    : protectedBasePreview

const bankFeeValuePreview=Math.max(
  0,
  clientTotalPreview-
  protectedBasePreview
)

const serverPayload={
  ...payload,
  perfil_comercial:profile
}
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

    const currentKey = curtainKey(p, profileLabel[profile])

    return (
      !c.tecidoProdutoId ||
      width <= 0 ||
      height <= 0 ||
      c.simulationKey !== currentKey ||
      Boolean(c.error) ||
      !c.result?.preco_disponivel
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
    curtainPending,
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

  if(curtainPending){setError('Cortina: aguarde a simulação e revise o tecido/forro antes de salvar.');return}
  if(romanaPending){setError('Romana: resolva os avisos técnicos ou aguarde a simulação antes de salvar. Totais não confirmados.');return}if(romanaTetoPending){setError('Romana de teto: resolva os avisos técnicos ou aguarde a simulação antes de salvar. Totais não confirmados.');return}if(roloPending){setError('Rolô: resolva os avisos técnicos ou aguarde a simulação antes de salvar. Totais não confirmados.');return}if(doubleVisionPending){setError('Double Vision: resolva os avisos técnicos ou aguarde a simulação antes de salvar. Totais não confirmados.');return}if(serverPayload.itens.length===0){
  setError('Adicione ao menos um item.')
  return
}

if(saleType==='PARCEIRO'&&clientId){
  setError('Cliente direto e revenda não podem ser informados ao mesmo tempo. Altere o Tipo de venda para corrigir os vínculos.')
  return
}

if(saleType==='DIRETA'&&!clientId){
  setError('Selecione o cliente da venda direta.')
  return
}

if(saleType==='PARCEIRO'&&!partnerId){
  setError('Selecione a revenda.')
  return
}setSaving(true);setError('');try{const editing=budgetId!=null;const result=editing?await updateBudget(budgetId,serverPayload):await createBudget(serverPayload);setSaved(result);onSaved(result.id,editing?'updated':'created')}catch(e){setError(e instanceof Error?e.message:String(e))}finally{setSaving(false)}}
 const convertToSale=async()=>{
   const sourceBudgetId=budgetId||saved?.id

   if(!sourceBudgetId){
     setError('Salve o orçamento antes de converter em venda.')
     return
   }

   if(status!=='APROVADO'){
     setError('Apenas orçamentos aprovados podem ser convertidos em venda.')
     return
   }

   if(saved?.status!=='APROVADO'){
     setError('O status Aprovado ainda não foi salvo. Salve o orçamento e depois converta em venda.')
     return
   }

   if(converting)return

   const confirmed=window.confirm(
     'Converter este orçamento aprovado em venda? O cliente, itens, medidas, serviços, valores e dados técnicos serão copiados para o pedido comercial.'
   )

   if(!confirmed)return

   setConverting(true)
   setError('')

   try{
     const order=await convertBudgetToOrder(sourceBudgetId)
     setConvertedOrder(order)

     if(onConverted){
       onConverted()
     }
   }catch(e){
     setError(e instanceof Error?e.message:String(e))
   }finally{
     setConverting(false)
   }
 }

 const nextId=(items:{id:number}[])=>Math.max(0,...items.map(i=>i.id))+1
  const serviceOptions = useMemo(() => [...new Set(services.map(s => s.service).filter(Boolean))], [services])
if(loading)return <div className="panel loading-state">Carregando catálogo completo, clientes e orçamento...</div>
  return (
    <>
      <div className="new-budget-page" onFocusCapture={selectZeroOnFocus}><section className="new-budget-heading page-heading"><div><button type="button" className="back-button page-back" onClick={onBack}><ArrowLeft size={15}/> Voltar para orçamentos</button><p className="eyebrow">PROPOSTA COMERCIAL CONECTADA</p><h1>{budgetId?'Editar orçamento':'Novo orçamento'} <span className="draft-badge">API real</span></h1><p className="heading-subtitle">Catálogo, clientes, itens, totais e reabertura conectados ao FastAPI.</p></div><div className="budget-number">
  <span>NÚMERO</span>
  <strong>{saved?`#${saved.numero}`:'Automático'}</strong>
  {(budgetId||saved?.id)&&status==='APROVADO'&&(
    <button
      type="button"
      className="primary-button"
      onClick={convertToSale}
      disabled={converting||Boolean(convertedOrder)}
      style={{marginTop:12}}
    >
      {converting
        ? 'Convertendo...'
        : convertedOrder
          ? `Venda ${convertedOrder.numero||convertedOrder.id} criada`
          : 'Converter em venda'}
    </button>
  )}
</div></section>
      {error&&<div className="api-message error">{error}</div>}
      <div className={`new-budget-layout ${isSummaryCollapsed ? 'summary-collapsed' : ''}`}><div className="new-budget-main">
      <BudgetSection icon={<FileText size={17}/>} title="Perfil comercial" subtitle="Um único perfil para todos os produtos; o backend recalcula os preços."><Field label="Tabela de preço"><select value={profile} onChange={e=>setProfile(e.target.value as CommercialProfile)}><option value="DECORADOR">Decorador</option><option value="VAREJO">Varejo</option><option value="CONSUMIDOR_FINAL">Consumidor final</option></select></Field></BudgetSection>
      <BudgetSection
        icon={<WalletCards size={17}/>}
        title="Fluxo comercial"
        subtitle="Controle interno."
      >
        <div className="form-grid general-grid">

          <Field label="Vendedor Smart-tec">
            <select
              value={sellerId ?? ''}
              onChange={e=>
                setSellerId(
                  e.target.value
                    ? Number(e.target.value)
                    : null
                )
              }
            >
              <option value="">
                Sem vendedor definido
              </option>

              {sellers.map(s=>(
                <option
                  key={s.id}
                  value={s.id}
                >
                  {String(s.nome ?? `Funcionário ${s.id}`)}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Tipo de venda">
            <select
              value={
                saleType==='DIRETA'
                  ? 'DIRETA'
                  : 'PARCEIRO'
              }
              onChange={e=>{
                const tipo=e.target.value

                setSaleType(
                  tipo==='DIRETA'
                    ? 'DIRETA'
                    : 'PARCEIRO'
                )

                if(tipo==='DIRETA'){
                  setPartnerId(null)
                  setPartnerPercent(0)

                  setShowPartnerRepresentative(false)
                  changeRepresentative(null)

                  setPartnerFinalClient('')
                  setPartnerFinalDocument('')
                  setPartnerFinalPhone('')
                  setPartnerFinalEmail('')
                  setPartnerFinalAddress('')
                  setPartnerFinalClientFull(false)

                  setIncludeRt(false)
                  setRtValue(0)
                  setRtPercent(0)
                }else{
                  setClientId(0)
                }
              }}
            >
              <option value="DIRETA">
                Venda direta
              </option>

              <option value="PARCEIRO">
                Venda por revenda
              </option>
            </select>
          </Field>

          {saleType==='DIRETA' ? (
            <>
              <Field label="Cliente">
                <div className="product-search-box">
                  <select
                    value={clientId}
                    onChange={e=>
                      handleClientSelectChange(
                        e.target.value
                      )
                    }
                  >
                    <option value={0}>
                      Selecione o cliente
                    </option>

                    {clients.map(c=>(
                      <option
                        key={c.id}
                        value={c.id}
                      >
                        {c.nome}
                      </option>
                    ))}

                    <option value={CREATE_CLIENT_VALUE}>
                      + Cadastrar novo cliente
                    </option>
                  </select>
                </div>
              </Field>

              <Field label="Representante?">
                <select
                  value={
                    showDirectRepresentative
                      ? 'SIM'
                      : 'NAO'
                  }
                  onChange={e=>{
                    const ativo=
                      e.target.value==='SIM'

                    setShowDirectRepresentative(ativo)

                    if(!ativo){
                      changeRepresentative(null)
                      setIncludeRt(false)
                      setRtType('VALOR_FIXO')
                      setRtValue(0)
                      setRtPercent(0)
                    }
                  }}
                >
                  <option value="NAO">
                    Não
                  </option>

                  <option value="SIM">
                    Sim
                  </option>
                </select>
              </Field>

              {showDirectRepresentative && (
                <>
                  <Field label="Representante">
                    <select
                      value={representativeId ?? ''}
                      onChange={e=>handleRepresentativeSelect(e.target.value)}
                    >
                      <option value="">
                        Selecione o representante
                      </option>

                      {representatives.map(r=>(
                        <option
                          key={r.id}
                          value={r.id}
                        >
                          {r.nome}
                        </option>
                      ))}
                      <option value={CREATE_COMMERCIAL_VALUE}>+ Cadastrar novo representante</option>
                    </select>
                  </Field>

                  <Field label="RT">
                    <select disabled={representativeId===null}
                      value={
                        includeRt
                          ? 'SIM'
                          : 'NAO'
                      }
                      onChange={e=>{
                        const ativo=
                          e.target.value==='SIM'

                        setIncludeRt(ativo)

                        if(!ativo){
                          setRtType('VALOR_FIXO')
                          setRtValue(0)
                          setRtPercent(0)
                        }
                      }}
                    >
                      <option value="NAO">
                        Sem RT
                      </option>

                      <option value="SIM">
                        Incluir RT
                      </option>
                    </select>
                  </Field>

                  {includeRt && (
                    <>
                      <Field label="Tipo de RT">
                        <select
                          value={rtType}
                          onChange={e=>{
                            const tipo=e.target.value as
                              'VALOR_FIXO'|'PERCENTUAL'

                            setRtType(tipo)

                            if(tipo==='VALOR_FIXO'){
                              setRtPercent(0)
                            }else{
                              setRtValue(0)
                            }
                          }}
                        >
                          <option value="VALOR_FIXO">
                            Valor fixo
                          </option>

                          <option value="PERCENTUAL">
                            Percentual
                          </option>
                        </select>
                      </Field>

                      {rtType==='VALOR_FIXO' ? (
                        <Field label="Valor RT">
                          <ZeroNumberInput
                            min="0"
                            step="0.01"
                            value={rtValue === 0 ? '' : rtValue}
                            onValueChange={value =>
                              setRtValue(
                                value
                              )
                            }
                          />
                        </Field>
                      ) : (
                        <Field label="RT %">
                          <ZeroNumberInput
                            min="0"
                            max="100"
                            step="0.01"
                            value={rtPercent === 0 ? '' : rtPercent}
                            onValueChange={value =>
                              setRtPercent(
                                value
                              )
                            }
                          />
                        </Field>
                      )}
                    </>
                  )}
                </>
              )}
            </>
          ) : (
            <>
              <Field label="Revenda">
                <select
                  value={partnerId ?? ''}
                  onChange={e=>{
                    if(e.target.value===CREATE_COMMERCIAL_VALUE){setCommercialRegistration('revenda');return}
                    const id=
                      e.target.value
                        ? Number(e.target.value)
                        : null

                    setPartnerId(id)

                    if(!id){
                      setPartnerPercent(0)
                      return
                    }

                    const partner=
                      partners.find(
                        p=>p.id===id
                      )

                    setPartnerPercent(
                      Number(
                        partner?.percentual_padrao ?? 0
                      )
                    )
                  }}
                >
                  <option value="">
                    Selecione a revenda
                  </option>

                  {partners.map(p=>(
                    <option
                      key={p.id}
                      value={p.id}
                    >
                      {p.nome}
                    </option>
                  ))}
                  <option value={CREATE_COMMERCIAL_VALUE}>+ Cadastrar nova revenda</option>
                </select>
              </Field>

              <Field label="% revenda">
                <ZeroNumberInput
                  min="0"
                  step="0.01"
                  disabled={!partnerId}
                  value={partnerPercent === 0 ? '' : partnerPercent}
                  onValueChange={value =>
                    setPartnerPercent(
                      value
                    )
                  }
                />
              </Field>

              <Field label="Representante?">
                <select
                  value={
                    showPartnerRepresentative
                      ? 'SIM'
                      : 'NAO'
                  }
                  onChange={e=>{
                    const ativo=
                      e.target.value==='SIM'

                    setShowPartnerRepresentative(ativo)

                    if(!ativo){
                      changeRepresentative(null)
                      setIncludeRt(false)
                      setRtValue(0)
                      setRtPercent(0)
                    }
                  }}
                >
                  <option value="NAO">
                    Não
                  </option>

                  <option value="SIM">
                    Sim
                  </option>
                </select>
              </Field>

              {showPartnerRepresentative && (
                <>
                  <Field label="Representante">
                    <select value={representativeId ?? ''} onChange={e=>handleRepresentativeSelect(e.target.value)}>
                      <option value="">Selecione o representante</option>
                      {representatives.map(r=><option key={r.id} value={r.id}>{r.nome}</option>)}
                      <option value={CREATE_COMMERCIAL_VALUE}>+ Cadastrar novo representante</option>
                    </select>
                  </Field>

                  <Field label="RT">
                    <select disabled={representativeId===null}
                      value={
                        includeRt
                          ? 'SIM'
                          : 'NAO'
                      }
                      onChange={e=>{
                        const ativo=
                          e.target.value==='SIM'

                        setIncludeRt(ativo)

                        if(!ativo){
                          setRtValue(0)
                          setRtPercent(0)
                        }
                      }}
                    >
                      <option value="NAO">
                        Sem RT
                      </option>

                      <option value="SIM">
                        Incluir RT
                      </option>
                    </select>
                  </Field>

                  {includeRt && (
                    <>
                      <Field label="Tipo de RT">
                        <select
                          value={rtType}
                          onChange={e=>{
                            const tipo=e.target.value as
                              'VALOR_FIXO'|'PERCENTUAL'

                            setRtType(tipo)

                            if(tipo==='VALOR_FIXO'){
                              setRtPercent(0)
                            }else{
                              setRtValue(0)
                            }
                          }}
                        >
                          <option value="VALOR_FIXO">
                            Valor fixo
                          </option>

                          <option value="PERCENTUAL">
                            Percentual
                          </option>
                        </select>
                      </Field>

                      {rtType==='VALOR_FIXO' ? (
                        <Field label="Valor RT">
                          <ZeroNumberInput
                            min="0"
                            step="0.01"
                            value={rtValue === 0 ? '' : rtValue}
                            onValueChange={value =>
                              setRtValue(
                                value
                              )
                            }
                          />
                        </Field>
                      ) : (
                        <Field label="RT %">
                          <ZeroNumberInput
                            min="0"
                            max="100"
                            step="0.01"
                            value={rtPercent === 0 ? '' : rtPercent}
                            onValueChange={value =>
                              setRtPercent(
                                value
                              )
                            }
                          />
                        </Field>
                      )}
                    </>
                  )}
                </>
              )}

              <Field label="Cliente">
                <input
                  type="text"
                  placeholder="Nome ou referência"
                  value={partnerFinalClient}
                  onChange={e=>
                    setPartnerFinalClient(
                      e.target.value
                    )
                  }
                />
              </Field>

              <Field label="Dados completos?">
                <select
                  disabled={!partnerFinalClient.trim()}
                  value={
                    partnerFinalClientFull
                      ? 'SIM'
                      : 'NAO'
                  }
                  onChange={e=>
                    setPartnerFinalClientFull(
                      e.target.value==='SIM'
                    )
                  }
                >
                  <option value="NAO">
                    Não
                  </option>

                  <option value="SIM">
                    Sim
                  </option>
                </select>
              </Field>

              {partnerFinalClientFull &&
                partnerFinalClient.trim() && (
                  <>
                    <Field label="CPF / CNPJ">
                      <input
                        type="text"
                        value={partnerFinalDocument}
                        onChange={e=>
                          setPartnerFinalDocument(
                            e.target.value
                          )
                        }
                      />
                    </Field>

                    <Field label="Telefone">
                      <input
                        type="text"
                        value={partnerFinalPhone}
                        onChange={e=>
                          setPartnerFinalPhone(
                            e.target.value
                          )
                        }
                      />
                    </Field>

                    <Field label="E-mail">
                      <input
                        type="email"
                        value={partnerFinalEmail}
                        onChange={e=>
                          setPartnerFinalEmail(
                            e.target.value
                          )
                        }
                      />
                    </Field>

                    <Field label="Endereço">
                      <input
                        type="text"
                        value={partnerFinalAddress}
                        onChange={e=>
                          setPartnerFinalAddress(
                            e.target.value
                          )
                        }
                      />
                    </Field>
                  </>
                )}

              <div
                style={{
                  gridColumn:'1 / -1',
                  border:'1px solid #d9dee7',
                  borderRadius:12,
                  padding:'16px 18px',
                  background:'#fafafa',
                }}
              >
                <div
                  style={{
                    fontSize:12,
                    textTransform:'uppercase',
                    letterSpacing:'.08em',
                    marginBottom:10,
                    opacity:.65,
                  }}
                >
                  Prévia do cabeçalho do orçamento
                </div>

                {partnerFinalClient.trim() && (
                  <div style={{marginBottom:6}}>
                    <strong>Cliente:</strong>{' '}
                    {partnerFinalClient}
                  </div>
                )}

                {showPartnerRepresentative &&
                  representativeId && (
                    <div style={{marginBottom:6}}>
                      <strong>Representante:</strong>{' '}
                      {representatives.find(r=>r.id===representativeId)?.nome ?? `Representante #${representativeId}`}
                    </div>
                )}

                {sellerId && (
                  <div style={{marginBottom:6}}>
                    <strong>Vendedor Smart-tec:</strong>{' '}
                    {
                      String(sellers.find(
                        s=>s.id===sellerId
                      )?.nome ?? '')
                    }
                  </div>
                )}

                {partnerId && (
                  <div>
                    <strong>Revenda:</strong>{' '}
                    {
                      partners.find(
                        p=>p.id===partnerId
                      )?.nome ?? ''
                    }
                  </div>
                )}

                {!partnerFinalClient.trim() &&
                  !representativeId &&
                  !partnerId && (
                    <span style={{opacity:.6}}>
                      Selecione a revenda para visualizar.
                    </span>
                )}
              </div>
            </>
          )}

        </div>
      </BudgetSection>
      <BudgetSection
        icon={<FileText size={17}/>}
        title="Dados do orçamento"
        subtitle="Situação e validade deste orçamento."
      >
        <div className="form-grid general-grid">

          <Field label="Status">
            <select
              value={status}
              onChange={e=>
                setStatus(
                  e.target.value
                )
              }
            >
              <option value="EM_ABERTO">
                Em aberto
              </option>

              <option value="APROVADO">
                Aprovado
              </option>

              <option value="CANCELADO">
                Cancelado
              </option>
            </select>
          </Field>

          <Field label="Validade">
            <input
              type="date"
              value={validity}
              onChange={e=>
                setValidity(
                  e.target.value
                )
              }
            />
          </Field>

        </div>
      </BudgetSection>
      <BudgetSection icon={<PackagePlus size={17}/>} title="Produtos" subtitle={`${catalog.length} produtos carregados; somente ativos aparecem na busca.`} count={`${products.length} itens`}>{romanaPending && <div className="api-message error">Romana com simulação pendente, inválida ou indisponível: os totais ainda não estão confirmados e o salvamento está bloqueado.</div>}{romanaTetoPending && <div className="api-message error">Romana de teto com simulação pendente, inválida ou indisponível: os totais ainda não estão confirmados e o salvamento está bloqueado.</div>}{roloPending && <div className="api-message error">Rolô com simulação pendente, inválida ou indisponível: os totais ainda não estão confirmados e o salvamento está bloqueado.</div>}{doubleVisionPending && <div className="api-message error">Double Vision com simulação pendente, inválida ou indisponível: os totais ainda não estão confirmados e o salvamento está bloqueado.</div>}<div className="product-rows">{products.map(p=><BudgetProductRow key={p.id} product={p} catalog={catalog} commercialType={profileLabel[profile]} validationAttempted={validationAttempted} onRomana={onRomana} onRomanaTeto={onRomanaTeto} onRolo={onRolo} onDoubleVision={onDoubleVision} onCurtain={onCurtain} onChange={n=>setProducts(rows=>rows.map(r=>r.id===n.id?n:r))} onRemove={()=>setProducts(rows=>rows.filter(r=>r.id!==p.id))} onCreateProduct={handleOpenProductModal}/>)}</div><button type="button" className="secondary-button add-product" onClick={()=>setProducts(rows=>[...rows,emptyProduct(nextId(rows))])}><Plus size={16}/> Adicionar produto</button></BudgetSection>
      <BudgetSection icon={<ReceiptText size={17}/>} title="Serviços" subtitle="Persistidos como itens do tipo SERVICO." count={`${services.length} itens`}><div className="service-rows">{services.map(s=><BudgetServiceRow key={s.id} service={s} onChange={n=>setServices(rows=>rows.map(r=>r.id===n.id?n:r))} onRemove={()=>setServices(rows=>rows.filter(r=>r.id!==s.id))} onCreateService={handleOpenServiceModal} createServiceValue={CREATE_SERVICE_VALUE} serviceOptions={serviceOptions}/>)}</div><button type="button" className="secondary-button add-product" onClick={()=>setServices(rows=>[...rows,{id:nextId(rows),service:'Instalação',details:'',quantity:1,value:0,discount:0}])}><Plus size={16}/> Adicionar serviço</button></BudgetSection>
      <BudgetSection icon={<Truck size={17}/>} title="Transporte" subtitle="Ainda sem campos próprios no contrato."><div className="form-grid relationship-grid"><Field label="Frete"><input type="number" value={freight} disabled/><small>Não persistido nesta fase</small></Field><Field label="Transportadora"><input disabled placeholder="Não persistida nesta fase"/></Field></div></BudgetSection>
      <BudgetSection icon={<WalletCards size={17}/>} title="Pagamento" subtitle="Não persistido pelo contrato atual."><div className="api-message">Condição, parcelas, vencimento e forma de pagamento permanecem pendentes de modelagem futura.</div></BudgetSection>
      <BudgetSection icon={<FileText size={17}/>} title="Observações" subtitle="Informações para o cliente e anotações internas da equipe."><div className="budget-observations-grid"><Field label="Observações para o cliente"><textarea value={observation} onChange={e=>setObservation(e.target.value)}/></Field><Field label="Observações internas"><textarea value={internalObservation} onChange={e=>setInternalObservation(e.target.value)}/></Field></div></BudgetSection>
<BudgetSection icon={<ReceiptText size={17}/>} title="Payload da API" subtitle="O preço de produto é apenas estimativo; o servidor recalcula o valor definitivo."><pre className="payload-preview">{JSON.stringify(serverPayload,null,2)}</pre></BudgetSection>
      </div><BudgetSummary
        products={productTotal}
        services={serviceTotal}
        freight={freight}

        discount={discount}
        onDiscount={setDiscount}

        includeBankFee={includeBankFee}
        onIncludeBankFee={setIncludeBankFee}

        bankFeePercent={bankFeePercent}
        onBankFeePercent={setBankFeePercent}

        internalValue={internalValuePreview}
        partnerValue={partnerValuePreview}
        rtValue={rtValuePreview}
        bankFeeValue={bankFeeValuePreview}
        clientTotal={clientTotalPreview}

        onCancel={onBack}
        onSave={save}

        saving={saving}
        isCollapsed={isSummaryCollapsed}
        onToggle={()=>
          setIsSummaryCollapsed(
            prev=>!prev
          )
        }
      /></div></div>
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

      {commercialRegistration && <CommercialRegistrationDialog entity={commercialRegistration} onClose={()=>setCommercialRegistration(null)} onCreated={record=>{
        if(commercialRegistration==='revenda'){setPartners(rows=>[record,...rows]);setPartnerId(record.id);setPartnerPercent(Number(record.percentual_padrao??0))}
        else {setRepresentatives(rows=>[record,...rows]);changeRepresentative(record.id)}
      }} />}
      {showClientModal&&<div className="modal-overlay" onClick={handleCloseClientModal}><div className="modal-container" onClick={e=>e.stopPropagation()}><div className="modal-header"><h3><UserPlus size={16}/> Cadastrar novo cliente</h3><button type="button" className="modal-close" onClick={handleCloseClientModal}><X size={16}/></button></div><form className="modal-form" onSubmit={e=>{e.preventDefault();handleCreateClient()}}><div className="modal-field"><label>Tipo *</label><select value={clientForm.tipo} onChange={e=>handleClientFormChange('tipo',e.target.value)}><option value="">Selecione</option><option value="Pessoa Física">Pessoa Física</option><option value="Pessoa Jurídica">Pessoa Jurídica</option></select></div><div className="modal-field"><label>Nome *</label><input type="text" value={clientForm.nome} onChange={e=>handleClientFormChange('nome',e.target.value)} placeholder="Nome do cliente" autoFocus/></div>{clientModalError&&<div className="modal-error">{clientModalError}</div>}<div className="modal-actions"><button type="button" className="secondary-button" onClick={handleCloseClientModal} disabled={clientModalSaving}>Cancelar</button><button type="submit" className="primary-button" disabled={clientModalSaving||!clientForm.tipo.trim()||!clientForm.nome.trim()}>{clientModalSaving?<><Loader2 size={14} className="spinning"/> Salvando...</>:<><UserPlus size={14}/> Salvar e selecionar</>}</button></div></form></div></div>}

      {showServiceModal&&<div className="modal-overlay" onClick={handleCloseServiceModal}><div className="modal-container" onClick={e=>e.stopPropagation()}><div className="modal-header"><h3><PackagePlus size={16}/> Cadastrar novo serviço</h3><button type="button" className="modal-close" onClick={handleCloseServiceModal}><X size={16}/></button></div><form className="modal-form" onSubmit={e=>{e.preventDefault();handleCreateService()}}><div className="modal-field"><label>Nome do serviço *</label><input type="text" value={serviceForm.nome} onChange={e=>handleServiceFormChange('nome',e.target.value)} placeholder="Ex: Instalação, Medição, Manutenção" autoFocus/></div>{serviceModalError&&<div className="modal-error">{serviceModalError}</div>}<div className="modal-actions"><button type="button" className="secondary-button" onClick={handleCloseServiceModal} disabled={serviceModalSaving}>Cancelar</button><button type="submit" className="primary-button" disabled={serviceModalSaving||!serviceForm.nome.trim()}>{serviceModalSaving?<><Loader2 size={14} className="spinning"/> Salvando...</>:<><PackagePlus size={14}/> Salvar e usar</>}</button></div></form></div></div>}

      {showProductModal&&<div className="modal-overlay" onClick={handleCloseProductModal}><div className="modal-container" onClick={e=>e.stopPropagation()}><div className="modal-header"><h3><PackagePlus size={16}/> Cadastrar novo produto</h3><button type="button" className="modal-close" onClick={handleCloseProductModal}><X size={16}/></button></div><form className="modal-form" onSubmit={e=>{e.preventDefault();handleCreateProduct()}}><div className="modal-field"><label>Nome *</label><input type="text" value={productForm.nome} onChange={e=>handleProductFormChange('nome',e.target.value)} placeholder="Nome do produto" autoFocus/></div><div className="modal-field"><label>Grupo do produto *</label><select value={productForm.grupo_produto} onChange={e=>handleProductFormChange('grupo_produto',e.target.value)}><option value="">Selecione</option>{productGroups.map(g=><option key={g} value={g}>{g}</option>)}</select></div><div className="modal-field"><label>Unidade de venda *</label><select value={productForm.unidade_venda} onChange={e=>handleProductFormChange('unidade_venda',e.target.value)}><option value="">Selecione</option>{effectiveProductUnits.map(u=><option key={u} value={u}>{u}</option>)}</select></div><div className="modal-field"><label>Valor de custo *</label><input type="text" inputMode="decimal" value={productForm.valor_custo} onChange={e=>handleProductFormChange('valor_custo',e.target.value)} placeholder="Ex: 150,00"/></div>{productModalError&&<div className="modal-error">{productModalError}</div>}<div className="modal-actions"><button type="button" className="secondary-button" onClick={handleCloseProductModal} disabled={productModalSaving}>Cancelar</button><button type="submit" className="primary-button" disabled={productModalSaving||!productForm.nome.trim()||!productForm.grupo_produto.trim()||!productForm.unidade_venda.trim()||!productForm.valor_custo.trim()}>{productModalSaving?<><Loader2 size={14} className="spinning"/> Salvando...</>:<><PackagePlus size={14}/> Salvar e selecionar</>}</button></div></form></div></div>}
    </>
  )
}
function BudgetSection({icon,title,subtitle,count,children}:{icon:React.ReactNode;title:string;subtitle:string;count?:string;children:React.ReactNode}){return <section className="form-section panel"><div className="section-title"><div className="section-icon">{icon}</div><div><h2>{title}</h2><p>{subtitle}</p></div>{count&&<span className="section-count">{count}</span>}</div>{children}</section>}
function Field({label,children}:{label:string;children:React.ReactNode}){return <label className="field"><span>{label}</span>{children}</label>}
