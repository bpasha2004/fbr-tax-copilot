#!/usr/bin/env bash
set -euo pipefail
command -v docker >/dev/null || { echo "Docker is required. Install Docker Desktop first."; exit 1; }
docker compose pull
docker compose build
docker compose up -d
python scripts/smoke_stack.py
