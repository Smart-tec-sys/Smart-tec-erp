# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, String, Boolean
from backend.core.database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(100), nullable=True)
    telefone = Column(String(20), nullable=True)
    cpf_cnpj = Column(String(20), nullable=True)
    ativo = Column(Boolean, default=True)
