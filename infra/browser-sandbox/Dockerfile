# Browser sandbox (directive 2026-10-09 §17): the same isolation as
# infra/sandbox (run with --network none, read-only source, caps dropped,
# non-root) plus headless Chromium driven by Playwright, so generated web
# products are clicked through like a user would. Debian's chromium package
# (arm64 and amd64); Playwright only drives it -- no browser download.
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends chromium fonts-dejavu-core fonts-noto-core \
 && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir playwright==1.56.0 pytest==8.3.5

RUN useradd -m -u 10001 sandbox
ENV OMNI_CHROMIUM=/usr/bin/chromium
WORKDIR /workspace
USER 10001:10001
ENTRYPOINT []
CMD ["python", "-c", "print('omni browser sandbox')"]
