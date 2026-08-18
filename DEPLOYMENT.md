# Deployment Runbook

## Local full stack

```bash
cp config/.env.stack.example .env.stack
docker compose --env-file .env.stack up --build
```

Core services:

- FastAPI: `127.0.0.1:8000`
- MCP Streamable HTTP: `127.0.0.1:8001`
- Payment sandbox: `127.0.0.1:8010`
- Ollama: `127.0.0.1:11434`
- PostgreSQL and Redis stay on the internal Compose network.

## Verification

```bash
python scripts/verify_ollama.py
python scripts/smoke_stack.py
curl http://127.0.0.1:8000/api/v1/health/readiness
```

The readiness endpoint should report database, Redis and ChromaDB as healthy. The Ollama dependency endpoint should report the configured generation model.

## Production checklist

1. Replace Compose secrets with a cloud secret manager.
2. Set `ENV=production` and a PostgreSQL URL.
3. Set a strong `SECRET_KEY` and `API_KEY`.
4. Set trusted CORS origins and proxy settings.
5. Enable MFA for write operations.
6. Put the API behind TLS and a WAF/load balancer.
7. Configure managed PostgreSQL backups and restore testing.
8. Export logs/metrics/traces to the organization's observability platform.
9. Connect only verified payment-provider sandbox/production endpoints.
10. Pin `FBR_FINANCE_ACT_2026_SHA256` after retrieving the official Finance Act 2026 file through the approved source-management process.
11. Have tax rules reviewed by a qualified Pakistani tax professional before production use.
