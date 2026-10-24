"""Isolated, token-authenticated GET control plane. Never deploy with production credentials."""
import base64, binascii, datetime, hmac, json, os, re, shlex, subprocess, threading
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
ALLOWED={"pytest","python3","git","grep","find","ls","cat","head","tail","wc","diff","sed","awk","tree","pwd","rg"}
GIT_READ={"status","diff","log","show","rev-parse","branch"}
DENY={"-exec","-execdir","-ok","-okdir","--exec","--output","-c","-f","--file","--config","-o","--pager","--external-diff"}
def audit(action, result, detail=""):
    item={"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"action":action,"result":result,"detail":str(detail)[:150]}
    # No URL, token, command, file body, or GitHub API response in application logs.
    print(json.dumps(item),flush=True)

def run(args):
    try:
        p=subprocess.run(args,cwd=ROOT,env={**os.environ,"GIT_TERMINAL_PROMPT":"0","GIT_ASKPASS":"/app/askpass.sh"},
                         shell=False,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
        output=p.stdout[:MAX]; err=p.stderr[:MAX-len(output)]
        out=output.decode("utf-8","replace"); error=err.decode("utf-8","replace")
        for secret in (PAT,TOKEN):
            if secret: out=out.replace(secret,"[redacted]"); error=error.replace(secret,"[redacted]")
        return {"exit_code":p.returncode,"stdout":out,"stderr":error,"truncated":len(p.stdout)+len(p.stderr)>MAX}
    except subprocess.TimeoutExpired: return {"exit_code":124,"stdout":"","stderr":"timeout 120s","truncated":True}
    except OSError as e: return {"exit_code":127,"stdout":"","stderr":type(e).__name__,"truncated":False}

def repo_path(name):
    if not name or name.startswith("/"): raise ValueError("invalid relative path")
    p=(ROOT/name).resolve()
    if ROOT not in p.parents or ".git" in Path(name).parts: raise ValueError("path outside repository")
    return p

def git(*args): return run(["git",*args])
def autosave(path):
    for args in (("add","--",path),("commit","-m","autosave: "+path),("push",)):
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

class Handler(BaseHTTPRequestHandler):
    def log_message(self,format,*args):
        # Never log raw request URLs; query-string token stays out of application logs.
        pass
    def reply(self,status,obj):
        body=json.dumps(obj,ensure_ascii=False).encode()
        for secret in (TOKEN,PAT):
            if secret: body=body.replace(secret.encode(),b"[redacted]")
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
            with LOCK:
                if pathname=="/read" and self.command=="GET":
                    p=repo_path(q.get("path",[""])[0])
                    if not p.is_file() or p.stat().st_size>MAX: return self.reply(413,{"error":"not a readable file <=50KB"})
                    b=p.read_bytes();return self.reply(200,{"content":b.decode("utf-8","replace"),"b64":base64.b64encode(b).decode(),"bytes":len(b)})
                if pathname=="/write" and self.command in ("GET","POST"):
                    name=q.get("path",[""])[0];p=repo_path(name)
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
                if pathname=="/run" and self.command=="GET":
                    argv=shlex.split(q.get("cmd",[""])[0])
                    if not argv or argv[0] not in ALLOWED or any(x in DENY or x.startswith("-exec") for x in argv[1:]):
                        return self.reply(403,{"error":"command not allowed"})
                    if argv[0]=="git" and (len(argv)<2 or argv[1] not in GIT_READ):return self.reply(403,{"error":"git read only"})
                    if argv[0]=="python3" and argv[1:3] not in (["-m","pytest"],["-m","compileall"]):return self.reply(403,{"error":"python3 restricted"})
                    return self.reply(200,run(argv))
                if pathname=="/git" and self.command in ("GET","POST"):
                    op=q.get("op",[""])[0]
                    commands={"status":["git","status","--short","--branch"],"diff":["git","diff","--no-ext-diff"],"log":["git","log","-10","--oneline"],"pull":["git","pull","--ff-only"],"add":["git","add","--all"],"push":["git","push"]}
                    if op=="commit":
                        msg=q.get("msg",[""])[0] if self.command=="GET" else self.headers.get("X-Commit-Message","")
                        if not msg or len(msg)>180 or "\n" in msg:raise ValueError("invalid commit message")
                        cmd=["git","commit","-m",msg]
                    else:cmd=commands.get(op)
                    if cmd is None:raise ValueError("unsupported git op")
                    result=run(cmd)
                    if op in ("pull","add","commit","push"):audit("git:"+op,"ok" if result["exit_code"]==0 else "failed")
                    return self.reply(200 if result["exit_code"]==0 else 409,result)
                if pathname=="/pr" and self.command=="GET" and q.get("op",[""])[0]=="create":
                    result=gh_pr(q.get("title",[""])[0],q.get("head",[""])[0],q.get("base",["main"])[0])
                    audit("pr:create","ok" if result["ok"] else "failed")
                    return self.reply(201 if result["ok"] else 502,result)
        except (ValueError, OSError, binascii.Error) as e:
            return self.reply(400,{"error":str(e)})
        return self.reply(404,{"error":"not found"})
    def do_GET(self):self.dispatch()
    def do_POST(self):self.dispatch()

if __name__=="__main__":
    if len(TOKEN)<40:raise SystemExit("SERVICE_TOKEN requires >=40 random characters")
    if not (ROOT/".git").exists():raise SystemExit("repo missing (entrypoint should clone)")
    ThreadingHTTPServer(("0.0.0.0",PORT),Handler).serve_forever()
