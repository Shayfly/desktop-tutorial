FROM python:3.12-slim

RUN useradd -m -u 10001 sandbox
WORKDIR /workspace

# Dependency allowlist (decision 2026-10-07 #25): exactly the packages in
# omni_prod/dependency_policy.py, pinned. Generated code gets nothing else:
# the sandbox runs with --network none and no install step, and anything off
# the list fails as UNSUPPORTED_DEPENDENCY before this image is started.
# tests/test_dependency_policy.py fails if this list and the policy drift.
RUN python -m pip install --no-cache-dir \
    pytest==8.3.5

USER 10001:10001
ENTRYPOINT []
CMD ["python", "-m", "pytest", "-q"]
