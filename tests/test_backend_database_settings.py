"""Database settings tests without connections or real credentials."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from sqlalchemy.engine import make_url
from app.settings import get_database_url

class BackendDatabaseSettingsTest(unittest.TestCase):
    def setUp(self):
        self.original_environment = dict(os.environ)
        self.env=patch.dict(os.environ,{},clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        os.environ.update(DB_HOST="localhost",DB_PORT="5432",DB_NAME="test_database",DB_USER="test_user")

    def test_database_url_has_priority(self):
        os.environ["DATABASE_URL"]="postgresql://external_user@external.test.invalid/external_database"
        os.environ.pop("DB_HOST")
        self.assertEqual(get_database_url(),os.environ["DATABASE_URL"])

    def test_complete_db_fields_build_correct_url(self):
        url=make_url(get_database_url())
        self.assertEqual((url.host,url.port,url.database,url.username),("localhost",5432,"test_database","test_user"))

    def test_password_is_optional(self):
        self.assertIsNone(make_url(get_database_url()).password)

    def test_password_special_characters_preserved(self):
        os.environ["DB_PASSWORD"]="test-only@:/#"
        self.assertEqual(make_url(get_database_url()).password,"test-only@:/#")

    def test_each_required_field_is_validated(self):
        for name in ("DB_HOST","DB_PORT","DB_NAME","DB_USER"):
            with self.subTest(name=name):
                value=os.environ.pop(name)
                with self.assertRaisesRegex(RuntimeError,name): get_database_url()
                os.environ[name]=value

    def test_invalid_port_error_has_no_value(self):
        os.environ["DB_PORT"]="private-invalid-value"
        with self.assertRaises(RuntimeError) as caught: get_database_url()
        self.assertIn("DB_PORT",str(caught.exception))
        self.assertNotIn("private-invalid-value",str(caught.exception))

    def test_main_startup_fails_without_database_settings(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            env={key:value for key,value in self.original_environment.items() if not key.startswith(("DB_","DATABASE_URL","SUPABASE_","SMARTTEC_"))}
            env["PYTHONIOENCODING"]="utf-8"
            env["SMARTTEC_AUTH_MODE"]="dev"
            code=f"import app.settings as s; s.PROJECT_ROOT=__import__('pathlib').Path({directory!r}); import app.main"
            result=subprocess.run([sys.executable,"-c",code],cwd=root,env=env,capture_output=True,text=True,encoding="utf-8",timeout=30)
            self.assertNotEqual(result.returncode,0)
            self.assertIn("Configuração do banco incompleta",result.stderr)
            for name in ("DB_HOST","DB_PORT","DB_NAME","DB_USER"): self.assertIn(name,result.stderr)

if __name__ == "__main__": unittest.main()
