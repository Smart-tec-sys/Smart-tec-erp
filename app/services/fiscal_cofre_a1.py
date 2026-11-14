"""Núcleo criptográfico A1: AES-256-GCM com DEK independente e envoltória KMS.

NÃO inclui chave-mestra, provedor KMS real, rota de upload ou serviço SEFAZ.
Nenhum certificado real deve ser importado enquanto o cofre externo não existir.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable
import os
import re
import struct
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.services.fiscal_certificado_a1 import MAX_PFX_BYTES, MAX_SENHA_BYTES

VERSAO = 1
MAX_CIFRADO = MAX_PFX_BYTES + MAX_SENHA_BYTES + 64
_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9:./_@+-]{0,159}$")


class CofreIndisponivel(RuntimeError):
    """Falha segura sem expor material criptográfico."""


@runtime_checkable
class ProvedorKms(Protocol):
    """Contrato de chaves externo; NÃO existe implementação real nesta fase."""
    def envelopar(self, dek: bytes, *, contexto: bytes) -> tuple[str, bytes]: ...
    def desenvelopar(self, key_id: str, wrapped: bytes, *, contexto: bytes) -> bytes: ...


@dataclass(frozen=True)
class EnvelopeA1:
    empresa_id: int
    versao: int
    key_id: str
    chave_envelopada: bytes = field(repr=False)
    nonce: bytes = field(repr=False)
    conteudo_cifrado: bytes = field(repr=False)

    def __repr__(self):
        return f"EnvelopeA1(empresa_id={self.empresa_id}, versao={self.versao}, protegido=True)"


def _contexto(empresa_id: int) -> bytes:
    if isinstance(empresa_id, bool) or not isinstance(empresa_id, int) or empresa_id <= 0:
        raise CofreIndisponivel("Identificador de empresa inválido.")
    return f"smarttec:a1:tenant:{empresa_id}:v1".encode("ascii")


def _validar_envelope(env: EnvelopeA1) -> None:
    if not isinstance(env, EnvelopeA1):
        raise CofreIndisponivel("Registro do cofre inválido.")
    _contexto(env.empresa_id)
    if env.versao != VERSAO or not isinstance(env.key_id, str) or not _KEY_PATTERN.fullmatch(env.key_id):
        raise CofreIndisponivel("Versão ou identificador de chave inválido.")
    if (not isinstance(env.chave_envelopada, bytes)
        or not 32 <= len(env.chave_envelopada) <= 4096
        or not isinstance(env.nonce, bytes) or len(env.nonce) != 12
        or not isinstance(env.conteudo_cifrado, bytes)
        or not 20 <= len(env.conteudo_cifrado) <= MAX_CIFRADO):
        raise CofreIndisponivel("Envelope A1 inválido.")


def _kms(provedor: ProvedorKms) -> ProvedorKms:
    if not isinstance(provedor, ProvedorKms):
        raise CofreIndisponivel("Gerenciador externo de chaves indisponível.")
    return provedor


def proteger_a1(empresa_id: int, pfx: bytes, senha: bytes,
                provedor: ProvedorKms) -> EnvelopeA1:
    """Cifra PFX e senha juntos usando DEK única e AAD vinculada à empresa."""
    contexto = _contexto(empresa_id)
    if not isinstance(pfx, bytes) or not 0 < len(pfx) <= MAX_PFX_BYTES:
        raise CofreIndisponivel("PFX não aceito pelo cofre.")
    if not isinstance(senha, bytes) or not 0 < len(senha) <= MAX_SENHA_BYTES:
        raise CofreIndisponivel("Senha não aceita pelo cofre.")
    provedor = _kms(provedor)
    plain = struct.pack(">I", len(pfx)) + pfx + struct.pack(">H", len(senha)) + senha
    dek = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    try:
        key_id, wrapped = provedor.envelopar(dek, contexto=contexto)
        if (not isinstance(key_id, str) or not _KEY_PATTERN.fullmatch(key_id)
            or not isinstance(wrapped, bytes)):
            raise CofreIndisponivel("KMS não retornou identificador de chave válido.")
        ciphertext = AESGCM(dek).encrypt(nonce, plain, contexto)
        env = EnvelopeA1(empresa_id, VERSAO, key_id, wrapped, nonce, ciphertext)
        _validar_envelope(env)
        return env
    except CofreIndisponivel:
        raise
    except Exception as exc:
        raise CofreIndisponivel("Falha ao proteger o certificado no KMS.") from exc


def abrir_a1_interno(empresa_id: int, env: EnvelopeA1,
                     provedor: ProvedorKms) -> tuple[bytes, bytes]:
    """Somente uso de assinador interno futuro; jamais retornar em endpoint HTTP."""
    contexto = _contexto(empresa_id)
    _validar_envelope(env)
    if env.empresa_id != empresa_id:
        raise CofreIndisponivel("Certificado de outra empresa.")
    provedor = _kms(provedor)
    try:
        dek = provedor.desenvelopar(env.key_id, env.chave_envelopada, contexto=contexto)
        if not isinstance(dek, bytes) or len(dek) != 32:
            raise CofreIndisponivel("Chave devolvida pelo KMS inválida.")
        plain = AESGCM(dek).decrypt(env.nonce, env.conteudo_cifrado, contexto)
        if len(plain) < 7:
            raise CofreIndisponivel("Conteúdo do cofre inválido.")
        pfx_len = struct.unpack(">I", plain[:4])[0]
        pos = 4 + pfx_len
        if not 0 < pfx_len <= MAX_PFX_BYTES or pos + 2 > len(plain):
            raise CofreIndisponivel("Conteúdo do cofre inválido.")
        senha_len = struct.unpack(">H", plain[pos:pos+2])[0]
        if not 0 < senha_len <= MAX_SENHA_BYTES or pos + 2 + senha_len != len(plain):
            raise CofreIndisponivel("Conteúdo do cofre inválido.")
        return plain[4:pos], plain[pos+2:]
    except (InvalidTag, ValueError, TypeError) as exc:
        raise CofreIndisponivel("Envelope adulterado ou credencial KMS incorreta.") from exc
    except CofreIndisponivel:
        raise
    except Exception as exc:
        raise CofreIndisponivel("Erro de leitura protegida no KMS.") from exc


def rotacionar_envelope(empresa_id: int, env: EnvelopeA1,
                       provedor_antigo: ProvedorKms,
                       provedor_novo: ProvedorKms) -> EnvelopeA1:
    """Troca DEK/nonce e chave de proteção; não altera tenant."""
    pfx, senha = abrir_a1_interno(empresa_id, env, provedor_antigo)
    return proteger_a1(empresa_id, pfx, senha, provedor_novo)
