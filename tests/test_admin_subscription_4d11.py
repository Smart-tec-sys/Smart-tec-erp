"""4D.11: exercita definicoes reais por AST e transacoes simuladas, sem banco/rede.

Reutiliza o isolamento do teste de entrypoints anterior; nao importa o ERP.
Executar diretamente com python -I -B para nao criar caches.
"""
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[1]
support = runpy.run_path(str(ROOT / "tests/test_admin_subscription_entrypoints.py"))
FakeDB, Store = support["FakeDB"], support["Store"]
HTTPException, Member = support["HTTPException"], support["Member"]
contract = support["contract"]


class TrialPolicy4D11Tests(unittest.TestCase):
    def setUp(self):
        self.service, self.routes = support["namespaces"]()
        self.member = Member()

    def tearDown(self):
        self.assertEqual(support["NETWORK_ATTEMPTS"], [])

    def trial(self, db, **payload):
        return self.routes.admin_iniciar_trial(
            empresa_id=7, payload=self.routes.AdminTrialStartInput(**payload),
            member=self.member, db=db,
        )

    def prepare(self, db, **overrides):
        values = dict(plano_id=1, periodicidade="MENSAL", valor=Decimal("99.90"),
                      forma_pagamento_id=1, renovacao_automatica=False)
        values.update(overrides)
        return self.routes.admin_prepare_subscription(
            7, self.routes.AdminSubscriptionContractInput(**values), self.member, db
        )

    def assert_unchanged_refusal(self, db, operation, code, message):
        before = deepcopy(db.store.state)
        with self.assertRaises(HTTPException) as caught:
            operation()
        self.assertEqual(caught.exception.status_code, code)
        self.assertEqual(caught.exception.detail, message)
        self.assertEqual(db.store.state, before)
        self.assertEqual((db.commits, db.rollbacks), (0, 1))
        self.assertFalse(db.locked)
        self.assertFalse(any(sql.startswith(("INSERT ", "UPDATE ", "DELETE "))
                             for sql, _ in db.executions))

    def test_explicit_zero_refuses_before_trial_grants_or_audit_writes(self):
        for days in (1, 7, 30):
            with self.subTest(requested_days=days):
                db = FakeDB()
                db.store.state["plans"][1]["dias_trial"] = 0
                db.store.state["payments"] = [{"id": 900, "status": "PAGO"}]
                self.assert_unchanged_refusal(
                    db, lambda: self.trial(db, plano_id=1, dias=days),
                    409, "Trial não permitido para este plano.",
                )

    def test_allowed_plan_preserves_requested_duration_and_history(self):
        for configured_days in (1, 7, 30):
            with self.subTest(configured_days=configured_days):
                old = contract("CANCELADA")
                db = FakeDB(Store([old]))
                db.store.state["plans"][1]["dias_trial"] = configured_days
                result = self.trial(db, plano_id=1, dias=10, observacoes="Teste ficticio")
                self.assertEqual(result["status"], "TRIAL")
                self.assertEqual(result["data_fim_trial"] - result["data_inicio_trial"],
                                 timedelta(days=10))
                self.assertEqual(db.store.state["contracts"][0], old)
                self.assertEqual(db.store.state["plans"][1]["dias_trial"], configured_days)
                self.assertEqual((db.commits, db.rollbacks), (1, 0))

    def test_unknown_legacy_configuration_is_not_treated_as_explicit_zero(self):
        for value in (None, "0", False):
            with self.subTest(configuration=value):
                db = FakeDB()
                db.store.state["plans"][1]["dias_trial"] = value
                self.assertEqual(self.trial(db, plano_id=1)["status"], "TRIAL")
        db = FakeDB()  # fixture anterior sem a chave dias_trial
        self.assertNotIn("dias_trial", db.store.state["plans"][1])
        self.assertEqual(self.trial(db, plano_id=1)["status"], "TRIAL")

    def test_without_plan_keeps_existing_administrative_behavior(self):
        db = FakeDB()
        db.store.state["plans"][1]["dias_trial"] = 0
        result = self.trial(db)
        self.assertEqual(result["data_fim_trial"] - result["data_inicio_trial"],
                         timedelta(days=7))
        self.assertIsNone(db.store.state["contracts"][0]["plano_id"])

    def test_prior_trials_and_live_contracts_are_untouched_and_keep_conflict(self):
        for state in self.service.LIVE_CONTRACT_STATUSES:
            with self.subTest(existing_state=state):
                db = FakeDB(Store([contract(state)]))
                db.store.state["plans"][1]["dias_trial"] = 0
                db.store.state["payments"] = [{"id": 900, "status": "PAGO"}]
                self.assert_unchanged_refusal(
                    db, lambda: self.trial(db, plano_id=1), 409,
                    "Empresa já possui assinatura vigente; utilize o contrato existente.",
                )
                self.assertFalse(any("FROM planos_saas" in sql for sql, _ in db.executions))

    def test_zero_does_not_prevent_conversion_of_a_prior_trial(self):
        for state in ("TRIAL", "TRIAL_EXPIRADO"):
            for period in ("MENSAL", "ANUAL"):
                with self.subTest(existing_state=state, period=period):
                    old = contract(state)
                    db = FakeDB(Store([old]))
                    db.store.state["plans"][1]["dias_trial"] = 0
                    result = self.prepare(db, trial_id=old["id"], periodicidade=period)
                    self.assertEqual(result["assinatura_id"], old["id"])
                    row, = db.store.state["contracts"]
                    for key in ("id", "status", "data_inicio_trial", "data_fim_trial"):
                        self.assertEqual(row[key], old[key])
                    self.assertEqual(row["periodicidade"], period)

    def test_zero_does_not_prevent_a_paid_contract_for_either_cycle(self):
        for period in ("MENSAL", "ANUAL"):
            with self.subTest(period=period):
                db = FakeDB()
                db.store.state["plans"][1]["dias_trial"] = 0
                result = self.prepare(db, periodicidade=period)
                self.assertEqual(result["status"], "PENDENTE")
                row, = db.store.state["contracts"]
                self.assertEqual(row["periodicidade"], period)
                self.assertIsNone(row["data_inicio_trial"])
                self.assertIsNone(row["data_fim_trial"])
                self.assertEqual(db.store.state["grants"], [])

    def test_missing_or_inactive_plan_keeps_404_before_trial_policy(self):
        for identifier, active in ((999, True), (1, False)):
            with self.subTest(plan=identifier, active=active):
                db = FakeDB()
                db.store.state["plans"][1].update(ativo=active, dias_trial=0)
                self.assert_unchanged_refusal(
                    db, lambda: self.trial(db, plano_id=identifier),
                    404, "plano ativo não encontrado",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
