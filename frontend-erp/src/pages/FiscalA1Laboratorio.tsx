import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { getFiscalA1Laboratorio, importarFiscalA1Laboratorio, type FiscalA1Laboratorio as Status } from '../services/fiscal'

export function FiscalA1Laboratorio() {
  const [status, setStatus] = useState<Status>()
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState('')
  const [mensagem, setMensagem] = useState('')
  const enviando = useRef(false)

  useEffect(() => {
    let ativo = true
    getFiscalA1Laboratorio()
      .then(resultado => { if (ativo) setStatus(resultado) })
      .catch(() => { if (ativo) setErro('Não foi possível consultar o certificado.') })
    return () => { ativo = false }
  }, [])

  async function importar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    if (enviando.current || !status?.importacao_lab_habilitada) return
    const formulario = evento.currentTarget
    const dados = new FormData(formulario)
    const arquivo = dados.get('arquivo')
    const senha = dados.get('senha')
    if (!(arquivo instanceof File) || !arquivo.size || typeof senha !== 'string' || !senha) return

    formulario.reset()
    enviando.current = true
    setSalvando(true)
    setErro('')
    setMensagem('')
    try {
      const resultado = await importarFiscalA1Laboratorio(arquivo, senha)
      if (resultado.certificado_armazenado !== true) {
        setErro('Não foi possível confirmar a importação do certificado.')
        return
      }
      setStatus({ importacao_lab_habilitada: true, certificado_lab_armazenado: true })
      setMensagem('Certificado importado.')
    } catch {
      setErro('Não foi possível importar o certificado. Confira o arquivo de teste e a senha.')
    } finally {
      enviando.current = false
      setSalvando(false)
    }
  }

  if (!status) return erro ? <p className="fiscal-v1-error" role="alert">{erro}</p> : <p role="status">Consultando certificado…</p>
  if (!status.importacao_lab_habilitada) return <p>A importação de teste está indisponível.</p>

  return <>
    <p>Homologação. Use apenas um certificado de teste.</p>
    <p role="status">{mensagem || (status.certificado_lab_armazenado ? 'Certificado de teste cadastrado.' : 'Nenhum certificado de teste cadastrado.')}</p>
    <form className="fiscal-v1-grid" onSubmit={importar}>
      <label>Arquivo<input name="arquivo" type="file" accept=".pfx,.p12" required disabled={salvando} /></label>
      <label>Senha<input name="senha" type="password" autoComplete="off" required maxLength={256} disabled={salvando} /></label>
      <button className="fiscal-v1-save" type="submit" disabled={salvando}>{salvando ? 'Importando…' : 'Importar certificado'}</button>
    </form>
    {erro && <p className="fiscal-v1-error" role="alert">{erro}</p>}
  </>
}
