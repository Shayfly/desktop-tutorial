#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures, json, os, time, urllib.request
URL=os.getenv('OMNI_LOAD_URL','http://127.0.0.1:8000/api/status')
REQUESTS=int(os.getenv('OMNI_LOAD_REQUESTS','200')); CONCURRENCY=int(os.getenv('OMNI_LOAD_CONCURRENCY','20'))
def hit(_):
    t=time.perf_counter()
    try:
        with urllib.request.urlopen(URL,timeout=10) as r: r.read(); status=r.status
        return status,int((time.perf_counter()-t)*1000),''
    except Exception as exc: return 0,int((time.perf_counter()-t)*1000),str(exc)[:200]
start=time.perf_counter()
with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as ex: results=list(ex.map(hit,range(REQUESTS)))
elapsed=time.perf_counter()-start; lat=sorted(x[1] for x in results); ok=sum(1 for s,_,_ in results if 200<=s<400)
p95=lat[min(len(lat)-1,int((len(lat)-1)*.95))] if lat else 0
payload={'url':URL,'requests':REQUESTS,'concurrency':CONCURRENCY,'ok':ok,'errors':REQUESTS-ok,'success_rate':round(ok/REQUESTS,4) if REQUESTS else 0,'p95_ms':p95,'rps':round(REQUESTS/elapsed,2) if elapsed else 0}
print(json.dumps(payload,indent=2)); raise SystemExit(0 if ok==REQUESTS else 2)
