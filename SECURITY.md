# Security

## Production requirements

- PostgreSQL and Redis are mandatory.
- Use a cloud secret manager or Vault for API keys, OAuth secrets and provider credentials.
- Set `DEBUG=False`.
- Keep CORS restricted to known origins.
- Enable MFA for write operations where operational policy requires it.
- Never commit taxpayer PII, session tokens or provider credentials.
- Provider webhooks require HMAC + timestamp verification and event deduplication.
- Provider mutation retries require idempotency keys.
- Current-year tax calculation remains fail-closed until authoritative source material is indexed and rule verification policy passes.

## Threat model

See `THREAT_MODEL.md`.
