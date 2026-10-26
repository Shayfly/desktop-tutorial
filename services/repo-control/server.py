"""Isolated, token-authenticated GET control plane. Never deploy with production credentials."""
import base64, binascii, datetime, hmac, json, os, re, shlex, subprocess, threading, selectors, signal, time, uuid, contextlib
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT=Path(os.getenv("REPO_DIR","/app/repo")).resolve()
TOKEN=os.getenv("SERVICE_TOKEN","")
PAT=os.getenv("GITHUB_PAT","")
PORT=int(os.getenv("PORT","8000"))
LOCK=threading.RLock()
MAX=50*1024
JOBS={}
JOBS_LOCK=threading.Lock()
MAX_JOBS=32
MAX_ACTIVE_JOBS=2
JOB_TIMEOUT=120
JOB_QUEUE_MAX=600
JOB_TIMEOUT_MAX=900
ACTIVE=threading.BoundedSemaphore(MAX_ACTIVE_JOBS)

ALLOWED={"pytest","python3","git","grep","find","ls","cat","head","tail","wc","diff","sed","awk","tree","pwd","rg","sort","uniq","echo"}
GIT_READ={"status","diff","log","show","rev-parse","branch","fetch"}
def audit(action, result, detail=""):
    item={"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"action":action,"result":result,"detail":str(detail)[:150]}
    # No URL, token, command, file body, or GitHub API response in application logs.
    print(json.dumps(item),flush=True)

def run(args, *, git_credentials=False, timeout=120, input_bytes=None):
    """Bounded-memory subprocess capture; on timeout kill the whole process group."""
    env = os.environ.copy()
    for name in ("GITHUB_PAT", "SERVICE_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        env.pop(name, None)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["PYTHONUNBUFFERED"] = "1"
    env.pop("GIT_ASKPASS", None)
    if git_credentials:
        env["GITHUB_PAT"] = PAT
        env["GIT_ASKPASS"] = "/app/askpass.sh"
    try:
        proc = subprocess.Popen(args, cwd=ROOT, env=env, shell=False,
                                stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                start_new_session=True)
        if input_bytes is not None:
            proc.stdin.write(input_bytes)
            proc.stdin.close()
        output = {"stdout": bytearray(), "stderr": bytearray()}
        truncated = False
        selector = selectors.DefaultSelector()
        for key in ("stdout", "stderr"):
            os.set_blocking(getattr(proc, key).fileno(), False)
            selector.register(getattr(proc, key), selectors.EVENT_READ, key)
        deadline = time.monotonic() + timeout
        try:
            while selector.get_map():
                if time.monotonic() >= deadline:
                    raise subprocess.TimeoutExpired(args, timeout)
                for event, _ in selector.select(timeout=min(0.25, max(0, deadline-time.monotonic()))):
                    stream = event.fileobj
                    chunk = os.read(stream.fileno(), 8192)
                    if not chunk:
                        selector.unregister(stream)
                        stream.close()
                        continue
                    remaining = MAX - sum(len(v) for v in output.values())
                    if len(chunk) > remaining:
                        truncated = True
                    if remaining > 0:
                        output[event.data].extend(chunk[:remaining])
            remaining_time = deadline - time.monotonic()
            if remaining_time <= 0:
                raise subprocess.TimeoutExpired(args, timeout)
            code = proc.wait(timeout=remaining_time)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            out=output["stdout"].decode("utf-8","replace")
            err=output["stderr"].decode("utf-8","replace")
            for credential in (PAT,TOKEN):
                if credential:
                    out=out.replace(credential,"[redacted]")
                    err=err.replace(credential,"[redacted]")
            return {"exit_code":124,"stdout":out,"stderr":err+"\ntimeout "+str(round(timeout,3))+"s",
                    "truncated":truncated,"_deadline_expired":True}
        finally:
            selector.close()
            for stream in (proc.stdout, proc.stderr):
                if stream and not stream.closed: stream.close()
        out = output["stdout"].decode("utf-8", "replace")
        err = output["stderr"].decode("utf-8", "replace")
        for credential in (PAT, TOKEN):
            if credential:
                out = out.replace(credential, "[redacted]")
                err = err.replace(credential, "[redacted]")
        return {"exit_code":code, "stdout":out, "stderr":err, "truncated":truncated}
    except OSError as exc:
        return {"exit_code":127, "stdout":"","stderr":type(exc).__name__,
                "truncated":False}


def validate_segment(argv):
    """A guardrail against accidental mutations, not a sandbox."""
    if not argv or argv[0] not in ALLOWED:
        return False
    cmd = argv[0]
    opts = argv[1:]
    if cmd == "git":
        return len(opts) >= 1 and opts[0] in GIT_READ and not any(
            x in ("-c", "--config", "--external-diff", "--output") for x in opts)
    if cmd == "python3":
        if opts[:2] in (["-m", "pytest"], ["-m", "compileall"]) or (len(opts)>=2 and opts[0]=="-c"):
            return True
        return bool(opts and opts[0].endswith(".py") and not opts[0].startswith("-")
                    and safe_script(opts[0]))
    if cmd == "find":
        return not any(x in ("-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint",
                            "-fprint0", "-fprintf", "-fls") for x in opts)
    if cmd == "sed":
        return not any(x == "-i" or x.startswith("-i") or x.startswith("--in-place") for x in opts)
    if cmd == "awk":
        return not any(x in ("-i", "--include") for x in opts)
    return not (cmd in ("grep", "rg") and any(x in ("--include-from",) for x in opts))

def safe_script(name):
    try:
        path = repo_path(name)
        return path.is_file() and path.suffix == ".py"
    except (OSError, ValueError):
        return False

def split_pipeline(command):
    lexer = shlex.shlex(command, posix=True, punctuation_chars="|")
    lexer.whitespace_split = True
    args = list(lexer)
    if not args or "||" in args:
        raise ValueError("invalid pipeline")
    parts = [[]]
    for token in args:
        if token == "|":
            if not parts[-1]:
                raise ValueError("empty pipeline stage")
            parts.append([])
        else:
            parts[-1].append(token)
    if len(parts) > 5 or not parts[-1]:
        raise ValueError("invalid pipeline")
    return parts

def run_pipeline(parts, *, deadline=None):
    """One deadline shared by all pipeline stages, including queued time."""
    if deadline is None:
        deadline = time.monotonic() + JOB_TIMEOUT
    previous = None
    truncated = False
    for stage in parts:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return {"exit_code":124,"stdout":"","stderr":"job deadline exhausted","truncated":False,"_deadline_expired":True}
        result = run(stage, input_bytes=previous, timeout=remaining)
        truncated = truncated or result["truncated"]
        if result["exit_code"] != 0:
            result["truncated"] = truncated
            return result
        previous = result["stdout"].encode("utf-8", "replace")
    result["truncated"] = truncated
    return result


def repo_path(name):
    if not name or name.startswith("/"): raise ValueError("invalid relative path")
    p=(ROOT/name).resolve()
    if ROOT not in p.parents or ".git" in Path(name).parts: raise ValueError("path outside repository")
    return p

def current_branch():
    value = git("branch", "--show-current")
    return value["stdout"].strip() if value["exit_code"] == 0 else ""

def main_push_preflight():
    """Inform before writing; server-side rules may still change after the probe."""
    branch = current_branch()
    status = git("status", "--porcelain")
    dirty = bool(status["stdout"].strip()) if status["exit_code"] == 0 else None
    if branch != "main":
        return {"branch":branch,"dirty":dirty,"main_push":"not_applicable"}
    result = git("push","--dry-run","origin","HEAD:refs/heads/main")
    return {"branch":"main","dirty":dirty,"main_push":"rejected" if result["exit_code"] else "dry_run_allowed_unverified",
            "exit_code":result["exit_code"],
            "warning":"dry-run is not proof that branch protection will allow a real push"}

def checkout_branch(branch, create=False):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,120}", branch) or ".." in branch or branch.endswith((".","/")) or branch.startswith("-"):
        raise ValueError("invalid branch")
    dirty = git("status","--porcelain")
    if dirty["exit_code"] or dirty["stdout"].strip():
        raise ValueError("uncommitted work; checkout refused")
    if create:
        return git("switch","-c",branch)
    remote = git("fetch","origin","+refs/heads/"+branch+":refs/remotes/origin/"+branch)
    if remote["exit_code"] != 0:
        return remote
    return git("switch",branch) if git("show-ref","--verify","--quiet","refs/heads/"+branch)["exit_code"] == 0 else git("switch","--track","-c",branch,"origin/"+branch)

def git(*args): return run(["git",*args], git_credentials=True)
def autosave(path):
    branch = current_branch()
    if not branch or branch == "main":
        return {"ok":False,"phase":"preflight","reason":"checkout a named feature branch before autosave"}
    upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    push_args = ("push",) if upstream["exit_code"] == 0 else ("push", "--set-upstream", "origin", branch)
    for args in (("add","--",path),("commit","-m","autosave: "+path),push_args):
        r=git(*args)
        if r["exit_code"]!=0:
            if args[0]=="commit" and "nothing to commit" in r["stdout"]+r["stderr"]:
                return {"ok":True,"phase":"unchanged","result":r}
            return {"ok":False,"phase":args[0],"result":r}
    return {"ok":True,"phase":"push"}

def gh_pr(title,head,base):
    if not PAT: raise ValueError("GITHUB_PAT not configured")
    repo=os.getenv("GITHUB_REPO","Shayfly/desktop-tutorial")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",repo): raise ValueError("invalid GITHUB_REPO")
    if not title or len(title)>180 or not re.fullmatch(r"[A-Za-z0-9_./-]+",head) or not re.fullmatch(r"[A-Za-z0-9_./-]+",base):
        raise ValueError("invalid title or branch")
    payload=json.dumps({"title":title,"head":head,"base":base,"draft":True}).encode()
    req=Request("https://api.github.com/repos/"+repo+"/pulls",data=payload,method="POST",
       headers={"Authorization":"Bearer "+PAT,"Accept":"application/vnd.github+json","Content-Type":"application/json","X-GitHub-Api-Version":"2022-11-28"})
    try:
        with urlopen(req,timeout=30) as r: data=json.load(r)
        return {"ok":True,"number":data["number"],"url":data["html_url"],"head":head,"base":base,"draft":True}
    except HTTPError as e:
        return {"ok":False,"http_status":e.code,"error":"GitHub pull request API rejected request"}

def gh_json(path, method="GET", body=None):
    if not PAT: raise ValueError("GITHUB_PAT not configured")
    repo=os.getenv("GITHUB_REPO","Shayfly/desktop-tutorial")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",repo): raise ValueError("invalid GITHUB_REPO")
    data=json.dumps(body).encode() if body is not None else None
    req=Request("https://api.github.com/repos/"+repo+path,data=data,method=method,
       headers={"Authorization":"Bearer "+PAT,"Accept":"application/vnd.github+json","Content-Type":"application/json","X-GitHub-Api-Version":"2022-11-28"})
    try:
        with urlopen(req,timeout=30) as r: return {"ok":True,"status":r.status,"data":json.load(r)}
    except HTTPError as e:
        try: detail=e.read().decode("utf-8","replace")[:300]
        except Exception: detail=""
        return {"ok":False,"http_status":e.code,"error":"GitHub API rejected request","detail":detail}
def launch_job(parts, timeout=None):
    """Queued/running/done in memory; the deadline begins at admission."""
    admitted = time.monotonic()
    timeout = JOB_TIMEOUT if timeout is None else timeout
    if not (0 < timeout <= JOB_TIMEOUT_MAX):
        raise ValueError("timeout out of range")
    with JOBS_LOCK:
        if len(JOBS) >= MAX_JOBS:
            finished=[key for key,value in JOBS.items() if value["status"]=="done"]
            if finished:
                del JOBS[finished[0]]
            else:
                return None
        job_id=uuid.uuid4().hex
        JOBS[job_id]={"status":"queued","result":None,
                      "sha":None,"dirty":None,
                      "created_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      "queued_seconds":0.0,"timed_out":False,"stage":None}
    def worker():
        queue_deadline=admitted+JOB_QUEUE_MAX
        def done(result,sha=None,dirty=None,stage="command",queue_timeout=False):
            with JOBS_LOCK:
                JOBS[job_id].update(status="done",result=result,sha=sha,dirty=dirty,
                                    stage=stage,timed_out=bool(result.pop("_deadline_expired",False)),
                                    queue_timeout=queue_timeout,
                                    queued_seconds=round(time.monotonic()-admitted,3) if queue_timeout else JOBS[job_id]["queued_seconds"])
        def queue_expired():
            done({"exit_code":125,"stdout":"","stderr":"queue timeout "+str(JOB_QUEUE_MAX)+"s","truncated":False},
                 stage="queue",queue_timeout=True)
        remaining=queue_deadline-time.monotonic()
        if remaining<=0 or not ACTIVE.acquire(timeout=remaining):
            queue_expired()
            return
        try:
            remaining=queue_deadline-time.monotonic()
            if remaining<=0 or not LOCK.acquire(timeout=remaining):
                queue_expired()
                return
            try:
                started=time.monotonic()
                deadline=started+timeout
                with JOBS_LOCK:
                    JOBS[job_id]["queued_seconds"]=round(started-admitted,3)
                def remaining(): return deadline-time.monotonic()
                if remaining()<=0:
                    done({"exit_code":124,"stdout":"","stderr":"timeout "+str(timeout)+"s","truncated":False,"_deadline_expired":True},stage="metadata")
                    return
                info=run(["git","rev-parse","HEAD"],git_credentials=True,timeout=remaining())
                if info["exit_code"]==124:
                    done(info,stage="metadata")
                    return
                sha=info["stdout"].strip() if info["exit_code"]==0 else None
                if remaining()<=0:
                    done({"exit_code":124,"stdout":"","stderr":"timeout "+str(timeout)+"s","truncated":False,"_deadline_expired":True},sha,stage="metadata")
                    return
                dirtyinfo=run(["git","status","--porcelain"],git_credentials=True,timeout=remaining())
                if dirtyinfo["exit_code"]==124:
                    done(dirtyinfo,sha,stage="metadata")
                    return
                dirty=bool(dirtyinfo["stdout"].strip()) if dirtyinfo["exit_code"]==0 else None
                with JOBS_LOCK:
                    JOBS[job_id].update(status="running",sha=sha,dirty=dirty,stage="command")
                if remaining()<=0:
                    done({"exit_code":124,"stdout":"","stderr":"timeout "+str(timeout)+"s","truncated":False,"_deadline_expired":True},sha,dirty)
                    return
                try:
                    result=run_pipeline(parts,deadline=deadline)
                except Exception:
                    result={"exit_code":1,"stdout":"","stderr":"internal execution error","truncated":False}
                done(result,sha,dirty)
            finally:
                LOCK.release()
        finally:
            ACTIVE.release()
    threading.Thread(target=worker,daemon=True,name="repo-job-"+job_id[:8]).start()
    return job_id

class Handler(BaseHTTPRequestHandler):
    def log_message(self,format,*args):
        # Never log raw request URLs; query-string token stays out of application logs.
        pass
    def reply(self,status,obj):
        body=json.dumps(obj,ensure_ascii=False).encode()
        for secret in (TOKEN,PAT):
            if secret:
                body=body.replace(secret.encode(),b"[redacted]")
        self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Cache-Control","no-store");self.send_header("Pragma","no-cache")
        self.send_header("Referrer-Policy","no-referrer")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
    def dispatch(self):
        q=parse_qs(urlsplit(self.path).query,keep_blank_values=True)
        pathname=urlsplit(self.path).path
        supplied=q.get("token",[""])[0]
        header=self.headers.get("Authorization","")
        if pathname=="/health" and self.command=="GET": return self.reply(200,{"ok":True,"repo_exists":(ROOT/".git").exists()})
        if not TOKEN or not (hmac.compare_digest(supplied,TOKEN) or hmac.compare_digest(header,"Bearer "+TOKEN)):
            return self.reply(401,{"error":"unauthorized"})
        if pathname=="/health": return self.reply(200,{"ok":True,"repo_exists":(ROOT/".git").exists()})
        if not (ROOT/".git").exists(): return self.reply(503,{"error":"clone not available"})
        try:
            if pathname in ("/run","/job"):
                return self.dispatch_jobs(pathname,q)
            is_mutation = (pathname=="/write" or
                           (pathname=="/git" and q.get("op",[""])[0] not in ("status","diff","log")) or
                           pathname=="/pr")
            with (LOCK if is_mutation else contextlib.nullcontext()):
                if pathname=="/preflight" and self.command=="GET":
                    return self.reply(200,main_push_preflight())
                if pathname=="/read" and self.command=="GET":
                    p=repo_path(q.get("path",[""])[0])
                    if not p.is_file() or p.stat().st_size>MAX: return self.reply(413,{"error":"not a readable file <=50KB"})
                    b=p.read_bytes();return self.reply(200,{"content":b.decode("utf-8","replace"),"b64":base64.b64encode(b).decode(),"bytes":len(b)})
                if pathname=="/write" and self.command in ("GET","POST"):
                    name=q.get("path",[""])[0];p=repo_path(name)
                    branch=current_branch()
                    if not branch or branch=="main":
                        audit("write:denied","blocked","non-feature branch")
                        return self.reply(409,{"error":"checkout a named feature branch before writing"})
                    if p.is_symlink(): raise ValueError("symlink not allowed")
                    if self.command=="GET":
                        raw=q.get("b64",[""])[0]
                        if not raw or len(raw)>12000: raise ValueError("invalid b64 length")
                        data=base64.b64decode(raw,altchars=b"-_",validate=True)
                        append=q.get("append",["0"])[0]
                    else:
                        n=int(self.headers.get("Content-Length","0"))
                        if n<=0 or n>128*1024: raise ValueError("invalid body length")
                        data=self.rfile.read(n);append=self.headers.get("X-Append","0")
                    if append not in ("0","1") or not data or len(data)>128*1024: raise ValueError("invalid write")
                    p.parent.mkdir(parents=True,exist_ok=True)
                    with p.open("ab" if append=="1" else "wb") as f:f.write(data)
                    saved=autosave(name);audit("write","ok" if saved["ok"] else "partial",name)
                    return self.reply(200 if saved["ok"] else 503,{"written":name,"bytes":len(data),"git_persistence":saved})
                if pathname=="/git" and self.command in ("GET","POST"):
                    op=q.get("op",[""])[0]
                    commands={"status":["git","status","--short","--branch"],"diff":["git","diff","--no-ext-diff"],"log":["git","log","-10","--oneline"],"pull":["git","pull","--ff-only"],"add":["git","add","--all"],"push":["git","push"]}
                    if op=="checkout":
                        branch=q.get("branch",[""])[0]
                        create=q.get("create",["0"])[0]=="1" or q.get("new",["0"])[0]=="1"
                        result=checkout_branch(branch,create)
                        audit("git:checkout","ok" if result["exit_code"]==0 else "failed",branch)
                        return self.reply(200 if result["exit_code"]==0 else 409,result)
                    if op=="push" and current_branch()=="main":
                        return self.reply(409,{"error":"main push blocked by service policy; use a feature branch"})
                    if op=="commit":
                        msg=q.get("msg",[""])[0] if self.command=="GET" else self.headers.get("X-Commit-Message","")
                        if not msg or len(msg)>180 or "\n" in msg:raise ValueError("invalid commit message")
                        cmd=["git","commit","-m",msg]
                    else:cmd=commands.get(op)
                    if cmd is None:raise ValueError("unsupported git op")
                    result=run(cmd, git_credentials=True)
                    if op in ("pull","add","commit","push"):audit("git:"+op,"ok" if result["exit_code"]==0 else "failed")
                    return self.reply(200 if result["exit_code"]==0 else 409,result)
                if pathname=="/pr" and self.command=="GET" and q.get("op",[""])[0]=="rebase":
                    num=q.get("number",[""])[0]
                    if not re.fullmatch(r"[0-9]+",num): raise ValueError("invalid pr number")
                    d=gh_json("/pulls/"+num)
                    if not d["ok"]: return self.reply(502,d)
                    dd=d["data"]
                    hb=dd["head"]["ref"]
                    if dd["base"]["ref"]!="main":
                        t=gh_json("/pulls/"+num,method="PATCH",body={"base":"main"})
                        if not t["ok"]: return self.reply(502,t)
                    checkout_branch(hb)
                    git("reset","--hard","origin/"+hb)
                    r=git("rebase","origin/main")
                    if r["exit_code"]!=0:
                        if q.get("theirs",["0"])[0]=="1":
                            git("rebase","--abort")
                            r=git("rebase","-X","theirs","origin/main")
                        if r["exit_code"]!=0:
                            f=git("diff","--name-only","--diff-filter=U")
                            git("rebase","--abort")
                            audit("pr:rebase","conflict",num)
                            return self.reply(409,{"ok":False,"pr":num,"branch":hb,"conflict":f["stdout"][:400]})
                    p=git("push","--force","origin",hb)
                    audit("pr:rebase","ok" if p["exit_code"]==0 else "failed",num)
                    return self.reply(200,{"ok":p["exit_code"]==0,"pr":num,"branch":hb,"push_exit":p["exit_code"]})
                if pathname=="/pr" and self.command=="GET" and q.get("op",[""])[0] in ("sweep","retarget"):
                    op=q.get("op",[""])[0]
                    r=gh_json("/pulls?state=open&per_page=100")
                    if not r["ok"]: return self.reply(502,r)
                    out=[]
                    for p in r["data"]:
                        n=p["number"]
                        b=p["base"]["ref"]
                        if op=="retarget":
                            if b=="main": continue
                            c=gh_json("/compare/"+b+"...main")
                            if not c["ok"] or (c["data"] or {}).get("status") not in ("identical","ahead"): continue
                            t=gh_json("/pulls/"+str(n),method="PATCH",body={"base":"main"})
                            out.append(str(n)+" retarget "+b+" -> "+("ok" if t["ok"] else "fail"))
                            continue
                        if p["draft"] and q.get("drafts",["0"])[0]!="1": continue
                        if b!="main": continue
                        d=gh_json("/pulls/"+str(n))
                        dd=d.get("data") or {}
                        if dd.get("mergeable_state")!="clean":
                            out.append(str(n)+" skip "+str(dd.get("mergeable_state")))
                            continue
                        m=gh_json("/pulls/"+str(n)+"/merge",method="PUT",body={"merge_method":"squash"})
                        out.append(str(n)+" merge "+("ok" if m["ok"] else "fail"))
                    audit("pr:"+op,"ok",str(len(out)))
                    return self.reply(200,{"ok":True,"op":op,"count":len(out),"actions":out})
                if pathname=="/pr" and self.command=="GET" and q.get("op",[""])[0] in ("get","scan"):
                    if q.get("op",[""])[0]=="scan":
                        r=gh_json("/pulls?state=open&per_page=100&sort=created&direction=asc")
                        if not r["ok"]: return self.reply(502,r)
                        lines=[]
                        for p in r["data"]:
                            n=p["number"]
                            d=gh_json("/pulls/"+str(n))
                            dd=d.get("data") or {}
                            lines.append(" ".join([str(n),"DRAFT" if p["draft"] else "READY","base="+p["base"]["ref"],"state="+str(dd.get("mergeable_state")),"files="+str(dd.get("changed_files")),"auto="+("y" if p.get("auto_merge") else "n"),p["created_at"][:10],p["title"][:46]]))
                        audit("pr:scan","ok",str(len(lines)))
                        return self.reply(200,{"ok":True,"count":len(lines),"lines":lines})
                    num=q.get("number",[""])[0]
                    if not re.fullmatch(r"[0-9]+",num): raise ValueError("invalid pr number")
                    d=gh_json("/pulls/"+num)
                    if not d["ok"]: return self.reply(502,d)
                    dd=d["data"]
                    audit("pr:get","ok",num)
                    return self.reply(200,{"ok":True,"number":dd["number"],"title":dd["title"],"draft":dd["draft"],"base":dd["base"]["ref"],"head":dd["head"]["ref"],"state":dd.get("mergeable_state"),"mergeable":dd.get("mergeable"),"files":dd.get("changed_files"),"adds":dd.get("additions"),"dels":dd.get("deletions"),"auto_merge":bool(dd.get("auto_merge")),"created":dd["created_at"][:10],"body":(dd.get("body") or "")[:200]})
                if pathname=="/pr" and self.command=="GET" and q.get("op",[""])[0] in ("list","ready","merge"):
                    op=q.get("op",[""])[0]
                    num=q.get("number",[""])[0]
                    if op=="list":
                        r=gh_json("/pulls?state=open&per_page=100")
                        if not r["ok"]: return self.reply(502,r)
                        items=[{"n":p["number"],"title":p["title"][:90],"draft":p["draft"],"head":p["head"]["ref"],"base":p["base"]["ref"],"mergeable_state":p.get("mergeable_state"),"created":p["created_at"][:10]} for p in r["data"]]
                        audit("pr:list","ok",str(len(items)))
                        return self.reply(200,{"ok":True,"count":len(items),"pulls":items})
                    if not re.fullmatch(r"[0-9]+",num): raise ValueError("invalid pr number")
                    if op=="ready":
                        r=gh_json("/pulls/"+num,method="PATCH",body={"draft":False})
                        audit("pr:ready","ok" if r["ok"] else "failed",num)
                        return self.reply(200 if r["ok"] else 502,r)
                    r=gh_json("/pulls/"+num+"/merge",method="PUT",body={"merge_method":q.get("method",["squash"])[0]})
                    audit("pr:merge","ok" if r["ok"] else "failed",num)
                    return self.reply(200 if r["ok"] else 502,r)
                if pathname=="/pr" and self.command=="GET" and q.get("op",[""])[0]=="create":
                    result=gh_pr(q.get("title",[""])[0],q.get("head",[""])[0],q.get("base",["main"])[0])
                    audit("pr:create","ok" if result["ok"] else "failed")
                    return self.reply(201 if result["ok"] else 502,result)
        except (ValueError, OSError, binascii.Error) as e:
            return self.reply(400,{"error":str(e)})
        return self.reply(404,{"error":"not found"})
    def dispatch_jobs(self,pathname,q):
        if pathname=="/job" and self.command=="GET":
            job_id=q.get("id",[""])[0]
            with JOBS_LOCK:
                job=JOBS.get(job_id)
                snapshot=dict(job) if job else None
            return self.reply(200 if snapshot else 404,
                              {"id":job_id,**snapshot} if snapshot else {"error":"job not found"})
        if pathname=="/run" and self.command=="GET":
            parts=split_pipeline(q.get("cmd",[""])[0])
            if not all(validate_segment(argv) for argv in parts):
                audit("run:denied","blocked","command allowlist or mutating flag")
                return self.reply(403,{"error":"command not allowed; write via /write"})
            if q.get("async",["0"])[0]=="1":
                requested=q.get("timeout",[""])[0]
                seconds=JOB_TIMEOUT if not requested else float(requested)
                if not __import__("math").isfinite(seconds): raise ValueError("invalid timeout")
                if not (0 < seconds <= JOB_TIMEOUT_MAX):
                    raise ValueError("timeout must be >0 and <=900")
                job_id=launch_job(parts,timeout=seconds)
                if job_id is None: return self.reply(429,{"error":"job queue full"})
                return self.reply(202,{"id":job_id,"status":"queued"})
            if "timeout" in q:
                return self.reply(400,{"error":"timeout requires async=1"})
            return self.reply(200,run_pipeline(parts))
        return self.reply(404,{"error":"not found"})
    def do_GET(self):self.dispatch()
    def do_POST(self):self.dispatch()

if __name__=="__main__":
    if len(TOKEN)<40:raise SystemExit("SERVICE_TOKEN requires >=40 random characters")
    if not (ROOT/".git").exists():raise SystemExit("repo missing (entrypoint should clone)")
    ThreadingHTTPServer(("0.0.0.0",PORT),Handler).serve_forever()
