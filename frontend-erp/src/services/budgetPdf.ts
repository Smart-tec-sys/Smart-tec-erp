import { createElement } from 'react'
import { pdf } from '@react-pdf/renderer'
import type { ApiBudget } from '../types/budget'
import { BudgetPdfDocument } from '../components/budgetPdf/BudgetPdfDocument'
import { prepareBudgetPdfData } from './budgetPdfData'
import type { BudgetPdfMode,BudgetPdfContext } from './budgetPdfData'
export type { BudgetPdfMode,BudgetPdfContext } from './budgetPdfData'
export async function generateBudgetPdf(budget:ApiBudget,mode:BudgetPdfMode,context:BudgetPdfContext={}):Promise<Blob>{
 const data=prepareBudgetPdfData(budget,mode,context)
 const blob=await pdf(createElement(BudgetPdfDocument,{data})).toBlob()
 if(blob.type!=='application/pdf'||blob.size===0)throw new Error('Não foi possível gerar um PDF válido.')
 return blob
}
export async function loadBudgetPdfContext(budget:ApiBudget):Promise<BudgetPdfContext>{
 const api=await import('./api')
 const auth=await import('./auth')
 const [clients,resellers,sellers,representatives,me]=await Promise.allSettled([
  budget.cliente_id==null?Promise.resolve([]):api.getClients(),
  budget.parceiro_id==null?Promise.resolve([]):api.getCommercialPartners(),
  budget.vendedor_id==null?Promise.resolve([]):api.getFuncionariosCadastro(),
  budget.representante_id==null?Promise.resolve([]):api.getRepresentatives(),auth.getAuthMe()
 ])
 return {client:clients.status==='fulfilled'?clients.value.find(item=>item.id===budget.cliente_id):undefined,
 resellerName:resellers.status==='fulfilled'?resellers.value.find(item=>item.id===budget.parceiro_id)?.nome:undefined,
 sellerName:sellers.status==='fulfilled'?(String(sellers.value.find(item=>item.id===budget.vendedor_id)?.nome??'')||undefined):undefined,
 representativeName:representatives.status==='fulfilled'?representatives.value.find(item=>item.id===budget.representante_id)?.nome:undefined,
 companyName:me.status==='fulfilled'?me.value.empresas.find(item=>item.id===auth.getEmpresaId())?.nome:undefined}
}
export function downloadBudgetPdf(blob:Blob,filename:string){
 const url=URL.createObjectURL(blob),link=document.createElement('a')
 link.href=url;link.download=filename;document.body.appendChild(link);link.click();link.remove()
 // Retain the URL until the browser has consumed the download request.
 setTimeout(()=>URL.revokeObjectURL(url),60000)
}
