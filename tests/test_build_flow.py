import io
import zipfile

from live_core.executor import ExecutionResult
from live_core.service import CustomerService
from live_core.store import MemoryStore


def zip_bytes(files: dict[str, str]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, body in files.items():
            z.writestr(name, body)
    return out.getvalue()


def make_user(store: MemoryStore):
    return store.create_user("builder@example.com", "hash-placeholder")


def test_successful_build_records_stage_progression_and_promotes_version():
    store = MemoryStore()
    user = make_user(store)
    artifact = zip_bytes({"index.html": "<h1>Hello</h1>"})

    def generator(prompt: str, title: str, target_markets: list[str]) -> bytes:
        return artifact

    def executor(blob: bytes, timeout_seconds: int) -> ExecutionResult:
        return ExecutionResult(ok=True, entrypoint="index.html", checked_js=0, error=None)

    service = CustomerService(store, generator=generator, executor=executor)
    build = service.build(user.id, "Build a tiny web game")

    assert build.stage == "ready"
    assert build.status == "ready"
    assert build.version_id
    assert store.get_build_events(build.id) == [
        "planning", "generating", "running", "testing", "ready"
    ]
    project = store.get_project(build.project_id, user.id)
    assert project is not None
    assert project.active_version_id == build.version_id
    versions = store.list_versions(project.id, user.id)
    assert len(versions) == 1


def test_failed_execution_never_promotes_version():
    store = MemoryStore()
    user = make_user(store)
    artifact = zip_bytes({"index.html": "<script src='app.js'></script>", "app.js": "const = ;"})

    def generator(prompt: str, title: str, target_markets: list[str]) -> bytes:
        return artifact

    def executor(blob: bytes, timeout_seconds: int) -> ExecutionResult:
        return ExecutionResult(ok=False, entrypoint="index.html", checked_js=1, error="JavaScript syntax check failed")

    service = CustomerService(store, generator=generator, executor=executor)
    build = service.build(user.id, "Build a broken web game")

    assert build.stage == "failed"
    assert build.status == "failed"
    assert "JavaScript" in (build.error or "")
    assert build.version_id is None
    assert store.get_build_events(build.id) == [
        "planning", "generating", "running", "testing", "failed"
    ]
    project = store.get_project(build.project_id, user.id)
    assert project is not None
    assert project.active_version_id is None
    assert store.list_versions(project.id, user.id) == []
