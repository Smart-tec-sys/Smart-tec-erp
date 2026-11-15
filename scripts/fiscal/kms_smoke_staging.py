"""Smoke test AWS KMS/Render OIDC — staging exclusivo, sem certificados.

Execute manualmente no shell do serviço fiscal dedicado, após configurar OIDC,
IAM e KMS. Nunca executa importação A1, banco, XML ou SEFAZ.
Apenas cria uma DEK aleatória de 32 bytes em memória e verifica round-trip.
Não imprime chave, ciphertext, ARN, token, contexto nem dados de empresas.
"""
from __future__ import annotations

import os
import sys

from app.services.fiscal_kms_aws import criar_provedor_kms_staging
from app.services.fiscal_cofre_a1 import CofreIndisponivel

# Identificador artificial restrito a este ensaio; nunca corresponde a um
# tenant obtido de um cliente real.
CONTEXTO_TESTE = b"smarttec:a1:tenant:999999999:v1"


def main() -> int:
    try:
        provedor = criar_provedor_kms_staging()
        original = os.urandom(32)
        key_arn, cifrado = provedor.envelopar(original, contexto=CONTEXTO_TESTE)
        recuperado = provedor.desenvelopar(
            key_arn, cifrado, contexto=CONTEXTO_TESTE
        )
        if recuperado != original:
            print("FALHA: resultado KMS divergente.")
            return 1
        # O mesmo blob não pode ser desenvelopado usando outra empresa.
        try:
            provedor.desenvelopar(
                key_arn, cifrado,
                contexto=b"smarttec:a1:tenant:999999998:v1",
            )
        except CofreIndisponivel:
            pass
        else:
            print("FALHA: isolamento por contexto KMS não confirmado.")
            return 1
    except Exception:
        # Exceções SDK podem carregar metadados de infraestrutura.
        # Não imprimir mensagens, traceback ou variáveis neste teste.
        print("FALHA: verifique autorização OIDC, região, IAM e KMS no console seguro.")
        return 1

    print("OK: OIDC/KMS real validado com DEK fictícia e isolamento de contexto.")
    print("Certificado A1 e emissão NF-e continuam desabilitados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
