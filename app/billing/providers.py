"""Payment provider adapter.

Two implementations share one webhook-signature scheme (Stripe's
documented `Stripe-Signature: t=<unix>,v1=<hex hmac-sha256("t.payload")>`):

- TestPaymentProvider: local test mode. Checkout returns an in-app URL
  clearly marked TEST MODE; completing it produces a *signed* event that
  goes through exactly the same verification and processing path a real
  webhook does. No money moves.
- StripePaymentProvider: creates Checkout Sessions via Stripe's REST API.
  It is implemented but has NOT been exercised against Stripe (no
  credentials supplied); see docs/BILLING_AND_PLANS.md for enablement.

Subscription state only ever changes in response to a verified event,
never because a user clicked "upgrade".
"""

import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request
import uuid

SIGNATURE_TOLERANCE_SECONDS = 300  # replay protection window


class BillingConfigError(Exception):
    pass


class SignatureError(Exception):
    pass


def sign_payload(payload: bytes, secret: str, timestamp: int | None = None) -> str:
    ts = int(timestamp if timestamp is not None else time.time())
    digest = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"


def verify_signature(payload: bytes, header: str | None, secret: str, now: float | None = None) -> None:
    if not secret:
        raise SignatureError("Webhook secret is not configured.")
    if not header:
        raise SignatureError("Missing signature header.")
    parts = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
    try:
        ts = int(parts.get("t", ""))
    except ValueError:
        raise SignatureError("Malformed signature timestamp.")
    if abs((now or time.time()) - ts) > SIGNATURE_TOLERANCE_SECONDS:
        raise SignatureError("Signature timestamp outside tolerance (possible replay).")
    expected = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    candidates = [v for k, v in (p.split("=", 1) for p in header.split(",") if "=" in p) if k == "v1"]
    if not any(hmac.compare_digest(expected, c) for c in candidates):
        raise SignatureError("Signature mismatch.")


class PaymentProvider:
    name = "none"
    is_test = False

    def __init__(self, webhook_secret: str):
        self.webhook_secret = webhook_secret

    def create_checkout(self, organization_id: str, plan_code: str, price_ref: str | None,
                        success_url: str, cancel_url: str) -> dict:
        raise BillingConfigError("No payment provider is configured.")

    def parse_webhook(self, payload: bytes, signature_header: str | None) -> dict:
        verify_signature(payload, signature_header, self.webhook_secret)
        return json.loads(payload)


class TestPaymentProvider(PaymentProvider):
    name = "test"
    is_test = True

    def create_checkout(self, organization_id, plan_code, price_ref, success_url, cancel_url):
        session_id = f"cs_test_{uuid.uuid4().hex[:24]}"
        return {"session_id": session_id, "mode": "test",
                "url": f"/app/billing/test-checkout?session={session_id}&plan={plan_code}"}

    def build_event(self, event_type: str, data: dict) -> tuple[bytes, str]:
        body = json.dumps({"id": f"evt_test_{uuid.uuid4().hex[:24]}", "type": event_type,
                           "livemode": False, "created": int(time.time()), "data": {"object": data}}).encode()
        return body, sign_payload(body, self.webhook_secret)


class StripePaymentProvider(PaymentProvider):
    name = "stripe"

    def __init__(self, webhook_secret: str, secret_key: str):
        super().__init__(webhook_secret)
        self.secret_key = secret_key

    def create_checkout(self, organization_id, plan_code, price_ref, success_url, cancel_url):
        if not self.secret_key:
            raise BillingConfigError("STRIPE_SECRET_KEY is not set.")
        if not price_ref:
            raise BillingConfigError(f"No Stripe price is configured for plan '{plan_code}'.")
        form = urllib.parse.urlencode({
            "mode": "subscription",
            "line_items[0][price]": price_ref,
            "line_items[0][quantity]": "1",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "client_reference_id": organization_id,
            "metadata[organization_id]": organization_id,
            "metadata[plan_code]": plan_code,
            "subscription_data[metadata][organization_id]": organization_id,
            "subscription_data[metadata][plan_code]": plan_code,
        }).encode()
        req = urllib.request.Request("https://api.stripe.com/v1/checkout/sessions", data=form,
                                     headers={"Authorization": f"Bearer {self.secret_key}"})
        with urllib.request.urlopen(req, timeout=15) as resp:  # fixed host; not user-controlled
            data = json.loads(resp.read())
        return {"session_id": data["id"], "mode": "live" if data.get("livemode") else "stripe_test",
                "url": data["url"]}


def get_payment_provider(config) -> PaymentProvider:
    name = (config.get("BILLING_PROVIDER") or "test").lower()
    secret = config.get("BILLING_WEBHOOK_SECRET") or ""
    if name == "stripe":
        return StripePaymentProvider(secret, config.get("STRIPE_SECRET_KEY") or "")
    if name == "test":
        return TestPaymentProvider(secret)
    return PaymentProvider(secret)
