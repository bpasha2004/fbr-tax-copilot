"""Check that Ollama is live and both the generation and embedding models exist."""
import json, os, urllib.request
base = os.getenv("OLLAMA_URL", "http://localhost:11434")
model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

def post(path, payload):
    req = urllib.request.Request(base + path, data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=120) as r: return json.loads(r.read())

with urllib.request.urlopen(base + "/api/tags", timeout=10) as r:
    models = {m.get("name") for m in json.load(r).get("models", [])}
if model not in models and model + ":latest" not in models:
    raise SystemExit(f"Missing Ollama generation model: {model}")
emb = post("/api/embeddings", {"model":"nomic-embed-text","prompt":"FBR tax smoke test"})
if not emb.get("embedding"):
    raise SystemExit("Ollama embedding request returned no vector")
print(f"OLLAMA PASS: {model} + nomic-embed-text")
