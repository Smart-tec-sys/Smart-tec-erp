"""Validação estrutural de referência (mirror público pinado), NÃO oficial.

O exemplo XML da Smart-tec não é assinado. Por definição, o schema completo
nfe_v4.00.xsd deve recusá-lo pela falta de ds:Signature. Estes testes verificam
que o restante do XML está alinhado com os XSDs da referência e que falhas
adicionais são efetivamente detectadas; não testam criptografia ou SEFAZ.

IMPORTANTE: referência espelhada não prova conformidade com pacote OFICIAL
PL_010g v1.03; o pacote oficial precisa ser obtido e confrontado em outra etapa.
"""
import os
import unittest
from pathlib import Path
from lxml import etree

from tests.test_fiscal_nfe_assinatura_laboratorio import criar_certificado_laboratorio
from app.services.fiscal_nfe_assinatura_laboratorio import (
    assinar_xml_ficticio_pfx_laboratorio, verificar_xml_assinado_laboratorio,
)

from app.services.fiscal_nfe_xml_homologacao import (
    gerar_xml_ficticio_nao_assinado,
    NS_DS,
    NS_NFE,
)


SCHEMA_DIR = os.getenv("SMARTTEC_NFE_XSD_DIR", "")


@unittest.skipUnless(SCHEMA_DIR, "XSD de referência não disponível (CI carrega arquivo pinado).")
class ReferenciaXsdTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        files = list(Path(SCHEMA_DIR).rglob("nfe_v4.00.xsd"))
        if len(files) != 1:
            raise AssertionError(
                "A cópia de referência do schema precisa conter exatamente um nfe_v4.00.xsd."
            )
        cls.root_schema = files[0]
        parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
        cls.schema = etree.XMLSchema(etree.parse(str(cls.root_schema), parser=parser))

    def erros(self, xml: bytes):
        parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
        root = etree.fromstring(xml, parser=parser)
        ok = self.schema.validate(root)
        return ok, [str(error.message) for error in self.schema.error_log]

    def test_prototipo_e_rejeitado_por_nao_possuir_assinatura(self):
        ok, errors = self.erros(gerar_xml_ficticio_nao_assinado())
        self.assertFalse(ok, "XML não assinado não pode passar no XSD da NF-e completo.")
        self.assertTrue(any("Signature" in e for e in errors), errors)

    def test_todas_as_outras_taggens_seguem_schema_de_referencia(self):
        _, errors = self.erros(gerar_xml_ficticio_nao_assinado())
        # Exigir que o único problema de estrutura na referência seja a
        # ausência de assinatura; quaisquer outras falhas são regressão.
        self.assertEqual(
            len(errors), 1,
            "Erros adicionais no XSD de referência além da assinatura: " + "\n".join(errors)
        )
        self.assertIn("Signature", errors[0], errors)

    def test_exemplo_assinado_passou_no_xsd_de_referencia(self):
        pfx, senha = criar_certificado_laboratorio()
        assinado = assinar_xml_ficticio_pfx_laboratorio(pfx, senha)
        self.assertTrue(verificar_xml_assinado_laboratorio(assinado))
        ok, errors = self.erros(assinado)
        self.assertTrue(ok, "XMLDSig de laboratório falhou no XSD de referência: " + "\\n".join(errors))

    def test_validador_captura_elemento_invalido(self):
        xml = gerar_xml_ficticio_nao_assinado()
        root = etree.fromstring(xml)
        ns = {"n": NS_NFE}
        ide = root.find(".//n:ide", namespaces=ns)
        self.assertIsNotNone(ide)
        etree.SubElement(ide, f"{{{NS_NFE}}}campoInexistenteNoLeiaute").text = "X"
        ok, errors = self.erros(etree.tostring(root, encoding="utf-8", xml_declaration=True))
        self.assertFalse(ok)
        self.assertTrue(any("campoInexistenteNoLeiaute" in e for e in errors), errors)

    def test_assinatura_nunca_e_criada_pelo_gerador(self):
        root = etree.fromstring(gerar_xml_ficticio_nao_assinado())
        self.assertIsNone(root.find(f"{{{NS_DS}}}Signature"))
        self.assertEqual(root.find(f"{{{NS_NFE}}}infNFe").get("versao"), "4.00")


if __name__ == "__main__":
    unittest.main()
