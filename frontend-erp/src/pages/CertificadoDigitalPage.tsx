import { useEffect, useState } from 'react'
import { useAuthSession } from '../components/AuthGate'
import { setEmpresaId } from '../services/auth'
import { getFiscalCertificadoA1Status, type FiscalCertificadoA1Status } from '../services/fiscal'
import { FiscalA1Laboratorio } from './FiscalA1Laboratorio'
import './FiscalPage.css'

const EMPRESA_LAB_A1 = 999999999

export function CertificadoDigitalPage() {
  const session = useAuthSession()
  const empresaId = session?.empresa.id
  const papel = session?.empresa.papel
  const podeGerenciar = papel === 'OWNER' || papel === 'ADMIN'
  const laboratorio = session?.empresas.find(empresa =>
    empresa.id === EMPRESA_LAB_A1 && empresa.slug === 'laboratorio-fiscal-a1' &&
    (empresa.papel === 'OWNER' || empresa.papel === 'ADMIN')
  )
  const laboratorioAtivo = podeGerenciar && laboratorio !== undefined && laboratorio.id === empresaId
  const [status, setStatus] = useState<FiscalCertificadoA1Status>()
  const [erro, setErro] = useState('')

  useEffect(() => {
    if (!podeGerenciar || empresaId === undefined) return
    let ativo = true
    getFiscalCertificadoA1Status()
      .then(resultado => {
        if (ativo && resultado.empresa_id === empresaId) setStatus(resultado)
        else if (ativo) setErro('A empresa ativa mudou. Reabra esta página.')
      })
      .catch(() => {
        if (ativo) setErro('Não foi possível consultar o certificado da empresa.')
      })
    return () => { ativo = false }
  }, [empresaId, podeGerenciar])

  return <main className="fiscal-v1">
    <nav className="fiscal-v1-tabs" aria-label="Configurações">
      <a href="#/configuracoes">Voltar às configurações</a>
    </nav>
    <header className="fiscal-v1-head">
      <h1>Certificado digital</h1>
    </header>
    <section className="fiscal-v1-panel">
      <h2>Certificado A1</h2>
      {!podeGerenciar && <p>O proprietário ou administrador da empresa pode gerenciar o certificado.</p>}
      {podeGerenciar && !status && !erro && <p role="status">Consultando certificado…</p>}
      {podeGerenciar && erro && <p className="fiscal-v1-error" role="alert">{erro}</p>}
      {podeGerenciar && status && <>
        <p role="status"><strong>{status.situacao === 'NAO_CONFIGURADO' ? 'Não configurado' : status.situacao}</strong></p>
        <p>{status.aviso}</p>
      </>}
    </section>
    {laboratorioAtivo && <details className="fiscal-v1-setup">
      <summary>Laboratório</summary>
      <p>Use apenas certificados fictícios.</p>
      <FiscalA1Laboratorio />
    </details>}
    {laboratorio && !laboratorioAtivo && <details className="fiscal-v1-setup">
      <summary>Laboratório</summary>
      <button className="fiscal-v1-add" type="button" onClick={() => {
        setEmpresaId(laboratorio.id)
        window.location.reload()
      }}>Abrir {laboratorio.nome}</button>
    </details>}
  </main>
}
