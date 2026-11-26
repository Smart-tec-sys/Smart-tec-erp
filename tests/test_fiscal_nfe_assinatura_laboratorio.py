"""Assinatura XMLDSig NF-e — somente PFX efêmero fictício em memória."""
import unittest
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from lxml import etree

from app.services.fiscal_nfe_assinatura_laboratorio import (
    LAB_CN, NS_NFE, NS_DS, XmlFiscalNaoHabilitado,
    assinar_xml_ficticio_pfx_laboratorio, verificar_xml_assinado_laboratorio,
)
from app.services.fiscal_nfe_xml_homologacao import gerar_xml_ficticio_nao_assinado


def criar_certificado_laboratorio(cn=LAB_CN, *, expired=False, digital_signature=True):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    now = datetime.now(timezone.utc)
    before, after = ((now - timedelta(days=4), now - timedelta(days=2))
                     if expired else
                     (now - timedelta(minutes=10), now + timedelta(days=1)))
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(before)
        .not_valid_after(after)
        .add_extension(x509.KeyUsage(
            digital_signature=digital_signature, content_commitment=False,
            key_encipherment=False, data_encipherment=False, key_agreement=False,
            key_cert_sign=False, crl_sign=False,
            encipher_only=False, decipher_only=False,
        ), critical=True)
        .sign(private_key, hashes.SHA256())
    )
    password = b"senha-ficticia-somente-teste"
    pfx = pkcs12.serialize_key_and_certificates(
        name=b"fiscal-laboratorio", key=private_key, cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(password),
    )
    return pfx, password


class AssinaturaLaboratorioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pfx, cls.password = criar_certificado_laboratorio()

    def assinado(self):
        return assinar_xml_ficticio_pfx_laboratorio(self.pfx, self.password)

    def test_assinatura_valida_e_referencia_infNFe(self):
        xml = self.assinado()
        self.assertTrue(verificar_xml_assinado_laboratorio(xml))
        root = etree.fromstring(xml)
        self.assertEqual([x.tag for x in root], [
            f"{{{NS_NFE}}}infNFe", f"{{{NS_DS}}}Signature"
        ])
        inf_id = root[0].get("Id")
        refs = root.xpath("//ds:SignedInfo/ds:Reference/@URI", namespaces={"ds":NS_DS})
        self.assertEqual(refs, ["#" + inf_id])
        self.assertEqual(root.xpath("count(//ds:X509Certificate)", namespaces={"ds":NS_DS}), 1)

    def test_criptografia_detecta_alteracao_em_produto(self):
        root = etree.fromstring(self.assinado())
        element = root.find(".//{" + NS_NFE + "}vProd")
        self.assertIsNotNone(element)
        element.text = "999.00"
        with self.assertRaisesRegex(XmlFiscalNaoHabilitado, "alterado"):
            verificar_xml_assinado_laboratorio(etree.tostring(root))

    def test_criptografia_detecta_alteracao_em_signed_info(self):
        root = etree.fromstring(self.assinado())
        c14n = root.find(".//{" + NS_DS + "}DigestValue")
        self.assertIsNotNone(c14n)
        c14n.text = "AAAAAAAAAAAAAAAAAAAAAAAAAAA="
        with self.assertRaises(XmlFiscalNaoHabilitado):
            verificar_xml_assinado_laboratorio(etree.tostring(root))

    def test_criptografia_detecta_assinatura_alterada(self):
        root = etree.fromstring(self.assinado())
        signature = root.find(".//{" + NS_DS + "}SignatureValue")
        self.assertIsNotNone(signature)
        signature.text = "AA" + signature.text[2:]
        with self.assertRaises(XmlFiscalNaoHabilitado):
            verificar_xml_assinado_laboratorio(etree.tostring(root))

    def test_rejeita_referencia_externa(self):
        root = etree.fromstring(self.assinado())
        reference = root.find(".//{" + NS_DS + "}Reference")
        reference.set("URI", "https://example.invalid/")
        with self.assertRaisesRegex(XmlFiscalNaoHabilitado, "referência|Referência"):
            verificar_xml_assinado_laboratorio(etree.tostring(root))

    def test_rejeita_algoritmo_trocado(self):
        root = etree.fromstring(self.assinado())
        method = root.find(".//{" + NS_DS + "}SignatureMethod")
        method.set("Algorithm", "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256")
        with self.assertRaises(XmlFiscalNaoHabilitado):
            verificar_xml_assinado_laboratorio(etree.tostring(root))

    def test_rejeita_id_duplicado_ou_elemento_extra(self):
        root = etree.fromstring(self.assinado())
        etree.SubElement(root, f"{{{NS_NFE}}}infNFe", Id=root[0].get("Id"))
        with self.assertRaises(XmlFiscalNaoHabilitado):
            verificar_xml_assinado_laboratorio(etree.tostring(root))

    def test_rejeita_senha_errada(self):
        with self.assertRaises(XmlFiscalNaoHabilitado):
            assinar_xml_ficticio_pfx_laboratorio(self.pfx, b"senha-errada")

    def test_nao_aceita_pfx_real_ou_externo(self):
        pfx, password = criar_certificado_laboratorio("CNPJ-DE-EMPRESA-REAL")
        with self.assertRaisesRegex(XmlFiscalNaoHabilitado, "laboratório"):
            assinar_xml_ficticio_pfx_laboratorio(pfx, password)

    def test_rejeita_certificado_expirado_e_sem_uso_assinatura(self):
        for kwargs in ({"expired":True}, {"digital_signature":False}):
            with self.subTest(kwargs=kwargs):
                pfx, password = criar_certificado_laboratorio(**kwargs)
                with self.assertRaises(XmlFiscalNaoHabilitado):
                    assinar_xml_ficticio_pfx_laboratorio(pfx, password)

    def test_bloqueia_payload_real_e_xml_externo(self):
        with self.assertRaises(TypeError):
            assinar_xml_ficticio_pfx_laboratorio(self.pfx, self.password, empresa_id=1)
        with self.assertRaises(TypeError):
            assinar_xml_ficticio_pfx_laboratorio(self.pfx, self.password, xml=b"<nfe/>")
        with self.assertRaises(XmlFiscalNaoHabilitado):
            verificar_xml_assinado_laboratorio(gerar_xml_ficticio_nao_assinado())

    def test_rejeita_entrada_xml_com_dtd(self):
        payload = b'<!DOCTYPE NFe [<!ENTITY test SYSTEM "file:///etc/passwd">]>' + self.assinado()
        with self.assertRaises(XmlFiscalNaoHabilitado):
            verificar_xml_assinado_laboratorio(payload)


if __name__ == "__main__":
    unittest.main()
