from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)

from app.database import Base


def _criado_em():
    return Column(DateTime, nullable=False, server_default=func.now())


def _atualizado_em():
    return Column(DateTime, nullable=False, server_default=func.now())


class ContaFinanceiraDB(Base):
    __tablename__ = "contas_financeiras"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    nome = Column(String(120), nullable=False)
    tipo = Column(String(20), nullable=False, default="BANCO")
    banco = Column(String(120), nullable=True)
    agencia = Column(String(30), nullable=True)
    numero_conta = Column(String(40), nullable=True)
    saldo_inicial = Column(Numeric(14, 2), nullable=False, default=0)
    ativo = Column(Boolean, nullable=False, default=True)
    observacao = Column(Text, nullable=True)
    criado_em = _criado_em()
    atualizado_em = _atualizado_em()


class FormaPagamentoDB(Base):
    __tablename__ = "formas_pagamento"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    nome = Column(String(80), nullable=False)
    tipo = Column(String(20), nullable=False, default="OUTRO")
    conta_financeira_id = Column(
        Integer,
        ForeignKey("contas_financeiras.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    disponivel_para = Column(String(10), nullable=False, default="AMBOS")
    ativo = Column(Boolean, nullable=False, default=True)
    criado_em = _criado_em()
    atualizado_em = _atualizado_em()


class PlanoContaDB(Base):
    __tablename__ = "plano_contas"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    codigo = Column(String(30), nullable=False)
    nome = Column(String(120), nullable=False)
    tipo = Column(String(20), nullable=False)
    pai_id = Column(Integer, ForeignKey("plano_contas.id"), nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    criado_em = _criado_em()
    atualizado_em = _atualizado_em()


class SituacaoFinanceiraDB(Base):
    __tablename__ = "situacoes_financeiras"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    nome = Column(String(80), nullable=False)
    tipo = Column(String(20), nullable=False, default="AMBOS")
    quitado = Column(Boolean, nullable=False, default=False)
    padrao = Column(Boolean, nullable=False, default=False)
    ativo = Column(Boolean, nullable=False, default=True)
    criado_em = _criado_em()
    atualizado_em = _atualizado_em()


class CentroCustoDB(Base):
    __tablename__ = "centros_custo"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    nome = Column(String(120), nullable=False)
    observacao = Column(Text, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    criado_em = _criado_em()
    atualizado_em = _atualizado_em()
