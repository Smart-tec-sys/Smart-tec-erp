import { createElement } from 'react'
import { pdf } from '@react-pdf/renderer'
import type { ApiBudget } from '../types/budget'
import { BudgetPdfDocument } from '../components/budgetPdf/BudgetPdfDocument'
import { budgetPdfFilename, prepareBudgetPdfData } from './budgetPdfData'
import type { BudgetPdfMode,BudgetPdfContext } from './budgetPdfData'
export type { BudgetPdfMode,BudgetPdfContext } from './budgetPdfData'
export async function generateBudgetPdf(budget:ApiBudget,mode:BudgetPdfMode,context:BudgetPdfContext={}):Promise<Blob>{
 const data=prepareBudgetPdfData(budget,mode,context)
 const blob=await pdf(createElement(BudgetPdfDocument,{data})).toBlob()
 if(blob.type!=='application/pdf'||blob.size===0)throw new Error('Não foi possível gerar um PDF válido.')
 return blob
}
async function loadCompanyLogo(path:string,apiUrl:string):Promise<string>{
 const url=new URL(path,apiUrl)
 if(!['http:','https:'].includes(url.protocol))throw new Error('Endereço de logo inválido.')
 const response=await fetch(url,{signal:AbortSignal.timeout(10000),credentials:'omit'})
 if(!response.ok)throw new Error('Logo indisponível.')
 const blob=await response.blob()
 if(!['image/png','image/jpeg','image/webp'].includes(blob.type)||blob.size===0||blob.size>5*1024*1024)throw new Error('Logo inválida.')
 // Decodificar antes do renderer; normalizar WebP e imagens para PNG.
 const bitmap=await createImageBitmap(blob)
 try{
  if(!bitmap.width||!bitmap.height||bitmap.width*bitmap.height>25000000)throw new Error('Dimensões da logo inválidas.')
  const scale=Math.min(1,800/Math.max(bitmap.width,bitmap.height))
  const canvas=document.createElement('canvas')
  canvas.width=Math.max(1,Math.round(bitmap.width*scale));canvas.height=Math.max(1,Math.round(bitmap.height*scale))
  const context=canvas.getContext('2d')
  if(!context)throw new Error('Não foi possível preparar a logo.')
  context.drawImage(bitmap,0,0,canvas.width,canvas.height)
  return canvas.toDataURL('image/png')
 }finally{bitmap.close()}
}
export async function loadBudgetPdfContext(budget:ApiBudget,mode:BudgetPdfMode):Promise<BudgetPdfContext>{
 const api=await import('./api')
 const auth=await import('./auth')
 const empresaId=await budgetPdfCompanyId()
 const internal=mode==='reseller_internal'
 const resellerDocument=internal||mode==='reseller_commercial'
 let clients,resellers,sellers,representatives,me
 try{
  [clients,resellers,sellers,representatives,me]=await Promise.all([
   mode!=='direct'||budget.cliente_id==null?Promise.resolve([]):api.getClients(),
   !resellerDocument||budget.parceiro_id==null?Promise.resolve([]):api.getCommercialPartners(),
   !internal||budget.vendedor_id==null?Promise.resolve([]):api.getFuncionariosCadastro(),
   !internal||budget.representante_id==null?Promise.resolve([]):api.getRepresentatives(),
   auth.authEnabled?auth.getAuthMe():api.request<{id:number;nome:string;nome_fantasia?:string|null;documento?:string|null;logo_url?:string|null}>('/empresa/atual').then(company=>({empresas:[company]}))
  ])
 }catch{throw new Error('Não foi possível carregar os dados da empresa ou dos cadastros para o PDF. Tente novamente.')}
 if(await budgetPdfCompanyId()!==empresaId)throw new Error('A empresa ativa mudou. Abra novamente o orçamento.')
 const company=me.empresas.find(item=>item.id===empresaId)
 if(!company)throw new Error('Empresa ativa não encontrada para gerar o PDF.')
 const client=clients.find(item=>item.id===budget.cliente_id)
 const reseller=resellers.find(item=>item.id===budget.parceiro_id)
 const seller=sellers.find(item=>item.id===budget.vendedor_id)
 const representative=representatives.find(item=>item.id===budget.representante_id)
 if((mode==='direct'&&budget.cliente_id!=null&&!client)||(resellerDocument&&budget.parceiro_id!=null&&!reseller)||(internal&&budget.vendedor_id!=null&&!seller)||(internal&&budget.representante_id!=null&&!representative))throw new Error('Cadastro vinculado ao orçamento não encontrado. Confira os dados antes de gerar o PDF.')
 const context:BudgetPdfContext={
  client,resellerName:reseller?.nome,sellerName:seller?String(seller.nome??''):undefined,
  representativeName:representative?.nome,companyName:company.nome,
  companyTradeName:company.nome_fantasia??undefined,
  companyDocument:'documento' in company&&typeof company.documento==='string'?company.documento:undefined,
  warnings:[],
 }
 if(company.logo_url){
  try{context.companyLogo=await loadCompanyLogo(company.logo_url,api.apiConfig.baseUrl)}
  catch{context.warnings?.push('A logo da empresa não pôde ser carregada. O PDF foi gerado sem logo.')}
 }
 return context
}
async function budgetPdfCompanyId():Promise<number>{
 const auth=await import('./auth')
 if(auth.authEnabled){
  const empresaId=auth.getEmpresaId()
  if(empresaId==null)throw new Error('Empresa ativa não encontrada para gerar o PDF.')
  return empresaId
 }
 const headers=await auth.getApiAuthHeaders()
 const empresaId=Number(headers['X-Empresa-ID'])
 if(!Number.isInteger(empresaId)||empresaId<=0)throw new Error('Empresa local não configurada para gerar o PDF.')
 return empresaId
}
export async function prepareSavedBudgetPdf(id:number,mode:BudgetPdfMode){
 const api=await import('./api')
 const empresaId=await budgetPdfCompanyId()
 let budget:ApiBudget
 try{budget=await api.getBudget(id)}
 catch{throw new Error('Não foi possível recarregar o orçamento salvo. Tente novamente.')}
 if(await budgetPdfCompanyId()!==empresaId)throw new Error('A empresa ativa mudou. Abra novamente o orçamento.')
 // Validar o modo antes de consultas auxiliares ou geração.
 const projection=prepareBudgetPdfData(budget,mode)
 const context=await loadBudgetPdfContext(budget,mode)
 if(await budgetPdfCompanyId()!==empresaId)throw new Error('A empresa ativa mudou. Abra novamente o orçamento.')
 const blob=await generateBudgetPdf(budget,mode,context)
 if(await budgetPdfCompanyId()!==empresaId)throw new Error('A empresa ativa mudou. Abra novamente o orçamento.')
 return {budget,blob,warnings:[...(context.warnings??[]),...projection.warnings],filename:budgetPdfFilename(String(budget.numero||budget.id),mode)}
}
export function downloadBudgetPdf(blob:Blob,filename:string){
 const url=URL.createObjectURL(blob),link=document.createElement('a')
 link.href=url;link.download=filename;document.body.appendChild(link);link.click();link.remove()
 // Retain the URL until the browser has consumed the download request.
 setTimeout(()=>URL.revokeObjectURL(url),60000)
}
