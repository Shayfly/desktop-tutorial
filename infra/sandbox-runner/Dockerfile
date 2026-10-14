FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
# Only the Docker CLI is needed: it talks to the host daemon through the
# mounted socket. Installing docker.io with --no-install-recommends produced an
# image without a docker binary, so every sandbox run failed with "No such file
# or directory: 'docker'" (Golden E2E #1 on Preview, 2026-10-07). Newer Debian
# releases package the client separately as docker-cli; install that, fall
# back to docker.io, and fail the image build if the client is still missing.
RUN apt-get update \
 && (apt-get install -y --no-install-recommends docker-cli || apt-get install -y --no-install-recommends docker.io) \
 && rm -rf /var/lib/apt/lists/* \
 && docker --version
COPY requirements-production.txt /app/requirements-production.txt
RUN python -m pip install --no-cache-dir -r /app/requirements-production.txt
COPY omni_prod /app/omni_prod
EXPOSE 8010
CMD ["uvicorn","omni_prod.sandbox_service:app","--host","0.0.0.0","--port","8010"]
