import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import { ProducaoPanel } from '../src/components/ProducaoPanel'
import { statusProducao, type OrdemProducao, type PecaProducao } from '../src/services/producao'

// Harness isolado: nenhuma requisicao e enviada ao ERP ou a provedores externos.
sessionStorage.setItem('smarttec.erp.auth.v1', JSON.stringify({
  accessToken: 'TEST_ONLY', refreshToken: 'TEST_ONLY', expiresAt: Date.now() + 3600000, empresaId: 1,
}))
let ordem: OrdemProducao | null = null
let falha = false
let chamadas = 0
const peca: PecaProducao = {
  id: 1, codigo: 'OP-000001-I1-P0001', pedido_item_id: 1, sequencia: 1,
  modelo: 'CORTINA', tecido: 'Tecido de teste', cor: 'Branco', largura: 2, altura: 2,
  acionamento: 'Manual', ambiente: '', observacoes: '', status: 'AGUARDANDO', historico: [],
}
globalThis.fetch = async (input, options) => {
  const url = new URL(input instanceof Request ? input.url : String(input))
  const payload = options?.body ? JSON.parse(String(options.body)) : {}
  chamadas += 1
  await new Promise(resolve => setTimeout(resolve, 100))
  if (!url.pathname.startsWith('/producao/')) throw new Error('Requisição fora do harness.')
  if (falha) return Response.json({ detail: 'Produção simulada indisponível' }, { status: 503 })
  if (url.pathname === '/producao/' && !options?.method) return Response.json(ordem ? [ordem] : [])
  if (url.pathname === '/producao/vendas/1' && options?.method === 'POST') {
    if (ordem) return Response.json({ detail: 'OP já existente' }, { status: 409 })
    if (payload.confirmar_fabricacao !== true) return Response.json({ detail: 'Sem confirmação' }, { status: 409 })
    ordem = {
      id: 1, pedido_id: 1, confirmado_por: '7', confirmado_em: new Date().toISOString(),
      liberado_por: null, liberado_em: null, status: 'AGUARDANDO',
      pendencias: ['Peça 1: informe ambiente.'], pecas: [structuredClone(peca)], calculos_por_peca: {},
    }
    return Response.json(ordem, { status: 201 })
  }
  if (!ordem) return Response.json({ detail: 'OP inexistente' }, { status: 404 })
  if (url.pathname.endsWith('/ficha') || url.pathname.endsWith('/etiqueta')) {
    const nome = url.pathname.endsWith('/ficha') ? 'Ficha de fabricação' : 'Etiqueta existente'
    return new Response(`<!doctype html><html lang="pt-BR"><meta charset="utf-8"><button onclick="window.print()">Imprimir</button><h1>${nome}</h1><p>OP-000001-I1-P0001 · Sala</p></html>`,
      { headers: { 'Content-Type': 'text/html' } })
  }
  if (options?.method === 'PATCH') {
    if (ordem.liberado_em) return Response.json({ detail: 'Ficha imutável' }, { status: 409 })
    Object.assign(ordem.pecas[0], { ambiente: payload.ambiente, observacoes: payload.observacoes })
    ordem.pendencias = ordem.pecas[0].ambiente ? [] : ['Peça 1: informe ambiente.']
  } else if (url.pathname.endsWith('/liberar')) {
    if (ordem.pendencias.length) return Response.json({ detail: 'Liberação bloqueada' }, { status: 409 })
    ordem.liberado_em = new Date().toISOString()
    ordem.liberado_por = '7'
  } else if (url.pathname.endsWith('/status')) {
    const atual = ordem.pecas[0].status
    if (!ordem.liberado_em || payload.status_atual !== atual ||
        payload.status !== statusProducao[statusProducao.indexOf(atual) + 1])
      return Response.json({ detail: 'Transição bloqueada' }, { status: 409 })
    ordem.pecas[0].status = payload.status
    ordem.pecas[0].historico.push({ de: atual, para: payload.status, usuario: '7', em: new Date().toISOString() })
    ordem.status = payload.status
  } else throw new Error(`Rota não prevista no harness: ${url.pathname}`)
  return Response.json(ordem)
}

function Harness() {
  const [geracao, setGeracao] = useState(0)
  const [status, setStatus] = useState('ABERTO')
  return <main style={{ maxWidth: 1050, margin: 'auto', fontFamily: 'Arial' }}>
    <h1>Produção V1 — somente dados simulados</h1>
    <button onClick={() => { ordem = null; falha = false; setStatus('ABERTO'); setGeracao(g => g + 1) }}>Reiniciar cenário</button>
    <label><input type="checkbox" onChange={event => { falha = event.target.checked }} /> Simular indisponibilidade</label>
    <button onClick={() => setStatus('CANCELADO')}>Cancelar venda simulada</button>
    <button onClick={() => setStatus('CONCLUIDO')}>Concluir venda simulada</button>
    <button onClick={() => {
      const resultado = document.getElementById('resultado')
      if (resultado) resultado.textContent = JSON.stringify({ chamadas, ordem })
    }}>Inspecionar dados simulados</button>
    <pre id="resultado" />
    <ProducaoPanel key={geracao} pedidoId={1} statusVenda={status} />
  </main>
}

const root = document.getElementById('root')
if (!root) throw new Error('Container do teste não encontrado.')
createRoot(root).render(<Harness />)
