# Preview worker + router image: the orchestrator that starts generated-app
# preview containers on the host daemon (docker-out-of-docker), and the
# stdlib router Caddy forwards preview hostnames to. Generated code never runs
# in this container; it runs in the locked-down containers built by
# omni_prod.preview_runtime.build_run_argv (read-only, no capabilities,
# unprivileged user, CPU/memory/pids limits).
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update \
 && (apt-get install -y --no-install-recommends docker-cli || apt-get install -y --no-install-recommends docker.io) \
 && rm -rf /var/lib/apt/lists/* \
 && docker --version
COPY requirements-production.txt /app/requirements-production.txt
RUN python -m pip install --no-cache-dir -r /app/requirements-production.txt
COPY omni_prod /app/omni_prod
CMD ["python", "-m", "omni_prod.worker"]
