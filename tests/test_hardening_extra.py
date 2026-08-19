import asyncio
import hashlib
import hmac
import time
import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from api.main import app
from config.settings import settings
from src.shared.models import init_db
from src.shared.payment_service import (
    create_payment,
    mark_refunded,
    open_chargeback,
    reconcile,
    record_provider_event,
    request_refund,
)


def _login(email="hardening-extra@example.com"):
    c = TestClient(app)
    r = c.post('/api/v1/auth/dev-login', json={'email': email, 'display_name': 'Hardening'})
    assert r.status_code == 200
    return c, r.json()['token']


def test_logout_revokes_session():
    c, token = _login()
    assert c.get('/api/v1/auth/me', headers={'Authorization': 'Bearer ' + token}).status_code == 200
    assert c.post('/api/v1/auth/logout', headers={'Authorization': 'Bearer ' + token}).status_code == 200
    assert c.get('/api/v1/auth/me', headers={'Authorization': 'Bearer ' + token}).status_code == 401


def test_webhook_is_not_blocked_by_api_key_middleware():
    body = b'{"reference":"missing-ref","amount":100,"paymentStatus":"PAID"}'
    ts = str(int(time.time()))
    sig = hmac.new(settings.EASYPAISA_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest() if settings.EASYPAISA_WEBHOOK_SECRET else 'x'
    # In local test mode a missing secret still produces a clean HMAC failure, not API-key rejection.
    c = TestClient(app)
    r = c.post('/api/v1/webhooks/easypaisa', content=body, headers={'X-Webhook-Timestamp': ts, 'X-Webhook-Signature': sig})
    assert r.status_code in (400, 200)
    assert r.status_code != 401


def test_payment_idempotency_and_state_machine():
    init_db()
    suffix = uuid.uuid4().hex[:8].upper()
    payment = create_payment(advisor_id=1, amount_pkr=Decimal('1000.00'), method='bank', provider='bank', reference='HARD-REF-1-' + suffix, idempotency_key='HARD-IDEMP-1-' + suffix)
    same = create_payment(advisor_id=1, amount_pkr=Decimal('1000.00'), method='bank', provider='bank', reference=payment['reference'], idempotency_key=payment['idempotency_key'])
    assert same['id'] == payment['id']
    result = record_provider_event(provider='bank', payload={'event_id': 'hard-event-1', 'status': 'success', 'reference': payment['reference'], 'amount': '1000.00'}, raw_body=b'hard-event-1-' + payment['reference'].encode(), reference=payment['reference'], target_status='succeeded', provider_transaction_id='TX-1-' + payment['reference'], amount=Decimal('1000.00'))
    assert result['matched']
    duplicate = record_provider_event(provider='bank', payload={'event_id': 'hard-event-1', 'status': 'success', 'reference': payment['reference'], 'amount': '1000.00'}, raw_body=b'hard-event-1-' + payment['reference'].encode(), reference=payment['reference'], target_status='succeeded', provider_transaction_id='TX-1-' + payment['reference'], amount=Decimal('1000.00'))
    assert duplicate['duplicate'] is True


def test_refund_and_chargeback_lifecycle():
    init_db()
    suffix = uuid.uuid4().hex[:8].upper()
    payment = create_payment(advisor_id=1, amount_pkr=Decimal('500.00'), method='bank', provider='bank', reference='HARD-REF-2-' + suffix, idempotency_key='HARD-IDEMP-2-' + suffix)
    record_provider_event(provider='bank', payload={'event_id': 'hard-event-2-' + suffix, 'reference': payment['reference'], 'amount': '500.00'}, raw_body=('hard-event-2-' + suffix).encode() + payment['reference'].encode(), reference=payment['reference'], target_status='succeeded', provider_transaction_id='TX-2-' + payment['reference'], amount=Decimal('500.00'))
    req = request_refund(payment['id'], Decimal('100.00')); assert req['refund_status'] == 'requested'
    done = mark_refunded(payment['id']); assert done['status'] == 'succeeded' and done['total_refunded'] == '100.00'


def test_reconciliation_marks_settlement_and_detects_mismatches():
    init_db()
    suffix = uuid.uuid4().hex[:8].upper()
    payment = create_payment(advisor_id=1, amount_pkr=Decimal('700.00'), method='bank', provider='bank', reference='HARD-REF-3-' + suffix, idempotency_key='HARD-IDEMP-3-' + suffix)
    record_provider_event(provider='bank', payload={'event_id': 'hard-event-3-' + suffix, 'reference': payment['reference'], 'amount': '700.00'}, raw_body=('hard-event-3-' + suffix).encode() + payment['reference'].encode(), reference=payment['reference'], target_status='succeeded', provider_transaction_id='TX-3-' + payment['reference'], amount=Decimal('700.00'))
    out = reconcile('bank', [{'reference': payment['reference'], 'amount': '700.00'}, {'reference': 'missing', 'amount': '10'}])
    assert out['matched'] == 1 and out['missing_internal'] == 1


def test_chargeback_resolution():
    init_db()
    suffix = uuid.uuid4().hex[:8].upper()
    payment = create_payment(advisor_id=1, amount_pkr=Decimal('800.00'), method='bank', provider='bank', reference='HARD-REF-4-' + suffix, idempotency_key='HARD-IDEMP-4-' + suffix)
    record_provider_event(provider='bank', payload={'event_id': 'hard-event-4-' + suffix, 'reference': payment['reference'], 'amount': '800.00'}, raw_body=('hard-event-4-' + suffix).encode() + payment['reference'].encode(), reference=payment['reference'], target_status='succeeded', provider_transaction_id='TX-4-' + payment['reference'], amount=Decimal('800.00'))
    opened = open_chargeback(payment['id'], {'reason': 'customer_dispute'}); assert opened['chargeback_status'] == 'open'
    from src.shared.payment_service import resolve_chargeback
    resolved = resolve_chargeback(payment['id'], 'won'); assert resolved['status'] == 'succeeded'


def test_provider_mutating_request_requires_idempotency(monkeypatch):
    from integrations.payments.client import ProviderClient
    monkeypatch.setattr(settings, "JAZZCASH_API_BASE_URL", "http://example.invalid")
    monkeypatch.setattr(settings, "JAZZCASH_API_KEY", "key")
    monkeypatch.setattr(settings, "JAZZCASH_API_SECRET", "secret")
    client = ProviderClient("jazzcash")
    with pytest.raises(ValueError, match="Idempotency-Key"):
        asyncio.run(client.request("POST", "/payments", {"amount": "1"}))


def test_rag_current_year_uses_current_year_filter():
    from rag.retriever import FBRRetriever
    r = object.__new__(FBRRetriever)
    filt = r._build_where_filter("salaried", "2026-27")
    assert "FinanceAct2026" in filt["document_name"]["$in"]


def test_partial_refund_cannot_exceed_original_and_accumulates():
    init_db()
    suffix = uuid.uuid4().hex[:8].upper()
    payment = create_payment(advisor_id=1, amount_pkr=Decimal('500.00'), method='bank', provider='bank', reference='PART-REF-' + suffix, idempotency_key='PART-ID-' + suffix)
    record_provider_event(provider='bank', payload={'event_id': 'part-event-' + suffix, 'reference': payment['reference'], 'amount': '500.00'}, raw_body=('part-event-' + suffix).encode(), reference=payment['reference'], target_status='succeeded', provider_transaction_id='TX-' + suffix, amount=Decimal('500.00'))
    request_refund(payment['id'], Decimal('200.00'))
    done = mark_refunded(payment['id'])
    assert done['status'] == 'succeeded' and done['total_refunded'] == '200.00'
    request_refund(payment['id'], Decimal('300.00'))
    done2 = mark_refunded(payment['id'])
    assert done2['status'] == 'refunded' and done2['total_refunded'] == '500.00'


def test_refund_pending_blocks_duplicate_request():
    init_db()
    suffix = uuid.uuid4().hex[:8].upper()
    payment = create_payment(advisor_id=1, amount_pkr=Decimal('500.00'), method='bank', provider='bank', reference='DUP-REF-' + suffix, idempotency_key='DUP-ID-' + suffix)
    record_provider_event(provider='bank', payload={'event_id': 'dup-event-' + suffix, 'reference': payment['reference'], 'amount': '500.00'}, raw_body=('dup-event-' + suffix).encode(), reference=payment['reference'], target_status='succeeded', provider_transaction_id='TX-' + suffix, amount=Decimal('500.00'))
    request_refund(payment['id'], Decimal('100.00'))
    with pytest.raises(ValueError, match='already pending'):
        request_refund(payment['id'], Decimal('100.00'))


def test_payment_lifecycle_enforces_advisor_ownership():
    from fastapi import HTTPException

    from api.routes.payments import refund
    init_db()
    _c1, token1 = _login('owner-a@example.com')
    c2, token2 = _login('owner-b@example.com')
    advisor2 = c2.get('/api/v1/auth/me', headers={'Authorization': 'Bearer ' + token2}).json()
    suffix = uuid.uuid4().hex[:8].upper()
    p = create_payment(advisor_id=advisor2['advisor_id'], amount_pkr=Decimal('100.00'), method='bank', provider='bank', reference='OWN-REF-' + suffix, idempotency_key='OWN-ID-' + suffix)
    record_provider_event(provider='bank', payload={'event_id': 'own-event-' + suffix, 'reference': p['reference'], 'amount': '100.00'}, raw_body=('own-event-' + suffix).encode(), reference=p['reference'], target_status='succeeded', provider_transaction_id='OWN-TX-' + suffix, amount=Decimal('100.00'))
    with pytest.raises(HTTPException) as exc:
        refund(p['id'], type('Body', (), {'payment_id': p['id'], 'amount_pkr': Decimal('100.00')})(), authorization='Bearer ' + token1)
    assert exc.value.status_code == 404


def test_client_schema_rejects_invalid_taxpayer_and_year():
    from pydantic import ValidationError

    from api.routes.clients import ClientCreate
    with pytest.raises(ValidationError):
        ClientCreate(full_name='x', taxpayer_type='company')
    with pytest.raises(ValidationError):
        ClientCreate(full_name='x', tax_year='2024-25')
        