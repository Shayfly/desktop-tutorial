"""Real FastAPI app + real PostgreSQL; object storage = LocalFileStore (test only)."""
import sys
sys.path.insert(0, sys.argv[1])
import uvicorn
from common import LocalFileStore
from omni_prod import investor_app as I
from omni_prod.workspace import PostgresProjectWorkspace

I._v28.engine.workspace = PostgresProjectWorkspace(I._v28_pool, LocalFileStore())
uvicorn.run(I.app, host='127.0.0.1', port=8148, log_level='warning')
