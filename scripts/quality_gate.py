"""Repository quality gate used locally and in CI."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd), flush=True)
    result = subprocess.run(cmd, check=False)
    if result.returncode:
        raise SystemExit(result.returncode)


def main() -> None:
    run([sys.executable, "-m", "ruff", "check", "."])
    run([sys.executable, "-m", "compileall", "-q", "."])
    run([sys.executable, "-m", "pytest", "-q"])
    run([sys.executable, "-m", "eval.run"])

    import yaml

    yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))
    print("docker-compose.yml: YAML OK")

    run([sys.executable, "-m", "pip_audit", "-r", "requirements.txt"])
    print("QUALITY GATE: PASS")


if __name__ == "__main__":
    main()
