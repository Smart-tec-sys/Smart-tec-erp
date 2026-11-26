"""Cofre A1 criptografado: testes com KMS EFÊMERO E FICTÍCIO, nunca Render."""
import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock, patch

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException

from app.services.fiscal_cofre_a1 import (
    CofreIndisponivel, proteger_a1, abrir_a1_interno, rotacionar_envelope,
)
from app.services.fiscal_cofre_a1_repository import (
    guardar_envelope_cifrado, consultar_envelope_interno,
)
from app.tenant.context import TenantContext


class KmsFakeTemporario:
    """Disponível exclusivamente em tests; não está no código de produção."""
    def __init__(self, key_id="test-kms-key"):
        self.key_id = key_id
        self.master = AESGCM.generate_key(bit_length=256)

    def envelopar(self, dek, *, contexto):
        nonce = __import__("os").urandom(12)
        return self.key_id, nonce + AESGCM(self.master).encrypt(nonce, dek, contexto)

    def desenvelopar(self, key_id, wrapped, *, contexto):
        if key_id != self.key_id:
            raise ValueError("KMS fake wrong key")
        return AESGCM(self.master).decrypt(wrapped[:12], wrapped[12:], contexto)


class CofreA1Tests(unittest.TestCase):
    def setUp(self):
        self.kms = KmsFakeTemporario()
        self.pfx = b"PKCS12-FICTICIO-NUNCA-USAR"
        self.senha = b"senha-ficticia-em-memoria"
        self.env = proteger_a1(1, self.pfx, self.senha, self.kms)

    def test_round_trip_com_seguro_por_tenant(self):
        self.assertEqual(abrir_a1_interno(1, self.env, self.kms), (self.pfx, self.senha))
        self.assertNotIn(self.pfx, self.env.conteudo_cifrado)
        self.assertNotIn(self.senha, self.env.conteudo_cifrado)
        self.assertNotIn(self.senha, repr(self.env).encode())
        self.assertEqual(len(self.env.nonce), 12)
        self.assertEqual(len(self.env.conteudo_cifrado), 4+len(self.pfx)+2+len(self.senha)+16)

    def test_deks_e_nonces_diferentes_em_duas_operacoes(self):
        other = proteger_a1(1,self.pfx,self.senha,self.kms)
        self.assertNotEqual(other.nonce,self.env.nonce)
        self.assertNotEqual(other.chave_envelopada,self.env.chave_envelopada)
        self.assertNotEqual(other.conteudo_cifrado,self.env.conteudo_cifrado)

    def test_isolamento_por_empresa_sem_abrir_kms(self):
        with self.assertRaisesRegex(CofreIndisponivel, "outra empresa"):
            abrir_a1_interno(2, self.env, self.kms)
        forged = replace(self.env, empresa_id=2)
        with self.assertRaises(CofreIndisponivel):
            abrir_a1_interno(2, forged, self.kms)

    def test_ciphertext_nonce_e_chave_trocados_bloqueados(self):
        cases = [
            replace(self.env, conteudo_cifrado=self.env.conteudo_cifrado[:-1]+bytes([self.env.conteudo_cifrado[-1]^1])),
            replace(self.env, nonce=bytes([self.env.nonce[0]^1])+self.env.nonce[1:]),
            replace(self.env, chave_envelopada=self.env.chave_envelopada[:-1]+bytes([self.env.chave_envelopada[-1]^1])),
        ]
        for forged in cases:
            with self.subTest(forged=forged.key_id), self.assertRaises(CofreIndisponivel):
                abrir_a1_interno(1, forged, self.kms)

    def test_bloqueio_sem_kms_real(self):
        with self.assertRaises(CofreIndisponivel):
            proteger_a1(1,self.pfx,self.senha,None)
        with self.assertRaises(CofreIndisponivel):
            abrir_a1_interno(1,self.env,None)

    def test_rotacao_nova_dek_preserva_payload(self):
        kms_new = KmsFakeTemporario("test-kms-rotated")
        updated = rotacionar_envelope(1,self.env,self.kms,kms_new)
        self.assertEqual(updated.key_id,"test-kms-rotated")
        self.assertNotEqual(updated.nonce,self.env.nonce)
        self.assertEqual(abrir_a1_interno(1,updated,kms_new),(self.pfx,self.senha))
        with self.assertRaises(CofreIndisponivel):
            abrir_a1_interno(1,updated,self.kms)

    def test_rejeita_payload_e_metadados_invalidos(self):
        for pfx, senha in [(b"",b"test"),(self.pfx,b""),(b"x"*(128*1024+1),self.senha),(self.pfx,b"x"*257)]:
            with self.subTest(size=len(pfx)),self.assertRaises(CofreIndisponivel):
                proteger_a1(1,pfx,senha,self.kms)
        with self.assertRaises(CofreIndisponivel):
            abrir_a1_interno(1,replace(self.env,versao=5),self.kms)

    def test_repositorio_requer_admin_e_tenant(self):
        db=Mock()
        with self.assertRaises(HTTPException) as ctx:
            guardar_envelope_cifrado(db,TenantContext(empresa_id=1),self.env)
        self.assertEqual(ctx.exception.status_code,403)
        db.add.assert_not_called()
        with patch("app.services.fiscal_cofre_a1_repository.exigir_admin") as admin:
            with self.assertRaises(HTTPException) as cross:
                guardar_envelope_cifrado(db,TenantContext(empresa_id=2,user_id=8),self.env)
            self.assertEqual(cross.exception.status_code,403)
            admin.assert_called_once()
        db.add.assert_not_called()

    def test_repositorio_grava_apenas_bytes_cifrados(self):
        db=Mock()
        db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value=None
        tenant=TenantContext(empresa_id=1,user_id=8)
        with patch("app.services.fiscal_cofre_a1_repository.exigir_admin"), \
             patch("app.services.fiscal_cofre_a1_repository._empresa") as emp:
            result=guardar_envelope_cifrado(db,tenant,self.env)
            self.assertTrue(result["envelope_armazenado"])
            self.assertFalse(result["emissao_habilitada"])
            emp.assert_called_once()
        stored=db.add.call_args[0][0]
        self.assertEqual(stored.empresa_id,1)
        self.assertEqual(stored.conteudo_cifrado,self.env.conteudo_cifrado)
        self.assertNotIn(self.pfx,stored.conteudo_cifrado)
        self.assertNotIn(self.senha,stored.conteudo_cifrado)
        db.commit.assert_called_once()

    def test_repositorio_consulta_somente_tenant_ativo(self):
        db=Mock()
        tenant=TenantContext(empresa_id=1,user_id=8)
        row=SimpleNamespace(empresa_id=1,versao=self.env.versao,key_id=self.env.key_id,
                            chave_envelopada=self.env.chave_envelopada,nonce=self.env.nonce,
                            conteudo_cifrado=self.env.conteudo_cifrado)
        db.query.return_value.filter.return_value.first.return_value=row
        with patch("app.services.fiscal_cofre_a1_repository.exigir_admin"), \
             patch("app.services.fiscal_cofre_a1_repository._empresa"):
            found=consultar_envelope_interno(db,tenant)
        self.assertEqual(found.empresa_id,1)
        self.assertEqual(abrir_a1_interno(1,found,self.kms),(self.pfx,self.senha))


if __name__ == "__main__":
    unittest.main()
