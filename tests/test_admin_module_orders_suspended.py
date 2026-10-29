"""Focused order-creation tests execute the status query in SQLite memory only."""
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.routes import admin


@pytest.fixture
def module_order_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as connection:
        connection.connection.driver_connection.create_function("NOW", 0, lambda: datetime.now().isoformat())
        with Session(bind=connection) as session:
            session.execute(text("CREATE TABLE modulos_saas (id INTEGER PRIMARY KEY,codigo TEXT,nome TEXT,ativo BOOLEAN)"))
            session.execute(text("CREATE TABLE empresa_modulos_saas (id INTEGER PRIMARY KEY,empresa_id INTEGER,modulo_id INTEGER,status TEXT)"))
            session.execute(text("""CREATE TABLE pedidos_modulos_saas (
                id INTEGER PRIMARY KEY,empresa_id INTEGER,modulo_id INTEGER,
                solicitado_por_usuario_id INTEGER,responsavel_equipe_id INTEGER,
                status TEXT,valor NUMERIC,periodicidade TEXT,data_pedido TEXT,
                forma_pagamento_id INTEGER,forma_pagamento TEXT,observacoes TEXT,
                criado_em TEXT,atualizado_em TEXT)"""))
            session.execute(text("INSERT INTO modulos_saas VALUES (1,'TEST','Módulo de teste',TRUE)"))
            session.commit()
            # SQLite cannot bind Decimal directly; retain the real SQL and convert its test-only binding.
            class DB:
                def execute(self, statement, params=None):
                    bindings = {k: str(v) if isinstance(v, Decimal) else v for k,v in (params or {}).items()}
                    return session.execute(statement, bindings)
                def commit(self): session.commit()
                def rollback(self): session.rollback()
            monkeypatch.setattr(admin, "_require_admin_empresa", lambda db,company: None)
            monkeypatch.setattr(admin, "_audit_admin", Mock())
            method = Mock(return_value=(7,"PIX de teste"))
            monkeypatch.setattr(admin, "resolve_order_payment_method", method)
            yield DB(), method
    engine.dispose()


@pytest.mark.parametrize("module_status,blocked", [
    ("ATIVO",True), ("PENDENTE",True), ("SUSPENSO",True),
    ("CANCELADO",False), ("EXPIRADO",False),
])
def test_new_avulso_order_respects_existing_commercial_link(module_order_db,module_status,blocked):
    db,method = module_order_db
    db.execute(text("INSERT INTO empresa_modulos_saas VALUES (1,4,1,:status)"),{"status":module_status})
    db.commit()
    member = SimpleNamespace(has_permission=lambda permission: True,usuario_id=1,equipe_id=1)
    payload = admin.AdminModuleOrderCreateInput(modulo_id=1,valor=100,periodicidade="MENSAL",forma_pagamento_id=7)
    if blocked:
        with pytest.raises(HTTPException) as exc:
            admin.admin_criar_pedido_modulo(4,payload,member,db)
        assert exc.value.status_code == 409
        assert exc.value.detail == "empresa já possui vínculo vigente ou suspenso para este módulo"
        method.assert_not_called()
        assert db.execute(text("SELECT count(*) FROM pedidos_modulos_saas")).scalar_one() == 0
    else:
        result = admin.admin_criar_pedido_modulo(4,payload,member,db)
        assert result["ok"] is True and result["status"] == "SOLICITADO"
        row = db.execute(text("SELECT empresa_id,modulo_id,status,forma_pagamento_id FROM pedidos_modulos_saas")).one()
        assert tuple(row) == (4,1,"SOLICITADO",7)
    assert db.execute(text("SELECT status FROM empresa_modulos_saas WHERE id=1")).scalar_one() == module_status
