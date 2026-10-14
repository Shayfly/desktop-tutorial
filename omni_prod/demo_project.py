from __future__ import annotations
from dataclasses import dataclass
from html import escape
import json
import re

from .autonomous_core import ExecutionReport, AcceptanceFailure
from .product_spec import ProductSpec
from .project_manifest import ProjectManifest


def _title_from_prompt(prompt: str) -> str:
    cleaned = re.sub(r'\s+', ' ', prompt).strip()
    if not cleaned:
        raise ValueError('prompt cannot be empty')
    words = cleaned.split(' ')[:7]
    return ' '.join(words)[:80]


_CATEGORY_RULES = (
    ('crm', ('crm','customer','technician','pipeline','lead')),
    ('booking', ('booking','reservation','appointment','hotel','calendar')),
    ('marketplace', ('marketplace','provider','courier','delivery','uber')),
    ('commerce', ('ecommerce','store','shop','cart','checkout','inventory')),
    ('analytics', ('analytics','dashboard','cohort','funnel','metrics')),
    ('game3d', ('3d game','football game','soccer game','unreal','unity','godot')),
    ('mobile', ('mobile app','android','ios','offline app')),
)
_CATEGORY_MODULES = {
    'crm': ('Customers','Pipeline','Jobs','Team','Payments','Reports'),
    'booking': ('Availability','Bookings','Customers','Resources','Payments','Reminders'),
    'marketplace': ('Listings','Customers','Providers','Orders','Reviews','Payouts'),
    'commerce': ('Catalog','Inventory','Cart','Orders','Payments','Refunds'),
    'analytics': ('Overview','Funnels','Cohorts','Events','Exports','Alerts'),
    'game3d': ('Game Loop','Players','Physics','Progression','Audio','Performance'),
    'mobile': ('Home','Offline Queue','Media','Notifications','Sync','Settings'),
    'web': ('Overview','Content','Forms','Users','Analytics','Settings'),
}

def classify_demo_category(prompt: str) -> str:
    lower=prompt.lower()
    for category,words in _CATEGORY_RULES:
        if any(w in lower for w in words): return category
    return 'web'


def demo_spec(prompt: str) -> ProductSpec:
    title = _title_from_prompt(prompt)
    return ProductSpec.from_dict({
        'title': title,
        'summary': f'Offline demonstrator generated from: {prompt[:300]}',
        'stack': ['HTML5', 'CSS3', 'JavaScript'],
        'requirements': [
            {'id': 'R1', 'text': 'Create a runnable responsive web preview', 'kind': 'functional', 'mandatory': True},
            {'id': 'R2', 'text': 'Preserve the original product request in the generated project', 'kind': 'data', 'mandatory': True},
            {'id': 'R3', 'text': 'Include machine-readable Omni build verification metadata', 'kind': 'quality', 'mandatory': True},
        ],
        'acceptance': [
            {'id': 'A1', 'requirement_id': 'R1', 'text': 'index.html contains a responsive application shell'},
            {'id': 'A2', 'requirement_id': 'R2', 'text': 'request.json contains the original prompt'},
            {'id': 'A3', 'requirement_id': 'R3', 'text': '.omni/project.json maps verification commands to acceptance ids'},
        ],
    })


def create_demo_repository(prompt: str, spec: ProductSpec) -> dict[str, str]:
    safe_title = escape(spec.title)
    safe_prompt = escape(prompt[:2000])
    category = classify_demo_category(prompt)
    modules = _CATEGORY_MODULES[category]
    module_cards = ''.join(f'<article><h2>{escape(name)}</h2><p>Generated {escape(category)} module contract.</p></article>' for name in modules)
    manifest = {
        'build': [],
        'verify': [
            {'name': 'html exists', 'argv': ['python', '-c', "from pathlib import Path; assert Path('index.html').exists()"], 'acceptance_ids': ['A1']},
            {'name': 'request preserved', 'argv': ['python', '-c', "import json; assert json.load(open('request.json', encoding='utf-8'))['prompt']"], 'acceptance_ids': ['A2']},
            {'name': 'manifest present', 'argv': ['python', '-c', "from pathlib import Path; assert Path('.omni/project.json').exists()"], 'acceptance_ids': ['A3']},
        ],
    }
    html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{safe_title} — Omni Preview</title><link rel="stylesheet" href="styles.css"></head>
<body><main class="shell"><header><span class="badge">OMNI GENERATED PREVIEW</span><h1>{safe_title}</h1>
<p class="lead">{safe_prompt}</p><p class="category">Category: {category}</p></header><section class="grid">{module_cards}</section><button id="action">Run interaction</button><p id="result" aria-live="polite"></p></main><script src="app.js"></script></body></html>'''
    css = '''*{box-sizing:border-box}body{margin:0;font-family:Inter,system-ui,sans-serif;background:#0b1020;color:#f7f8fb;min-height:100vh}.shell{max-width:1050px;margin:auto;padding:64px 24px}.badge{font-size:12px;letter-spacing:.12em;border:1px solid #4e5b7e;border-radius:999px;padding:8px 12px}h1{font-size:clamp(38px,7vw,78px);line-height:.95;margin:24px 0}.lead{max-width:780px;color:#b9c1d5;font-size:19px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:42px 0}.grid article{background:#121a31;border:1px solid #26314f;border-radius:20px;padding:22px}button{border:0;border-radius:14px;padding:14px 20px;font-weight:700;cursor:pointer}@media(max-width:760px){.grid{grid-template-columns:1fr}.shell{padding-top:36px}}'''
    js = "document.getElementById('action').onclick=()=>{document.getElementById('result').textContent='Interaction verified locally.'}"
    return {
        'index.html': html,
        'styles.css': css,
        'app.js': js,
        'request.json': json.dumps({'prompt': prompt, 'spec': spec.to_dict()}, ensure_ascii=False, indent=2),
        '.omni/project.json': json.dumps(manifest, indent=2),
        'domain.json': json.dumps({'category':category,'modules':list(modules)}, ensure_ascii=False, indent=2),
        'openapi.json': json.dumps({'openapi':'3.1.0','info':{'title':spec.title,'version':'0.1.0'},'paths':{'/health':{'get':{'responses':{'200':{'description':'ok'}}}}}}, indent=2),
        'schema.sql': 'CREATE TABLE app_events (id INTEGER PRIMARY KEY, module TEXT NOT NULL, payload TEXT NOT NULL);\n',
        'README.md': f'# {spec.title}\n\nOffline deterministic {category} starter. Live AI generation requires a configured local model endpoint.\n\nModules: '+', '.join(modules)+'\n',
        'package.json': json.dumps({'name':'omni-preview','private':True,'scripts':{'test':'python tests/smoke_test.py'}}, indent=2),
        'tests/smoke_test.py': "from pathlib import Path\nassert Path('index.html').exists()\nassert 'aria-live' in Path('index.html').read_text()\n",
        'locales/en.json': json.dumps({'build':'Build','status':'Status'}, indent=2),
        'locales/he.json': json.dumps({'build':'בנייה','status':'סטטוס'}, ensure_ascii=False, indent=2),
        'i18n/README.md': '# i18n\nEnglish default. Hebrew is RTL. Locale formatting must use platform Intl APIs.\n',
        '.github/workflows/verify.yml': 'name: verify\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n        with: {python-version: \"3.12\"}\n      - run: python tests/smoke_test.py\n',
        'Dockerfile': 'FROM nginx:alpine\nCOPY index.html styles.css app.js /usr/share/nginx/html/\n',
    }


class StaticDemoVerifier:
    """Non-executing verifier for the offline investor demonstration.

    This intentionally does not execute generated code. Production/live builds use
    SandboxRepositoryExecutor and Docker instead.
    """

    def execute(self, *, repository: dict[str, str], spec: ProductSpec) -> ExecutionReport:
        failures: list[AcceptanceFailure] = []
        if '<meta name="viewport"' not in repository.get('index.html', ''):
            failures.append(AcceptanceFailure('A1', 'responsive viewport missing', 'index.html'))
        try:
            payload = json.loads(repository.get('request.json', '{}'))
            if not payload.get('prompt'):
                raise ValueError('prompt missing')
        except Exception as exc:
            failures.append(AcceptanceFailure('A2', 'request trace missing', str(exc)))
        try:
            manifest = ProjectManifest.from_repository(repository)
            known = {a.id for a in spec.acceptance}
            referenced = {aid for check in manifest.verify for aid in check.acceptance_ids}
            if not known.issubset(referenced):
                raise ValueError('not all acceptance ids are verified')
        except Exception as exc:
            failures.append(AcceptanceFailure('A3', 'project manifest invalid', str(exc)))
        return ExecutionReport(not failures, tuple(failures), 'static offline verifier; no generated code executed')
