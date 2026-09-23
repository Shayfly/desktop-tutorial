from __future__ import annotations

import mimetypes

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from .security import hash_password, new_session_token, token_digest, verify_password
from .service import CustomerService
from .store import BuildRecord, ProjectRecord, Store, UserRecord, VersionRecord


PREVIEW_CSP = "sandbox allow-scripts allow-forms allow-modals allow-popups; base-uri 'none'; object-src 'none'"


class AuthInput(BaseModel):
    email: str
    password: str


class BuildInput(BaseModel):
    prompt: str
    project_id: str | None = None
    target_markets: list[str] = Field(default_factory=list)


class RunBuildInput(BaseModel):
    target_markets: list[str] = Field(default_factory=list)


def _normalize_email(value: str) -> str:
    email = value.strip().lower()
    if not email or "@" not in email or email.startswith("@") or email.endswith("@"):
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    return email


def _extract_bearer(request: Request) -> str:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return token.strip()


def _user_payload(user: UserRecord) -> dict[str, str]:
    return {"id": user.id, "email": user.email}


def _project_payload(project: ProjectRecord) -> dict:
    return {
        "id": project.id,
        "title": project.title,
        "active_version_id": project.active_version_id,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
    }


def _version_payload(version: VersionRecord) -> dict:
    return {
        "id": version.id,
        "project_id": version.project_id,
        "artifact_id": version.artifact_id,
        "prompt": version.prompt,
        "parent_version_id": version.parent_version_id,
        "created_at": version.created_at.isoformat(),
    }


def _build_payload(build: BuildRecord) -> dict:
    return {
        "id": build.id,
        "project_id": build.project_id,
        "prompt": build.prompt,
        "stage": build.stage,
        "status": build.status,
        "error": build.error,
        "version_id": build.version_id,
        "created_at": build.created_at.isoformat(),
        "updated_at": build.updated_at.isoformat(),
    }


def create_router(store: Store) -> APIRouter:
    router = APIRouter()
    service = CustomerService(store)

    def require_user(request: Request) -> UserRecord:
        token = _extract_bearer(request)
        session = store.get_session_by_digest(token_digest(token))
        if not session:
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        user = store.get_user(session.user_id)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        return user

    @router.post("/api/live/auth/register")
    def register(body: AuthInput):
        email = _normalize_email(body.email)
        if len(body.password) < 10:
            raise HTTPException(status_code=422, detail="Password must be at least 10 characters")
        if store.get_user_by_email(email):
            raise HTTPException(status_code=409, detail="An account already exists for this email")
        try:
            user = store.create_user(email, hash_password(body.password))
        except ValueError as exc:
            raise HTTPException(status_code=409, detail="An account already exists for this email") from exc
        token, digest = new_session_token()
        store.create_session(user.id, digest)
        return {"token": token, "user": _user_payload(user)}

    @router.post("/api/live/auth/login")
    def login(body: AuthInput):
        email = _normalize_email(body.email)
        user = store.get_user_by_email(email)
        if not user or not verify_password(body.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        token, digest = new_session_token()
        store.create_session(user.id, digest)
        return {"token": token, "user": _user_payload(user)}

    @router.post("/api/live/auth/logout")
    def logout(request: Request, user: UserRecord = Depends(require_user)):
        token = _extract_bearer(request)
        store.revoke_session(token_digest(token))
        return {"ok": True, "user_id": user.id}

    @router.get("/api/live/me")
    def me(user: UserRecord = Depends(require_user)):
        return _user_payload(user)

    @router.get("/api/live/projects")
    def list_projects(user: UserRecord = Depends(require_user)):
        return {"projects": [_project_payload(p) for p in service.list_projects(user.id)]}

    @router.get("/api/live/projects/{project_id}/versions")
    def list_versions(project_id: str, user: UserRecord = Depends(require_user)):
        try:
            versions = service.list_versions(user.id, project_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project not found") from exc
        return {"versions": [_version_payload(v) for v in versions]}

    @router.post("/api/live/builds")
    def start_build(body: BuildInput, user: UserRecord = Depends(require_user)):
        try:
            build = service.start_build(user.id, body.prompt, body.project_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project not found") from exc
        return _build_payload(build)

    @router.post("/api/live/builds/{build_id}/run")
    def run_build(build_id: str, body: RunBuildInput, user: UserRecord = Depends(require_user)):
        try:
            build = service.run_build(user.id, build_id, body.target_markets)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Build not found") from exc
        return _build_payload(build)

    @router.get("/api/live/builds/{build_id}")
    def get_build(build_id: str, user: UserRecord = Depends(require_user)):
        try:
            build, events = service.get_build(user.id, build_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Build not found") from exc
        payload = _build_payload(build)
        payload["events"] = [
            {
                "stage": event.stage,
                "message": event.message,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ]
        return payload

    @router.post("/api/live/projects/{project_id}/versions/{version_id}/restore")
    def restore(project_id: str, version_id: str, user: UserRecord = Depends(require_user)):
        try:
            project = service.restore_version(user.id, project_id, version_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Version not found") from exc
        return _project_payload(project)

    @router.get("/api/live/projects/{project_id}/versions/{version_id}/export")
    def export(project_id: str, version_id: str, user: UserRecord = Depends(require_user)):
        try:
            blob = service.export_version(user.id, project_id, version_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Version not found") from exc
        return Response(
            content=blob,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="148AI-{project_id}.zip"'},
        )

    @router.post("/api/live/projects/{project_id}/versions/{version_id}/preview")
    def create_preview(project_id: str, version_id: str, user: UserRecord = Depends(require_user)):
        try:
            handle = service.create_preview_handle(user.id, project_id, version_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Version not found") from exc
        return {"url": f"/preview/live/{handle}/", "preview_id": handle}

    def _serve_preview(preview_id: str, path: str | None = None):
        try:
            data, resolved_path = service.preview_asset(preview_id, path)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Preview not found") from exc
        media_type = mimetypes.guess_type(resolved_path)[0] or "application/octet-stream"
        return Response(
            content=data,
            media_type=media_type,
            headers={
                "Content-Security-Policy": PREVIEW_CSP,
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "Cache-Control": "private, no-store",
            },
        )

    @router.get("/preview/live/{preview_id}/")
    def preview_root(preview_id: str):
        return _serve_preview(preview_id, None)

    @router.get("/preview/live/{preview_id}/{path:path}")
    def preview_asset(preview_id: str, path: str):
        return _serve_preview(preview_id, path)

    router.state = {"require_user": require_user, "store": store, "service": service}
    return router
