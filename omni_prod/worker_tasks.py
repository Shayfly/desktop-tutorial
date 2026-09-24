from __future__ import annotations

"""RQ worker entrypoint for the M1 durable async build pipeline.

Enqueued (see investor_app.py's v28_build_async) as
"omni_prod.worker_tasks.execute_live_build_job" with the build_id as the sole
payload -- no bearer token, no secret, no process-local state, per the M1
spec. Everything this function needs is reconstructed from durable Postgres
state via PostgresBuildRepository, so it can run in a separate worker process
(or be retried in a new one) with nothing carried over from the request that
created the job.

DEVIATION FROM THE LITERAL M1-COMPLETION INSTRUCTION: it specified calling
`_v28.engine.build(prompt)`. `_v28.engine` is `UnifiedOmniEngine`
(omni_prod/unified_engine.py) -- the deterministic, zero-paid-provider
TEMPLATE engine used by the synchronous Free-tier `/build` endpoint, not real
AI generation. Its `.build()` signature is also
`build(self, *, project_id: str, prompt: str) -> BuildResult`, not a
single-argument `build(prompt)`. Calling it here would silently route every
"durable async AI build" through the same deterministic templates as the
free synchronous path -- exactly the "deterministic template fallback that
pretends an AI build succeeded" the founder's master directive explicitly
forbids as fake success (section 3.1).

The actual real-AI-generation engine already exists in this codebase at
investor_app.py's `_live_engine()` (a fresh `AutonomousProductEngine` wired
to `RoutedModelGateway` + `SandboxRepositoryExecutor`/
`RemoteSandboxRepositoryExecutor`, the same one the existing synchronous
`/api/live/build` endpoint uses) and its `.build(self, prompt: str) ->
AutonomousResult` signature matches the instruction's intent exactly. That is
what is called below. `_v28.engine.workspace` (the actual, correct project
version store shared by /history, /export, /restore) is still used to commit
the result, since that part of the instruction was correct.
"""

from .models import BuildStatus


def execute_live_build_job(build_id: str) -> None:
    # Imported lazily so this module can be imported (e.g. by tests) without
    # requiring the full investor_app.py dependency graph (fastapi, the
    # entire routes module, etc.) unless a job is actually being executed.
    from .investor_app import _v28, _v28_pool, _live_engine
    from .job_repository import PostgresBuildRepository

    if _v28_pool is None:
        raise RuntimeError(
            "execute_live_build_job requires OMNI_CREATOR_PERSISTENCE=postgres "
            "in the worker process (this process was not started with it)."
        )

    jobs = PostgresBuildRepository(_v28_pool)

    try:
        request = jobs.get_request(build_id)
    except KeyError:
        # Nothing durable to work from. This should not happen for a build_id
        # that reached the queue (create_request() commits before enqueue),
        # but there is nothing safe to do about it here besides not crash the
        # worker loop on an unknown id.
        return

    internal_project_id = request["internal_project_id"]
    prompt = request["prompt"]

    if not jobs.transition(build_id=build_id, expected=BuildStatus.QUEUED, target=BuildStatus.RUNNING):
        # Already transitioned (duplicate delivery, a previous worker attempt,
        # or a cancelled job). Idempotent no-op rather than an error.
        return

    try:
        engine = _live_engine()
        result = engine.build(prompt)

        version_id = None
        artifact_key = None
        if result.repository:
            version = _v28.engine.workspace.commit(
                project_id=internal_project_id,
                repository=result.repository,
                message=f"live build {build_id}",
            )
            version_id = version.id
            # version.artifact_key is only non-None when the workspace is the
            # durable PostgresProjectWorkspace (S3 configured); the in-memory
            # fallback leaves it None rather than inventing one.
            artifact_key = version.artifact_key

        evidence = {
            "passed": result.report.passed,
            "repair_rounds": result.repair_rounds,
            "failures": [
                {"acceptance_id": f.acceptance_id, "message": f.message, "evidence": f.evidence}
                for f in result.report.failures
            ],
            "build_log_tail": result.report.build_log[-4000:],
        }

        # Real spend is not tracked per-model-call in this codebase yet (see
        # PATCH_APPLICATION_REPORT.md); settle() with no actual_provider_cost_usd
        # falls back to the estimate reserved at request time rather than
        # fabricating a real-usage number, per the master directive's
        # "do not invent token/cost numbers and call them actual usage".
        _v28.subscriptions.settle(build_id=build_id)

        if result.status == "ready":
            jobs.transition(
                build_id=build_id, expected=BuildStatus.RUNNING, target=BuildStatus.READY,
                result_version_id=version_id, artifact_key=artifact_key,
                repair_rounds=result.repair_rounds, evidence_json=evidence,
            )
        else:
            jobs.transition(
                build_id=build_id, expected=BuildStatus.RUNNING, target=BuildStatus.FAILED,
                error_code="verification_failed",
                error_message="build did not pass verification",
                result_version_id=version_id,
                repair_rounds=result.repair_rounds, evidence_json=evidence,
            )
    except Exception as exc:
        _v28.subscriptions.release(build_id=build_id)
        jobs.transition(
            build_id=build_id, expected=BuildStatus.RUNNING, target=BuildStatus.FAILED,
            error_code="worker_exception", error_message=str(exc)[:2000],
        )
        raise
