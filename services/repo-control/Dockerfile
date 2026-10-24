FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates findutils grep sed gawk diffutils tree coreutils ripgrep && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pytest pytest-asyncio httpx requests fastapi pydantic
RUN useradd -m -u 10001 svc && mkdir -p /app/repo && chown -R svc:svc /app
WORKDIR /app
COPY services/repo-control/server.py /app/server.py
COPY services/repo-control/entrypoint.sh /app/entrypoint.sh
COPY services/repo-control/askpass.sh /app/askpass.sh
RUN chmod 700 /app/entrypoint.sh /app/askpass.sh
USER svc
ENV PORT=8000 REPO_DIR=/app/repo PYTHONUNBUFFERED=1 PYTHONPATH=/app/repo PATH=/home/svc/.local/bin:$PATH
EXPOSE 8000
CMD ["/app/entrypoint.sh"]