from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from .security import hash_password, new_session_token, token_digest, verify_password
from .store import Store, UserRecord


class AuthInput(BaseModel):
    email: str
    password: str


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


def create_router(store: Store) -> APIRouter:
    router = APIRouter()

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

    router.state = {"require_user": require_user, "store": store}
    return router
