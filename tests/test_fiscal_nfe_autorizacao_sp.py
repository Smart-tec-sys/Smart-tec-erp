import ssl
from unittest.mock import Mock, patch

import pytest

from app.services import fiscal_nfe_autorizacao_sp as sefaz
from app.services.fiscal_nfe_xml_homologacao import NS_DS, NS_NFE


CHAVE = "35" + "1" * 42


def retorno(status="100", chave=CHAVE, protocolo="135261000000001"):
    numero = f"<nProt>{protocolo}</nProt>" if protocolo else ""
    return f"""
    <Envelope xmlns="http://www.w3.org/2003/05/soap-envelope"><Body>
      <retEnviNFe xmlns="{NS_NFE}" versao="4.00">
        <tpAmb>2</tpAmb><cStat>104</cStat><xMotivo>Lote processado</xMotivo>
        <protNFe versao="4.00"><infProt>
          <tpAmb>2</tpAmb><chNFe>{chave}</chNFe>{numero}
          <cStat>{status}</cStat><xMotivo>Resultado da nota</xMotivo>
        </infProt></protNFe>
      </retEnviNFe>
    </Body></Envelope>
    """.encode()


def nota(ambiente="2"):
    # Fixture de transporte. O assinador e a validação XSD são etapas anteriores.
    return f"""<NFe xmlns="{NS_NFE}">
    <infNFe Id="NFe{CHAVE}" versao="4.00"><ide><cUF>35</cUF><mod>55</mod><tpAmb>{ambiente}</tpAmb></ide></infNFe>
    <Signature xmlns="{NS_DS}"><SignedInfo><Reference URI="#NFe{CHAVE}"/></SignedInfo>
    <SignatureValue>AA==</SignatureValue></Signature></NFe>""".encode()


def test_autoriza_com_o_protocolo_correspondente_ao_xml_enviado():
    contexto = ssl.create_default_context()
    resposta = Mock(status=200)
    resposta.read.return_value = retorno()
    with patch.object(sefaz, "HTTPSConnection") as conexao:
        conexao.return_value.getresponse.return_value = resposta
        resultado = sefaz.autorizar_homologacao_sp(nota(), "1", contexto)

    conexao.assert_called_once_with("homologacao.nfe.fazenda.sp.gov.br", timeout=45, context=contexto)
    request = conexao.return_value.request.call_args
    assert request.args == ("POST", "/ws/nfeautorizacao4.asmx")
    assert b"<indSinc>1</indSinc>" in request.kwargs["body"]
    assert nota() in request.kwargs["body"]
    assert resultado.autorizada
    assert resultado.protocolo == "135261000000001"


def test_lote_processado_com_rejeicao_297_nao_autoriza_a_nota():
    resultado = sefaz.interpretar_retorno(retorno(status="297", protocolo=""), CHAVE)
    assert resultado.status_lote == "104"
    assert resultado.status_nfe == "297"
    assert not resultado.autorizada


def test_protocolo_de_outra_nota_e_inconclusivo():
    with pytest.raises(sefaz.RetornoAutorizacaoInconclusivo, match="não corresponde"):
        sefaz.interpretar_retorno(retorno(chave="35" + "2" * 42), CHAVE)


def test_xml_de_producao_e_bloqueado_antes_de_abrir_conexao():
    with patch.object(sefaz, "HTTPSConnection") as conexao:
        with pytest.raises(ValueError, match="homologação"):
            sefaz.autorizar_homologacao_sp(nota("1"), "1", ssl.create_default_context())
    conexao.assert_not_called()


def test_falha_de_rede_nao_retransmite_a_nota():
    with patch.object(sefaz, "HTTPSConnection") as conexao:
        conexao.return_value.getresponse.side_effect = TimeoutError()
        with pytest.raises(sefaz.RetornoAutorizacaoInconclusivo):
            sefaz.autorizar_homologacao_sp(nota(), "1", ssl.create_default_context())
    conexao.return_value.request.assert_called_once()
