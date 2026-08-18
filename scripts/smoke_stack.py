"""Live integration smoke test for API, Ollama, MCP and payment sandbox."""
import json, os, sys, time, urllib.request

BASE = os.getenv("APP_URL", "http://localhost:8000")
OLLAMA = os.getenv("OLLAMA_URL", "http://localhost:11434")
MCP = os.getenv("MCP_URL", "http://localhost:8001")
PAY = os.getenv("PAYMENT_SANDBOX_URL", "http://localhost:8010")

def get(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.status, r.read().decode()

checks = {}
for name, url in {"api": f"{BASE}/api/v1/health", "ollama": f"{OLLAMA}/api/tags", "mcp": MCP, "payment_sandbox": f"{PAY}/health"}.items():
    try:
        status, body = get(url); checks[name] = status < 400
        print(f"{name}: {status}")
    except Exception as exc:
        checks[name] = False; print(f"{name}: FAIL — {exc}")

if not all(checks.values()):
    raise SystemExit("Live stack check failed; inspect the service logs.")
print("LIVE STACK: PASS")
