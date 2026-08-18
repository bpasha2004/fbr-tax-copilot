.PHONY: test eval lint compile security stack-up stack-down verify clean

test:
	pytest -q

eval:
	python -m eval.run

lint:
	ruff check .

compile:
	python -m compileall -q .

security:
	pip-audit -r requirements.txt

stack-up:
	docker compose up --build

stack-down:
	docker compose down

verify:
	python scripts/verify_ollama.py
	python scripts/smoke_stack.py

clean:
	find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache \) -prune -exec rm -rf {} +
