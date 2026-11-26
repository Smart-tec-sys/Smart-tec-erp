import { useEffect, useState } from 'react'
import { useAuthSession } from '../components/AuthGate'
import { setEmpresaId } from '../services/auth'
import { getFiscalCertificadoA1Status, importarFiscalA1Empresa, type FiscalCertificadoA1Status } from '../services/fiscal'
import { FiscalA1Laboratorio, FormularioCertificadoA1 } from './FiscalA1Laboratorio'
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
    if (!podeGerenciar || laboratorioAtivo || empresaId === undefined) return
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
  }, [empresaId, laboratorioAtivo, podeGerenciar])

  return <main className="fiscal-v1">
    <header className="fiscal-v1-head">
      <h1>Certificado digital</h1>
    </header>
    <section className="fiscal-v1-panel">
      <h2>Certificado A1</h2>
      {laboratorioAtivo ? <FiscalA1Laboratorio /> : <>
        {!podeGerenciar && <p>O proprietário ou administrador da empresa pode gerenciar o certificado.</p>}
        {podeGerenciar && !status && !erro && <p role="status">Consultando certificado…</p>}
        {podeGerenciar && erro && <p className="fiscal-v1-error" role="alert">{erro}</p>}
        {podeGerenciar && status && (status.importacao_habilitada === true
          ? <FormularioCertificadoA1
              armazenado={status.certificado_armazenado}
              importarArquivo={(arquivo, senha) => importarFiscalA1Empresa(arquivo, senha, status.empresa_id)}
            />
          : <p>A importação do certificado da empresa ainda não está disponível.</p>)}
        {laboratorio && <button className="fiscal-v1-add" type="button" onClick={() => {
          setEmpresaId(laboratorio.id)
          window.location.reload()
        }}>Abrir empresa de teste</button>}
      </>}
    </section>
  </main>
}
