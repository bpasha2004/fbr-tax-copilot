import json
import logging
import time
import uuid

logger = logging.getLogger("fbr.observability")
SENSITIVE_KEYS = {"cnic", "ntn", "email", "phone", "iban", "api_key", "secret", "token", "password", "authorization"}

def request_id():
    return uuid.uuid4().hex

def sanitize(data):
    if isinstance(data, dict):
        return {k: ("[REDACTED]" if k.lower() in SENSITIVE_KEYS else sanitize(v)) for k, v in data.items()}
    if isinstance(data, list):
        return [sanitize(v) for v in data]
    return data

def emit(event, **fields):
    logger.info(json.dumps(sanitize({"event": event, **fields}), separators=(",", ":")))

class Timer:
    def __init__(self):
        self.start = time.perf_counter()
    def ms(self):
        return round((time.perf_counter() - self.start) * 1000, 2)
