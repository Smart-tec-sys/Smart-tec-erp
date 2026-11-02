import os
import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.parse import urlencode

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@127.0.0.1:1/test")

from fastapi import FastAPI

from app.routes import diagnostico
from app.services import revendas_v1_up as service


class ASGIClient:
    def __init__(self, app):
        self.app = app

    def post(self, path, headers=None, **kwargs):
        body = json.dumps(kwargs["json"]).encode() if "json" in kwargs else kwargs.get("content", "").encode()
        scope = {
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": "POST", "scheme": "http", "path": path, "raw_path": path.encode(),
            "query_string": urlencode(kwargs.get("params", {})).encode(),
            "headers": [(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()],
            "client": ("test", 1), "server": ("test", 80), "root_path": "",
        }
        messages = []

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            messages.append(message)

        asyncio.run(self.app(scope, receive, send))
        status = next(message["status"] for message in messages if message["type"] == "http.response.start")
        text = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body").decode()
        return SimpleNamespace(status_code=status, text=text, json=lambda: json.loads(text))


def columns():
    return [(name, *definition) for name, definition in service.COLUMNS.items()]


class FakeCursor:
    def __init__(self, database=service.DATABASE, table="parceiros_comerciais",
                 before=None, after=None, counts=(4, 4, 4), fail=None):
        self.database = database
        self.table = table
        self.before = [] if before is None else before
        self.after = columns() if after is None else after
        self.counts = iter(counts)
        self.fail = fail
        self.queries = []
        self.commits = 0
        self.catalogs = 0
        self.current = ""
        self.closed = False

    def execute(self, sql):
        self.queries.append(sql)
        self.current = sql
        if self.fail and self.fail(sql):
            raise RuntimeError("postgresql://user:SECRET@host/db TOKEN_SECRET")
        if sql == "COMMIT;":
            self.commits += 1

    def fetchone(self):
        if self.current.startswith("SELECT current_database()"):
            return self.database, self.table
        if self.current.startswith("SELECT count(*)"):
            return (next(self.counts),)
        raise AssertionError("Unexpected SQL")

    def fetchall(self):
        self.catalogs += 1
        return self.before if self.catalogs == 1 else self.after

    def close(self):
        self.closed = True


class ExecutorTests(unittest.TestCase):
    def run_fake(self, cursor):
        driver = Mock()
        driver.autocommit = False
        driver.cursor.return_value = cursor
        connection = Mock(driver_connection=driver)
        with patch.object(service.engine, "raw_connection", return_value=connection):
            result = service.run_revendas_v1_up()
        self.assertFalse(driver.autocommit)
        connection.close.assert_called_once()
        return result

    def test_success_validates_every_column_constraints_index_and_count(self):
        cursor = FakeCursor()
        result = self.run_fake(cursor)
        self.assertEqual(result, {
            "ok": True, "database": "smarttec_erp_staging",
            "message": "REVENDAS V1 aplicada com sucesso", "columns_validated": 21,
        })
        self.assertEqual(cursor.commits, 2)
        self.assertIn("BEGIN READ ONLY;", cursor.queries)
        self.assertTrue(any(query.startswith("DO $validate_constraints$") for query in cursor.queries))
        self.assertTrue(any(query.startswith("DO $validate_index$") for query in cursor.queries))
        self.assertTrue(cursor.closed)

    def test_compatible_existing_columns_are_allowed(self):
        self.run_fake(FakeCursor(before=columns()))

    def test_bad_database_and_missing_table_abort_before_begin(self):
        for values in ({"database": "production"}, {"table": None}):
            with self.subTest(values=values):
                cursor = FakeCursor(**values)
                with self.assertRaises(service.RevendasV1UpError):
                    self.run_fake(cursor)
                self.assertNotIn("BEGIN;", cursor.queries)
                self.assertEqual(cursor.commits, 0)

    def test_incompatible_column_aborts_before_ddl(self):
        cursor = FakeCursor(before=[("limite_credito", "numeric(14,2)", False, "0")])
        with self.assertRaisesRegex(service.RevendasV1UpError, "incompativel"):
            self.run_fake(cursor)
        self.assertFalse(any("ADD COLUMN" in sql for sql in cursor.queries))
        self.assertIn("ROLLBACK;", cursor.queries)

    def test_missing_file_and_tampered_file_do_not_connect(self):
        with patch.object(service.engine, "raw_connection") as connect:
            for error in (FileNotFoundError(), UnicodeError()):
                with patch.object(service.MIGRATION_PATH.__class__, "read_text", side_effect=error):
                    with self.assertRaises(service.RevendasV1UpError):
                        service.run_revendas_v1_up()
            with patch.object(service.MIGRATION_PATH.__class__, "read_text", return_value="BEGIN; DROP TABLE x; COMMIT;"):
                with self.assertRaisesRegex(service.RevendasV1UpError, "SHA-256"):
                    service.run_revendas_v1_up()
            connect.assert_not_called()

    def test_windows_line_endings_are_hash_compatible(self):
        original = service.MIGRATION_PATH.read_text(encoding="utf-8")
        with patch.object(service.MIGRATION_PATH.__class__, "read_text", return_value=original.replace("\n", "\r\n")):
            self.assertEqual(len(service._read_migration()[1]), 3)

    def test_execution_error_rolls_back_and_sanitizes(self):
        cursor = FakeCursor(fail=lambda sql: "ADD COLUMN" in sql)
        with self.assertRaises(service.RevendasV1UpError) as caught:
            self.run_fake(cursor)
        self.assertEqual(caught.exception.error_type, "RuntimeError")
        self.assertNotIn("SECRET", str(caught.exception))
        self.assertEqual(cursor.commits, 0)
        self.assertIn("ROLLBACK;", cursor.queries)

    def test_precommit_count_change_rolls_back(self):
        cursor = FakeCursor(counts=(4, 5))
        with self.assertRaisesRegex(service.RevendasV1UpError, "antes"):
            self.run_fake(cursor)
        self.assertEqual(cursor.commits, 0)
        self.assertIn("ROLLBACK;", cursor.queries)

    def test_commit_error_is_not_reported_as_success(self):
        cursor = FakeCursor(fail=lambda sql: sql == "COMMIT;")
        with self.assertRaises(service.RevendasV1UpError) as caught:
            self.run_fake(cursor)
        self.assertNotIn("SECRET", str(caught.exception))
        self.assertNotIn("BEGIN READ ONLY;", cursor.queries)

    def test_connection_cleanup_error_invalidates_and_reports_committed_state(self):
        cursor = FakeCursor()
        driver = Mock()
        driver.autocommit = False
        driver.cursor.return_value = cursor
        connection = Mock(driver_connection=driver)
        connection.close.side_effect = RuntimeError("SECRET")
        with patch.object(service.engine, "raw_connection", return_value=connection):
            with self.assertRaisesRegex(service.RevendasV1UpError, "COMMITADA") as caught:
                service.run_revendas_v1_up()
        self.assertNotIn("SECRET", str(caught.exception))
        connection.invalidate.assert_called_once()

    def test_postcommit_divergences_are_explicit_and_do_not_undo_up(self):
        cases = [
            {"after": columns()[:-1]},
            {"counts": (4, 4, 5)},
            {"fail": lambda sql: sql.startswith("DO $validate_constraints$")},
            {"fail": lambda sql: sql.startswith("DO $validate_index$")},
        ]
        for case in cases:
            with self.subTest(case=case):
                cursor = FakeCursor(**case)
                with self.assertRaisesRegex(service.RevendasV1UpError, "COMMITADA"):
                    self.run_fake(cursor)
                self.assertEqual(cursor.commits, 1)
                index = cursor.queries.index("COMMIT;")
                self.assertIn("BEGIN READ ONLY;", cursor.queries[index + 1:])
                self.assertEqual(cursor.queries[-1], "ROLLBACK;")


class RouteTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(diagnostico.router)
        self.client = ASGIClient(app)
        self.env = patch.dict(os.environ, {"DIAG_DB_TARGET_TOKEN": "TEST_ONLY"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.runner = patch.object(diagnostico, "run_revendas_v1_up")
        self.execute = self.runner.start()
        self.addCleanup(self.runner.stop)
        self.headers = {"X-Diagnostic-Token": "TEST_ONLY"}
        self.path = "/diag/run-revendas-v1-up"

    def test_missing_invalid_and_disabled_token_never_execute(self):
        self.assertEqual(self.client.post(self.path).status_code, 401)
        self.assertEqual(self.client.post(self.path, headers={"X-Diagnostic-Token": "INVALID"}).status_code, 403)
        with patch.dict(os.environ, {"DIAG_DB_TARGET_TOKEN": ""}):
            self.assertEqual(self.client.post(self.path, headers=self.headers).status_code, 503)
        self.execute.assert_not_called()

    def test_rejects_any_body_or_query(self):
        for kwargs in ({"json": {}}, {"json": {"sql": "COMMIT"}}, {"content": " "}, {"params": {"file": "up.sql"}}):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(self.client.post(self.path, headers=self.headers, **kwargs).status_code, 400)
        self.execute.assert_not_called()

    def test_success_route(self):
        self.execute.return_value = {"ok": True, "database": service.DATABASE, "message": "REVENDAS V1 aplicada com sucesso", "columns_validated": 21}
        response = self.client.post(self.path, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), self.execute.return_value)
        self.execute.assert_called_once_with()

    def test_safe_service_error(self):
        self.execute.side_effect = service.RevendasV1UpError("Falha sanitizada.", "RuntimeError")
        response = self.client.post(self.path, headers=self.headers)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"]["error_type"], "RuntimeError")
        self.assertNotIn("TEST_ONLY", response.text)


if __name__ == "__main__":
    unittest.main()
