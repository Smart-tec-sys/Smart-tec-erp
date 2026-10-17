"""Wix webhook diagnostics only: no database or provisioning dependencies."""
import hashlib
import json
import logging
import os
from uuid import UUID

import jwt
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/webhooks/wix", tags=["Webhooks Wix"])
logger = logging.getLogger("uvicorn.error.wix_webhooks")
EVENT_TYPE = "wix.pricing_plans.v2.order_purchased"
MAX_BODY_BYTES = 256 * 1024

# Reference only. These limits are NOT applied by this endpoint.
PLAN_MAPPING = {
    "1c973b08-47e1-4dcd-ab73-8cc4a8831fea": ("Smart-tec Visita Connect", 2),
    "57fe070c-5e20-41a6-b118-6b32773fecf9": ("Smart-tec ERP Essencial", 2),
    "6fec4ea9-a428-4507-be8c-516b3cbda075": ("Smart-tec ERP Profissional", 3),
    "6522d0b2-63bd-43f9-bb40-cb95154cc2f2": ("Smart-tec Prime Connect", 4),
}
ORDER_STATUSES = {"UNDEFINED", "DRAFT", "PENDING", "ACTIVE", "PAUSED", "ENDED", "CANCELED"}
PAYMENT_STATUSES = {"UNDEFINED", "PAID", "REFUNDED", "FAILED", "UNPAID", "PENDING", "NOT_APPLICABLE"}


def object_value(value):
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict):
        raise ValueError("Expected object")
    return value


def identifier(value, required=False):
    if value is None and not required:
        return None
    if not isinstance(value, str):
        raise ValueError("Invalid identifier")
    return str(UUID(value))


def fingerprint(value):
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest() if value else None


def valid_instance_id(value):
    # The REST contract supplies a string. Validate without rewriting its value.
    return (
        isinstance(value, str)
        and value != ""
        and not any(
            character.isspace() or ord(character) < 32 or 127 <= ord(character) <= 159
            for character in value
        )
    )


def require_allowed_instance(envelope):
    allowed = os.getenv("WIX_ALLOWED_INSTANCE_ID")
    if not valid_instance_id(allowed):
        logger.error("wix_webhook_instance_configuration_invalid")
        raise HTTPException(status_code=503, detail="Webhook Wix não configurado")

    instance_id = envelope.get("instanceId")
    if not valid_instance_id(instance_id):
        raise ValueError("Invalid installation identifier")
    if instance_id != allowed:
        logger.warning("wix_webhook_instance_not_allowed")
        raise HTTPException(status_code=403, detail="Instalação Wix não autorizada")


def diagnostic_fields(claims):
    envelope = object_value(claims["data"])
    # claims reaches this function only after RS256 verification.
    require_allowed_instance(envelope)
    if envelope.get("eventType") != EVENT_TYPE:
        raise HTTPException(status_code=403, detail="Evento Wix não autorizado")
    event = object_value(envelope["data"])
    if event.get("entityFqdn") != "wix.pricing_plans.v2.order" or event.get("slug") != "purchased":
        raise ValueError("Inconsistent event")
    order = object_value(object_value(object_value(event["actionEvent"])["body"])["order"])
    buyer = object_value(order.get("buyer", {}))
    # Wix event IDs are opaque strings: preserve the exact idempotency key.
    event_id = event.get("id")
    if not isinstance(event_id, str) or event_id == "":
        raise ValueError("Invalid event identifier")
    order_id = identifier(order.get("id"), required=True)
    if identifier(event.get("entityId"), required=True) != order_id:
        raise ValueError("Inconsistent order")
    plan_id = identifier(order.get("planId"), required=True)
    plan_name = order.get("planName")
    if plan_name is not None and (not isinstance(plan_name, str) or len(plan_name) > 512):
        raise ValueError("Invalid plan name")
    status = order.get("status")
    payment = order.get("lastPaymentStatus")
    if status is not None and (not isinstance(status, str) or status not in ORDER_STATUSES):
        raise ValueError("Invalid status")
    if payment is not None and (not isinstance(payment, str) or payment not in PAYMENT_STATUSES):
        raise ValueError("Invalid payment status")
    known_name = PLAN_MAPPING.get(plan_id, (None, None))[0]
    return {
        "event_id": event_id,
        "event_type": EVENT_TYPE,
        "order_id": order_id,
        "planId": plan_id,
        "planName": plan_name if plan_name == known_name else None,
        "planName_fingerprint": fingerprint(plan_name) if plan_name != known_name else None,
        "buyer.memberId_fingerprint": fingerprint(identifier(buyer.get("memberId"))),
        "buyer.contactId_fingerprint": fingerprint(identifier(buyer.get("contactId"))),
        "status": status,
        "lastPaymentStatus": payment,
        "subscriptionId": identifier(order.get("subscriptionId")),
    }


@router.post("/pricing-plans")
async def pricing_plans_webhook(request: Request):
    # Preserve the raw JWT bytes; never parse or reserialize the request as JSON.
    raw_body = bytearray()
    async for chunk in request.stream():
        raw_body.extend(chunk)
        if len(raw_body) > MAX_BODY_BYTES:
            raise HTTPException(status_code=413, detail="Payload Wix excede o limite")
    if not raw_body:
        raise HTTPException(status_code=400, detail="Payload Wix inválido")

    pem = os.getenv("WIX_WEBHOOK_PUBLIC_KEY", "").replace("\\n", "\n").strip()
    try:
        public_key = load_pem_public_key(pem.encode("ascii"))
        if not isinstance(public_key, RSAPublicKey):
            raise ValueError("Expected RSA public key")
    except (ValueError, TypeError, UnicodeError):
        logger.error("wix_webhook_configuration_invalid")
        raise HTTPException(status_code=503, detail="Webhook Wix não configurado") from None

    try:
        claims = jwt.decode(
            bytes(raw_body), public_key, algorithms=["RS256"],
            options={"require": ["data"], "verify_aud": False},
        )
    except jwt.InvalidTokenError:
        logger.warning("wix_webhook_signature_or_token_invalid")
        raise HTTPException(status_code=401, detail="Token Wix inválido") from None

    try:
        fields = diagnostic_fields(claims)
    except HTTPException:
        raise
    except (ValueError, TypeError, KeyError, RecursionError):
        logger.warning("wix_webhook_payload_invalid")
        raise HTTPException(status_code=400, detail="Payload Wix inválido") from None

    # ETAPA 2: persist an atomic unique event_id receipt BEFORE business effects.
    # No persistence/cache/deduplication now: retries produce the same event_id log.
    # Do not mark events processed in memory or pretend duplicates are suppressed.
    logger.info("wix_pricing_plans_received %s", json.dumps(fields, ensure_ascii=True, sort_keys=True))
    return {"status": "received"}
