# Visual Edit real-browser walkthrough (local, $0)

Real FastAPI + PostgreSQL + real preview router (inspector wrapper, TLS). Test-only
substitutes: local-file object storage, a local process instead of a preview
container, a harness-written modification candidate (no model call).

```bash
export VE_DB=postgresql://postgres@127.0.0.1:55432/ve148          # fresh database
export OMNI_DATABASE_URL=$VE_DB OMNI_CREATOR_PERSISTENCE=postgres OMNI_ENV=development
export PREVIEW_DOMAIN_TEMPLATE='https://{preview_id}.prv.148ai.test' OMNI_REDIS_URL=redis://127.0.0.1:6379/3
export PYTHONPATH=<repo>:<repo>/tools/ui_visual_edit UX=<repo>/tools/ui_visual_edit
python -m omni_prod.migrate
cd tools/ui_visual_edit
openssl req -x509 -newkey rsa:2048 -nodes -keyout tls.key -out tls.crt -days 2 \
  -subj "/CN=*.prv.148ai.test" -addext "subjectAltName=DNS:*.prv.148ai.test"
python serve_api.py <repo> &          # app on 127.0.0.1:8148
python preview_host.py <repo> &       # router on 127.0.0.1:443 (root) + local preview processes
python walkthrough.py <out dir>       # run without HTTP(S)_PROXY in the environment
```
