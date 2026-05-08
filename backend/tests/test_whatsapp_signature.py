import hashlib
import hmac

import pytest

from app.integrations.whatsapp import verify_signature


def test_verify_signature_accepts_correctly_signed_payload() -> None:
    secret = "test-secret"
    body = b'{"a": 1}'
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_signature(body=body, signature_header=sig, app_secret=secret) is True


def test_verify_signature_rejects_tampered_payload() -> None:
    secret = "test-secret"
    body = b'{"a": 1}'
    sig = "sha256=" + hmac.new(secret.encode(), b'{"a":2}', hashlib.sha256).hexdigest()
    assert verify_signature(body=body, signature_header=sig, app_secret=secret) is False


def test_verify_signature_rejects_missing_or_malformed_header() -> None:
    assert verify_signature(body=b"", signature_header=None, app_secret="x") is False
    assert verify_signature(body=b"", signature_header="not-a-valid-sig", app_secret="x") is False
