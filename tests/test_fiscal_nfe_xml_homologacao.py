"""XML da NF-e 4.00: exemplo sintético isolado, não assinado e não transmissível."""
import re
import unittest
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET

from app.services.fiscal_nfe_xml_homologacao import (
    XmlFiscalNaoHabilitado, gerar_xml_ficticio_nao_assinado,
    validar_xsd_documento_assinado, _dv_chave, NS_NFE
)


class XmlHomologacaoTests(unittest.TestCase):
    def test_xml_formado_com_grupos_essenciais_modelo55(self):
        xml = gerar_xml_ficticio_nao_assinado()
        root = ET.fromstring(xml)
        ns = {"n": NS_NFE}
        self.assertEqual(root.tag, "{" + NS_NFE + "}NFe")
        inf = root.find("n:infNFe", ns)
        self.assertEqual(inf.attrib["versao"], "4.00")
        self.assertRegex(inf.attrib["Id"], r"^NFe\d{44}$")
        self.assertEqual(
            [n.tag.removeprefix("{" + NS_NFE + "}") for n in list(inf)],
            ["ide", "emit", "dest", "det", "total", "transp", "pag", "infAdic"]
        )
        self.assertEqual(inf.findtext("n:ide/n:tpAmb", namespaces=ns), "2")
        self.assertEqual(inf.findtext("n:ide/n:mod", namespaces=ns), "55")
        self.assertEqual(inf.findtext("n:det/n:prod/n:qCom", namespaces=ns), "2.5000")
        self.assertEqual(inf.findtext("n:det/n:prod/n:vUnCom", namespaces=ns), "100.0000")
        self.assertEqual(inf.findtext("n:total/n:ICMSTot/n:vNF", namespaces=ns), "250.00")
        self.assertEqual(inf.findtext("n:pag/n:detPag/n:tPag", namespaces=ns), "90")
        self.assertIsNone(root.find("{http://www.w3.org/2000/09/xmldsig#}Signature"))
        self.assertIn(b"NAO TRANSMITIR", xml)

    def test_gera_id_sintetico_com_digito_mod11(self):
        root = ET.fromstring(gerar_xml_ficticio_nao_assinado())
        key = root.find("{" + NS_NFE + "}infNFe").attrib["Id"][3:]
        self.assertEqual(len(key), 44)
        self.assertEqual(_dv_chave(key[:43]), key[43:])

    def test_mesmo_exemplo_produz_mesmo_xml_sem_aleatoriedade(self):
        self.assertEqual(gerar_xml_ficticio_nao_assinado(), gerar_xml_ficticio_nao_assinado())

    def test_quantidade_quatro_casas_sem_arredondar(self):
        xml = gerar_xml_ficticio_nao_assinado(
            quantidade="0.0001", preco_unitario="100000.0000", subtotal="10.00"
        )
        root = ET.fromstring(xml)
        self.assertEqual(
            root.findtext(".//{" + NS_NFE + "}qCom"), "0.0001"
        )

    def test_rejeita_valor_inconsistente(self):
        with self.assertRaises(XmlFiscalNaoHabilitado):
            gerar_xml_ficticio_nao_assinado(
                quantidade="2.5000", preco_unitario="100.0000", subtotal="260.00"
            )

    def test_rejeita_valor_nao_finito_ou_precisao_maior(self):
        samples = [
            ("NaN", "100.0000", "250.00"),
            ("0.00001", "100.0000", "250.00"),
            ("0.0000", "100.0000", "250.00"),
            ("2.5000", "Infinity", "250.00"),
            ("2.5000", "100.00000", "250.00"),
            ("2.5000", "100.0000", "-1"),
        ]
        for q, p, t in samples:
            with self.subTest(q=q, p=p, t=t), self.assertRaises(XmlFiscalNaoHabilitado):
                gerar_xml_ficticio_nao_assinado(quantidade=q, preco_unitario=p, subtotal=t)

    def test_rejeita_schema_ausente_antes_de_validar_xml_nao_assinado(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises(XmlFiscalNaoHabilitado) as err:
                validar_xsd_documento_assinado(
                    gerar_xml_ficticio_nao_assinado(), Path(tmp) / "nfe_v4.00.xsd"
                )
            self.assertIn("não está assinado", str(err.exception))

    def test_nao_expoe_dados_reais_nem_integracao_com_banco(self):
        xml = gerar_xml_ficticio_nao_assinado()
        # Interface do gerador não aceita payload da empresa, tenant ou banco.
        with self.assertRaises(TypeError):
            gerar_xml_ficticio_nao_assinado(empresa_id=1)
        self.assertNotIn(b"smarttec_persianas_prod", xml)
        self.assertNotIn(b"total_cliente_final", xml)
        self.assertNotIn(b"valor_parceiro", xml)


if __name__ == "__main__":
    unittest.main()
