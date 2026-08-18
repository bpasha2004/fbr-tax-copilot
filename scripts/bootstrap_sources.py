"""Fetch and integrity-check authoritative current-year FBR sources."""
from pathlib import Path
from urllib.request import Request, urlopen
import hashlib, time
from config.settings import settings

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/documents/fbr"
SOURCES = {
    "2026-27": ("20266291261044366FinanceAct2026.pdf", "https://download1.fbr.gov.pk/Docs/20266291261044366FinanceAct2026.pdf"),
}

def _verify(path: Path, expected: str) -> None:
    if expected:
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual.lower() != expected.lower():
            raise RuntimeError(f"SHA-256 mismatch for {path.name}")

def fetch(tax_year: str, name: str, url: str) -> None:
    target = OUT / name
    OUT.mkdir(parents=True, exist_ok=True)
    expected = settings.FBR_FINANCE_ACT_2026_SHA256 if tax_year == "2026-27" else ""
    if target.exists() and target.stat().st_size > 100_000:
        _verify(target, expected)
        print(f"Existing verified source: {target.name}")
        return
    for attempt in range(1, 4):
        try:
            req = Request(url, headers={"User-Agent": "FBR-Tax-Copilot/1.0"})
            with urlopen(req, timeout=60) as response, target.open("wb") as fh:
                while chunk := response.read(1024 * 1024):
                    fh.write(chunk)
            if target.stat().st_size <= 100_000:
                raise RuntimeError("Downloaded source is unexpectedly small")
            _verify(target, expected)
            print(f"Fetched and verified: {target.name} ({target.stat().st_size:,} bytes)")
            return
        except Exception:
            target.unlink(missing_ok=True)
            if attempt == 3: raise
            time.sleep(attempt * 2)

for tax_year, (name, url) in SOURCES.items():
    fetch(tax_year, name, url)

print("CURRENT FBR SOURCES: READY")
