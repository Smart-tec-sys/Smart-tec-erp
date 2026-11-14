import { apiConfig } from './api'
import { getApiAuthHeaders } from './auth'

export type FiscalEmpresaDados = {
  inscricao_estadual: string | null
  inscricao_municipal: string | null
  cnae_principal: string | null
  regime_especial_tributacao: string | null
  informacoes_complementares: string | null
  crt: '1' | '2' | '3' | '4' | null
  uf: string | null
  municipio_codigo_ibge: string | null
  cidade: string | null
  cep: string | null
  logradouro: string | null
  numero: string | null
  bairro: string | null
  complemento: string | null
  serie_nfe: number | null
  ambiente: 'HOMOLOGACAO'
}
export type FiscalProdutoDados = {
  ncm: string | null
  cfop_padrao_saida: string | null
  cest: string | null
  origem_mercadoria: string | null
  cst_icms: string | null
  csosn: string | null
  cst_pis: string | null
  cst_cofins: string | null
  cst_ibs_cbs: string | null
  cclass_trib_ibs_cbs: string | null
}
export type FiscalEmpresaResponse = { empresa_id:number; documento:string|null; razao_social:string|null; nome_fantasia:string|null; dados:FiscalEmpresaDados; emissao_habilitada:false }
export type FiscalProdutoResponse = { empresa_id:number; produto_id:number; dados:FiscalProdutoDados; configurado:boolean; emissao_habilitada:false }

async function fiscalRequest<T>(path:string, method:'GET'|'PATCH'='GET', body?:Record<string,unknown>):Promise<T> {
  const auth = await getApiAuthHeaders()
  const response = await fetch(apiConfig.baseUrl + path,{
    method, headers:{'Content-Type':'application/json',...auth},
    ...(body ? {body: JSON.stringify(body)} : {}),
  })
  if(!response.ok) {
    // Não exibir stack traces ou corpo bruto de erro.
    throw new Error(response.status===403?'Somente administradores podem editar o cadastro fiscal.':
      response.status===404?'Cadastro não encontrado na empresa ativa.':
      response.status===422?'Revise os campos fiscais e seus formatos.':
      'Não foi possível consultar ou salvar o cadastro fiscal.')
  }
  return response.json() as Promise<T>
}

export const getFiscalEmpresa = ()=>fiscalRequest<FiscalEmpresaResponse>('/fiscal/cadastros/empresa')
export const patchFiscalEmpresa = (data:Partial<FiscalEmpresaDados>)=>
  fiscalRequest<FiscalEmpresaResponse>('/fiscal/cadastros/empresa','PATCH',data)
export const getFiscalProduto = (id:number)=>fiscalRequest<FiscalProdutoResponse>('/fiscal/cadastros/produtos/'+id)
export const patchFiscalProduto = (id:number,data:Partial<FiscalProdutoDados>)=>
  fiscalRequest<FiscalProdutoResponse>('/fiscal/cadastros/produtos/'+id,'PATCH',data)

export type FiscalPendencia = { codigo:string; campo:string; nivel:string; mensagem:string }
export type PreparacaoNfeResponse = {
  documento: 'NFE'; estado: 'NAO_APTO_EMISSAO'; simulacao:true; transmitido:false;
  pedido_id:number; numero_venda:string|null;
  resumo: Record<string,string|number|null>;
  quantidade_pendencias:number; pendencias:FiscalPendencia[];
  cadastros_fiscais?:{
    emitente_cadastrado:boolean; total_skus:number;
    skus_com_cadastro:number; skus_sem_cadastro:number[];
    tipo_validacao:string;
  };
  aviso:string;
}
export const prepararNfeVenda = (pedidoId:number)=>
  fiscalRequest<PreparacaoNfeResponse>('/pedidos/'+pedidoId+'/fiscal/preparacao-nfe')
