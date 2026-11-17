import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { getFiscalA1Laboratorio, importarFiscalA1Laboratorio, type FiscalA1Laboratorio as Status } from '../services/fiscal'

export function FiscalA1Laboratorio() {
  const [status, setStatus] = useState<Status>()
  const [erro, setErro] = useState('')

  useEffect(() => {
    let ativo = true
    getFiscalA1Laboratorio()
      .then(resultado => { if (ativo) setStatus(resultado) })
      .catch(() => { if (ativo) setErro('Não foi possível consultar o certificado.') })
    return () => { ativo = false }
  }, [])

  if (!status) return erro ? <p className="fiscal-v1-error" role="alert">{erro}</p> : <p role="status">Consultando certificado…</p>
  if (!status.importacao_lab_habilitada) return <p>A importação de teste está indisponível.</p>

  return <>
    <p>Homologação. Use apenas um certificado de teste.</p>
    <FormularioCertificadoA1
      armazenado={status.certificado_lab_armazenado}
      importarArquivo={importarFiscalA1Laboratorio}
      teste
    />
  </>
}

type FormularioCertificadoA1Props = {
  armazenado: boolean
  importarArquivo: (arquivo: File, senha: string) => Promise<{ certificado_armazenado: boolean }>
  teste?: boolean
}

export function FormularioCertificadoA1({ armazenado, importarArquivo, teste = false }: FormularioCertificadoA1Props) {
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState('')
  const [importado, setImportado] = useState(false)
  const enviando = useRef(false)
  const tipo = teste ? 'Certificado de teste' : 'Certificado A1'

  async function importar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    if (enviando.current) return
    const formulario = evento.currentTarget
    const dados = new FormData(formulario)
    const arquivo = dados.get('arquivo')
    const senha = dados.get('senha')
    if (!(arquivo instanceof File) || !arquivo.size || typeof senha !== 'string' || !senha) return
    if (arquivo.size > 128 * 1024) {
      setErro('Selecione um arquivo de certificado de até 128 KB.')
      return
    }

    formulario.reset()
    enviando.current = true
    setSalvando(true)
    setErro('')
    try {
      const resultado = await importarArquivo(arquivo, senha)
      if (resultado.certificado_armazenado !== true) {
        setErro('Não foi possível confirmar a importação do certificado.')
        return
      }
      setImportado(true)
    } catch {
      setErro(teste
        ? 'Não foi possível importar o certificado. Confira o arquivo de teste e a senha.'
        : 'Não foi possível importar o certificado. Confira o arquivo, a senha e o CNPJ da empresa.')
    } finally {
      enviando.current = false
      setSalvando(false)
    }
  }

  return <>
    <p role="status">{importado ? 'Certificado importado.' : armazenado ? `${tipo} cadastrado.` : 'Nenhum certificado cadastrado.'}</p>
    <form className="fiscal-v1-grid" onSubmit={importar} aria-busy={salvando}>
      <label>Arquivo<input name="arquivo" type="file" accept=".pfx,.p12" required disabled={salvando} /></label>
      <label>Senha<input name="senha" type="password" autoComplete="off" required maxLength={256} disabled={salvando} /></label>
      <button className="fiscal-v1-save" type="submit" disabled={salvando}>{salvando ? 'Importando…' : 'Importar certificado'}</button>
    </form>
    {erro && <p className="fiscal-v1-error" role="alert">{erro}</p>}
  </>
}
