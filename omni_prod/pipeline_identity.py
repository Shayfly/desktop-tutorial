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
                kept = [self.visit(n) for n in value if self._keep(n)]
                setattr(node, field, kept or [ast.Pass()])
            elif isinstance(value, ast.AST):
                self.visit(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item)
        return node


def stripped(source: str) -> tuple[str, set[str], set[str]]:
    """(AST dump with flag additions removed, flag-only names, names still referenced after stripping)."""
    tree = ast.parse(source)
    flag_only = _flag_only(tree)
    tree = _Strip(flag_only).visit(tree)
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


def closure(read=lambda p: (ROOT / p).read_text(encoding='utf-8')) -> list[str]:
    todo = [p for p in gate_roots() if p.endswith('.py')]
    seen: set[str] = set()
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        seen.add(p)
        todo.extend(_imports(read(p), p) - seen)
    return sorted(seen)


def source_manifest(read=lambda p: (ROOT / p).read_text(encoding='utf-8')) -> dict:
    """{path: sha256 of the stripped AST (Python) or of the bytes (other gate files)}, plus the flag-only names."""
    files, flag_only, used = {}, {}, set()
    for p in closure(read):
        dump, only, refs = stripped(read(p))
        files[p] = hashlib.sha256(dump.encode('utf-8')).hexdigest()
        if only:
            flag_only[p] = sorted(only)
        used |= refs
    for p in gate_roots():
        if not p.endswith('.py'):
            files[p] = hashlib.sha256(read(p).encode('utf-8')).hexdigest()
    leaked = sorted(n for names in flag_only.values() for n in names if n in used)
    return {'files': files, 'flag_only': flag_only, 'leaked_flag_only': leaked}


def digest() -> str:
    body = json.dumps(components(), ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(body.encode('utf-8')).hexdigest()


if __name__ == '__main__':
    import sys
    if sys.argv[1:] == ['--source']:
        print(json.dumps(source_manifest(), indent=1, sort_keys=True))
    else:
        print(digest())
