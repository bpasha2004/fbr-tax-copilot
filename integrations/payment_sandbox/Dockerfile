FROM python:3.12-slim
WORKDIR /app
COPY integrations/payment_sandbox/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY integrations/payment_sandbox/server.py /app/server.py
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8010"]
