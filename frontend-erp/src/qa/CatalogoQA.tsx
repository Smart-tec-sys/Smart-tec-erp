import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import { BudgetProductRow } from '../components/BudgetProductRow'
import type { ApiProduct, BudgetProduct } from '../types/budget'
import '../styles.css'
import '../theme/tokens.css'

const sample: ApiProduct[] = [
  ...['BEGE','BRANCO','CINZA','CREME','MARROM'].map((color, i) => ({
    id: 101+i, nome: 'BK NAPOLES - '+color+' - 2,60M',
    grupo_tecnico: 'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL',
    cor: color, largura: 2.6, unidade_venda: 'M²', custo_final: 10+i*5,
    status_comercial: 'ATIVO', empresa_id: 1,
  })),
  ...['WHITE','ALPINO','BEGE'].map((color, i) => ({
    id: 201+i, nome: 'TECIDO BK BRISK 2,00M ('+color+')',
    grupo_tecnico: 'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL',
    cor: color, largura: 2, unidade_venda: 'M²', custo_final: 15+i*7,
    status_comercial: 'ATIVO', empresa_id: 1,
  })),
  ...['AMENDOA','BLACK','BRANCO'].map((color,i) => ({
    id: 301+i, nome: 'ROMANA BK BRISK ('+color+')',
    grupo_tecnico: 'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL',
    familia_tecnica: 'ROMANA_BK_BRISK', modelo_tecnico: 'ROMANA',
    cor: color, unidade_venda: 'M²', custo_final: 30+i*8,
    status_comercial: 'ATIVO', empresa_id: 1,
  })),
  ...['AMENDOA','BEGE','CINZA','FENDI','GELO'].map((color, i) => ({
    id: 501+i, nome: 'TEC PICASSO BK - '+color+' - 2,50M',
    grupo_tecnico: 'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL',
    cor: null, largura: 2.5, unidade_venda: 'M²', custo_final: 12+i*4,
    status_comercial: 'ATIVO', empresa_id: 1,
  })),
  ...['WHITE','BLACK','IVORY'].map((color,i) => ({
    id: 601+i, nome: 'DOUBLE VISION BK. MEXICO ('+color+')',
    grupo_tecnico: 'TECIDOS_PERSIANAS_DOUBLE_VISION',
    modelo_tecnico: 'DOUBLE_VISION', cor: color, unidade_venda: 'M²',
    custo_final: 20+i*3, status_comercial: 'ATIVO', empresa_id: 1,
  })),
  { id: 401, nome: 'ROLÔ BK NAPOLES', grupo_tecnico: 'PERSIANA_ROLO',
    familia_tecnica: 'ROLO_BK_NAPOLES', modelo_tecnico: 'ROLO',
    status_comercial: 'ATIVO', unidade_venda: 'M²', custo_final: 80 },
]

const initial: BudgetProduct = {
  id: 1, productId: null, product: '', code: '', family: '', groupTechnical: '',
  modelTechnical: '', unit: '', color: '', details: '', environment: '',
  quantity: 1, width: '', height: '', price: 0, discount: 0,
}

function QA() {
  const [product, setProduct] = useState<BudgetProduct>(initial)
  return <main style={{maxWidth: 1100, margin:'24px auto', padding:20}}>
    <h1>Homologação do catálogo — dados sintéticos</h1>
    <p>Sem API e sem escrita no banco. Use a busca de produto e a seleção de cor.</p>
    <BudgetProductRow
      product={product} catalog={sample} commercialType="Varejo"
      onChange={setProduct} onRemove={() => setProduct(initial)}
      onRomana={() => {}} onRomanaTeto={() => {}} onRolo={() => {}}
      onDoubleVision={() => {}} onCurtain={() => {}} />
    <pre data-testid="selected-json">{JSON.stringify({
      id: product.productId, produto: product.product, cor: product.color,
      preco: product.price, roloKind: product.roloKind, romanaKind: product.romanaKind,
      familia: product.family,
    }, null, 2)}</pre>
  </main>
}

createRoot(document.getElementById('root')!).render(<QA />)
