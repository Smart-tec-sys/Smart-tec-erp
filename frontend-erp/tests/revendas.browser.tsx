import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import { RevendaForm } from '../src/components/RevendaForm'
import type { Revenda } from '../src/services/revendas'
import '../src/pages/cadastrosPage.css'
import '../src/pages/revendasPage.css'

// Harness isolado: nenhuma consulta sai para o backend ou fornecedores externos.
sessionStorage.setItem('smarttec.erp.auth.v1', JSON.stringify({
  accessToken: 'TEST_ONLY', refreshToken: 'TEST_ONLY', expiresAt: Date.now() + 3600000, empresaId: 1,
}))
let failure = false
const fixture: Revenda = {
  id: 12, nome: 'Revenda salva', ativo: true, percentual_padrao: '12.3456',
  razao_social: 'Razão salva', documento: '11222333000181', tipo_pessoa: 'JURIDICA',
  logradouro: 'Rua salva', limite_credito: null,
}
globalThis.fetch = async (input, options) => {
  const target = new URL(input instanceof Request ? input.url : String(input))
  if (target.pathname === '/funcionarios/') return Response.json([{ id: 3, nome: 'Vendedor sintético', situacao: 'Ativo' }])
  if (target.pathname === '/consultas/cnpj') {
    await new Promise(resolve => setTimeout(resolve, 800))
    if (failure) return Response.json({ detail: 'Consulta simulada indisponível' }, { status: 503 })
    return Response.json({ fonte: 'Adapter simulado CNPJ', consultado_em: '2026-11-02T12:00:00Z', dados: {
      razao_social: 'Razão consultada', nome_fantasia: 'Revenda sintética', situacao_cadastral: 'ATIVA',
      telefone_comercial: '11999999999', email: 'sintetico@example.invalid', cep: '01001000',
      logradouro: 'Praça consultada', numero: '10', complemento: 'Sala sintética', bairro: 'Sé', cidade: 'São Paulo', estado: 'SP',
    } })
  }
  if (target.pathname === '/consultas/cep') {
    if (failure) return Response.json({ detail: 'CEP simulado indisponível' }, { status: 503 })
    return Response.json({ fonte: 'Adapter simulado CEP', consultado_em: '2026-11-02T12:00:00Z', dados: {
      cep: '01001000', logradouro: 'Praça consultada', bairro: 'Sé', cidade: 'São Paulo', estado: 'SP',
    } })
  }
  if (target.pathname === '/representantes/parceiros' || target.pathname === '/representantes/parceiros/12') {
    if (options?.method !== 'POST' && options?.method !== 'PATCH') throw new Error('Método inesperado no harness.')
    return Response.json({ id: 12, ...JSON.parse(String(options.body)) })
  }
  throw new Error(`Requisição não permitida no harness: ${target.pathname}`)
}
function Harness() {
  const [mode, setMode] = useState<'novo' | 'editar'>('novo')
  const [generation, setGeneration] = useState(0)
  const [show, setShow] = useState(false)
  const [saved, setSaved] = useState<Revenda | null>(null)
  return <div data-testid="fundo" style={{ minHeight: 2400, transform: 'translateZ(0)' }}>
    <div style={{ position: 'sticky', top: 0, padding: 12, background: 'white', zIndex: 1 }}><button onClick={() => { setMode('novo'); setShow(true); setGeneration(value => value + 1) }}>Novo teste</button>
      <button onClick={() => { setMode('editar'); setShow(true); setGeneration(value => value + 1) }}>Editar teste</button>
      <label><input type="checkbox" onChange={event => { failure = event.target.checked }} /> Simular falha externa</label>
      <pre data-testid="resultado">{saved ? JSON.stringify(saved) : 'Nenhum cadastro salvo'}</pre></div>
    {show && <RevendaForm key={generation} revenda={mode === 'editar' ? fixture : undefined}
      onClose={() => setShow(false)} onSaved={record => { setSaved(record); setShow(false) }} />}
  </div>
}
const root = document.getElementById('root')
if (!root) throw new Error('Container de teste não encontrado.')
createRoot(root).render(<Harness />)
