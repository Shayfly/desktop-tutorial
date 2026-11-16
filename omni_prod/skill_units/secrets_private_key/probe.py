"""skill.secrets.private_key -- static: No private key (PEM block) is written into the generated source.
The patterns are the repository's own scanner's (omni_prod.secret_scan), so the build and the repository are held to one definition. Reads source: the gate runs it on every text file."""
from omni_prod.secret_scan import scan_text

KINDS = ('private_key',)

def probe(text):
    findings = [{'where': f'line {f.line}', 'why': f.kind} for f in scan_text(text or '')
                if f.kind in KINDS]
    return {'status': 'fail', 'code': 'PRIVATE_KEY_IN_SOURCE', 'findings': findings} if findings else {'status': 'pass'}
