import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import {
  assinarXmlVendaFiscalLaboratorio,
  conferirXmlVendaFiscalLaboratorio,
  getFiscalA1Laboratorio,
  importarFiscalA1Laboratorio,
  testarAssinaturaFiscalA1Laboratorio,
  verificarFiscalA1Laboratorio,
  type FiscalA1Laboratorio as Status,
} from '../services/fiscal'

const moeda = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

const testesHomologacao = [
  {
    titulo: 'Verificar PFX no cofre',
    executar: async () => {
      const resultado = await verificarFiscalA1Laboratorio()
      if (!resultado.certificado_lab_verificado) throw new Error('Certificado não verificado')
      return 'PFX fictício decifrado e validado no servidor.'
    },
  },
  {
    titulo: 'Testar assinatura de XML fictício',
    executar: async () => {
      const resultado = await testarAssinaturaFiscalA1Laboratorio()
      if (!resultado.assinatura_lab_verificada) throw new Error('Assinatura não verificada')
      return 'XML fictício assinado e assinatura verificada no servidor.'
    },
  },
  {
    titulo: 'Conferir XML da venda fictícia',
    executar: async () => {
      const resultado = await conferirXmlVendaFiscalLaboratorio()
      if (resultado.assinado !== false || resultado.transmitido !== false) throw new Error('Resultado inesperado')
      return `XML da venda fictícia conferido. ${resultado.campos_conferidos} campos validados, total de ${moeda.format(Number(resultado.total))}.`
    },
  },
  {
    titulo: 'Assinar XML da venda fictícia',
    executar: async () => {
      const resultado = await assinarXmlVendaFiscalLaboratorio()
      if (!resultado.assinado || !resultado.assinatura_lab_verificada || !resultado.xsd_validado || resultado.transmitido !== false) {
        throw new Error('XML assinado não validado')
      }
      return `XML da venda fictícia assinado e validado no XSD ${resultado.xsd_validado}. ${resultado.campos_conferidos} campos conferidos, total de ${moeda.format(Number(resultado.total))}. Sem transmissão.`
    },
  },
]

export function FiscalA1Laboratorio() {
  const [status, setStatus] = useState<Status>()
  const [erro, setErro] = useState('')

  const [operacao, setOperacao] = useState('')
  const [resultadoTeste, setResultadoTeste] = useState('')
  const [erroTeste, setErroTeste] = useState('')
  const ocupado = useRef(false)

  useEffect(() => {
    let ativo = true
    getFiscalA1Laboratorio()
      .then(resultado => { if (ativo) setStatus(resultado) })
      .catch(() => { if (ativo) setErro('Não foi possível consultar o certificado.') })
    return () => { ativo = false }
  }, [])

  async function importarCertificado(arquivo: File, senha: string) {
    if (ocupado.current) throw new Error('Operação em andamento')
    ocupado.current = true
    setOperacao('importar')
    setResultadoTeste('')
    setErroTeste('')
    try {
      const resultado = await importarFiscalA1Laboratorio(arquivo, senha)
      if (resultado.certificado_armazenado) {
        setStatus(atual => atual && { ...atual, certificado_lab_armazenado: true })
      }
      return resultado
    } finally {
      ocupado.current = false
      setOperacao('')
    }
  }

  async function executarTeste(teste: (typeof testesHomologacao)[number]) {
    if (ocupado.current) return
    ocupado.current = true
    setOperacao(teste.titulo)
    setResultadoTeste('')
    setErroTeste('')
    try {
      setResultadoTeste(await teste.executar())
    } catch {
      setErroTeste(`Falha no teste “${teste.titulo}”.`)
    } finally {
      ocupado.current = false
      setOperacao('')
    }
  }

  if (!status) return erro ? <p className="fiscal-v1-error" role="alert">{erro}</p> : <p role="status">Consultando certificado…</p>
  if (!status.importacao_lab_habilitada) return <p>A importação de teste está indisponível.</p>

  return <>
    <p>Homologação. Use apenas um certificado de teste.</p>
    <FormularioCertificadoA1
      armazenado={status.certificado_lab_armazenado}
      importarArquivo={importarCertificado}
      bloqueado={operacao !== '' && operacao !== 'importar'}
      teste
    />
    <details className="fiscal-v1-setup">
      <summary>Testes de homologação</summary>
      {status.certificado_lab_armazenado
        ? <div className="fiscal-v1-grid" aria-busy={operacao !== '' && operacao !== 'importar'}>
            {testesHomologacao.map(teste => <button
              key={teste.titulo}
              className="fiscal-v1-add"
              type="button"
              disabled={operacao !== ''}
              onClick={() => void executarTeste(teste)}
            >{operacao === teste.titulo ? 'Executando…' : teste.titulo}</button>)}
          </div>
        : <p>Importe um certificado de teste para usar estes botões.</p>}
      {resultadoTeste && <p className="fiscal-v1-success" role="status">{resultadoTeste}</p>}
      {erroTeste && <p className="fiscal-v1-error" role="alert">{erroTeste}</p>}
    </details>
  </>
}

type FormularioCertificadoA1Props = {
  armazenado: boolean
  importarArquivo: (arquivo: File, senha: string) => Promise<{ certificado_armazenado: boolean }>
  teste?: boolean
  bloqueado?: boolean
}

export function FormularioCertificadoA1({ armazenado, importarArquivo, teste = false, bloqueado = false }: FormularioCertificadoA1Props) {
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState('')
  const [importado, setImportado] = useState(false)
  const enviando = useRef(false)
  const tipo = teste ? 'Certificado de teste' : 'Certificado A1'

  async function importar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    if (enviando.current || bloqueado) return
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
      <label>Arquivo<input name="arquivo" type="file" accept=".pfx,.p12" required disabled={salvando || bloqueado} /></label>
      <label>Senha<input name="senha" type="password" autoComplete="off" required maxLength={256} disabled={salvando || bloqueado} /></label>
      <button className="fiscal-v1-save" type="submit" disabled={salvando || bloqueado}>{salvando ? 'Importando…' : 'Importar certificado'}</button>
    </form>
    {erro && <p className="fiscal-v1-error" role="alert">{erro}</p>}
  </>
}
