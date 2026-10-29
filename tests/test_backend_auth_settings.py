"""Isolated startup checks, without network, credentials or database writes."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class BackendAuthSettingsTest(unittest.TestCase):
    def run_bootstrap(self, content=None, extra=None, import_main=False):
        with tempfile.TemporaryDirectory() as directory:
            local_root = Path(directory)
            if content is not None:
                (local_root / ".env").write_text(content, encoding="utf-8")
            environment = {key: value for key, value in os.environ.items() if not key.startswith(("SUPABASE_", "SMARTTEC_", "AUTH_MODE", "PYTHON_DOTENV_", "DB_", "DATABASE_URL"))}
            environment["DATABASE_URL"] = "postgresql://test_user@localhost/test_database"
            environment.update(extra or {})
            code = f"import sys; sys.path.insert(0, {str(ROOT)!r}); import app.settings as settings; settings.PROJECT_ROOT = __import__('pathlib').Path({directory!r}); "
            code += "import app.main; " if import_main else "settings.initialize_backend_configuration(); "
            code += "import os,json; print(json.dumps({name:os.getenv(name) for name in ('SMARTTEC_AUTH_MODE','SUPABASE_AUTH_ISSUER','SUPABASE_JWKS_URL')}))"
            return subprocess.run([sys.executable, "-c", code], env=environment, cwd=ROOT, capture_output=True, text=True, timeout=30)

    def test_clean_process_loads_local_env_independent_of_cwd(self):
        result=self.run_bootstrap("SMARTTEC_AUTH_MODE=authenticated\nSUPABASE_AUTH_ISSUER=https://local.test.invalid/auth/v1\nSUPABASE_JWKS_URL=https://local.test.invalid/jwks\n")
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)["SUPABASE_AUTH_ISSUER"],"https://local.test.invalid/auth/v1")

    def test_external_environment_wins(self):
        result=self.run_bootstrap("SMARTTEC_AUTH_MODE=authenticated\nSUPABASE_AUTH_ISSUER=https://local.test.invalid/auth/v1\nSUPABASE_JWKS_URL=https://local.test.invalid/jwks\n",{"SUPABASE_AUTH_ISSUER":"https://external.test.invalid/auth/v1"})
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)["SUPABASE_AUTH_ISSUER"],"https://external.test.invalid/auth/v1")

    def test_missing_required_fails_main_startup_without_values(self):
        result=self.run_bootstrap(None,{"SMARTTEC_AUTH_MODE":"authenticated","SUPABASE_AUTH_ISSUER":"https://private.test.invalid/auth/v1"},import_main=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn("SUPABASE_JWKS_URL",result.stderr)
        self.assertIn("Configuração Supabase incompleta",result.stderr)
        self.assertNotIn("private.test.invalid",result.stderr)

    def test_production_without_dotenv_starts(self):
        result=self.run_bootstrap(None,{"SMARTTEC_AUTH_MODE":"authenticated","SUPABASE_AUTH_ISSUER":"https://external.test.invalid/auth/v1","SUPABASE_JWKS_URL":"https://external.test.invalid/jwks"},import_main=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_dev_without_auth_config_is_supported(self):
        result=self.run_bootstrap(None,{"SMARTTEC_AUTH_MODE":"dev"})
        self.assertEqual(result.returncode,0,result.stderr)

    def test_invalid_mode_fails_clearly(self):
        result=self.run_bootstrap(None,{"SMARTTEC_AUTH_MODE":"invalid"},import_main=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn("SMARTTEC_AUTH_MODE inválido",result.stderr)

if __name__ == "__main__":
    unittest.main()
