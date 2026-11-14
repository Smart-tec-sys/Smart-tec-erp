"""Guarda envelopes cifrados por tenant; API HTTP não expõe importação/decriptação."""
from __future__ import annotations
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models.fiscal_certificado_cofre import FiscalCertificadoCofreDB
from app.services.fiscal_cofre_a1 import EnvelopeA1, _validar_envelope
from app.services.fiscal_cadastros import _empresa, exigir_admin
from app.tenant.isolation import require_tenant


def guardar_envelope_cifrado(db: Session, tenant, env: EnvelopeA1) -> dict:
    """Interno: admin autenticado, empresa ativa e dados apenas cifrados."""
    exigir_admin(db, tenant)
    empresa_id = require_tenant(tenant)
    _validar_envelope(env)
    if env.empresa_id != empresa_id:
        raise HTTPException(status_code=403, detail="Empresa não autorizada para o certificado.")
    _empresa(db, tenant, bloquear=True)
    row = (db.query(FiscalCertificadoCofreDB)
           .filter(FiscalCertificadoCofreDB.empresa_id == empresa_id)
           .with_for_update().first())
    if row is None:
        row = FiscalCertificadoCofreDB(empresa_id=empresa_id)
        db.add(row)
    row.versao, row.key_id = env.versao, env.key_id
    row.chave_envelopada, row.nonce = env.chave_envelopada, env.nonce
    row.conteudo_cifrado = env.conteudo_cifrado
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Não foi possível armazenar envelope cifrado.") from exc
    return {"empresa_id": empresa_id, "envelope_armazenado": True,
            "cofre_kms_habilitado": False, "emissao_habilitada": False}


def consultar_envelope_interno(db: Session, tenant) -> EnvelopeA1 | None:
    """Não expor por rota: somente operação administrativa backend."""
    exigir_admin(db, tenant)
    empresa_id = require_tenant(tenant)
    _empresa(db, tenant)
    row = (db.query(FiscalCertificadoCofreDB)
           .filter(FiscalCertificadoCofreDB.empresa_id == empresa_id).first())
    if row is None:
        return None
    env = EnvelopeA1(
        empresa_id=empresa_id, versao=row.versao, key_id=row.key_id,
        chave_envelopada=bytes(row.chave_envelopada),
        nonce=bytes(row.nonce), conteudo_cifrado=bytes(row.conteudo_cifrado),
    )
    _validar_envelope(env)
    return env
