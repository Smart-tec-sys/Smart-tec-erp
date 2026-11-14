"""Triagem segura A1: testes fictícios e acesso administrativo por empresa."""
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID, ObjectIdentifier
from fastapi import HTTPException

from app.services.fiscal_certificado_a1 import (
    CertificadoA1Invalido, CNPJ_OID, conferir_pfx_a1_local,
    status_a1_empresa,
)
from app.tenant.context import TenantContext

TEST_CNPJ = "11222333000181"


def pfx_teste(cnpj: str = TEST_CNPJ, *, selfsigned=False, expired=False,
              digital_signature=True, omit_cnpj=False, wrong_key=False):
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    issuer_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "EMPRESA FICTICIA")])
    issuer = subject if selfsigned else x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "CA FICTICIA SEM ICP-BRASIL")
    ])
    now = datetime.now(timezone.utc)
    before = now - timedelta(days=60)
    after = now - timedelta(days=1) if expired else now + timedelta(days=30)
    san = [x509.DNSName("teste.example.invalid")] if omit_cnpj else [
        x509.OtherName(CNPJ_OID, b"\x0c\x0e" + cnpj.encode("ascii"))
    ]
    cert = (x509.CertificateBuilder()
        .subject_name(subject).issuer_name(issuer)
        .public_key(rsa_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(before).not_valid_after(after)
        .add_extension(x509.SubjectAlternativeName(san), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.KeyUsage(
            digital_signature=digital_signature, content_commitment=False,
            key_encipherment=False, data_encipherment=False, key_agreement=False,
            key_cert_sign=False, crl_sign=False, encipher_only=False, decipher_only=False
        ), critical=True)
        .sign(rsa_key if selfsigned else issuer_key, hashes.SHA256()))
    password = b"senha-ficticia"
    # Intentionally use a random key when checking the mismatched-key case.
    key_to_encode = rsa.generate_private_key(public_exponent=65537, key_size=2048) if wrong_key else rsa_key
    try:
        blob = pkcs12.serialize_key_and_certificates(
            name=b"a1-teste", key=key_to_encode, cert=cert, cas=None,
            encryption_algorithm=serialization.BestAvailableEncryption(password)
        )
    except ValueError:
        # cryptography/OpenSSL rejects a non-matching key before loading it.
        if wrong_key:
            return None, password
        raise
    return blob, password


class CertificadoA1Tests(unittest.TestCase):
    def test_triagem_cnpj_igual_mas_sem_habilitar_emissao(self):
        pfx, password = pfx_teste()
        result = conferir_pfx_a1_local(pfx, password, cnpj_emitente=TEST_CNPJ)
        self.assertEqual(result["tipo"], "A1")
        self.assertTrue(result["cnpj_base_compatível"])
        self.assertFalse(result["cadeia_icp_brasil_verificada"])
        self.assertFalse(result["revogacao_verificada"])
        self.assertFalse(result["armazenado_em_cofre"])
        self.assertFalse(result["emissao_habilitada"])
        self.assertNotIn(TEST_CNPJ, str(result))
        self.assertNotIn("senha-ficticia", str(result))
        self.assertNotIn("serial", str(result))

    def test_matriz_e_filial_mesma_raiz_somente_triagem(self):
        pfx, senha = pfx_teste()
        result = conferir_pfx_a1_local(pfx, senha, cnpj_emitente="11.222.333/0002-62")
        self.assertEqual(result["verificacao"], "TRIAGEM_LOCAL_INCOMPLETA")

    def test_recusa_cnpj_base_diferente(self):
        pfx, senha = pfx_teste("99999999000191")
        with self.assertRaisesRegex(CertificadoA1Invalido, "CNPJ-base"):
            conferir_pfx_a1_local(pfx, senha, cnpj_emitente=TEST_CNPJ)

    def test_recusa_certificado_autossinado(self):
        pfx, senha = pfx_teste(selfsigned=True)
        with self.assertRaisesRegex(CertificadoA1Invalido, "autossinado"):
            conferir_pfx_a1_local(pfx, senha, cnpj_emitente=TEST_CNPJ)

    def test_recusa_certificado_sem_cnpj_e_sem_assinatura(self):
        for config in ({"omit_cnpj": True}, {"digital_signature": False}):
            with self.subTest(config=config):
                pfx, senha = pfx_teste(**config)
                with self.assertRaises(CertificadoA1Invalido):
                    conferir_pfx_a1_local(pfx, senha, cnpj_emitente=TEST_CNPJ)

    def test_recusa_vencimento_e_senha_errada(self):
        pfx, senha = pfx_teste(expired=True)
        with self.assertRaisesRegex(CertificadoA1Invalido, "vencido"):
            conferir_pfx_a1_local(pfx, senha, cnpj_emitente=TEST_CNPJ)
        pfx, senha = pfx_teste()
        with self.assertRaisesRegex(CertificadoA1Invalido, "senha inválidos"):
            conferir_pfx_a1_local(pfx, b"errada", cnpj_emitente=TEST_CNPJ)

    def test_recusa_arquivos_grandes_e_cnpj_invalido(self):
        with self.assertRaises(CertificadoA1Invalido):
            conferir_pfx_a1_local(b"x"*140000, b"senha", cnpj_emitente=TEST_CNPJ)
        with self.assertRaises(CertificadoA1Invalido):
            conferir_pfx_a1_local(b"file", b"senha", cnpj_emitente="123")

    def test_status_exige_admin_ativo_e_tenant(self):
        db = Mock()
        with self.assertRaises(HTTPException) as ctx:
            status_a1_empresa(db, TenantContext(empresa_id=1))
        self.assertEqual(ctx.exception.status_code, 403)
        with patch("app.services.fiscal_cadastros.exigir_admin") as check_admin, \
             patch("app.services.fiscal_cadastros._empresa") as find_empresa:
            find_empresa.return_value = SimpleNamespace(id=2)
            result = status_a1_empresa(db, TenantContext(empresa_id=2, user_id=9))
            check_admin.assert_called_once()
            self.assertEqual(result["empresa_id"], 2)
            self.assertFalse(result["certificado_armazenado"])
            self.assertFalse(result["cofre_configurado"])
            self.assertFalse(result["emissao_habilitada"])
            find_empresa.return_value = SimpleNamespace(id=1)
            with self.assertRaises(CertificadoA1Invalido):
                status_a1_empresa(db, TenantContext(empresa_id=2, user_id=9))


if __name__ == "__main__":
    unittest.main()
