"""Apenas envelope criptográfico A1; PFX/senha em claro nunca viram colunas."""
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, LargeBinary, SmallInteger, String, func
from app.database import Base


class FiscalCertificadoCofreDB(Base):
    __tablename__ = "fiscal_certificados_cofre"
    __table_args__ = (
        CheckConstraint("versao = 1", name="ck_fiscal_cofre_versao"),
        CheckConstraint("octet_length(nonce) = 12", name="ck_fiscal_cofre_nonce"),
        CheckConstraint("octet_length(chave_envelopada) BETWEEN 32 AND 4096",
                        name="ck_fiscal_cofre_chave"),
        CheckConstraint("octet_length(conteudo_cifrado) BETWEEN 20 AND 135000",
                        name="ck_fiscal_cofre_ciphertext"),
    )

    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), primary_key=True)
    versao = Column(SmallInteger, nullable=False, default=1)
    key_id = Column(String(160), nullable=False)
    chave_envelopada = Column(LargeBinary, nullable=False)
    nonce = Column(LargeBinary(12), nullable=False)
    conteudo_cifrado = Column(LargeBinary, nullable=False)
    criado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), nullable=False,
                           server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"FiscalCertificadoCofreDB(empresa_id={self.empresa_id}, cifrado=True)"
