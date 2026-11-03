"""Flag desligada recusa rotas antes de resolver banco, tenant ou servicos."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.routes.producao import router
from app.settings import producao_v1_habilitada
from app.tenant.dependencies import get_current_tenant


@pytest.mark.parametrize("flag", [None, "false", "", "0", "1", "invalid", "true"])
def test_flag_e_bloqueio_antes_do_banco(monkeypatch, flag):
    if flag is None:
        monkeypatch.delenv("PRODUCAO_V1_ENABLED", raising=False)
    else:
        monkeypatch.setenv("PRODUCAO_V1_ENABLED", flag)
    assert producao_v1_habilitada() == (flag == "true")
    if flag == "true":
        return
    app = FastAPI()
    app.include_router(router, prefix="/producao")

    def proibido():
        pytest.fail("Flag desligada nao pode resolver banco ou tenant.")

    app.dependency_overrides[get_db] = proibido
    app.dependency_overrides[get_current_tenant] = proibido
    with TestClient(app) as client:
        for route in router.routes:
            path = "/producao" + route.path
            for parameter in ("pedido_id", "ordem_id", "peca_id"):
                path = path.replace("{" + parameter + "}", "1")
            for method in route.methods:
                response = client.request(method, path, params={"pedido_id": 1}, json={})
                assert response.status_code == 503, (method, path, response.text)
                assert "desabilitada" in response.json()["detail"]
