FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends docker.io && rm -rf /var/lib/apt/lists/*
COPY requirements-production.txt /app/requirements-production.txt
RUN python -m pip install --no-cache-dir -r /app/requirements-production.txt
COPY omni_prod /app/omni_prod
EXPOSE 8010
CMD ["uvicorn","omni_prod.sandbox_service:app","--host","0.0.0.0","--port","8010"]
