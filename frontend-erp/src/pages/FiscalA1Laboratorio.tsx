import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { getFiscalA1Laboratorio, importarFiscalA1Laboratorio, verificarFiscalA1Laboratorio } from '../services/fiscal'
import type { FiscalA1Laboratorio as Status } from '../services/fiscal'

export function FiscalA1Laboratorio() {
  const [status, setStatus] = useState<Status>()
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState('')
  const [verificando, setVerificando] = useState(false)
  const [verificado, setVerificado] = useState(false)
  const enviando = useRef(false)

  useEffect(() => {
    let ativo = true
    getFiscalA1Laboratorio()
      .then(resultado => { if (ativo) setStatus(resultado) })
      .catch(() => { if (ativo) setErro('Não foi possível consultar a importação de laboratório.') })
    return () => { ativo = false }
  }, [])

  async function importar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    if (enviando.current) return
    const formulario = evento.currentTarget
    const dados = new FormData(formulario)
    const arquivo = dados.get('arquivo')
    const senha = dados.get('senha')
    if (!(arquivo instanceof File) || typeof senha !== 'string') return
    formulario.reset()
    enviando.current = true
    setSalvando(true)
    setErro('')
    setVerificado(false)
    try {
      const resultado = await importarFiscalA1Laboratorio(arquivo, senha)
      setStatus({ importacao_lab_habilitada: true, certificado_lab_armazenado: resultado.certificado_armazenado })
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : 'Falha ao importar o PFX de laboratório.')
    } finally {
      enviando.current = false
      setSalvando(false)
    }
  }

  async function verificar() {
    if (enviando.current) return
    enviando.current = true
    setVerificando(true)
    setVerificado(false)
    setErro('')
    try {
      const resultado = await verificarFiscalA1Laboratorio()
      setVerificado(resultado.certificado_lab_verificado)
    } catch {
      setErro('Não foi possível verificar o PFX armazenado no cofre.')
    } finally {
      enviando.current = false
      setVerificando(false)
    }
  }

  if (erro && !status) return <p role="alert">{erro}</p>
  if (!status?.importacao_lab_habilitada) return null
  return <form onSubmit={importar} className="fiscal-v1-grid">
    <p role="status">{status.certificado_lab_armazenado ? 'PFX fictício armazenado no cofre.' : 'Somente PFX fictício de laboratório.'}</p>
    <label>Arquivo PFX fictício<input name="arquivo" type="file" accept=".pfx,.p12" required disabled={salvando} /></label>
    <label>Senha do PFX fictício<input name="senha" type="password" autoComplete="off" required maxLength={256} disabled={salvando} /></label>
    <button className="fiscal-v1-save" disabled={salvando || verificando}>{salvando ? 'Importando...' : 'Importar PFX de laboratório'}</button>
    {status.certificado_lab_armazenado &&
      <button className="fiscal-v1-add" type="button" onClick={verificar} disabled={salvando || verificando}>
        {verificando ? 'Verificando...' : 'Verificar PFX no cofre'}
      </button>}
    {verificado && <p role="status">PFX fictício decifrado e validado no servidor.</p>}
    {erro && <p role="alert">{erro}</p>}
  </form>
}
