# Contributing

Run before opening a PR:

```bash
ruff check .
pytest -q
python -m eval.run
python -m compileall -q .
```

Rule changes must update the versioned JSON registry and add regression tests for every boundary.
AI changes must add an evaluation case or metric when behavior changes.
