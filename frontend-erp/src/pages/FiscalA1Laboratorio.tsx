import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { getFiscalA1Laboratorio, importarFiscalA1Laboratorio, testarAssinaturaFiscalA1Laboratorio, verificarFiscalA1Laboratorio } from '../services/fiscal'
import type { FiscalA1Laboratorio as Status } from '../services/fiscal'

export function FiscalA1Laboratorio() {
  const [status, setStatus] = useState<Status>()
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState('')
  const [verificando, setVerificando] = useState<'cofre' | 'assinatura' | null>(null)
  const [resultadoTeste, setResultadoTeste] = useState('')
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
    setResultadoTeste('')
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

  async function verificar(teste: 'cofre' | 'assinatura') {
    if (enviando.current) return
    enviando.current = true
    setVerificando(teste)
    setResultadoTeste('')
    setErro('')
    try {
      if (teste === 'assinatura') {
        const resultado = await testarAssinaturaFiscalA1Laboratorio()
        if (!resultado.assinatura_lab_verificada) throw new Error()
        setResultadoTeste('XML fictício assinado e assinatura verificada no servidor.')
      } else {
        const resultado = await verificarFiscalA1Laboratorio()
        if (!resultado.certificado_lab_verificado) throw new Error()
        setResultadoTeste('PFX fictício decifrado e validado no servidor.')
      }
    } catch {
      setErro(teste === 'assinatura' ? 'Não foi possível verificar a assinatura do XML fictício.' : 'Não foi possível verificar o PFX armazenado no cofre.')
    } finally {
      enviando.current = false
      setVerificando(null)
    }
  }

  if (erro && !status) return <p role="alert">{erro}</p>
  if (!status?.importacao_lab_habilitada) return null
  return <form onSubmit={importar} className="fiscal-v1-grid">
    <p role="status">{status.certificado_lab_armazenado ? 'PFX fictício armazenado no cofre.' : 'Somente PFX fictício de laboratório.'}</p>
    <label>Arquivo PFX fictício<input name="arquivo" type="file" accept=".pfx,.p12" required disabled={salvando} /></label>
    <label>Senha do PFX fictício<input name="senha" type="password" autoComplete="off" required maxLength={256} disabled={salvando} /></label>
    <button className="fiscal-v1-save" disabled={salvando || verificando !== null}>{salvando ? 'Importando...' : 'Importar PFX de laboratório'}</button>
    {status.certificado_lab_armazenado && <>
      <button className="fiscal-v1-add" type="button" onClick={() => verificar('cofre')} disabled={salvando || verificando !== null}>
        {verificando === 'cofre' ? 'Verificando...' : 'Verificar PFX no cofre'}
      </button>
      <button className="fiscal-v1-add" type="button" onClick={() => verificar('assinatura')} disabled={salvando || verificando !== null}>
        {verificando === 'assinatura' ? 'Verificando...' : 'Testar assinatura de XML fictício'}
      </button>
    </>}
    {resultadoTeste && <p role="status">{resultadoTeste}</p>}
    {erro && <p role="alert">{erro}</p>}
  </form>
}
