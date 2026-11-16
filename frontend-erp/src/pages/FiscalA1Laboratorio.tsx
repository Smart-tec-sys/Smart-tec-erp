import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { assinarXmlVendaFiscalLaboratorio, conferirXmlVendaFiscalLaboratorio, getFiscalA1Laboratorio, importarFiscalA1Laboratorio, testarAssinaturaFiscalA1Laboratorio, verificarFiscalA1Laboratorio } from '../services/fiscal'
import type { FiscalA1Laboratorio as Status } from '../services/fiscal'

type Teste = 'cofre' | 'assinatura' | 'venda' | 'venda-assinada'

export function FiscalA1Laboratorio() {
  const [status, setStatus] = useState<Status>()
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState('')
  const [verificando, setVerificando] = useState<Teste | null>(null)
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

  async function verificar(teste: Teste) {
    if (enviando.current) return
    enviando.current = true
    setVerificando(teste)
    setResultadoTeste('')
    setErro('')
    try {
      if (teste === 'venda-assinada') {
        const resultado = await assinarXmlVendaFiscalLaboratorio()
        if (!resultado.assinado || !resultado.assinatura_lab_verificada || !resultado.xsd_validado) throw new Error()
        const valor = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(resultado.total))
        setResultadoTeste(`XML da venda fictícia assinado e validado no XSD ${resultado.xsd_validado}. ${resultado.campos_conferidos} campos conferidos, total de ${valor}. Sem transmissão.`)
      } else if (teste === 'venda') {
        const { campos_conferidos, total } = await conferirXmlVendaFiscalLaboratorio()
        const valor = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(total))
        setResultadoTeste(`XML da venda fictícia conferido. ${campos_conferidos} campos validados, total de ${valor}. Sem assinatura ou transmissão.`)
      } else if (teste === 'assinatura') {
        const resultado = await testarAssinaturaFiscalA1Laboratorio()
        if (!resultado.assinatura_lab_verificada) throw new Error()
        setResultadoTeste('XML fictício assinado e assinatura verificada no servidor.')
      } else {
        const resultado = await verificarFiscalA1Laboratorio()
        if (!resultado.certificado_lab_verificado) throw new Error()
        setResultadoTeste('PFX fictício decifrado e validado no servidor.')
      }
    } catch {
      setErro(teste === 'venda-assinada' ? 'Não foi possível confirmar a assinatura e a validação XSD da venda fictícia.' :
        teste === 'venda' ? 'Não foi possível conferir o XML da venda fictícia.' :
        teste === 'assinatura' ? 'Não foi possível verificar a assinatura do XML fictício.' :
        'Não foi possível verificar o PFX armazenado no cofre.')
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
      <button className="fiscal-v1-add" type="button" onClick={() => verificar('venda-assinada')} disabled={salvando || verificando !== null}>
        {verificando === 'venda-assinada' ? 'Verificando...' : 'Assinar XML da venda fictícia'}
      </button>
    </>}
    <button className="fiscal-v1-add" type="button" onClick={() => verificar('venda')} disabled={salvando || verificando !== null}>
      {verificando === 'venda' ? 'Conferindo...' : 'Conferir XML da venda fictícia'}
    </button>
    {resultadoTeste && <p role="status">{resultadoTeste}</p>}
    {erro && <p role="alert">{erro}</p>}
  </form>
}
