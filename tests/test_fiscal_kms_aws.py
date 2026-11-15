"""Testes sem acesso AWS: adaptador real usa cliente KMS injetado e dados fictícios."""
import os
import tempfile
import unittest
from unittest.mock import Mock
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.services.fiscal_kms_aws import (
    AwsKmsProvedor, CofreIndisponivel, _encryption_context,
    _runtime_ready, situacao_kms_aws, criar_provedor_kms_staging,
)
from app.services.fiscal_cofre_a1 import proteger_a1, abrir_a1_interno

ARN="arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789abc"
ROLE="arn:aws:iam::123456789012:role/smarttec-fiscal-staging"


class KmsSimuladoBoto:
    """Simula apenas chamadas boto3 KMS no CI; não é provedor produtivo."""
    def __init__(self):
        self.master = AESGCM.generate_key(bit_length=256)
        self.encrypt_calls=[]
        self.decrypt_calls=[]
        self.fail=False

    @staticmethod
    def _aad(ctx):
        return "|".join(k + "=" + v for k,v in sorted(ctx.items())).encode("utf-8")

    def encrypt(self, **kwargs):
        self.encrypt_calls.append(kwargs)
        if self.fail:
            raise RuntimeError("API KMS indisponível")
        nonce=os.urandom(12)
        value=nonce+AESGCM(self.master).encrypt(
            nonce, kwargs["Plaintext"], self._aad(kwargs["EncryptionContext"]))
        return {"CiphertextBlob": value, "KeyId": kwargs["KeyId"]}

    def decrypt(self, **kwargs):
        self.decrypt_calls.append(kwargs)
        if self.fail:
            raise RuntimeError("API KMS indisponível")
        plain=AESGCM(self.master).decrypt(
            kwargs["CiphertextBlob"][:12], kwargs["CiphertextBlob"][12:],
            self._aad(kwargs["EncryptionContext"]))
        return {"Plaintext": plain, "KeyId": kwargs["KeyId"]}


class AwsKmsA1Tests(unittest.TestCase):
    def setUp(self):
        self.client=KmsSimuladoBoto()
        self.provider=AwsKmsProvedor(key_arn=ARN,client=self.client)

    def test_pfx_ficticio_isolado_empresa_e_envelope(self):
        env=proteger_a1(1,b"PFX FICTICIO",b"senha ficticia",self.provider)
        self.assertEqual(abrir_a1_interno(1,env,self.provider),(b"PFX FICTICIO",b"senha ficticia"))
        self.assertEqual(len(self.client.encrypt_calls),1)
        self.assertEqual(len(self.client.decrypt_calls),1)
        encrypt=self.client.encrypt_calls[0]
        self.assertEqual(len(encrypt["Plaintext"]),32)
        self.assertEqual(encrypt["KeyId"],ARN)
        self.assertEqual(encrypt["EncryptionContext"],{
            "smarttec:purpose":"smarttec-fiscal-a1-envelope-v1",
            "smarttec:empresa_id":"1"})
        self.assertNotIn(b"PFX FICTICIO",encrypt["Plaintext"])
        self.assertEqual(self.client.decrypt_calls[0]["EncryptionContext"],encrypt["EncryptionContext"])

    def test_tenant_alterado_nao_passara_descriptografia(self):
        env=proteger_a1(1,b"test",b"pass",self.provider)
        from dataclasses import replace
        forged=replace(env,empresa_id=2)
        with self.assertRaises(CofreIndisponivel):
            abrir_a1_interno(2,forged,self.provider)

    def test_falha_de_kms_retorna_erro_generico(self):
        self.client.fail=True
        with self.assertRaisesRegex(CofreIndisponivel,"Falha de cifragem AWS KMS"):
            proteger_a1(1,b"test",b"pass",self.provider)

    def test_rejeita_arn_invalido_e_chave_trocada(self):
        with self.assertRaises(CofreIndisponivel):
            AwsKmsProvedor(key_arn="alias/not-permitted",client=self.client)
        with self.assertRaises(CofreIndisponivel):
            self.provider.desenvelopar("arn:aws:kms:us-east-1:999999999999:key/12345678-1234-1234-1234-123456789abc",
                                      b"x"*64,contexto=b"smarttec:a1:tenant:1:v1")
        self.assertEqual(self.client.decrypt_calls,[])

    def test_contexto_rejeita_valores_arbitrarios(self):
        for x in (b"",b"smarttec:a1:tenant:0:v1",b"cnpj:11222333000181",
                  b"smarttec:a1:tenant:1:v2"):
            with self.subTest(x=x),self.assertRaises(CofreIndisponivel):
                _encryption_context(x)

    def test_flag_fechada_sem_oidc_ou_em_producao(self):
        self.assertEqual(situacao_kms_aws({}),"INATIVO")
        base={
            "SMARTTEC_FISCAL_A1_KMS_ADAPTER_ENABLED":"1","SMARTTEC_ENV":"staging",
            "SMARTTEC_AUTH_MODE":"authenticated","AWS_ROLE_ARN":ROLE,"AWS_REGION":"us-east-1",
            "SMARTTEC_FISCAL_A1_KMS_KEY_ARN":ARN,
        }
        self.assertFalse(_runtime_ready(base))
        with tempfile.NamedTemporaryFile() as token:
            base["AWS_WEB_IDENTITY_TOKEN_FILE"]=token.name
            self.assertTrue(_runtime_ready(base))
            self.assertEqual(situacao_kms_aws(base),"CONFIGURACAO_OIDC_DETECTADA_NAO_VERIFICADA")
            for bad in (
                {"SMARTTEC_ENV":"production"},
                {"SMARTTEC_AUTH_MODE":"dev"},
                {"AWS_ACCESS_KEY_ID":"no-long-lived-secrets"},
                {"AWS_SECRET_ACCESS_KEY":"no-long-lived-secrets"},
                {"AWS_REGION":"sa-east-1"},
                {"AWS_ROLE_ARN":"arn:aws:iam::999999999999:role/not-this-account"},
                {"SMARTTEC_FISCAL_A1_KMS_ADAPTER_ENABLED":"0"},
            ):
                with self.subTest(bad=bad):
                    self.assertFalse(_runtime_ready({**base,**bad}))
        with self.assertRaises(CofreIndisponivel):
            criar_provedor_kms_staging() # CI does not set the enabling flag


if __name__=="__main__":
    unittest.main()
