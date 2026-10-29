"""Etapa 4B: somente este arquivo, com python -I -B, sem rede/banco/aplicacao.

Carrega por AST apenas as definicoes reais exercitadas, sem executar imports
ou inicializacao do ERP. O banco abaixo simula transacoes e travas de linha;
nao comprova isolamento/locks do PostgreSQL. Validar depois, em PostgreSQL
descartavel, duas sessoes READ COMMITTED disputando trial/contrato em ambas
as ordens: somente uma criacao, outra HTTP 409, sem escrita/auditoria parcial.
"""
import ast
from collections.abc import Callable
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
from functools import wraps
import importlib.abc
import json
from pathlib import Path
import re
import socket
import sys
import threading
from types import SimpleNamespace
from typing import Annotated, Literal
import unittest
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
NETWORK_ATTEMPTS = []


def forbid_network(*args, **kwargs):
    NETWORK_ATTEMPTS.append(True)
    raise AssertionError("Rede proibida nos testes 4B")


for target in (
    "socket.create_connection", "socket.getaddrinfo",
    "socket.socket.connect", "socket.socket.connect_ex",
    "socket.socket.bind", "socket.socket.sendto",
    "urllib.request.urlopen", "urllib.request.OpenerDirector.open",
):
    guard = patch(target, side_effect=forbid_network)
    guard.start()
    unittest.addModuleCleanup(guard.stop)


class BlockExternalImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "app" or fullname.startswith(("app.", "psycopg", "asyncpg")):
            raise AssertionError("Importacao externa proibida: " + fullname)


import_guard = BlockExternalImports()
sys.meta_path.insert(0, import_guard)
unittest.addModuleCleanup(sys.meta_path.remove, import_guard)

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import bindparam, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

for target in ("sqlalchemy.create_engine", "sqlalchemy.engine.create_engine",
               "sqlalchemy.engine.create.create_engine"):
    guard = patch(target, side_effect=AssertionError("Banco real proibido"))
    guard.start()
    unittest.addModuleCleanup(guard.stop)


def load_definitions(relative_path, names, namespace):
    tree = ast.parse((ROOT / relative_path).read_text(encoding="utf-8"))
    selected = []
    found = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names:
            selected.append(node)
            found.add(node.name)
        elif isinstance(node, ast.Assign):
            matched = {target.id for target in node.targets if isinstance(target, ast.Name)} & names
            if matched:
                selected.append(node)
                found.update(matched)
    if found != names:
        raise AssertionError("Definicoes ausentes: " + repr(names - found))
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(ROOT / relative_path), "exec"), namespace)
    return SimpleNamespace(**namespace)


def unconfigured_dependency():
    raise AssertionError("Dependencia deve ser substituida no teste")


class Member:
    equipe_id = 101
    usuario_id = 201

    def __init__(self, allowed=True):
        self.allowed = allowed
        self.requested = []

    def has_permission(self, permission):
        self.requested.append(permission)
        return self.allowed and permission == "ASSINATURAS_EDITAR"


def database_dependency():
    raise AssertionError("Banco deve ser substituido no teste")


def namespaces():
    common = dict(
        HTTPException=HTTPException, status=status, text=text, bindparam=bindparam,
        date=date, timedelta=timedelta, Decimal=Decimal, wraps=wraps, json=json,
        IntegrityError=IntegrityError, Annotated=Annotated, Literal=Literal,
        BaseModel=BaseModel, Field=Field, Session=Session, Callable=Callable,
        PlatformMemberContext=Member, Depends=Depends,
        get_current_platform_member=unconfigured_dependency,
    )
    permission = load_definitions(
        "app/admin/dependencies.py", {"require_platform_permission"}, dict(common)
    ).require_platform_permission
    payment_method = Mock(return_value=(1, "PIX ficticio"))
    service_ns = dict(common, resolve_order_payment_method=payment_method)
    service = load_definitions(
        "app/admin/subscriptions.py",
        {"LIVE_CONTRACT_STATUSES", "transaction", "_company", "_audit", "_period",
         "_price", "plan_module_conflicts", "prepare_contract"},
        service_ns,
    )
    route_ns = dict(
        common, subscriptions=service, require_platform_permission=permission,
        get_db=database_dependency, router=APIRouter(),
    )
    routes = load_definitions(
        "app/routes/admin.py",
        {"AdminTrialStartInput", "AdminSubscriptionContractInput",
         "AdminSubscriptionActivateInput", "_audit_admin", "admin_iniciar_trial",
         "admin_prepare_subscription", "admin_ativar_assinatura"},
        route_ns,
    )
    return service, routes


class Result:
    def __init__(self, rows=(), value=None):
        self.rows = list(rows)
        self.value = value

    def mappings(self):
        return self

    def scalars(self):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows

    def scalar(self):
        return self.value if self.value is not None else self.first()

    def scalar_one(self):
        return self.scalar()


class Store:
    def __init__(self, contracts=()):
        self.lock = threading.Lock()
        self.state = dict(
            companies={7: dict(id=7, status="ATIVA")},
            plans={1: dict(id=1, ativo=True, periodicidade="MENSAL")},
            contracts=deepcopy(list(contracts)), grants=[], audits=[],
        )


class FakeDB:
    """SQL reconhecido explicitamente: qualquer operacao inesperada falha."""
    def __init__(self, store=None, fail_on=None, pause_insert=False):
        self.store = store or Store()
        self.working = None
        self.locked = False
        self.executions = []
        self.statements = []
        self.commits = self.rollbacks = 0
        self.fail_on = fail_on
        self.pause_insert = pause_insert
        self.attempted_lock = threading.Event()
        self.at_insert = threading.Event()
        self.resume = threading.Event()

    def execute(self, statement, params=None):
        sql = " ".join(str(statement).split())
        params = dict(params or {})
        self.executions.append((sql, deepcopy(params)))
        self.statements.append(statement)
        if self.fail_on and self.fail_on in sql:
            raise RuntimeError("Falha ficticia injetada")
        if "FROM information_schema.columns" in sql:
            return Result(value=3)
        if sql == "SELECT id,status FROM empresas WHERE id=:id FOR UPDATE":
            self.attempted_lock.set()
            if not self.locked:
                if not self.store.lock.acquire(timeout=5):
                    raise AssertionError("Trava simulada nao liberada")
                self.locked = True
                self.working = deepcopy(self.store.state)
            row = self.working["companies"].get(params["id"])
            return Result([row] if row else [])
        if not self.locked:
            raise AssertionError("Consulta/escrita antes da trava da empresa")
        state = self.working
        if "FROM planos_saas" in sql:
            row = state["plans"].get(params["id"])
            return Result([row] if row else [])
        if "FROM assinaturas_saas" in sql:
            company = params.get("empresa_id", params.get("company"))
            if "estados" in params:
                states = params["estados"]
            else:
                states = re.findall(r"'([A-Z_]+)'", sql.split("status IN", 1)[1])
            rows = [row for row in state["contracts"]
                    if row["empresa_id"] == company and row["status"] in states]
            return Result(sorted(rows, key=lambda row: row["id"], reverse="DESC" in sql))
        if "FROM plano_modulos_saas" in sql:
            return Result([11, 12])
        if "FROM empresa_modulos_saas" in sql:
            module = params.get("modulo_id", params.get("module"))
            rows = [row for row in state["grants"] if row["modulo_id"] == module]
            if "SELECT id " in sql:
                return Result(value=rows[0]["id"] if rows else None)
            return Result(rows)
        if sql.startswith("INSERT INTO assinaturas_saas"):
            if self.pause_insert:
                self.at_insert.set()
                if not self.resume.wait(5):
                    raise AssertionError("Insercao simulada nao liberada")
            trial = "'TRIAL'" in sql
            identifier = max([row["id"] for row in state["contracts"]] + [0]) + 1
            row = dict(
                id=identifier,
                empresa_id=params.get("empresa_id", params.get("company")),
                plano_id=params.get("plano_id", params.get("plan")),
                status="TRIAL" if trial else "PENDENTE",
                periodicidade=params.get("periodicidade", params.get("period")),
                data_inicio_trial=params.get("inicio"), data_fim_trial=params.get("fim"),
                data_inicio_assinatura=None, data_vencimento=None,
            )
            state["contracts"].append(row)
            return Result(value=identifier)
        if sql.startswith("UPDATE assinaturas_saas SET plano_id"):
            row = next(row for row in state["contracts"] if row["id"] == params["id"])
            row.update(plano_id=params["plan"], periodicidade=params["period"],
                       valor=params["price"], forma_pagamento_id=params["method"])
            return Result()
        if sql.startswith("INSERT INTO empresa_modulos_saas"):
            state["grants"].append(dict(params, id=len(state["grants"]) + 1))
            return Result()
        if sql.startswith("INSERT INTO auditoria_plataforma"):
            state["audits"].append(params)
            return Result()
        raise AssertionError("SQL inesperado: " + sql)

    def _release(self):
        self.working = None
        if self.locked:
            self.locked = False
            self.store.lock.release()

    def commit(self):
        self.commits += 1
        if self.working is not None:
            self.store.state = deepcopy(self.working)
        self._release()

    def rollback(self):
        self.rollbacks += 1
        self._release()


def contract(state, identifier=40, company=7):
    return dict(
        id=identifier, empresa_id=company, status=state, plano_id=1,
        data_inicio_trial=date(2026, 1, 1), data_fim_trial=date(2026, 1, 8),
        data_inicio_assinatura=None, data_vencimento=None,
    )


class SubscriptionEntrypointsTests(unittest.TestCase):
    def setUp(self):
        self.service, self.routes = namespaces()
        self.member = Member()

    def tearDown(self):
        self.assertEqual(NETWORK_ATTEMPTS, [])
        self.assertFalse(any(name == "app" or name.startswith("app.") for name in sys.modules))

    def trial(self, db, **payload):
        return self.routes.admin_iniciar_trial(
            empresa_id=7, payload=self.routes.AdminTrialStartInput(**payload),
            member=self.member, db=db,
        )

    def prepare(self, db, **overrides):
        values = dict(plano_id=1, periodicidade="MENSAL", valor=Decimal("100.00"),
                      forma_pagamento_id=1, renovacao_automatica=False)
        values.update(overrides)
        return self.routes.admin_prepare_subscription(
            empresa_id=7, payload=self.routes.AdminSubscriptionContractInput(**values),
            member=self.member, db=db,
        )

    def assert_http_error(self, code, action):
        with self.assertRaises(HTTPException) as captured:
            action()
        self.assertEqual(captured.exception.status_code, code)

    def test_trial_blocks_every_live_contract_state(self):
        for state in self.service.LIVE_CONTRACT_STATUSES:
            with self.subTest(state=state):
                db = FakeDB(Store([contract(state)]))
                before = deepcopy(db.store.state)
                self.assert_http_error(409, lambda: self.trial(db))
                self.assertEqual(db.store.state, before)
                self.assertEqual((db.commits, db.rollbacks), (0, 1))
                self.assertFalse(db.locked)

    def test_contract_policy_matches_trial_shared_states(self):
        for state in self.service.LIVE_CONTRACT_STATUSES:
            with self.subTest(state=state):
                db = FakeDB(Store([contract(state)]))
                self.assert_http_error(409, lambda: self.prepare(db))
                self.assertEqual(db.commits, 0)
                self.assertEqual(len(db.store.state["contracts"]), 1)

    def test_cancelled_history_allows_new_trial(self):
        old = contract("CANCELADA")
        db = FakeDB(Store([old]))
        result = self.trial(db, dias=9, observacoes="Teste ficticio")
        self.assertEqual(result["status"], "TRIAL")
        self.assertEqual(db.store.state["contracts"][0], old)
        self.assertEqual(len(db.store.state["contracts"]), 2)
        self.assertEqual(result["data_fim_trial"] - result["data_inicio_trial"], timedelta(days=9))
        self.assertEqual((db.commits, db.rollbacks), (1, 0))

    def test_cancelled_history_allows_new_pending_contract(self):
        old = contract("CANCELADA")
        db = FakeDB(Store([old]))
        result = self.prepare(db)
        self.assertEqual(result["status"], "PENDENTE")
        self.assertEqual(db.store.state["contracts"][0], old)
        self.assertEqual(db.store.state["grants"], [])

    def test_active_contract_of_other_company_does_not_block(self):
        db = FakeDB(Store([contract("ATIVA", company=8)]))
        self.trial(db)
        self.assertEqual(len(db.store.state["contracts"]), 2)

    def test_missing_and_inactive_company_rollback(self):
        for missing in (True, False):
            with self.subTest(missing=missing):
                db = FakeDB()
                if missing:
                    db.store.state["companies"].clear()
                else:
                    db.store.state["companies"][7]["status"] = "INATIVA"
                self.assert_http_error(404 if missing else 409, lambda: self.trial(db))
                self.assertEqual((db.commits, db.rollbacks), (0, 1))
                self.assertFalse(db.locked)

    def test_missing_and_inactive_plan_rollback(self):
        for missing in (True, False):
            with self.subTest(missing=missing):
                db = FakeDB()
                if missing:
                    db.store.state["plans"].clear()
                else:
                    db.store.state["plans"][1]["ativo"] = False
                self.assert_http_error(404, lambda: self.trial(db, plano_id=1))
                self.assertEqual(db.store.state["contracts"], [])
                self.assertEqual(db.rollbacks, 1)

    def test_trial_audit_keeps_actor_company_dates_and_notes(self):
        db = FakeDB()
        result = self.trial(db, dias=10, observacoes="Dado ficticio")
        audit, = db.store.state["audits"]
        self.assertEqual(
            {key: audit[key] for key in ("equipe_id", "usuario_id", "empresa_id", "acao", "recurso", "recurso_id")},
            dict(equipe_id=101, usuario_id=201, empresa_id=7, acao="TRIAL_INICIADO",
                 recurso="assinaturas_saas", recurso_id=str(result["assinatura_id"])),
        )
        details = json.loads(audit["detalhes"])
        self.assertEqual(details["dias"], 10)
        self.assertEqual(details["data_inicio"], result["data_inicio_trial"].isoformat())
        self.assertEqual(details["data_fim"], result["data_fim_trial"].isoformat())
        insert_params = next(params for sql, params in db.executions if sql.startswith("INSERT INTO assinaturas_saas"))
        self.assertEqual(insert_params["observacoes"], "Dado ficticio")

    def test_audit_error_rolls_back_trial_and_modules(self):
        db = FakeDB(fail_on="INSERT INTO auditoria_plataforma")
        before = deepcopy(db.store.state)
        with self.assertRaisesRegex(RuntimeError, "Falha ficticia"):
            self.trial(db, plano_id=1)
        self.assertEqual(db.store.state, before)
        self.assertEqual((db.commits, db.rollbacks), (0, 1))
        self.assertFalse(db.locked)

    def test_read_error_after_lock_rolls_back(self):
        db = FakeDB(fail_on="FROM assinaturas_saas")
        with self.assertRaises(RuntimeError):
            self.trial(db)
        self.assertEqual(db.rollbacks, 1)
        self.assertFalse(db.locked)

    def test_trial_preserves_independent_module_and_includes_missing_one(self):
        db = FakeDB()
        existing = dict(id=80, modulo_id=11, origem="CORTESIA", status="ATIVO")
        db.store.state["grants"].append(existing)
        self.trial(db, plano_id=1)
        self.assertEqual(db.store.state["grants"][0], existing)
        self.assertEqual(db.store.state["grants"][1]["modulo_id"], 12)

    def test_trial_conversion_keeps_same_contract_and_trial_dates(self):
        for state in ("TRIAL", "TRIAL_EXPIRADO"):
            with self.subTest(state=state):
                old = contract(state)
                db = FakeDB(Store([old]))
                result = self.prepare(db, trial_id=old["id"])
                self.assertEqual(result["assinatura_id"], old["id"])
                row, = db.store.state["contracts"]
                self.assertEqual(row["status"], state)
                self.assertEqual(row["data_inicio_trial"], old["data_inicio_trial"])
                self.assertEqual(row["data_fim_trial"], old["data_fim_trial"])

    def test_wrong_trial_conversion_still_rejected(self):
        db = FakeDB(Store([contract("TRIAL")]))
        self.assert_http_error(409, lambda: self.prepare(db, trial_id=999))
        self.assertEqual(db.commits, 0)

    def test_direct_paid_activation_remains_blocked(self):
        db = FakeDB()
        self.assert_http_error(409, lambda: self.routes.admin_ativar_assinatura(
            7, self.routes.AdminSubscriptionActivateInput(plano_id=1), self.member, db
        ))
        self.assertEqual(db.executions, [])

    def test_periodicity_accepts_only_exact_monthly_and_annual(self):
        values = dict(plano_id=1, valor="100.00", forma_pagamento_id=1)
        for period in ("MENSAL", "ANUAL"):
            self.assertEqual(self.routes.AdminSubscriptionContractInput(
                periodicidade=period, **values
            ).periodicidade, period)
        for period in ("SEMANAL", "UNICO", "", "mensal", " MENSAL", "ANUAL\n", None, 1):
            with self.subTest(period=period), self.assertRaises(ValidationError):
                self.routes.AdminSubscriptionContractInput(periodicidade=period, **values)
        with self.assertRaises(ValidationError):
            self.routes.AdminSubscriptionContractInput(**values)

    def test_other_contract_and_trial_validations_preserved(self):
        values = dict(plano_id=1, periodicidade="MENSAL", valor="100", forma_pagamento_id=1)
        for changes in ({"plano_id": 0}, {"valor": 0}, {"valor": "1.001"},
                        {"forma_pagamento_id": 0}, {"trial_id": 0}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.routes.AdminSubscriptionContractInput(**{**values, **changes})
        for days in (0, 31):
            with self.subTest(days=days), self.assertRaises(ValidationError):
                self.routes.AdminTrialStartInput(dias=days)
        self.assertEqual(self.routes.AdminTrialStartInput().dias, 7)

    def test_same_company_lock_precedes_both_entrypoint_reads(self):
        for operation in (self.trial, self.prepare):
            db = FakeDB()
            operation(db)
            business = [(sql, params) for sql, params in db.executions
                        if "information_schema" not in sql]
            self.assertEqual(business[0], (
                "SELECT id,status FROM empresas WHERE id=:id FOR UPDATE", {"id": 7}
            ))
            self.assertFalse(db.locked)
            self.assertEqual(db.commits, 1)

    def test_expanding_states_compile_for_postgresql(self):
        db = FakeDB()
        self.trial(db)
        statement = next(statement for statement in db.statements if "FROM assinaturas_saas" in str(statement))
        compiled = statement.params(empresa_id=7, estados=self.service.LIVE_CONTRACT_STATUSES).compile(
            dialect=postgresql.dialect(), compile_kwargs={"render_postcompile": True}
        )
        self.assertEqual(compiled.params["empresa_id"], 7)
        self.assertEqual(tuple(value for key, value in compiled.params.items() if key.startswith("estados_")),
                         self.service.LIVE_CONTRACT_STATUSES)

    def test_real_permission_dependency_is_wired_to_both_routes(self):
        # Exercise the actual dependency registered by FastAPI, without an ASGI
        # event loop: Windows asyncio may create a local TCP socketpair.
        for allowed in (False, True):
            for suffix, operation in (("trial", self.trial), ("assinaturas", self.prepare)):
                with self.subTest(allowed=allowed, endpoint=suffix):
                    db = FakeDB()
                    member = Member(allowed)
                    route = next(route for route in self.routes.router.routes
                                 if route.path == "/empresas/{empresa_id}/" + suffix)
                    dependency = next(item for item in route.dependant.dependencies if item.name == "member")
                    self.assertEqual(dependency.dependencies[0].call, unconfigured_dependency)
                    if allowed:
                        self.assertIs(dependency.call(member), member)
                        operation(db)
                        self.assertEqual(db.commits, 1)
                    else:
                        self.assert_http_error(403, lambda: dependency.call(member))
                        self.assertEqual(db.executions, [])
                        self.assertEqual(db.store.state["audits"], [])
                    self.assertEqual(member.requested, ["ASSINATURAS_EDITAR"])

    def test_simulated_competition_trial_and_contract_both_orders(self):
        for first, second in ((self.trial, self.prepare), (self.prepare, self.trial), (self.trial, self.trial)):
            with self.subTest(first=first.__name__, second=second.__name__):
                store = Store()
                winner = FakeDB(store, pause_insert=True)
                loser = FakeDB(store)
                outcomes = []

                def run(operation, db):
                    try:
                        outcomes.append(operation(db)["status"])
                    except HTTPException as error:
                        outcomes.append(error.status_code)
                    except BaseException as error:
                        outcomes.append(error)

                thread1 = threading.Thread(target=run, args=(first, winner), daemon=True)
                thread2 = threading.Thread(target=run, args=(second, loser), daemon=True)
                thread1.start()
                try:
                    self.assertTrue(winner.at_insert.wait(3))
                    thread2.start()
                    self.assertTrue(loser.attempted_lock.wait(3))
                    self.assertEqual(loser.commits, 0)
                    self.assertFalse(any("FROM assinaturas_saas" in sql for sql, _ in loser.executions))
                finally:
                    winner.resume.set()
                    thread1.join(5)
                    if thread2.ident is not None:
                        thread2.join(5)
                self.assertFalse(thread1.is_alive() or thread2.is_alive())
                self.assertCountEqual(outcomes, ["TRIAL" if first == self.trial else "PENDENTE", 409])
                self.assertEqual(len(store.state["contracts"]), 1)
                self.assertEqual(len(store.state["audits"]), 1)
                self.assertEqual((loser.commits, loser.rollbacks), (0, 1))


if __name__ == "__main__":
    unittest.main(verbosity=2)

