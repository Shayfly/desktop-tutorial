FROM python:3.12-slim

RUN useradd -m -u 10001 sandbox
WORKDIR /workspace

# Only the minimum baseline toolchain.
# Project-specific dependency installation should happen in a controlled build stage,
# preferably from allowlisted registries / mirrored dependencies in production.
RUN python -m pip install --no-cache-dir \
    pytest==8.3.5

USER 10001:10001
ENTRYPOINT []
CMD ["python", "-m", "pytest", "-q"]
