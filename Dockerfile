FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
# Every one-shot script in scripts/ (migrate.py, healthcheck.py,
# bootstrap_sources.py) is invoked as `python scripts/foo.py`, and Python
# sets sys.path[0] to the SCRIPT's own directory (/app/scripts), not the
# working directory — so `from config.settings import settings` fails
# with ModuleNotFoundError unless /app itself is also on the path.
ENV PYTHONPATH=/app
CMD ["uvicorn","api.main:app","--host","0.0.0.0","--port","8000"]
