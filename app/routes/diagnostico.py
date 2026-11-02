import hmac
import os

from fastapi import APIRouter, Header, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from app.services.revendas_v1_up import RevendasV1UpError, run_revendas_v1_up


router = APIRouter(prefix="/diag", tags=["Diagnostico temporario"])


@router.post("/run-revendas-v1-up")
async def executar_revendas_v1_up(
    request: Request,
    diagnostic_token: str | None = Header(None, alias="X-Diagnostic-Token"),
):
    expected = os.getenv("DIAG_DB_TARGET_TOKEN")
    if not expected or not expected.strip():
        raise HTTPException(503, detail="Diagnostico temporario desabilitado.")
    if diagnostic_token is None:
        raise HTTPException(401, detail="Token de diagnostico obrigatorio.")
    if not hmac.compare_digest(diagnostic_token.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(403, detail="Token de diagnostico invalido.")
    if request.query_params or await request.body():
        raise HTTPException(400, detail="Esta rota nao aceita corpo nem parametros de consulta.")
    try:
        return await run_in_threadpool(run_revendas_v1_up)
    except RevendasV1UpError as exc:
        raise HTTPException(500, detail={"error_type": exc.error_type, "message": str(exc)}) from None
