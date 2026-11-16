"""skill.secrets.assignment -- static: No password, secret, token or API key is assigned a literal value in the generated source (a value read from the environment is fine).
The patterns are the repository's own scanner's (omni_prod.secret_scan), so the build and the repository are held to one definition. Reads source: the gate runs it on every text file."""
from omni_prod.secret_scan import scan_text

KINDS = ('credential_assignment',)
# a value read from the environment at run time is not a hard-coded credential
_RUNTIME = ('process.env', 'os.environ', 'getenv(', 'import.meta.env')


def probe(text):
    findings = [{'where': f'line {f.line}', 'why': f.kind} for f in scan_text(text or '')
                if f.kind in KINDS and not any(r in f.preview for r in _RUNTIME)]
    return {'status': 'fail', 'code': 'HARDCODED_CREDENTIAL', 'findings': findings} if findings else {'status': 'pass'}
