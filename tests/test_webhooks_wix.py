"""Isolated ASGI tests: no main application, database, network or persistent files."""
import asyncio
import json
import time
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi import FastAPI

from app.routes.webhooks_wix import EVENT_TYPE, PLAN_MAPPING, router

EVENT_ID = "1ca4c4b1-80f6-4436-8bc5-cc6420f75b19"
ORDER_ID = "5f99efdb-5d56-d8c1-9d6c-298230054c63"
MEMBER_ID = "6bb98a18-dc53-4236-ad88-e4ab6b8de60d"


@pytest.fixture
def keys(monkeypatch):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode()
    monkeypatch.setenv("WIX_WEBHOOK_PUBLIC_KEY", pem)
    return private


@pytest.fixture
def envelope():
    plan_id = next(iter(PLAN_MAPPING))
    return {
        "eventType": EVENT_TYPE, "instanceId": "test-instance",
        "data": json.dumps({
            "id": EVENT_ID, "entityId": ORDER_ID,
            "entityFqdn": "wix.pricing_plans.v2.order", "slug": "purchased",
            "actionEvent": {"body": {"order": {
                "id": ORDER_ID, "planId": plan_id, "planName": PLAN_MAPPING[plan_id][0],
                "buyer": {"memberId": MEMBER_ID, "contactId": MEMBER_ID,
                          "email": "private@example.invalid"},
                "status": "ACTIVE", "lastPaymentStatus": "UNPAID",
                "subscriptionId": "558aad5d-3529-4a89-be79-14e77d15e3c7",
                "formData": {"secret": "private-form-data"},
            }}},
        }),
    }


def token(key, event, **claims):
    now = int(time.time())
    payload = {"data": json.dumps(event), "iat": now - 1, "exp": now + 300}
    payload.update(claims)
    return jwt.encode(payload, key, algorithm="RS256")


def post(body):
    app = FastAPI()
    app.include_router(router)
    if isinstance(body, str):
        body = body.encode()
    async def run():
        messages = []
        delivered = False
        async def receive():
            nonlocal delivered
            if delivered:
                return {"type": "http.disconnect"}
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}
        async def send(message):
            messages.append(message)
        await app({
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": "POST", "scheme": "http", "path": "/webhooks/wix/pricing-plans",
            "raw_path": b"/webhooks/wix/pricing-plans", "query_string": b"",
            "root_path": "", "headers": [(b"content-type", b"text/plain")],
            "client": ("127.0.0.1", 1), "server": ("test", 80),
        }, receive, send)
        status = next(m["status"] for m in messages if m["type"] == "http.response.start")
        data = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
        return status, json.loads(data)
    return asyncio.run(run())


def test_valid_signature_response_and_private_logging(keys, envelope, caplog):
    signed = token(keys, envelope)
    with caplog.at_level("INFO", logger="uvicorn.error.wix_webhooks"):
        status, body = post(signed)
    assert status == 200 and body == {"status": "received"}
    assert EVENT_ID in caplog.text and ORDER_ID in caplog.text
    assert "UNPAID" in caplog.text  # Receipt remains valid without confirming payment.
    for private in [signed, MEMBER_ID, "private@example.invalid", "private-form-data"]:
        assert private not in caplog.text
    assert "buyer.memberId_fingerprint" in caplog.text


def test_wrong_signature(keys, envelope):
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    assert post(token(other, envelope))[0] == 401


@pytest.mark.parametrize("raw", [b"", b"not-a-token", b'{"data":"jwt"}'])
def test_invalid_raw_body(keys, raw):
    assert post(raw)[0] in {400, 401}


@pytest.mark.parametrize("claims", [{"data": "invalid-json"}, {"data": "[]"}, {"data": None}])
def test_signed_invalid_payload(keys, envelope, claims):
    assert post(token(keys, envelope, **claims))[0] == (401 if claims["data"] is None else 400)


def test_unexpected_event(keys, envelope):
    envelope["eventType"] = "wix.pricing_plans.v2.order_canceled"
    assert post(token(keys, envelope))[0] == 403


def test_expired_token(keys, envelope):
    assert post(token(keys, envelope, exp=int(time.time()) - 60))[0] == 401


def test_algorithm_is_fixed(keys, envelope):
    signed = jwt.encode({"data": json.dumps(envelope)}, "untrusted-secret" * 3, algorithm="HS256")
    assert post(signed)[0] == 401


@pytest.mark.parametrize("key_value", ["", "invalid", "-----BEGIN PUBLIC KEY-----\\ninvalid"])
def test_unconfigured_key(monkeypatch, key_value):
    monkeypatch.setenv("WIX_WEBHOOK_PUBLIC_KEY", key_value)
    assert post("opaque.jwt.body")[0] == 503


def test_oversize_body(keys):
    assert post(b"x" * (256 * 1024 + 1))[0] == 413


def test_retry_identified_without_persistence(keys, envelope, caplog):
    signed = token(keys, envelope)
    with caplog.at_level("INFO", logger="uvicorn.error.wix_webhooks"):
        assert post(signed)[0] == 200
        assert post(signed)[0] == 200
    assert caplog.text.count(EVENT_ID) == 2


@pytest.mark.parametrize("mutation", ["missing_id", "wrong_order", "wrong_entity", "missing_order"])
def test_malformed_event(keys, envelope, mutation):
    event = json.loads(envelope["data"])
    if mutation == "missing_id":
        event.pop("id")
    elif mutation == "wrong_order":
        event["entityId"] = EVENT_ID
    elif mutation == "wrong_entity":
        event["entityFqdn"] = "wix.ecom.v1.order"
    else:
        event["actionEvent"]["body"].pop("order")
    envelope["data"] = json.dumps(event)
    assert post(token(keys, envelope))[0] == 400


def test_unknown_plan_name_is_hidden(keys, envelope, caplog):
    event = json.loads(envelope["data"])
    event["actionEvent"]["body"]["order"]["planName"] = "private-name@example.invalid\\nforged-log"
    envelope["data"] = json.dumps(event)
    with caplog.at_level("INFO", logger="uvicorn.error.wix_webhooks"):
        assert post(token(keys, envelope))[0] == 200
    assert "private-name" not in caplog.text and "forged-log" not in caplog.text
    assert "planName_fingerprint" in caplog.text


def test_escaped_pem_environment(keys, envelope, monkeypatch):
    pem = keys.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode()
    monkeypatch.setenv("WIX_WEBHOOK_PUBLIC_KEY", pem.replace("\n", "\\n"))
    assert post(token(keys, envelope))[0] == 200


def test_router_registered_in_main_without_loading_database():
    source = (Path(__file__).resolve().parents[1] / "app" / "main.py").read_text(encoding="utf-8")
    assert "from app.routes.webhooks_wix import router as router_webhooks_wix" in source
    assert "app.include_router(router_webhooks_wix)" in source


@pytest.mark.parametrize("event_id", ['1ca4c4b1-80f6-4436-8bc5-cc6420f75b19', '1CA4C4B1-80F6-4436-8BC5-CC6420F75B19', 'event-diagnostic-001', '  Event-With-Spaces  ', ' ', 'Evento-\xe7\r\nforged-log\t'])

def test_event_id_is_preserved_exactly(keys, envelope, caplog, event_id):
    event = json.loads(envelope["data"])
    event["id"] = event_id
    envelope["data"] = json.dumps(event)
    with caplog.at_level("INFO", logger="uvicorn.error.wix_webhooks"):
        status, body = post(token(keys, envelope))
    assert status == 200 and body == {"status": "received"}
    messages = [
        record.getMessage() for record in caplog.records
        if record.name == "uvicorn.error.wix_webhooks"
        and record.getMessage().startswith("wix_pricing_plans_received ")
    ]
    assert len(messages) == 1
    # JSON escaping protects the log while preserving the original identifier.
    assert chr(13) not in messages[0] and chr(10) not in messages[0]
    fields = json.loads(messages[0].split(" ", 1)[1])
    assert fields["event_id"] == event_id


@pytest.mark.parametrize("event_id", ["", None, 42, False, [], {}, 1.25])
def test_empty_or_non_string_event_id_is_rejected(keys, envelope, event_id):
    event = json.loads(envelope["data"])
    event["id"] = event_id
    envelope["data"] = json.dumps(event)
    assert post(token(keys, envelope))[0] == 400


def test_missing_event_id_is_rejected(keys, envelope):
    event = json.loads(envelope["data"])
    del event["id"]
    envelope["data"] = json.dumps(event)
    assert post(token(keys, envelope))[0] == 400
