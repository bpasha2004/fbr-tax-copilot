# FBR Tax Copilot — FinTech + AI Compliance Platform

> **A deterministic tax engine with regulatory RAG, MCP tools, AI safety gates, multi-tenant controls, and reproducible evaluation.**

This is not a chatbot that guesses tax. The architecture makes the tax calculation deterministic and makes the language model explain a verified result.

## What makes it stand out

- **Regulation-aware:** versioned tax rules with explicit tax-year routing. 2026–27 is the active configuration; 2025–26 remains available for regression/backtesting.
- **AI-grounded:** FBR source documents are embedded into ChromaDB. Retrieval is filtered by tax year and taxpayer type before LLM generation.
- **AI-safe:** the model cannot authoritatively change the tax figure. Citations, rule IDs, structured output and figure consistency are independently checked. Failed checks cause abstention.
- **Agent-ready:** deterministic tax operations are exposed through official MCP tools.
- **Evaluated, not hand-waved:** retrieval metrics, A/B comparisons, adversarial cases and regression tests live under `eval/` and `tests/`.
- **B2B FinTech controls:** PostgreSQL, Redis distributed rate limiting, tenant-scoped records, roles, MFA step-up support, money-safe NUMERIC storage, tamper-evident audit events, payment idempotency, lifecycle state machines, reconciliation, refund and chargeback workflows, and signed webhook verification.
- **Reproducible:** Docker Compose provisions PostgreSQL, Redis, ChromaDB, Ollama, the MCP server and a payment webhook sandbox.

## Architecture

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full system map.

```text
Advisor UI
   ↓
Auth + RBAC + MFA
   ↓
FastAPI API
   ├── Versioned Rules Engine ──→ verified tax number
   ├── MCP tools ───────────────→ deterministic operations
   └── RAG ──→ source gate ──→ LLM explanation
                         ↓
                independent safety validation
                         ↓
                    audit + response

Infrastructure: PostgreSQL | Redis | ChromaDB | Ollama | Docker
Evaluation: benchmark | A/B | adversarial tests | CI regression gate
```

## Tax-year coverage

- **2026–27:** current configuration for salaried calculations and Section 154A IT/ITeS export logic, with source references recorded in the rules registry.
- **2025–26:** retained for historical regression/backtesting.
- Rule data lives in `rules_engine/rules/*.json`; application code does not hard-code slab tables.

Tax rules are decision-support only and must be reviewed by a qualified Pakistani tax professional before production use.

## AI evaluation

```bash
python -m eval.run
pytest -q
```

The benchmark contains 50 controlled cases and can run against the live retriever when ChromaDB is populated. See [`EVALUATION.md`](EVALUATION.md).

## Full local stack

```bash
cp config/.env.stack.example .env.stack
docker compose --env-file .env.stack up --build
```

Services:

| Service | Local address | Purpose |
|---|---|---|
| FastAPI | `127.0.0.1:8000` | API + dashboard |
| MCP | `127.0.0.1:8001` | Streamable HTTP tool server |
| Payment sandbox | `127.0.0.1:8010` | HMAC webhook integration test |
| Ollama | `127.0.0.1:11434` | local generation + embeddings |
| PostgreSQL | internal | persistent transactional data |
| Redis | internal | distributed rate limiting |
| ChromaDB | persistent volume | document vectors |

The bootstrap flow fetches the current FBR source documents, pulls the configured Ollama models, ingests documents idempotently, then starts the API.

## Verification

```bash
python scripts/verify_ollama.py
python scripts/smoke_stack.py
curl http://127.0.0.1:8000/api/v1/health/readiness
```

For developer commands:

```bash
make test
make eval
make compile
make lint
make security
```

## Security posture

See [`THREAT_MODEL.md`](THREAT_MODEL.md) and [`SECURITY.md`](SECURITY.md).

Key controls include:

- short-lived signed session tokens
- active-account checks
- role-based access (`admin`, `advisor`, `reviewer`, `auditor`)
- optional production MFA enforcement for writes
- Redis-backed rate limiting with local fallback only for development/tests
- request-size limits and restrictive security headers
- HMAC + timestamp validation for payment webhooks
- sanitized structured observability logs
- append-only audit events
- production startup rejects SQLite and weak placeholder secrets

## Deployment

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for the deployment runbook, operational checklist, backups and environment-specific controls.

## Important boundary

This repository provides a real local payment/webhook sandbox and a production-oriented MCP/Ollama/Chroma deployment. Provider-specific production transactions require the provider's official sandbox/production credentials, current API contract and contractual/bank onboarding. See `PAYMENT_INTEGRATION_STATUS.md`.
