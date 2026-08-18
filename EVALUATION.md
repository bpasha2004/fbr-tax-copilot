# AI Evaluation

The benchmark is intentionally separate from the application runtime. This prevents “the model said it was confident” from becoming the measurement.

Metrics currently include:

- Recall@K
- Mean Reciprocal Rank
- latency p50 for live retrieval when available
- structured output validation
- figure consistency checks
- adversarial safety cases
- A/B retrieval comparison

Run:

```bash
python -m eval.run
```

Run the full regression suite:

```bash
pytest -q
```

The controlled offline benchmark contains 50 cases. The live retriever benchmark can be enabled when ChromaDB and Ollama are running.
