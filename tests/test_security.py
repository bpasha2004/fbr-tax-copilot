import hashlib,hmac,time,json
from unittest.mock import patch
from fastapi.testclient import TestClient
from api.main import app
from api.middleware.hmac_webhook import _verify_hmac,_check_timestamp

def test_hmac_verification_is_timing_safe_and_correct():
    body=b"{}"; secret="test-secret"
    sig=hmac.new(secret.encode(),body,hashlib.sha256).hexdigest()
    assert _verify_hmac(body,sig,secret)
    assert not _verify_hmac(body,sig[:-1]+"0",secret)

def test_webhook_timestamp_replay_window():
    assert _check_timestamp(str(int(time.time())))
    assert not _check_timestamp(str(int(time.time())-301))

def test_dev_login_creates_session():
    client=TestClient(app)
    r=client.post('/api/v1/auth/dev-login',json={'email':'test-advisor@example.com','display_name':'Test Advisor'})
    assert r.status_code==200
    assert r.json()['token']
    me=client.get('/api/v1/auth/me',headers={'Authorization':'Bearer '+r.json()['token']})
    assert me.status_code==200
