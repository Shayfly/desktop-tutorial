"""Identity of everything 148AI tells its models and checks with, for a fixed set of briefs (Michael 2026-11-10).

Model output is not deterministic, so "byte-identical output" can never be the test. What CAN be frozen is every
input the pipeline gives the models and every check it judges with:
  * the role instructions (architect, generator, repair, evolution, reviewer system prompts incl. skill guidance)
  * the reviewer checklist and the static probes that run
  * the sandbox scripts (behavioural acceptance runner + driver, visual QA, preview smoke)
  * the verification chain (stage classes, in order)
  * for each frozen-run brief: the deterministic contract scope (acceptance floor and waived kinds), the fact canon
`digest()` hashes them; with every flag off it must equal the digest recorded at the baseline commit.

Michael 2026-11-10 fix 1: that digest covers WHAT the pipeline says, not the CODE that runs the checks. A change to
the runner's behaviour with the flag off would pass it silently. `source_identity()` closes that: the whole import
closure of the gates (roots = the frozen gate files + the behavioural runner; the closure is computed from the code,
never a hand-written list) is compared with the baseline file by file, as ASTs, after removing exactly
  * `if <FLAG>:` blocks and `from .feature_flags import ...` lines (anywhere, at any depth),
  * the names a module declares in `_FLAG_ONLY` (and the declaration itself).
Comments and formatting do not count; every other change does. A `_FLAG_ONLY` name referenced outside a flag block
anywhere in the closure fails the check, so declaring a name flag-only cannot hide a live change. Non-Python gate
files (the workflow) are compared byte for byte.
"""
from __future__ import annotations

import hashlib
import json

# The five frozen-run briefs (docs/frozen-run-20261110.md). The cafe and florist texts are the real ones.
ARM_BRIEFS = {
    'restaurant': ('אני רוצה דף נחיתה בעברית לעסק שלי. שם העסק: קפה "בוקר טוב" – בית קפה שכונתי כתובת: רחוב הנביאים 12, '
                   'חיפה טלפון ו-WhatsApp: 050-1234567 שעות פתיחה: א׳–ה׳ 07:00–19:00, ו׳ 07:00–14:00, שבת סגור. '
                   'שלוש ביקורות של לקוחות: • "הקפה הכי טוב בחיפה" – דנה • "ארוחת בוקר מושלמת, נחזור" – יוסי ומיכל '
                   '• "שירות חם ומחירים הוגנים" – אבי. בלי הרשמה, בלי התחברות ובלי תשלום.'),
    'florist-hard': ('תבנה לי דף לחנות הפרחים שלי, "שושנת העמקים", ברח\' נתיב המזלות 22, ירושלים.\n'
                     'שיהיה יפה, ורוד וירוק, לא משהו כבד.\n'
                     'שיהיה כפתור להתקשר 052-1234567 וכפתור וואטסאפ לאותו מספר, עם הודעה מוכנה "היי, אשמח להזמין זר".\n'
                     "אנחנו פתוחים א'–ה' 8:00–19:00, ו' 8:00–13:00, שבת סגור.\n"
                     'שיהיה קטע עם מה שאומרים עלינו, ורשימה של זרים לחתונה, ליומולדת ולניחומים.\n'
                     'ותכתוב שאפשר גם להזמין משלוח באותו יום.'),
    'florist-new': ('תבנה לי דף לחנות הפרחים שלי, "שושנת העמקים", בירושלים.\nשיהיה יפה, ורוד וירוק, לא משהו כבד.\n'
                    'שיהיה קטע עם מה שאומרים עלינו, ורשימה של זרים לחתונה, ליומולדת ולניחומים.'),
    'negative': 'אפליקציית אייפון נייטיב עם תשלומים בתוך האפליקציה ו-Apple Pay',
    'saas-with-login': 'מערכת לניהול תורים לקוסמטיקאית עם התחברות ללקוחות ולמנהלת, לקוחה קובעת ומבטלת תור.',
}


def components() -> dict:
    from . import autonomous_agents as agents
    from . import behavior_acceptance, preview_smoke, visual_qa
    from .fact_canon import build_canon
    from .product_architect import content_only_approved, no_login_requested
    from .product_evolution import __dict__ as evo
    from .skills_runtime import WEB_SKILLS, checklist_for_review
    from .web_saas_acceptance import WEB_SAAS_REQUIRED_KINDS
    prompts = {name: getattr(agents, name) for name in sorted(dir(agents))
               if name.endswith('_SYSTEM') and isinstance(getattr(agents, name), str)}
    prompts.update({f'evolution.{k}': v for k, v in sorted(evo.items()) if k.endswith('_SYSTEM') and isinstance(v, str)})
    arms = {}
    for arm, text in ARM_BRIEFS.items():
        arms[arm] = {'no_login': no_login_requested(text), 'content_only': content_only_approved(text),
                     'canon': build_canon(text).to_dict()}
    return {
        'prompts': prompts,
        'skills': [{'key': s.key, 'version': s.version, 'roles': list(s.roles), 'guidance': s.guidance,
                    'checklist': list(s.checklist), 'probes': [c.__name__ for c in s.static_checks]} for s in WEB_SKILLS],
        'review_checklist': checklist_for_review(),
        'required_kinds': list(WEB_SAAS_REQUIRED_KINDS),
        'scripts': {'behavior_runner': behavior_acceptance._RUNNER_SOURCE, 'behavior_driver': behavior_acceptance._SCRIPT,
                    'visual_qa': visual_qa.SCRIPT, 'preview_smoke': preview_smoke._SMOKE},
        'arms': arms,
    }


import ast
import os
from pathlib import Path

FLAG_NAMES = {'SITE_AUTH_V2', '_SITE_AUTH_V2'}
ROOT = Path(__file__).resolve().parent.parent


def _is_flag_test(node) -> bool:
    t = node.test if isinstance(node, ast.If) else None
    if isinstance(t, ast.Name):
        return t.id in FLAG_NAMES
    if isinstance(t, ast.Attribute):
        return t.attr in FLAG_NAMES
    return False


def _flag_only(tree) -> set[str]:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '_FLAG_ONLY' for t in node.targets):
            try:
                value = ast.literal_eval(node.value)
            except ValueError:
                return set()
            return {n for names in value.values() for n in names}
    return set()


class _Strip(ast.NodeTransformer):
    def __init__(self, flag_only: set[str]):
        self.flag_only = flag_only
        self.removed_blocks = 0          # Michael fix 2: what was removed is reported, never silent
        self.removed_lines = 0

    def _keep(self, node) -> bool:
        if isinstance(node, ast.If) and _is_flag_test(node):
            return False
        if isinstance(node, ast.ImportFrom) and (node.module or '').endswith('feature_flags'):
            return False
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and node.name in self.flag_only:
            return False
        if isinstance(node, ast.Assign):
            names = {t.id for t in node.targets if isinstance(t, ast.Name)}
            if names and (names <= self.flag_only or names == {'_FLAG_ONLY'}):
                return False
        return True

    def generic_visit(self, node):
        for field, value in ast.iter_fields(node):
            if isinstance(value, list) and value and isinstance(value[0], ast.stmt):
                for n in value:
                    if not self._keep(n):
                        self.removed_blocks += 1
                        self.removed_lines += (getattr(n, 'end_lineno', n.lineno) or n.lineno) - n.lineno + 1
                kept = [self.visit(n) for n in value if self._keep(n)]
                setattr(node, field, kept or [ast.Pass()])
            elif isinstance(value, ast.AST):
                self.visit(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item)
        return node


def stripped(source: str, stats: dict | None = None) -> tuple[str, set[str], set[str]]:
    """(AST dump with flag additions removed, flag-only names, names still referenced after stripping)."""
    tree = ast.parse(source)
    flag_only = _flag_only(tree)
    strip = _Strip(flag_only)
    tree = strip.visit(tree)
    if stats is not None:
        stats.update(blocks=strip.removed_blocks, lines=strip.removed_lines, names=len(flag_only))
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | \
        {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    return ast.dump(tree, include_attributes=False), flag_only, used


def _imports(dump_source: str, path: str) -> set[str]:
    """omni_prod modules a (stripped) module imports, as repo paths."""
    tree = ast.parse(dump_source)
    tree = _Strip(_flag_only(tree)).visit(tree)
    pkg = Path(path).parent
    out = set()
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.ImportFrom):
            if node.level:
                base = pkg
                for _ in range(node.level - 1):
                    base = base.parent
                mod = (base / (node.module or '').replace('.', '/')) if node.module else base
                names = [mod] + [mod / a.name for a in node.names]
            elif (node.module or '').startswith('omni_prod'):
                mod = Path(node.module.replace('.', '/'))
                names = [mod] + [mod / a.name for a in node.names]
        elif isinstance(node, ast.Import):
            names = [Path(a.name.replace('.', '/')) for a in node.names if a.name.startswith('omni_prod')]
        for n in names:
            for cand in (n.with_suffix('.py'), n / '__init__.py'):
                if (ROOT / cand).is_file():
                    out.add(str(cand))
    return out


def gate_roots() -> list[str]:
    freeze = json.load(open(ROOT / 'docs' / 'gate-freeze.json', encoding='utf-8'))
    return sorted(set(freeze['gate_files']) | {'omni_prod/web_saas_acceptance.py', 'omni_prod/behavior_acceptance.py'})


def _named_py(source: str, path: str) -> set[str]:
    """Python files a module NAMES in a string literal (it reads them as text -- e.g. the runner source shipped into
    the sandbox). They are gate inputs exactly like imports (the coverage test found four on day one)."""
    # a name inside a flag block is not a flag-off input (named_files scans the stripped tree)
    return {rel for rel in named_files(source, path) if rel.endswith('.py') and rel.startswith('omni_prod/')}


def closure(read=lambda p: (ROOT / p).read_text(encoding='utf-8')) -> list[str]:
    todo = [p for p in gate_roots() if p.endswith('.py')]
    seen: set[str] = set()
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        seen.add(p)
        src = read(p)
        todo.extend((_imports(src, p) | _named_py(src, p)) - seen)
    return sorted(seen)


_DATA_EXT = ('.json', '.yaml', '.yml', '.txt', '.md', '.html', '.css', '.js', '.toml', '.csv', '.sql')
# Above these, the flag-only part of a change is large enough that a person must read it (Michael fix 2).
REVIEW_NAMES, REVIEW_LINES, REVIEW_FILE_LINES = 5, 120, 60      # Michael 2026-11-10: total and per file


def data_inputs(py_files, read=lambda p: (ROOT / p).read_text(encoding='utf-8')) -> list[str]:
    """Michael fix 1: every NON-Python input of the gates, so no input falls between the two identity checks:
    the non-Python gate files, every file under omni_prod/ that is not Python (assets, catalogs, templates), and
    every repo file a module of the closure names in a string literal (a catalog it opens, a workflow it reads)."""
    out = {p for p in gate_roots() if not p.endswith('.py')}
    for f in (ROOT / 'omni_prod').rglob('*'):
        if f.is_file() and f.suffix != '.py' and '__pycache__' not in f.parts and f.suffix not in ('.pyc',):
            out.add(str(f.relative_to(ROOT)))
    for p in py_files:
        for rel in named_files(read(p), p):
            # omni_prod Python joins the AST closure; everything else named by a gate -- incl. tests/*.py or app.py it
            # reads by path -- is compared byte for byte (the any-suffix scan found 11 such files)
            if not (rel.endswith('.py') and rel.startswith('omni_prod/')):
                out.add(rel)
    return sorted(out)


def named_files(source: str, path: str) -> set[str]:
    """Every existing repo FILE a module names in a string literal, whatever its suffix (Michael fix 5: a skill YAML,
    a fixtures file, a template -- not only .py), scanned on the flag-stripped tree."""
    out = set()
    tree = ast.parse(source)
    for node in ast.walk(_Strip(_flag_only(tree)).visit(tree)):
        v = node.value if isinstance(node, ast.Constant) else None
        if not (isinstance(v, str) and 2 < len(v) < 160 and '\n' not in v and '.' in v.split('/')[-1]
                and not v.startswith(('http:', 'https:', '/'))):
            continue
        if v == '.git' or v.startswith('.git/'):
            continue  # never a gate input; in a git WORKTREE .git is a FILE and would pass is_file() (CI 2026-11-10)
        for cand in (ROOT / v, ROOT / 'omni_prod' / v, (ROOT / path).parent / v):
            try:
                if cand.is_file() and cand.resolve().is_relative_to(ROOT):
                    out.add(str(cand.resolve().relative_to(ROOT)))
                    break
            except (OSError, ValueError):
                break
    return out


def source_manifest(read=lambda p: (ROOT / p).read_text(encoding='utf-8'),
                    read_bytes=lambda p: (ROOT / p).read_bytes()) -> dict:
    """{path: sha256 of the stripped AST} for every Python file of the gate closure, {path: sha256 of the bytes} for
    every non-Python input, the flag-only names, and how much was stripped (reported, never silent)."""
    files, flag_only, used, stripped_stats = {}, {}, set(), {}
    py = closure(read)
    for p in py:
        st: dict = {}
        dump, only, refs = stripped(read(p), st)
        files[p] = hashlib.sha256(dump.encode('utf-8')).hexdigest()
        if only:
            flag_only[p] = sorted(only)
        if st.get('blocks'):
            stripped_stats[p] = st
        used |= refs
    data = {p: hashlib.sha256(read_bytes(p)).hexdigest() for p in data_inputs(py, read)}
    leaked = sorted(n for names in flag_only.values() for n in names if n in used)
    total = {'files': len(stripped_stats), 'blocks': sum(s['blocks'] for s in stripped_stats.values()),
             'lines': sum(s['lines'] for s in stripped_stats.values()),
             'names': sum(len(v) for v in flag_only.values())}
    heavy = sorted(p for p, s in stripped_stats.items() if s['lines'] > REVIEW_FILE_LINES)
    total['heavy_files'] = heavy
    total['needs_human_review'] = total['names'] > REVIEW_NAMES or total['lines'] > REVIEW_LINES or bool(heavy)
    return {'files': files, 'data': data, 'flag_only': flag_only, 'leaked_flag_only': leaked,
            'stripped': stripped_stats, 'stripped_total': total}


def digest() -> str:
    body = json.dumps(components(), ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(body.encode('utf-8')).hexdigest()


if __name__ == '__main__':
    import sys
    if sys.argv[1:] == ['--source']:
        print(json.dumps(source_manifest(), indent=1, sort_keys=True))
    else:
        print(digest())
