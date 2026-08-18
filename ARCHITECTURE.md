# FBR Tax Copilot — Architecture

## Design principle

The system is deliberately split into **deterministic financial computation** and **probabilistic AI explanation**. The language model never decides the tax number.

```text
                         ┌─────────────────────┐
                         │ Advisor / Client UI │
                         └──────────┬──────────┘
                                    │
                            Auth + RBAC + MFA
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      FastAPI API    │
                         └───────┬───────┬─────┘
                                 │       │
                    ┌────────────┘       └─────────────┐
                    ▼                                  ▼
          ┌─────────────────┐                ┌────────────────┐
          │ Versioned Rules │                │   MCP Tools    │
          │ Engine          │                │ deterministic  │
          └────────┬────────┘                └───────┬────────┘
                   │                                 │
                   ▼                                 ▼
             tax result                       tool result
                   │                                 │
                   └──────────────┬──────────────────┘
                                  ▼
                      ┌────────────────────┐
                      │ RAG + source gate  │
                      └─────────┬──────────┘
                                ▼
                      ┌────────────────────┐
                      │ LLM explanation    │
                      └─────────┬──────────┘
                                ▼
                    ┌────────────────────────┐
                    │ Independent validation │
                    │ citations / figures /  │
                    │ schema / safety gate   │
                    └────────────┬───────────┘
                                 ▼
                         response + audit

Infrastructure:
PostgreSQL | Redis | ChromaDB | Ollama | Docker

Evaluation path:
benchmark → retrieval metrics → generation checks → adversarial cases → CI regression gate
```

## Multi-tenant boundary

Every client, calculation and payment record carries an `advisor_id`. Read and write operations are owner-scoped. Roles are `admin`, `advisor`, `reviewer`, and `auditor`.

## Financial safety boundary

The tax engine is authoritative for the tax number. RAG provides legal/source context. The LLM is allowed to explain verified numbers, not invent them. On failed grounding or figure validation the application abstains.
