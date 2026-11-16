"""skill.perf.blocking_script -- static: an external <script src> without defer/async/type=module blocks rendering."""
from omni_prod.skill_units import tags


def probe(html):
    findings = []
    for _, tag, a in tags(html):
        if tag == 'script' and a.get('src') and 'defer' not in a and 'async' not in a and a.get('type') != 'module':
            findings.append({'where': a['src'], 'why': 'no defer, async or type="module"'})
    return {'status': 'fail', 'code': 'SCRIPT_BLOCKING', 'findings': findings} if findings else {'status': 'pass'}
