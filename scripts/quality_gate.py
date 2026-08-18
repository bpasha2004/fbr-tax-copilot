"""Repository quality gate used locally and in CI."""
from pathlib import Path
import subprocess, sys

def run(cmd):
    print("$", " ".join(cmd)); return subprocess.run(cmd, check=False).returncode

if run([sys.executable, "-m", "compileall", "-q", "."]): sys.exit(1)
if run([sys.executable, "-m", "pytest", "-q"]): sys.exit(1)
try:
    import yaml
    yaml.safe_load(Path("docker-compose.yml").read_text())
    print("docker-compose.yml: YAML OK")
except ImportError:
    print("PyYAML not installed; compose YAML check skipped")
print("QUALITY GATE: PASS")
