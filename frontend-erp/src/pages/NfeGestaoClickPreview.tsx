import { useState } from 'react'
import './FiscalPage.css'

/**
 * Espelho estrutural do backup GestãoClick de 05/11/2026.
 * Fonte: notas_fiscais/notas_fiscais.xlsx,
 * notas_fiscais_produtos.xlsx, notas_fiscais_pagamentos.xlsx e
 * notas_fiscais_correcoes.xlsx.
 * Não reproduz layout original; não importa conteúdo fiscal real.
 * Nenhum endpoint, certificado, numeração ou transmissão está disponível.
 */
const fields = {
  identificacao: [
    ['numero', 'Número'], ['serie', 'Série'], ['situacao', 'Situação'],
    ['ambiente', 'Ambiente'], ['tipo', 'Tipo (entrada/saída)'],
    ['finalidade', 'Finalidade'], ['natureza', 'Natureza da operação'],
    ['cfop', 'CFOP da operação'], ['data', 'Data de emissão'],
    ['hora', 'Hora de emissão'], ['atendimento', 'Tipo de atendimento'],
    ['consumidor', 'Consumidor final'],
  ],
  destinatario: [
    ['nome', 'Nome ou razão social'], ['documento', 'CPF/CNPJ'],
    ['tipo', 'Tipo de contribuinte'], ['ie', 'Inscrição Estadual'],
    ['logradouro', 'Logradouro'], ['numero', 'Número'], ['complemento', 'Complemento'],
    ['bairro', 'Bairro'], ['cidade', 'Cidade'], ['uf', 'Estado (UF)'],
    ['cep', 'CEP'], ['telefone', 'Telefone'], ['email', 'E-mail'],
  ],
  totais: [
    ['produtos', 'Valor dos produtos'], ['frete', 'Frete'],
    ['seguro', 'Seguro'], ['descontos', 'Descontos'],
    ['baseicms', 'Base de cálculo ICMS'], ['icms', 'Valor ICMS'],
    ['baseicmsst', 'Base de cálculo ICMS-ST'], ['icmsst', 'Valor ICMS-ST'],
    ['ipi', 'IPI'], ['pis', 'PIS'], ['cofins', 'COFINS'],
    ['ii', 'II'], ['outros', 'Outros valores'], ['tributos', 'Total de tributos'],
    ['total', 'Valor total da NF-e'],
  ],
} as const

type SectionName = keyof typeof fields

const rows = [
  {codigo:'DEMO-RL-101',nome:'Persiana Rolô — produto fictício',cfop:'',ncm:'',unidade:'M²',quantidade:'2',valorUnitario:'',total:''},
  {codigo:'DEMO-RM-303',nome:'Persiana Romana — produto fictício',cfop:'',ncm:'',unidade:'M²',quantidade:'1',valorUnitario:'',total:''},
]

export function NfeGestaoClickPreview() {
  const [values, setValues] = useState<Record<string,string>>({
    'identificacao.ambiente':'Homologação',
    'identificacao.situacao':'Rascunho de demonstração',
    'identificacao.tipo':'Saída',
    'identificacao.finalidade':'NF-e normal',
  })
  const [products, setProducts] = useState(rows)
  const [payments,setPayments] = useState([{numero:'DEMO-01',forma:'',vencimento:'',valor:''}])
  const [correcoes,setCorrecoes] = useState([{numero:'',descricao:''}])
  const change=(key:string,val:string)=>setValues(v=>({...v,[key]:val}))

  const renderFields=(section:SectionName)=>(
    <div className="fiscal-v1-grid">
      {fields[section].map(([key,label])=>{
        const full=section+'.'+key
        return <label key={full}>
          <span>{label}</span>
          <input value={values[full]||''} placeholder={label}
            onChange={e=>change(full,e.target.value)}
            aria-label={label}/>
        </label>
      })}
    </div>
  )

  return <section className="fiscal-v1-panel fiscal-v1-nfe" aria-label="Prévia dos campos de nota fiscal">
    <h2>NF-e de produtos — estrutura do backup GestãoClick</h2>
    <p className="fiscal-v1-muted">
      Conferência visual dos grupos de dados existentes na exportação. Campos em branco e produtos de demonstração;
      nada nesta aba é salvo, autorizado ou enviado à SEFAZ.
    </p>

    <h3>1. Identificação da nota</h3>
    {renderFields('identificacao')}

    <h3>2. Emitente</h3>
    <p className="fiscal-v1-muted">
      CNPJ, razão social e endereço fiscal vêm do cadastro da empresa ativa.
      Configure esses dados na aba <strong>Dados da empresa</strong>.
    </p>

    <h3>3. Destinatário</h3>
    {renderFields('destinatario')}

    <h3>4. Produtos da NF-e</h3>
    <div className="fiscal-v1-table-wrap">
      <table className="fiscal-v1-table">
        <thead><tr>{['Código','Descrição','CFOP','NCM','Unidade','Qtd.','Valor unitário','Valor total'].map(t=><th key={t}>{t}</th>)}</tr></thead>
        <tbody>{products.map((p,i)=><tr key={i}>
          {(['codigo','nome','cfop','ncm','unidade','quantidade','valorUnitario','total'] as const).map(k=>
            <td key={k}><input aria-label={k+' do item '+(i+1)} value={p[k]}
              onChange={e=>setProducts(v=>v.map((r,j)=>i===j?{...r,[k]:e.target.value}:r))}/></td>)}
        </tr>)}</tbody>
      </table>
    </div>
    <button type="button" className="fiscal-v1-add" onClick={()=>setProducts(v=>[...v,{
      codigo:'',nome:'',cfop:'',ncm:'',unidade:'UN',quantidade:'1',valorUnitario:'',total:'',
    }])}>Adicionar linha fictícia</button>

    <h3>5. Frete, tributos e totais</h3>
    {renderFields('totais')}
    <p className="fiscal-v1-muted">Os campos de impostos nesta prévia não fazem cálculos tributários.</p>

    <h3>6. Pagamento e duplicatas</h3>
    <div className="fiscal-v1-table-wrap"><table className="fiscal-v1-table"><thead><tr>
      {['Duplicata nº','Forma de pagamento','Data de vencimento','Valor'].map(t=><th key={t}>{t}</th>)}
      </tr></thead><tbody>{payments.map((p,i)=><tr key={i}>
        {(['numero','forma','vencimento','valor'] as const).map(k=><td key={k}><input
          aria-label={k+' do pagamento '+(i+1)} value={p[k]}
          onChange={e=>setPayments(v=>v.map((r,j)=>j===i?{...r,[k]:e.target.value}:r))}/></td>)}
      </tr>)}</tbody></table></div>
    <button type="button" className="fiscal-v1-add" onClick={()=>setPayments(v=>[...v,{numero:'',forma:'',vencimento:'',valor:''}])}>Adicionar pagamento fictício</button>

    <h3>7. Carta de correção</h3>
    <p className="fiscal-v1-muted">O backup possui arquivo de correções vinculado ao número da nota. Esta seção é apenas demonstrativa.</p>
    {correcoes.map((c,i)=><div className="fiscal-v1-grid" key={i}>
      <label><span>Número da correção</span><input value={c.numero} onChange={e=>setCorrecoes(v=>v.map((r,j)=>j===i?{...r,numero:e.target.value}:r))}/></label>
      <label><span>Descrição da correção</span><input value={c.descricao} onChange={e=>setCorrecoes(v=>v.map((r,j)=>j===i?{...r,descricao:e.target.value}:r))}/></label>
    </div>)}

    <h3>8. Autorização e histórico</h3>
    <div className="fiscal-v1-grid">
      <label><span>Chave de acesso</span><input readOnly value="" placeholder="Somente após geração da NF-e"/></label>
      <label><span>Protocolo de autorização</span><input readOnly value="" placeholder="Somente após autorização SEFAZ"/></label>
    </div>
    <p className="fiscal-v1-muted">NFS-e de serviços é um fluxo separado. Nenhum botão de emitir está habilitado nesta prévia.</p>
  </section>
}
